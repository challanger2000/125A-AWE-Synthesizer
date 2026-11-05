#include "pluginterfaces/base/ipluginbase.h"
#include "pluginterfaces/vst/ivstcomponent.h"
#include "pluginterfaces/vst/ivstaudioprocessor.h"
#include "pluginterfaces/vst/ivstmessage.h"
#include "public.sdk/source/vst/hosting/hostclasses.h"
#include "public.sdk/source/vst/hosting/parameterchanges.h"
#include "public.sdk/source/common/memorystream.h"
#include "AssetState.h"
#include <windows.h>
#include <atomic>
#include <thread>
#include <cstdint>
#include <cstring>
#include <iostream>
using namespace Steinberg;
using namespace Steinberg::Vst;

// Deterministic race: pause inside the actual getState-compatible V10
// IBStream::read so a newer processor bank message is accepted while an
// older project recall has already begun.
class PausedStateStream final : public MemoryStream {
public:
    std::atomic<bool> pauseOnRead{false}, entered{false}, releaseRead{false};
    tresult PLUGIN_API read(void* data,int32 length,int32* received) override {
        if(pauseOnRead.load(std::memory_order_acquire) &&
           !entered.exchange(true,std::memory_order_acq_rel)) {
            while(!releaseRead.load(std::memory_order_acquire))
                std::this_thread::yield();
        }
        return MemoryStream::read(data,length,received);
    }
};

