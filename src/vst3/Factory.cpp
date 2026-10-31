#include "public.sdk/source/vst/vstaudioeffect.h"
#include "public.sdk/source/vst/vsteditcontroller.h"
#include "public.sdk/source/main/pluginfactory.h"
#include "base/source/fstreamer.h"
#include "pluginterfaces/vst/ivstevents.h"
#include "pluginterfaces/vst/ivstparameterchanges.h"
#include "Synth.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <memory>
#include <string>
#include <vector>

namespace AWE125 {
using namespace Steinberg;
using namespace Steinberg::Vst;
inline const FUID kProcessorUID(0x125A8000,0x81A24A93,0xB426CC70,0x3906F211);
inline const FUID kControllerUID(0x125A8000,0xAE274BC1,0xA4B02DA3,0x573CC990);
inline constexpr ParamID kProgramID=1000;
inline constexpr int32 kMagic=0x31455741, kVersion=1;

class Processor final : public AudioEffect {
public:
    Processor() { setControllerClass(kControllerUID); }
    static FUnknown* createInstance(void*) { return static_cast<IAudioProcessor*>(new Processor); }
    tresult PLUGIN_API initialize(FUnknown* ctx) override {
        const auto r=AudioEffect::initialize(ctx);
        if(r!=kResultOk)return r;
        addAudioOutput(STR16("Stereo"),SpeakerArr::kStereo);
        addEventInput(STR16("MIDI"),1);
        return kResultOk;
    }
    tresult PLUGIN_API canProcessSampleSize(int32 type) override {
        return type==kSample32?kResultTrue:kResultFalse;
    }
    tresult PLUGIN_API setupProcessing(ProcessSetup& setup) override {
        if(!std::isfinite(setup.sampleRate)||setup.sampleRate<=0.||
           setup.maxSamplesPerBlock<0||setup.maxSamplesPerBlock>262144)
            return kInvalidArgument;
        const auto result=AudioEffect::setupProcessing(setup);
        if(result!=kResultOk)return result;
        // A VST3 host's conformance test deliberately probes sample rates
        // outside practical audio ranges. Accept them without overflow,
        // using a safe internal rate; real host rates 8k..384k are exact.
        rate_=static_cast<uint32_t>(std::lround(
            std::clamp(setup.sampleRate,8000.0,384000.0)));
        capacity_=static_cast<uint32_t>(std::max(setup.maxSamplesPerBlock,1));
        scratch_.assign(size_t{capacity_}*2,0);
        synth_.reset();
        return kResultOk;
    }
    tresult PLUGIN_API setActive(TBool active) override {
        if(active) {
            if(!capacity_)return kResultFalse;
            synth_=std::make_unique<Synth>(rate_);
            synth_->Core().SetDriver(Awe32::Driver::Win95);
            if(const char* rom=std::getenv("AWE32_ROM_PATH");rom&&*rom) {
                std::string err;
                (void)synth_->Core().UseBox86Chip(rom,err);
            }
            synth_->Core().PowerOnInit();
            if(const char* sf=std::getenv("AWE32_SF2_PATH");sf&&*sf) {
                std::string err;
                (void)synth_->LoadBank(sf,err);
            }
            for(int c=0;c<16;++c)synth_->ProgramChange(static_cast<uint8_t>(c),program_);
        } else synth_.reset();
        return AudioEffect::setActive(active);
    }
    uint32 PLUGIN_API getLatencySamples() override {
        return synth_?synth_->Core().ChipLatencyFrames():0;
    }
    tresult PLUGIN_API getState(IBStream* state) override {
        if(!state)return kInvalidArgument;
        IBStreamer s(state,kLittleEndian);
        return s.writeInt32(kMagic)&&s.writeInt32(kVersion)&&s.writeInt32(program_)
               ? kResultOk:kResultFalse;
    }
    tresult PLUGIN_API setState(IBStream* state) override {
        if(!state)return kInvalidArgument;
        IBStreamer s(state,kLittleEndian);
        int32 magic=0,version=0,program=0;
        if(!s.readInt32(magic)||!s.readInt32(version)||!s.readInt32(program)||
           magic!=kMagic||version!=kVersion||program<0||program>127)
            return kResultFalse;
        program_=static_cast<uint8_t>(program);
        if(synth_)for(int c=0;c<16;++c)
            synth_->ProgramChange(static_cast<uint8_t>(c),program_);
        return kResultOk;
    }
    tresult PLUGIN_API process(ProcessData& data) override {
        if(data.numSamples<0)return kInvalidArgument;
        // VST3 explicitly permits a parameter-only process call without
        // any audio bus or output buffers. Apply changes before checking I/O.
        if(auto* changes=data.inputParameterChanges) {
            const int32 n=std::clamp(changes->getParameterCount(),0,1024);
            for(int32 i=0;i<n;++i) {
                auto* q=changes->getParameterData(i);
                if(!q||q->getParameterId()!=kProgramID||q->getPointCount()<=0)continue;
                int32 off=0;
                ParamValue val=0;
                if(q->getPoint(q->getPointCount()-1,off,val)==kResultOk&&std::isfinite(val)) {
                    program_=static_cast<uint8_t>(std::clamp(int(std::lround(val*127.)),0,127));
                    // The host can flush parameters before setActive.
                    // Program state must survive even without a Synth.
                    if(synth_)for(int c=0;c<16;++c)
                        synth_->ProgramChange(static_cast<uint8_t>(c),program_);
                }
            }
        }
        // Hosts may flush controls with numOutputs=0, numChannels=0 or a
        // null buffer. Such calls are valid: no audio work is required.
        if(data.numOutputs<1||!data.outputs ||
           data.outputs[0].numChannels<1 ||
           data.symbolicSampleSize!=kSample32 ||
           !data.outputs[0].channelBuffers32 ||
           !data.outputs[0].channelBuffers32[0])
            return kResultOk;
        auto* const l=data.outputs[0].channelBuffers32[0];
        auto* const r=(data.outputs[0].numChannels>=2)
            ? data.outputs[0].channelBuffers32[1] : nullptr;
        std::fill_n(l,data.numSamples,0.f);
        if(r)std::fill_n(r,data.numSamples,0.f);
        data.outputs[0].silenceFlags=r?3u:1u;
        if(!synth_||uint32(data.numSamples)>capacity_)
            return kResultOk;

        const auto render=[&](int32 from,int32 to) {
            if(to<=from)return;
            synth_->RenderBlock(scratch_.data()+size_t{2}*from,static_cast<uint32_t>(to-from));
            for(int32 i=from;i<to;++i) {
                const float left=scratch_[size_t{2}*i]/32768.f;
                const float right=scratch_[size_t{2}*i+1]/32768.f;
                if(r) {l[i]=left;r[i]=right;}
                else l[i]=(left+right)*0.5f;
            }
        };
        int32 pos=0;
        IEventList* events=data.inputEvents;
        const int32 n=events?std::clamp(events->getEventCount(),0,8192):0;
        for(int32 i=0;i<n;++i) {
            Event e{};
            if(events->getEvent(i,e)!=kResultOk||e.sampleOffset<pos)continue;
            const int32 at=std::clamp(e.sampleOffset,pos,data.numSamples);
            render(pos,at);
            pos=at;
            if(e.type==Event::kNoteOnEvent&&e.noteOn.channel>=0&&e.noteOn.channel<16&&
               e.noteOn.pitch>=0&&e.noteOn.pitch<=127&&std::isfinite(e.noteOn.velocity)) {
                const uint8_t vel=static_cast<uint8_t>(std::clamp(
                    int(std::lround(e.noteOn.velocity*127.f)),0,127));
                synth_->NoteOn(static_cast<uint8_t>(e.noteOn.channel),
                               static_cast<uint8_t>(e.noteOn.pitch),vel);
            }else if(e.type==Event::kNoteOffEvent&&e.noteOff.channel>=0&&
                     e.noteOff.channel<16&&e.noteOff.pitch>=0&&e.noteOff.pitch<=127) {
                synth_->NoteOff(static_cast<uint8_t>(e.noteOff.channel),
                                static_cast<uint8_t>(e.noteOff.pitch));
            }
        }
        render(pos,data.numSamples);
        for(int32 i=0;i<data.numSamples;++i)
            if(l[i]!=0.f||(r&&r[i]!=0.f)){data.outputs[0].silenceFlags=0;break;}
        return kResultOk;
    }
private:
    std::unique_ptr<Synth> synth_;
    std::vector<int16_t> scratch_;
    uint32_t rate_=44100,capacity_=0;
    uint8_t program_=0;
};
class Controller final : public EditControllerEx1 {
public:
    static FUnknown* createInstance(void*) {
        return static_cast<IEditController*>(new Controller);
    }
    tresult PLUGIN_API initialize(FUnknown* ctx) override {
        const auto r=EditControllerEx1::initialize(ctx);
        if(r!=kResultOk)return r;
        parameters.addParameter(STR16("Program"),nullptr,127,0,
                                ParameterInfo::kCanAutomate,kProgramID);
        return kResultOk;
    }
    tresult PLUGIN_API setComponentState(IBStream* stream) override {
        if(!stream)return kInvalidArgument;
        IBStreamer s(stream,kLittleEndian);
        int32 magic=0,version=0,program=0;
        if(!s.readInt32(magic)||!s.readInt32(version)||!s.readInt32(program)||
           magic!=kMagic||version!=kVersion||program<0||program>127)
            return kResultFalse;
        return setParamNormalized(kProgramID,static_cast<double>(program)/127.);
    }
};
}
using namespace Steinberg;
using namespace Steinberg::Vst;
BEGIN_FACTORY_DEF("125A Systems","https://github.com/challanger2000","")
DEF_CLASS2(INLINE_UID_FROM_FUID(AWE125::kProcessorUID),PClassInfo::kManyInstances,
           kVstAudioEffectClass,"125A AWE Synthesizer",Vst::kDistributable,
           Vst::PlugType::kInstrumentSynth,"0.1.0",kVstVersionString,
           AWE125::Processor::createInstance)
DEF_CLASS2(INLINE_UID_FROM_FUID(AWE125::kControllerUID),PClassInfo::kManyInstances,
           kVstComponentControllerClass,"125A AWE Synthesizer Controller",0,
           "","0.1.0",kVstVersionString,AWE125::Controller::createInstance)
END_FACTORY
