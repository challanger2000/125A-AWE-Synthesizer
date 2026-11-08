// Public, exported Windows VST3 binary, real SDK messages and audio buffers.
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include "pluginterfaces/base/ipluginbase.h"
#include "pluginterfaces/vst/ivstcomponent.h"
#include "pluginterfaces/vst/ivstaudioprocessor.h"
#include "pluginterfaces/vst/ivsteditcontroller.h"
#include "public.sdk/source/vst/hosting/hostclasses.h"
#include "public.sdk/source/vst/hosting/parameterchanges.h"
#include "public.sdk/source/vst/hosting/eventlist.h"
#include "public.sdk/source/common/memorystream.h"
#include "AssetState.h"
#include "MidiControlMapping.h"
#include <algorithm>
#include <array>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <vector>
using namespace Steinberg;using namespace Steinberg::Vst;
namespace {
void require(bool b,const char* text){if(!b)throw std::runtime_error(text);}
void state(IComponent* c,const AWE125::AssetState::Data& s) {
    MemoryStream stream;
    require(AWE125::AssetState::Write([&](const void* p,size_t n) {
        int32 written=0;return stream.write(const_cast<void*>(p),int32(n),&written)==kResultOk&&written==int32(n);
    },s),"write state");stream.seek(0,IBStream::kIBSeekSet,nullptr);
    require(c->setState(&stream)==kResultOk,"set state");
}
std::vector<float> render(IAudioProcessor* audio,int channel) {
    std::vector<float> pcm;pcm.reserve(16384);
    for(int block=0;block<8;++block) {
        std::array<float,1024> l{},r{};float* channels[]{l.data(),r.data()};
        AudioBusBuffers out{};out.numChannels=2;out.channelBuffers32=channels;
        EventList events;Event on{};on.type=Event::kNoteOnEvent;
        on.noteOn.channel=int16(channel);on.noteOn.pitch=60;on.noteOn.velocity=.85f;on.noteOn.noteId=1;
        if(!block)require(events.addEvent(on)==kResultOk,"note");
        ProcessData data{};data.processMode=kRealtime;data.symbolicSampleSize=kSample32;
        data.numSamples=1024;data.numOutputs=1;data.outputs=&out;data.inputEvents=&events;
        require(audio->process(data)==kResultOk,"actual DLL process");
        pcm.insert(pcm.end(),l.begin(),l.end());pcm.insert(pcm.end(),r.begin(),r.end());
    }return pcm;
}
struct Instance {
    IComponent* component=nullptr;IAudioProcessor* audio=nullptr;IEditController* controller=nullptr;
    IConnectionPoint *procConnection=nullptr,*ctrlConnection=nullptr;
    HostApplication host;bool active=false;
    Instance(IPluginFactory* factory,int rate,const AWE125::AssetState::Data& initial) {
        for(int i=0;i<factory->countClasses();++i){PClassInfo info{};factory->getClassInfo(i,&info);
            if(std::string(info.category)==kVstAudioEffectClass)
                require(factory->createInstance(info.cid,IComponent::iid,reinterpret_cast<void**>(&component))==kResultOk,"component");}
        require(component&&component->initialize(&host)==kResultOk,"initialize DLL");
        require(component->queryInterface(IAudioProcessor::iid,reinterpret_cast<void**>(&audio))==kResultOk,"audio interface");
        require(component->queryInterface(IConnectionPoint::iid,reinterpret_cast<void**>(&procConnection))==kResultOk,"connection");
        TUID uid{};require(component->getControllerClassId(uid)==kResultOk,"controller ID");
        require(factory->createInstance(uid,IEditController::iid,reinterpret_cast<void**>(&controller))==kResultOk,"controller");
        require(controller->initialize(&host)==kResultOk,"controller initialize");
        require(controller->queryInterface(IConnectionPoint::iid,reinterpret_cast<void**>(&ctrlConnection))==kResultOk,"controller connection");
        require(procConnection->connect(ctrlConnection)==kResultOk&&ctrlConnection->connect(procConnection)==kResultOk,"connect real controller");
        ProcessSetup setup{kRealtime,kSample32,1024,double(rate)};
        require(audio->setupProcessing(setup)==kResultOk,"setup");state(component,initial);
        require(component->setActive(true)==kResultOk&&audio->setProcessing(true)==kResultOk,"activate");active=true;
    }
    ~Instance(){
        if(active){audio->setProcessing(false);component->setActive(false);}
        if(procConnection&&ctrlConnection){procConnection->disconnect(ctrlConnection);ctrlConnection->disconnect(procConnection);}
        if(ctrlConnection)ctrlConnection->release();if(procConnection)procConnection->release();
        if(controller){controller->terminate();controller->release();}
        if(audio)audio->release();if(component){component->terminate();component->release();}
    }
};
}
int wmain(int argc,wchar_t** argv) {
    if(argc!=3)return 2;
    auto dll=LoadLibraryW(argv[1]);if(!dll)return 2;
    using GetFactory=IPluginFactory*(*)();auto get=reinterpret_cast<GetFactory>(GetProcAddress(dll,"GetPluginFactory"));
    if(!get)return 2;auto* factory=get();int checks=0,failures=0;
    try {
        auto assets=std::filesystem::path(argv[2]);
        for(int rate:{44100,48000,96000})for(unsigned program:{0u,7u,9u}) {
            AWE125::AssetState::Data wanted;wanted.pathsSpecified=true;wanted.program=program;
            wanted.channelPrograms.fill(program);wanted.romPath=(assets/"zero.rom").string();wanted.sf2Path=(assets/"bank.sf2").string();
            auto blank=wanted;blank.sf2Path.clear();
            Instance reference(factory,rate,wanted);auto expected=render(reference.audio,0);
            Instance actual(factory,rate,blank);
            auto* load=new HostMessage;load->setMessageID("125A_SF2_LOAD");
            load->getAttributes()->setInt("RequestID",1);
            load->getAttributes()->setBinary("Path",wanted.sf2Path.data(),uint32(wanted.sf2Path.size()));
            require(actual.procConnection->notify(load)==kResultOk,"real load message");load->release();
            auto got=render(actual.audio,0);
            const bool good=got==expected&&std::any_of(got.begin(),got.end(),[](float v){return v!=0.f;});
            ++checks;failures+=!good;
            std::cout<<(good?"PASS ":"FAIL ")<<"actual DLL first NoteOn after SF2 load rate="<<rate<<" program="<<program<<'\n';
        }
    } catch(const std::exception& e){std::cerr<<e.what()<<'\n';++failures;}
    factory->release();FreeLibrary(dll);
    std::cout<<"P171_EXPORTED_DLL checks="<<checks<<" failures="<<failures<<'\n';
    return checks==9&&failures==0?0:1;
}