// Reproduce the inverse P124 race: process() has observed an old bank
// generation, then waits in a host queue getter. A complete project recall
// publishes bank 0; only afterwards the blocked callback accepts bank 5.
class PausedParameterChanges final : public ParameterChanges {
public:
    explicit PausedParameterChanges(int32 n): ParameterChanges(n) {}
    std::atomic<bool> entered{false},releaseRead{false};
    int32 PLUGIN_API getParameterCount() override {
        entered.store(true,std::memory_order_release);
        while(!releaseRead.load(std::memory_order_acquire))
            std::this_thread::yield();
        return ParameterChanges::getParameterCount();
    }
};
static bool check(bool ok,const char* label) {
    std::cout<<(ok?"PASS: ":"FAIL: ")<<label<<"\n";
    return ok;
}
static bool snapshotState(IComponent* component,
                          AWE125::AssetState::Data& data) {
    MemoryStream stream;
    if(component->getState(&stream)!=kResultOk)return false;
    if(stream.seek(0,IBStream::kIBSeekSet,nullptr)!=kResultOk)return false;
    const auto read=[&](void* dst,size_t count) {
        int32 received=0;
        return count<=AWE125::AssetState::kMaxPath &&
            stream.read(dst,static_cast<int32>(count),&received)==kResultOk &&
            static_cast<size_t>(received)==count;
    };
    return AWE125::AssetState::Read(read,data);
}
static bool snapshotBank(IComponent* component,uint16_t& bank) {
    AWE125::AssetState::Data state;
    if(!snapshotState(component,state))return false;
    bank=static_cast<uint16_t>(state.bank);
    return true;
}
static bool makeRecall(IBStream& stream,uint32_t bank=0) {
    AWE125::AssetState::Data state;
    state.pathsSpecified=true;
    state.bank=bank;
    state.program=0;
    for(auto& p:state.channelPrograms)p=0;
    const auto write=[&](const void* data,size_t count) {
        int32 written=0;
        return count<=AWE125::AssetState::kMaxPath &&
            stream.write(const_cast<void*>(data),static_cast<int32>(count),
                         &written)==kResultOk &&
            written==static_cast<int32>(count);
    };
    return AWE125::AssetState::Write(write,state) &&
           stream.seek(0,IBStream::kIBSeekSet,nullptr)==kResultOk;
}
static tresult sendBank(IConnectionPoint* connection,int64 bank) {
    auto* message=new HostMessage;
    message->setMessageID("125A_BROWSER_BANK_RESELECT");
    message->getAttributes()->setInt("Bank",bank);
    const tresult result=connection->notify(message);
    message->release();
    return result;
}
int wmain(int argc,wchar_t** argv) {
    if(argc!=2)return 2;
    const HMODULE dll=LoadLibraryW(argv[1]);
    if(!dll)return 2;
    using FactoryFn=IPluginFactory*(*)();
    auto fn=reinterpret_cast<FactoryFn>(GetProcAddress(dll,"GetPluginFactory"));
    if(!fn){FreeLibrary(dll);return 2;}
    auto* factory=fn();
    IComponent* component=nullptr;
    for(int32 index=0;index<factory->countClasses();++index) {
        PClassInfo info{};
        if(factory->getClassInfo(index,&info)!=kResultOk ||
           std::strcmp(info.category,kVstAudioEffectClass)!=0)continue;
        if(factory->createInstance(info.cid,IComponent::iid,
               reinterpret_cast<void**>(&component))==kResultOk)break;
    }
    bool ok=check(component!=nullptr,"real VST3 processor factory instance");
    if(component) {
        const bool initialized=component->initialize(nullptr)==kResultOk;
        ok&=check(initialized,"processor initializes");
        IAudioProcessor* audio=nullptr;
        IConnectionPoint* connection=nullptr;
        ok&=check(component->queryInterface(IAudioProcessor::iid,
               reinterpret_cast<void**>(&audio))==kResultOk && audio,
               "real IAudioProcessor exposed");
        ok&=check(component->queryInterface(IConnectionPoint::iid,
               reinterpret_cast<void**>(&connection))==kResultOk && connection,
               "real IConnectionPoint exposed");
        if(initialized && audio && connection) {
            ProcessSetup setup{};
            setup.processMode=kRealtime;
            setup.symbolicSampleSize=kSample32;
            setup.sampleRate=44100.;
            setup.maxSamplesPerBlock=128;
            ok&=check(audio->setupProcessing(setup)==kResultOk,
                       "processor configured at 44.1 kHz");
            ok&=check(audio->getTailSamples()==kInfiniteTail,
                       "sounding synth reports a nonzero unbounded tail");
            uint16_t bank=999;
            ok&=check(snapshotBank(component,bank)&&bank==0,
                       "initial bank persists as zero");
            ok&=check(sendBank(connection,128)==kResultOk,
                       "reselect bank message is accepted by real plugin");
            ProcessData data{};
            data.processMode=kRealtime;
            data.symbolicSampleSize=kSample32;
            data.numSamples=0; // legal VST3 parameter-flush block, no ROM needed
            ok&=check(audio->process(data)==kResultOk,
                       "real zero-sample processor flush consumes bank command");
            ok&=check(snapshotBank(component,bank)&&bank==128,
                       "message selected bank 128 in processor state");
            ok&=check(sendBank(connection,128)==kResultOk &&
                       audio->process(data)==kResultOk &&
                       snapshotBank(component,bank)&&bank==128,
                       "repeated same-bank command accepted without automation");
            ok&=check(sendBank(connection,16384)==kInvalidArgument &&
                       snapshotBank(component,bank)&&bank==128,
                       "out-of-range bank rejected without mutation");
            ok&=check(sendBank(connection,0)==kResultOk &&
                       audio->process(data)==kResultOk &&
                       snapshotBank(component,bank)&&bank==0,
                       "bank zero can be reselected without parameter queue");
            // P124: pause an older setState() in its real stream reader.
            // A later accepted bank 5 must survive once recall completes.
            PausedStateStream paused;
            ok&=check(makeRecall(paused),"prepare real V10 recall bank zero");
            paused.pauseOnRead.store(true,std::memory_order_release);
            std::atomic<bool> recallSucceeded{false};
            std::thread slowRecall([&] {
                recallSucceeded.store(component->setState(&paused)==kResultOk,
                                       std::memory_order_release);
            });
            while(!paused.entered.load(std::memory_order_acquire))
                std::this_thread::yield();
            ok&=check(sendBank(connection,5)==kResultOk,
                       "new bank 5 accepted after old recall has started");
            paused.releaseRead.store(true,std::memory_order_release);
            slowRecall.join();
            ok&=check(recallSucceeded.load() &&
                      audio->process(data)==kResultOk &&
                      snapshotBank(component,bank) && bank==5,
                       "real VST3 older recall cannot replace later accepted bank 5");
            // An older pending browser command *should* be overridden when
            // a recall actually starts after it.
            MemoryStream plainRecall;
            ok&=check(makeRecall(plainRecall),"prepare newer bank-zero recall");
            ok&=check(sendBank(connection,7)==kResultOk &&
                      component->setState(&plainRecall)==kResultOk &&
                      audio->process(data)==kResultOk &&
                      snapshotBank(component,bank) && bank==0,
                       "new V10 recall overrides previously queued bank 7");
            // P125: prior real VST3 tests paused the RECALL, not process().
            // Here process() begins before recall, and bank 5 arrives through
            // the ordinary kBankID parameter path AFTER the recall commits.
            PausedParameterChanges delayedBank(1);
            int32 bankIndex=0,pointIndex=0;
            auto* bankQueue=delayedBank.addParameterData(ParamID(1002),bankIndex);
            const bool queuedBank5=bankQueue &&
                bankQueue->addPoint(64,5.0/16383.0,pointIndex)==kResultOk;
            ok&=check(queuedBank5,"enqueue later bank 5 at sample 64");
            if(queuedBank5) {
                ProcessData delayedBlock{};
                delayedBlock.processMode=kRealtime;
                delayedBlock.symbolicSampleSize=kSample32;
                delayedBlock.numSamples=128;
                delayedBlock.inputParameterChanges=&delayedBank;
                std::atomic<bool> callbackOk{false};
                std::thread blockedAudio([&] {
                    callbackOk.store(audio->process(delayedBlock)==kResultOk,
                                     std::memory_order_release);
                });
                while(!delayedBank.entered.load(std::memory_order_acquire))
                    std::this_thread::yield();
                MemoryStream midBlockRecall;
                const bool recallReady=makeRecall(midBlockRecall);
                const bool midRecallOk=recallReady &&
                    component->setState(&midBlockRecall)==kResultOk;
                delayedBank.releaseRead.store(true,std::memory_order_release);
                blockedAudio.join();
                uint16_t afterFirst=999,afterSecond=999;
                const bool firstSave=snapshotBank(component,afterFirst);
                const bool followingBlock=audio->process(data)==kResultOk;
                const bool secondSave=snapshotBank(component,afterSecond);
                ok&=check(midRecallOk&&callbackOk.load()&&firstSave &&
                          followingBlock&&secondSave &&
                          afterFirst==5&&afterSecond==5,
                          "mid-block recall bank 0 cannot undo later parameter bank 5 in next block");
                // Intentional later bank-zero automation must still work;
                // the fix must not turn bank selection into a sticky lock.
                ParameterChanges backToZero(1);
                int32 idx=0,pnt=0;
                auto* q=backToZero.addParameterData(ParamID(1002),idx);
                ProcessData turnBack{};
                turnBack.processMode=kRealtime;
                turnBack.symbolicSampleSize=kSample32;
                turnBack.numSamples=0;
                turnBack.inputParameterChanges=&backToZero;
                ok&=check(q&&q->addPoint(0,0.,pnt)==kResultOk &&
                          audio->process(turnBack)==kResultOk &&
                          snapshotBank(component,bank)&&bank==0,
                          "newer deliberate bank-zero parameter remains effective");
            }
            // A true exported VST3 processor concurrently receives rapid
            // program-change parameter queues and getState() calls.
            // The host must never serialize a mixture of two programs.
            std::atomic<bool> finished{false},writerOk{true};
            std::thread writer([&] {
                for(int n=0;n<1500;++n) {
                    ParameterChanges params(1);
                    int32 index=0,pointIndex=0;
                    auto* const q=params.addParameterData(ParamID(1000),index);
                    if(!q||q->addPoint(0,double(n%128)/127.,pointIndex)!=kResultOk) {
                        writerOk.store(false);
                        break;
                    }
                    ProcessData flush{};
                    flush.processMode=kRealtime;
                    flush.symbolicSampleSize=kSample32;
                    flush.numSamples=0;
                    flush.inputParameterChanges=&params;
                    if(audio->process(flush)!=kResultOk) {
                        writerOk.store(false);
                        break;
                    }
                }
                finished.store(true,std::memory_order_release);
            });
            bool coherent=true;
            int successfulReads=0;
            for(int i=0;i<3000;++i) {
                AWE125::AssetState::Data state;
                if(snapshotState(component,state)) {
                    ++successfulReads;
                    if(state.channelProgramMask!=0)coherent=false;
                    for(const auto program:state.channelPrograms)
                        if(program!=state.program)coherent=false;
                }
                if(finished.load(std::memory_order_acquire)&&i>=100)
                    break;
            }
            writer.join();
            AWE125::AssetState::Data final;
            const bool finalOk=snapshotState(component,final) &&
                final.channelProgramMask==0 &&
                final.program==1499%128;
            if(finalOk)for(const auto program:final.channelPrograms)
                if(program!=final.program)coherent=false;
            ok&=check(writerOk.load()&&finalOk&&coherent,
                "real VST3 getState never combines distinct program automation states");
            ok&=check(successfulReads>0,
                "real VST3 state snapshots succeed while program automation is running");

            // P123 regression: original P122 tested only ONE audio writer.
            // A second setState() writer must not leave half 7/half 9 in
            // the real exported processor, even after both calls end.
            auto recallNine=[&]()->bool {
                AWE125::AssetState::Data candidate;
                candidate.pathsSpecified=true;
                candidate.program=9;
                candidate.bank=9;
                candidate.channelProgramMask=0;
                for(auto& ch:candidate.channelPrograms)ch=9;
                MemoryStream stateBytes;
                const auto write=[&](const void* source,size_t count) {
                    int32 written=0;
                    return count<=AWE125::AssetState::kMaxPath &&
                        stateBytes.write(const_cast<void*>(source),
                            static_cast<int32>(count),&written)==kResultOk &&
                        written==static_cast<int32>(count);
                };
                if(!AWE125::AssetState::Write(write,candidate))return false;
                if(stateBytes.seek(0,IBStream::kIBSeekSet,nullptr)!=kResultOk)
                    return false;
                return component->setState(&stateBytes)==kResultOk;
            };
            std::atomic<bool> recallStart{false},recallOk{true},realtimeOk{true};
            std::thread audioProgram([&] {
                while(!recallStart.load(std::memory_order_acquire))
                    std::this_thread::yield();
                for(int i=0;i<2500;++i) {
                    ParameterChanges params(1);
                    int32 index=0,pointIndex=0;
                    auto* q=params.addParameterData(ParamID(1000),index);
                    if(!q || q->addPoint(0,7.0/127.0,pointIndex)!=kResultOk) {
                        realtimeOk.store(false);
                        break;
                    }
                    ProcessData flush{};
                    flush.processMode=kRealtime;
                    flush.symbolicSampleSize=kSample32;
                    flush.numSamples=0;
                    flush.inputParameterChanges=&params;
                    if(audio->process(flush)!=kResultOk) {
                        realtimeOk.store(false);
                        break;
                    }
                }
            });
            std::thread projectRecall([&] {
                recallStart.store(true,std::memory_order_release);
                for(int i=0;i<2500;++i)
                    if(!recallNine()) {recallOk.store(false);break;}
            });
            bool allCoherent=true;
            int reads=0;
            for(int i=0;i<6000;++i) {
                AWE125::AssetState::Data state;
                if(!snapshotState(component,state))continue;
                ++reads;
                if(state.channelProgramMask!=0)allCoherent=false;
                for(const auto v:state.channelPrograms)
                    if(v!=state.program)allCoherent=false;
            }
            audioProgram.join();
            projectRecall.join();
            AWE125::AssetState::Data last{};
            if(!snapshotState(component,last))allCoherent=false;
            for(const auto v:last.channelPrograms)
                if(v!=last.program)allCoherent=false;
            ok&=check(recallOk.load()&&realtimeOk.load()&&allCoherent&&reads>0,
                "real VST3 parallel setState/process/getState has no mixed channel programs");

            // Ordinary playback without automation must allow ALL host saves.
            // A synthetic/no-ROM instance exercises host state concurrency.
            // The sounding original-ROM scenario remains a separate QA gate.
            ok&=check(component->setActive(true)==kResultOk,
                "real VST3 processor activated for playback-save stress");
            ok&=check(audio->setProcessing(true)==kResultOk,
                "strict VST3 host: begin processing after activation");
            std::atomic<bool> playbackOk{true},started{false};
            std::thread playback([&] {
                ProcessData play{};
                play.processMode=kRealtime;
                play.symbolicSampleSize=kSample32;
                play.numSamples=128;
                started.store(true,std::memory_order_release);
                for(int i=0;i<15000;++i)
                    if(audio->process(play)!=kResultOk) {
                        playbackOk.store(false);
                        break;
                    }
            });
            while(!started.load(std::memory_order_acquire))
                std::this_thread::yield();
            int validSaves=0;
            for(int i=0;i<500;++i) {
                AWE125::AssetState::Data save;
                if(snapshotState(component,save))++validSaves;
            }
            playback.join();
            ok&=check(playbackOk.load()&&validSaves==500,
                "500/500 genuine getState calls succeed during no-automation playback");
            ok&=check(audio->setProcessing(false)==kResultOk,
                "strict VST3 host: stop processing succeeds");
            ok&=check(audio->setProcessing(true)==kResultOk &&
                      audio->setProcessing(false)==kResultOk &&
                      audio->setProcessing(true)==kResultOk,
                "legal start-stop-start sequence without intervening process");
            ProcessData resumed{};
            resumed.processMode=kRealtime;
            resumed.symbolicSampleSize=kSample32;
            resumed.numSamples=0;
            ok&=check(audio->process(resumed)==kResultOk &&
                      audio->setProcessing(false)==kResultOk,
                "strict host resumes zero-frame flush then stops");
            ok&=check(component->setActive(false)==kResultOk,
                "real VST3 deactivation after processing stop");
        }
        if(connection)connection->release();
        if(audio)audio->release();
        if(initialized)component->terminate();
        component->release();
    }
    factory->release();
    FreeLibrary(dll);
    std::cout<<(ok?"P122_REAL_VST3_BANK_HOST_PASS":
                   "P122_REAL_VST3_BANK_HOST_FAIL")<<"\n";
    return ok?0:1;
}
