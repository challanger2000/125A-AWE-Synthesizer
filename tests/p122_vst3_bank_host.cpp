#include "pluginterfaces/base/ipluginbase.h"
#include "pluginterfaces/vst/ivstcomponent.h"
#include "pluginterfaces/vst/ivstaudioprocessor.h"
#include "pluginterfaces/vst/ivstmessage.h"
#include "public.sdk/source/vst/hosting/hostclasses.h"
#include "public.sdk/source/vst/hosting/parameterchanges.h"
#include "public.sdk/source/common/memorystream.h"
#include "AssetState.h"
#include "MidiControlMapping.h"
#include "MidiProgramRouting.h"
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
static bool makeRecall(IBStream& stream,uint32_t bank=0,uint32_t program=0) {
    AWE125::AssetState::Data state;
    state.pathsSpecified=true;
    state.bank=bank;
    state.program=program;
    for(auto& p:state.channelPrograms)p=program;
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
            // P126 reverse direction: recall starts FIRST but finishes
            // AFTER an ordinary bank-5 parameter point was accepted and
            // saved. P125 only protected the inverse paused-audio schedule.
            MemoryStream normalizeZero;
            ok&=check(makeRecall(normalizeZero) &&
                      component->setState(&normalizeZero)==kResultOk &&
                      audio->process(data)==kResultOk,
                      "P126 start reverse-order probe with bank-zero recall");
            PausedStateStream reverseRecall;
            const bool reverseReady=makeRecall(reverseRecall);
            ok&=check(reverseReady,"P126 prepare paused original bank-zero recall");
            if(reverseReady) {
                reverseRecall.pauseOnRead.store(true,std::memory_order_release);
                std::atomic<bool> reverseOk{false};
                std::thread blockedRecall([&]{
                    reverseOk.store(component->setState(&reverseRecall)==kResultOk,
                                    std::memory_order_release);
                });
                while(!reverseRecall.entered.load(std::memory_order_acquire))
                    std::this_thread::yield();
                ParameterChanges bank5(1);
                int32 ix=0,pi=0;
                auto* q=bank5.addParameterData(ParamID(1002),ix);
                ProcessData laterParam{};
                laterParam.processMode=kRealtime;
                laterParam.symbolicSampleSize=kSample32;
                laterParam.numSamples=0;
                laterParam.inputParameterChanges=&bank5;
                const bool accepted=q&&q->addPoint(0,5./16383.,pi)==kResultOk &&
                                    audio->process(laterParam)==kResultOk;
                uint16_t beforeEnd=999,afterEnd=999,following=999;
                const bool savedDuring=accepted&&snapshotBank(component,beforeEnd);
                reverseRecall.releaseRead.store(true,std::memory_order_release);
                blockedRecall.join();
                const bool savedAfter=reverseOk.load()&&
                                      snapshotBank(component,afterEnd);
                const bool next=audio->process(data)==kResultOk &&
                                snapshotBank(component,following);
                ok&=check(savedDuring&&beforeEnd==5&&savedAfter&&afterEnd==5&&
                          next&&following==5,
                          "slow earlier recall 0 cannot erase later saved bank 5 parameter");
                MemoryStream newerRecall;
                ok&=check(makeRecall(newerRecall) &&
                          component->setState(&newerRecall)==kResultOk &&
                          audio->process(data)==kResultOk &&
                          snapshotBank(component,bank)&&bank==0,
                          "genuinely later bank-zero recall still supersedes bank 5");
            }
            // CC0 belongs to one MIDI channel. It must never suppress or
            // acknowledge a new GLOBAL browser selection for the others.
            ParameterChanges channelBank(1);
            int32 ccIndex=0,ccPoint=0;
            auto* cc=channelBank.addParameterData(
                AWE125::MidiControlMapping::ParamID(2,
                    AWE125::MidiControlMapping::Index(0)),ccIndex);
            ProcessData ccBlock{};
            ccBlock.processMode=kRealtime;
            ccBlock.symbolicSampleSize=kSample32;
            ccBlock.numSamples=0;
            ccBlock.inputParameterChanges=&channelBank;
            ok&=check(cc&&cc->addPoint(0,5./127.,ccPoint)==kResultOk &&
                      audio->process(ccBlock)==kResultOk &&
                      sendBank(connection,9)==kResultOk &&
                      audio->process(data)==kResultOk &&
                      snapshotBank(component,bank)&&bank==9,
                      "channel-3 CC0 cannot discard newer global browser bank 9");
            // P127 F01: two actual overlapping setState() calls. An old
            // paused bank-0 recall must not replace a NEWER completed bank-5
            // recall, including saved state and following block.
            MemoryStream f01Base;
            ok&=check(makeRecall(f01Base,0,0) &&
                      component->setState(&f01Base)==kResultOk &&
                      audio->process(data)==kResultOk,
                      "P127 prepare overlapping-recall test at bank 0");
            PausedStateStream oldProject;
            bool oldReady=makeRecall(oldProject,0,0);
            ok&=check(oldReady,"P127 serialize older bank-zero recall");
            if(oldReady) {
                oldProject.pauseOnRead.store(true,std::memory_order_release);
                std::atomic<tresult> oldResult{kResultOk};
                std::thread older([&] {
                    oldResult.store(component->setState(&oldProject),
                                    std::memory_order_release);
                });
                while(!oldProject.entered.load(std::memory_order_acquire))
                    std::this_thread::yield();
                MemoryStream newer;
                const bool newerOk=makeRecall(newer,5,9) &&
                    component->setState(&newer)==kResultOk;
                AWE125::AssetState::Data afterNew{};
                const bool observedNew=snapshotState(component,afterNew);
                oldProject.releaseRead.store(true,std::memory_order_release);
                older.join();
                AWE125::AssetState::Data afterOld{},afterFollow{};
                const bool oldSaved=snapshotState(component,afterOld);
                const bool forward=audio->process(data)==kResultOk &&
                    snapshotState(component,afterFollow);
                ok&=check(newerOk&&observedNew&&oldSaved&&forward &&
                          afterNew.bank==5&&afterNew.program==9 &&
                          afterOld.bank==5&&afterOld.program==9 &&
                          afterFollow.bank==5&&afterFollow.program==9 &&
                          oldResult.load()!=kResultOk,
                          "P127 older paused recall rejected, newer bank/program 5/9 retained");
            }
            // P127 F07: genuine host bank+program pair chosen while a
            // previous project recall is paused in IBStream::read.
            MemoryStream f07Base;
            ok&=check(makeRecall(f07Base,0,0) &&
                      component->setState(&f07Base)==kResultOk &&
                      audio->process(data)==kResultOk,
                      "P127 prepare late preset-pair selection");
            PausedStateStream slowPresetRecall;
            bool slowPresetReady=makeRecall(slowPresetRecall,0,0);
            ok&=check(slowPresetReady,"P127 serialize old bank0/program0 recall");
            if(slowPresetReady) {
                slowPresetRecall.pauseOnRead.store(true,std::memory_order_release);
                std::atomic<bool> slowPresetOk{false};
                std::thread earlier([&] {
                    slowPresetOk.store(component->setState(&slowPresetRecall)==kResultOk,
                                       std::memory_order_release);
                });
                while(!slowPresetRecall.entered.load(std::memory_order_acquire))
                    std::this_thread::yield();
                ParameterChanges presetEdits(2);
                int32 bidx=0,pidx=0,bpoint=0,ppoint=0;
                auto* qb=presetEdits.addParameterData(ParamID(1002),bidx);
                auto* qp=presetEdits.addParameterData(ParamID(1000),pidx);
                const bool editsReady=qb&&qp &&
                    qb->addPoint(0,5./16383.,bpoint)==kResultOk &&
                    qp->addPoint(0,9./127.,ppoint)==kResultOk;
                ProcessData presetFlush{};
                presetFlush.processMode=kRealtime;
                presetFlush.symbolicSampleSize=kSample32;
                presetFlush.numSamples=0;
                presetFlush.inputParameterChanges=&presetEdits;
                const bool applied=editsReady&&audio->process(presetFlush)==kResultOk;
                slowPresetRecall.releaseRead.store(true,std::memory_order_release);
                earlier.join();
                AWE125::AssetState::Data p{},again{};
                const bool saved=snapshotState(component,p);
                const bool follow=audio->process(data)==kResultOk&&
                    snapshotState(component,again);
                bool channels=true;
                for(auto n:p.channelPrograms)if(n!=9)channels=false;
                ok&=check(applied&&slowPresetOk.load()&&saved&&follow&&
                          p.bank==5&&p.program==9&&p.channelProgramMask==0&&
                          channels&&again.bank==5&&again.program==9,
                          "P127 complete later preset 5/9 survives earlier recall");
            }
            // P128: channel override accepted after an older recall START
            // must survive its later commit; an accepted program tuple is
            // authoritative even if the recall finishes afterwards.
            MemoryStream channelBase;
            ok&=check(makeRecall(channelBase,0,0) &&
                      component->setState(&channelBase)==kResultOk &&
                      audio->process(data)==kResultOk,
                      "P128 prepare channel-program recall overlap");
            PausedStateStream oldChannelRecall;
            const bool channelReady=makeRecall(oldChannelRecall,0,0);
            ok&=check(channelReady,"P128 serialize paused channel recall");
            if(channelReady) {
                oldChannelRecall.pauseOnRead.store(true,std::memory_order_release);
                std::atomic<tresult> recallResult{kResultFalse};
                std::thread prior([&] {
                    recallResult.store(component->setState(&oldChannelRecall),
                                       std::memory_order_release);
                });
                while(!oldChannelRecall.entered.load(std::memory_order_acquire))
                    std::this_thread::yield();
                ParameterChanges programEdits(3);
                int32 ix0=0,ix1=0,ix2=0,pt0=0,pt1=0,pt2=0;
                auto* global=programEdits.addParameterData(ParamID(1000),ix0);
                auto* ch1=programEdits.addParameterData(
                    AWE125::MidiProgramRouting::ParamID(0),ix1);
                auto* ch2=programEdits.addParameterData(
                    AWE125::MidiProgramRouting::ParamID(1),ix2);
                const bool edits=global&&ch1&&ch2 &&
                    global->addPoint(0,9./127.,pt0)==kResultOk &&
                    ch1->addPoint(0,11./127.,pt1)==kResultOk &&
                    ch2->addPoint(0,10./127.,pt2)==kResultOk;
                ProcessData flush{};
                flush.processMode=kRealtime;
                flush.symbolicSampleSize=kSample32;
                flush.numSamples=0;
                flush.inputParameterChanges=&programEdits;
                const bool accepted=edits&&audio->process(flush)==kResultOk;
                oldChannelRecall.releaseRead.store(true,std::memory_order_release);
                prior.join();
                AWE125::AssetState::Data channelState{};
                const bool recovered=audio->process(data)==kResultOk &&
                    snapshotState(component,channelState);
                ok&=check(accepted&&recallResult.load()==kResultOk&&recovered &&
                          channelState.program==9&&
                          (channelState.channelProgramMask&3u)==3u&&
                          channelState.channelPrograms[0]==11&&
                          channelState.channelPrograms[1]==10,
                          "P128 later channel program edits survive earlier recall");
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
