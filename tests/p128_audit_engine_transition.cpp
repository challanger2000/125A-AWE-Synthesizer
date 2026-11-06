// Independent P128 audit fixture. Never uses proprietary Creative ROM bytes.
// Drives the *real* exported Windows VST3 processor; no product-code hooks.
#include "pluginterfaces/base/ipluginbase.h"
#include "pluginterfaces/vst/ivstcomponent.h"
#include "pluginterfaces/vst/ivstaudioprocessor.h"
#include "pluginterfaces/vst/ivstevents.h"
#include "public.sdk/source/common/memorystream.h"
#include "AssetState.h"
#include <windows.h>
#include <array>
#include <atomic>
#include <chrono>
#include <cstring>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <thread>
#include <vector>
using namespace Steinberg;
using namespace Steinberg::Vst;

class PausedEvents final : public IEventList {
public:
    std::atomic<bool> entered{false}, resume{false};
    tresult PLUGIN_API queryInterface(const TUID,void** obj) override {
        if(obj)*obj=nullptr;
        return kNoInterface;
    }
    uint32 PLUGIN_API addRef() override {return 1;}
    uint32 PLUGIN_API release() override {return 1;}
    int32 PLUGIN_API getEventCount() override {
        entered.store(true,std::memory_order_release);
        while(!resume.load(std::memory_order_acquire))
            std::this_thread::yield(); // test host only
        return 1;
    }
    tresult PLUGIN_API getEvent(int32 index,Event& event) override {
        if(index!=0)return kResultFalse;
        event={};
        event.type=Event::kNoteOnEvent;
        event.sampleOffset=64;
        event.noteOn.channel=0;
        event.noteOn.pitch=60;
        event.noteOn.velocity=0.7f;
        return kResultOk;
    }
    tresult PLUGIN_API addEvent(Event&) override {return kResultFalse;}
};

static bool writeState(IComponent* c,const AWE125::AssetState::Data& state) {
    MemoryStream bytes;
    const auto write=[&](const void* src,size_t n) {
        int32 wrote=0;
        return n<=AWE125::AssetState::kMaxPath &&
               bytes.write(const_cast<void*>(src),static_cast<int32>(n),&wrote)==kResultOk &&
               wrote==static_cast<int32>(n);
    };
    return AWE125::AssetState::Write(write,state) &&
           bytes.seek(0,IBStream::kIBSeekSet,nullptr)==kResultOk &&
           c->setState(&bytes)==kResultOk;
}

// Windows SEH isolation: catch precisely an access violation from process().
// This helper has no C++ objects requiring exception unwinding.
static int guardedProcess(IAudioProcessor* audio,ProcessData* data) {
    __try {
        return audio->process(*data)==kResultOk?0:2;
    } __except(GetExceptionCode()==EXCEPTION_ACCESS_VIOLATION
               ? EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH) {
        return 100;
    }
}

int wmain(int argc,wchar_t** argv) {
    if(argc!=2)return 2;
    const HMODULE module=LoadLibraryW(argv[1]);
    if(!module)return 3;
    using FactoryFn=IPluginFactory*(*)();
    const auto fn=reinterpret_cast<FactoryFn>(GetProcAddress(module,"GetPluginFactory"));
    if(!fn)return 4;
    auto* factory=fn();
    IComponent* component=nullptr;
    for(int32 i=0;i<factory->countClasses();++i) {
        PClassInfo info{};
        if(factory->getClassInfo(i,&info)!=kResultOk ||
           std::strcmp(info.category,kVstAudioEffectClass)!=0)continue;
        if(factory->createInstance(info.cid,IComponent::iid,
               reinterpret_cast<void**>(&component))==kResultOk)break;
    }
    if(!component||component->initialize(nullptr)!=kResultOk)return 5;
    IAudioProcessor* audio=nullptr;
    if(component->queryInterface(IAudioProcessor::iid,
             reinterpret_cast<void**>(&audio))!=kResultOk||!audio)return 6;
    ProcessSetup setup{};
    setup.processMode=kRealtime;
    setup.symbolicSampleSize=kSample32;
    setup.sampleRate=44100.;
    setup.maxSamplesPerBlock=128;
    if(audio->setupProcessing(setup)!=kResultOk)return 7;

    // Valid-size but wholly synthetic 1-MiB test ROM. No proprietary ROM
    // or copyrighted SoundFont is used or shipped.
    auto rom=std::filesystem::temp_directory_path()/
        ("125A-P128-audit-synthetic-"+std::to_string(GetCurrentProcessId())+".raw");
    {
        std::ofstream out(rom,std::ios::binary|std::ios::trunc);
        std::vector<char> zero(1048576,0);
        out.write(zero.data(),static_cast<std::streamsize>(zero.size()));
        if(!out.good())return 8;
    }
    AWE125::AssetState::Data withEngine;
    withEngine.pathsSpecified=true;
    withEngine.romPath=rom.string();
    if(!writeState(component,withEngine))return 9;
    if(component->setActive(true)!=kResultOk)return 10;
    if(audio->getLatencySamples()==0) {
        std::cerr<<"INCONCLUSIVE: synthetic ROM did not activate the 86Box engine\n";
        return 11;
    }
    if(audio->setProcessing(true)!=kResultOk)return 12;
    PausedEvents events;
    std::array<float,128> l{},r{};
    float* ptrs[2]{l.data(),r.data()};
    AudioBusBuffers bus{};
    bus.numChannels=2;
    bus.channelBuffers32=ptrs;
    ProcessData data{};
    data.processMode=kRealtime;
    data.symbolicSampleSize=kSample32;
    data.numSamples=128;
    data.numOutputs=1;
    data.outputs=&bus;
    data.inputEvents=&events;

    // Positive control: the synthetic engine must process one complete
    // 128-frame block before any concurrent transition is introduced.
    events.resume.store(true,std::memory_order_release);
    if(guardedProcess(audio,&data)!=0)return 13;
    events.entered.store(false,std::memory_order_release);
    events.resume.store(false,std::memory_order_release);

    std::atomic<int> result{-1};
    std::thread callback([&]{result.store(guardedProcess(audio,&data));});
    const auto limit=std::chrono::steady_clock::now()+std::chrono::seconds(10);
    while(!events.entered.load(std::memory_order_acquire) &&
          std::chrono::steady_clock::now()<limit)
        std::this_thread::yield();
    if(!events.entered.load(std::memory_order_acquire)) {
        events.resume.store(true,std::memory_order_release);
        callback.join();
        return 14;
    }

    // At this point the plugin has captured a non-null engine and computed
    // canRender=true but has not yet observed MIDI events at sample 64.
    // A newer, valid project recall publishes a null engine.
    AWE125::AssetState::Data noEngine;
    noEngine.pathsSpecified=true;
    const bool unloaded=writeState(component,noEngine);
    std::cout<<"P128_AUDIT: active engine -> null publication after canRender, before MIDI event\n";
    std::cout.flush();
    events.resume.store(true,std::memory_order_release);
    callback.join();
    if(!unloaded)return 15;
    const int observed=result.load();
    if(observed==100) {
        std::cout<<"CONFIRMED: access violation during process() after engine publication\n";
        return 100;
    }
    if(observed==0) {
        std::cout<<"PASS: process() survived engine->null event-boundary transition\n";
        return 0;
    }
    std::cout<<"FAIL: process() returned unexpected result "<<observed<<"\n";
    return 16;
}
