#include "public.sdk/source/vst/vstaudioeffect.h"
#include "public.sdk/source/vst/vsteditcontroller.h"
#include "public.sdk/source/main/pluginfactory.h"
#include "base/source/fstreamer.h"
#include "pluginterfaces/base/ibstream.h"
#include "pluginterfaces/vst/ivstevents.h"
#include "pluginterfaces/vst/ivstparameterchanges.h"
#include "Synth.h"
#include "AssetState.h"
#include "AssetConfig.h"
#include "Opl3Midi.h"
#include "public.sdk/source/vst/vstparameters.h"
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
inline constexpr ParamID kEngineID=1001;
// Persistence data contract is in AssetState.h.

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
            ResolveAssets();
            if(!state_.romPath.empty()) {
                std::string error;
                if(!synth_->Core().UseBox86Chip(state_.romPath,error))
                    assetError_=std::move(error);
            }
            synth_->Core().PowerOnInit();
            if(!state_.sf2Path.empty()) {
                std::string error;
                if(!synth_->LoadBank(state_.sf2Path,error))
                    assetError_=std::move(error);
            }
            for(int c=0;c<16;++c)synth_->ProgramChange(static_cast<uint8_t>(c),
                static_cast<uint8_t>(state_.program));
            // Both engines are constructed outside the audio callback.
            // The OPL3 delay matches the 86Box FIFO reported to the host.
            opl_=std::make_unique<Opl3Midi>(rate_,synth_->Core().ChipLatencyFrames());
            fmReady_=true;
            if(!state_.ibkPath.empty()) {
                std::string error;
                if(!opl_->LoadMelodicIbk(state_.ibkPath,error)) {
                    assetError_=std::move(error);
                    fmReady_=false; // never play the test patch as a failed bank
                }
            }
            for(int c=0;c<16;++c)
                opl_->ProgramChange(static_cast<uint8_t>(c),
                    static_cast<uint8_t>(state_.program));
        } else {opl_.reset();synth_.reset();}
        return AudioEffect::setActive(active);
    }
    uint32 PLUGIN_API getLatencySamples() override {
        return synth_?synth_->Core().ChipLatencyFrames():0;
    }
    tresult PLUGIN_API getState(IBStream* stream) override {
        if(!stream)return kInvalidArgument;
        ResolveAssets();
        const auto send=[&](const void* buffer,size_t n) {
            int32 written=0;
            return n<=AssetState::kMaxPath &&
                stream->write(const_cast<void*>(buffer),static_cast<int32>(n),
                              &written)==kResultOk &&
                written==static_cast<int32>(n);
        };
        return AssetState::Write(send,state_) ? kResultOk:kResultFalse;
    }
    tresult PLUGIN_API setState(IBStream* stream) override {
        if(!stream)return kInvalidArgument;
        const auto receive=[&](void* buffer,size_t n) {
            int32 received=0;
            return n<=AssetState::kMaxPath &&
                stream->read(buffer,static_cast<int32>(n),&received)==kResultOk &&
                received==static_cast<int32>(n);
        };
        AssetState::Data candidate;
        if(!AssetState::Read(receive,candidate))return kResultFalse;
        state_=std::move(candidate);
        if(synth_)for(int c=0;c<16;++c)
            synth_->ProgramChange(static_cast<uint8_t>(c),
                static_cast<uint8_t>(state_.program));
        // File replacement while active is deferred until reactivation.
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
                if(!q||q->getPointCount()<=0)continue;
                int32 off=0;
                ParamValue val=0;
                if(q->getPoint(q->getPointCount()-1,off,val)==kResultOk&&std::isfinite(val)) {
                    if(q->getParameterId()==kProgramID) {
                        state_.program=static_cast<uint32_t>(std::clamp(
                            int(std::lround(val*127.)),0,127));
                        if(synth_)for(int c=0;c<16;++c)
                            synth_->ProgramChange(static_cast<uint8_t>(c),
                                static_cast<uint8_t>(state_.program));
                        if(opl_)for(int c=0;c<16;++c)
                            opl_->ProgramChange(static_cast<uint8_t>(c),
                                static_cast<uint8_t>(state_.program));
                    } else if(q->getParameterId()==kEngineID) {
                        const uint32_t mode=(val>=0.5)?1u:0u;
                        if(mode!=state_.engine) {
                            if(opl_)opl_->AllNotesOff();
                            if(synth_)for(int c=0;c<16;++c)
                                synth_->ControlChange(static_cast<uint8_t>(c),120,0);
                            state_.engine=mode;
                        }
                    }
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
        if(!synth_||!opl_||uint32(data.numSamples)>capacity_)
            return kResultOk;

        const auto render=[&](int32 from,int32 to) {
            if(to<=from)return;
            if(state_.engine==1)
                {
                if(fmReady_)
                    opl_->RenderBlock(scratch_.data()+size_t{2}*from,
                                      static_cast<uint32_t>(to-from));
                else
                    std::fill_n(scratch_.data()+size_t{2}*from,
                                size_t{2}*(to-from),int16_t{0});
            }
            else
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
                if(state_.engine==1) {
                    if(fmReady_)opl_->NoteOn(static_cast<uint8_t>(e.noteOn.channel),
                                 static_cast<uint8_t>(e.noteOn.pitch),vel);
                } else
                    synth_->NoteOn(static_cast<uint8_t>(e.noteOn.channel),
                                   static_cast<uint8_t>(e.noteOn.pitch),vel);
            }else if(e.type==Event::kNoteOffEvent&&e.noteOff.channel>=0&&
                     e.noteOff.channel<16&&e.noteOff.pitch>=0&&e.noteOff.pitch<=127) {
                if(state_.engine==1)
                    opl_->NoteOff(static_cast<uint8_t>(e.noteOff.channel),
                                  static_cast<uint8_t>(e.noteOff.pitch));
                else
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
    std::unique_ptr<Opl3Midi> opl_;
    std::vector<int16_t> scratch_;
    uint32_t rate_=44100,capacity_=0;
    AssetState::Data state_{};
    std::string assetError_;
    bool fmReady_=true;
    void ResolveAssets() {
        AssetConfig::Paths configured;
        if(!state_.pathsSpecified) {
            if(AssetConfig::Load(configured)) {
                state_.romPath=std::move(configured.rom);
                state_.sf2Path=std::move(configured.sf2);
                state_.ibkPath=std::move(configured.ibk);
                state_.pathsSpecified=true;
            } else assetError_="Invalid 125A assets.cfg";
        } else if(state_.ibkPath.empty() && AssetConfig::Load(configured)) {
            // Legacy V1-V3 projects have no IBK field. Preserve their
            // ROM/SF2 paths while adopting an optional configured FM bank.
            state_.ibkPath=std::move(configured.ibk);
        }
    }
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
        auto* engine=new StringListParameter(STR16("Hardware"),kEngineID);
        engine->appendString(STR16("EMU8000 AWE32/64"));
        engine->appendString(STR16("Yamaha OPL3"));
        parameters.addParameter(engine);
        return kResultOk;
    }
    tresult PLUGIN_API setComponentState(IBStream* stream) override {
        if(!stream)return kInvalidArgument;
        const auto read=[&](void* buffer,size_t n) {
            int32 received=0;
            return n<=AssetState::kMaxPath &&
                stream->read(buffer,static_cast<int32>(n),&received)==kResultOk &&
                received==static_cast<int32>(n);
        };
        AssetState::Data model;
        if(!AssetState::Read(read,model))return kResultFalse;
        if(setParamNormalized(kProgramID,static_cast<double>(model.program)/127.)!=kResultOk)
            return kResultFalse;
        return setParamNormalized(kEngineID,static_cast<double>(model.engine));
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
