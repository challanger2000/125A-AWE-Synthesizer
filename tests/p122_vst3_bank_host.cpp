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
