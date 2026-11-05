#include "pluginterfaces/base/ipluginbase.h"
#include "pluginterfaces/vst/ivstcomponent.h"
#include "pluginterfaces/vst/ivstaudioprocessor.h"
#include "pluginterfaces/vst/ivstmessage.h"
#include "public.sdk/source/vst/hosting/hostclasses.h"
#include "public.sdk/source/common/memorystream.h"
#include "AssetState.h"
#include <windows.h>
#include <cstdint>
#include <cstring>
#include <iostream>
using namespace Steinberg;
using namespace Steinberg::Vst;

static bool check(bool ok,const char* label) {
    std::cout<<(ok?"PASS: ":"FAIL: ")<<label<<"\n";
    return ok;
}
static bool snapshotBank(IComponent* component,uint16_t& bank) {
    MemoryStream stream;
    if(component->getState(&stream)!=kResultOk)return false;
    if(stream.seek(0,IBStream::kIBSeekSet,nullptr)!=kResultOk)return false;
    AWE125::AssetState::Data data;
    const auto read=[&](void* dst,size_t count) {
        int32 received=0;
        return count<=AWE125::AssetState::kMaxPath &&
            stream.read(dst,static_cast<int32>(count),&received)==kResultOk &&
            static_cast<size_t>(received)==count;
    };
    if(!AWE125::AssetState::Read(read,data))return false;
    bank=static_cast<uint16_t>(data.bank);
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
