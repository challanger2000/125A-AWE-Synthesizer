#include "public.sdk/source/vst/vstaudioeffect.h"
#include "public.sdk/source/vst/vsteditcontroller.h"
#include "public.sdk/source/main/pluginfactory.h"
#include "base/source/fstreamer.h"
#include "pluginterfaces/base/ibstream.h"
#include "pluginterfaces/vst/ivstevents.h"
#include "pluginterfaces/vst/ivstparameterchanges.h"
#include "pluginterfaces/vst/ivstmidicontrollers.h"
#include "Synth.h"
#include "AssetState.h"
#include "AssetConfig.h"
#include "PresetCatalog.h"
#include "PresetBrowserView.h"
#include "Sf2LoadPolicy.h"
#include "RomGmBank.h"
#include "MidiControlMapping.h"
#include "public.sdk/source/vst/vstparameters.h"
#include "public.sdk/source/main/moduleinit.h"
#include "pluginterfaces/base/ustring.h"
#include "vstgui/plugin-bindings/vst3editor.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <exception>
#include <filesystem>
#include <iomanip>
#include <sstream>
#if defined(_WIN32)
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif
#include <memory>
#include <mutex>
#include <string>
#include <vector>

namespace AWE125 {
using namespace Steinberg;
using namespace Steinberg::Vst;
inline const FUID kProcessorUID(0x125A8000,0x81A24A93,0xB426CC70,0x3906F211);
inline const FUID kControllerUID(0x125A8000,0xAE274BC1,0xA4B02DA3,0x573CC990);
inline constexpr ParamID kProgramID=1000;
inline constexpr ParamID kGuiFirstID=1100;
inline constexpr int kGuiCount=AssetState::kControlCount;
inline constexpr ParamID kBankID=1002; // SF2 bank, fixed normalized range 0..16383
inline constexpr ParamID kVolumeID=MasterOutput::kParamID; // post-chip stereo master volume
// Persistence data contract is in AssetState.h.
// Factory banks are packaged *inside* the Windows VST3 by CMake. The path
// is resolved on activation, never from the realtime audio callback.
static std::string FactoryBank(const wchar_t* filename) {
#if defined(_WIN32)
    wchar_t path[32768]{};
    const auto mod=reinterpret_cast<HMODULE>(Steinberg::getPlatformModuleHandle());
    const DWORD count=GetModuleFileNameW(mod,path,32768);
    if(!mod||count==0||count>=32768)return {};
    // .../Synth.vst3/Contents/x86_64-win/Synth.vst3 ->
    // .../Synth.vst3/Contents/Resources/<bank>
    return (std::filesystem::path(path).parent_path().parent_path()/
            "Resources"/filename).string();
#else
    (void)filename;
    return {};
#endif
}

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
        std::lock_guard<std::mutex> lock(engineMutex_);
        if(active) {
            if(!capacity_)return kResultFalse;
            hostActive_=true;
            synth_.reset();
            assetError_.clear();
            ResolveAssets();
            sf2Configured_=!state_.sf2Path.empty();
            sf2Loaded_=false;
            gmLoaded_=false;
            std::string status;
            if(state_.romPath.empty()) {
                // Strict AWE64 mode: ROM absent means NO software fallback.
                // The editor still opens, allowing the user to load the ROM.
                status="Original-Wave-ROM erforderlich: ROM LADEN. Bis dahin kein Audio.";
            } else {
                try {
                    auto chip=std::make_unique<Synth>(rate_);
                    chip->Core().SetDriver(Awe32::Driver::Win95);
                    std::string error;
                    if(!chip->Core().UseBox86Chip(state_.romPath,error) ||
                       chip->Core().ChipVariant()!=Emu8000Core::Chip::Box86) {
                        assetError_="ROM-Ladefehler: "+(error.empty() ?
                            std::string("86Box-EMU8000 konnte nicht starten"):error);
                        status=assetError_;
                    } else {
                        chip->Core().PowerOnInit();
                        for(int i=0;i<kGuiCount;++i)
                            chip->SetGuiControl(i,
                                float(state_.controls[i])/AssetState::kControlScale);
                        const auto banks=RomGmBank::LoadBanks(
                            *chip,state_.romPath,state_.sf2Path);
                        gmLoaded_=banks.gm;
                        sf2Loaded_=banks.sf2;
                        if(sf2Configured_&&!sf2Loaded_) {
                            assetError_="SF2-Ladefehler: "+banks.sf2Error;
                            status=assetError_;
                        } else if(gmLoaded_&&sf2Loaded_)
                            status="86Box: originale GM-ROM-Bank und SF2 geladen.";
                        else if(gmLoaded_)
                            status="86Box: originale 1MGM-Bank (SYNTHGM.SBK) geladen.";
                        else if(sf2Loaded_)
                            status="86Box: SF2 geladen. SYNTHGM.SBK fehlt neben ROM.";
                        else
                            status="86Box: ROM bereit. SYNTHGM.SBK neben ROM oder SF2 laden.";
                        chip->SelectBrowserBank(static_cast<uint16_t>(state_.bank));
                        for(int c=0;c<16;++c)
                            chip->ProgramChange(static_cast<uint8_t>(c),
                                                static_cast<uint8_t>(state_.program));
                        synth_=std::move(chip);
                    }
                } catch(const std::exception& e) {
                    assetError_="ROM-Ladefehler: "+std::string(e.what());
                    status=assetError_;
                    synth_.reset();
                }
            }
            sendTextMessage(("125A_SF2_STATUS:"+status).c_str());
            sendTextMessage(("125A_HW_INFO:"+HardwareDescriptor()).c_str());
        } else {
            hostActive_=false;
            sf2Loaded_=false;
            gmLoaded_=false;
            synth_.reset();
        }
        return AudioEffect::setActive(active);
    }
    // Binary connection message, not the SDK's 255-char text-message path.
    // Load on the host's connection thread, then swap the chip under a short
    // render try-lock. Failed loads retain the previous working SoundFont.
    tresult PLUGIN_API notify(IMessage* msg) override {
        if(msg && FIDStringsEqual(msg->getMessageID(),"125A_HW_INFO_REQUEST")) {
            std::string snapshot;
            {
                std::lock_guard<std::mutex> lock(engineMutex_);
                snapshot=HardwareDescriptor();
            }
            sendTextMessage(("125A_HW_INFO:"+snapshot).c_str());
            return kResultOk;
        }
        if(msg && FIDStringsEqual(msg->getMessageID(),"125A_ROM_LOAD")) {
            const void* bytes=nullptr;
            uint32 length=0;
            if(!msg->getAttributes() ||
               msg->getAttributes()->getBinary("Path",bytes,length)!=kResultOk ||
               !bytes || !length || length>AssetState::kMaxPath)
                return kInvalidArgument;
            const std::string path(static_cast<const char*>(bytes),length);
            if(!AssetState::validPath(path))return kInvalidArgument;
            AssetState::Data model;
            uint32_t sampleRate=44100;
            bool active=false;
            {
                std::lock_guard<std::mutex> lock(engineMutex_);
                model=state_;
                sampleRate=rate_;
                active=hostActive_;
            }
            std::string error;
            std::string sf2Error;
            bool loadedSf2=false,loadedGm=false;
            std::unique_ptr<Synth> prepared;
            try {
                // A chip with the new ROM is fully initialized off the audio
                // thread. A bad image NEVER replaces the previous good chip.
                prepared=std::make_unique<Synth>(sampleRate);
                prepared->Core().SetDriver(Awe32::Driver::Win95);
                if(!prepared->Core().UseBox86Chip(path,error)) {
                    if(error.empty())error="ungueltige EMU8000-Wave-ROM";
                } else {
                    prepared->Core().PowerOnInit();
                    for(int i=0;i<kGuiCount;++i)
                        prepared->SetGuiControl(
                            i,float(model.controls[i])/AssetState::kControlScale);
                    if(active) {
                        auto banks=RomGmBank::LoadBanks(
                            *prepared,path,model.sf2Path);
                        loadedGm=banks.gm;
                        loadedSf2=banks.sf2;
                        sf2Error=std::move(banks.sf2Error);
                    }
                    // A valid ROM is accepted even if an old/invalid SF2
                    // cannot be loaded; a valid bank can then be selected.
                    if(error.empty()) {
                        prepared->SelectBrowserBank(static_cast<uint16_t>(model.bank));
                        for(int c=0;c<16;++c)
                            prepared->ProgramChange(static_cast<uint8_t>(c),
                                                     static_cast<uint8_t>(model.program));
                    }
                }
            } catch(const std::exception& e) {error=e.what();}
            if(!error.empty()) {
                sendTextMessage(("125A_SF2_STATUS:ROM-Ladefehler: "+error).c_str());
                sendTextMessage("125A_ROM_ACK:ERROR");
                return kResultOk;
            }
            std::string info;
            {
                std::lock_guard<std::mutex> lock(engineMutex_);
                if(active) synth_.swap(prepared);
                state_.romPath=path;
                state_.pathsSpecified=true;
                sf2Configured_=!model.sf2Path.empty();
                sf2Loaded_=active&&loadedSf2&&
                    bool(synth_)&&synth_->Core().ChipVariant()==Emu8000Core::Chip::Box86;
                gmLoaded_=active&&loadedGm&&
                    bool(synth_)&&synth_->Core().ChipVariant()==Emu8000Core::Chip::Box86;
                info=HardwareDescriptor();
            }
            sendTextMessage(("125A_HW_INFO:"+info).c_str());
            const std::string status=active ?
                (!sf2Error.empty() ?
                    ("ROM geladen. SF2-Ladefehler: "+sf2Error) :
                    (loadedGm ? "ROM + originale 1MGM GM-Bank geladen." :
                     "ROM geladen. SYNTHGM.SBK neben ROM ablegen.")) :
                "ROM validiert. Wird bei Aktivierung geladen.";
            sendTextMessage(("125A_SF2_STATUS:"+status).c_str());
            sendTextMessage("125A_ROM_ACK:OK");
            return kResultOk;
        }
        if(!msg || !FIDStringsEqual(msg->getMessageID(),"125A_SF2_LOAD"))
            return AudioEffect::notify(msg);
        const void* bytes=nullptr;
        uint32 bytesCount=0;
        if(!msg->getAttributes() ||
           msg->getAttributes()->getBinary("Path",bytes,bytesCount)!=kResultOk ||
           !bytes || bytesCount==0 || bytesCount>AssetState::kMaxPath)
            return kInvalidArgument;
        const std::string path(static_cast<const char*>(bytes),bytesCount);
        if(!AssetState::validPath(path))return kInvalidArgument;
        uint32_t sampleRate=44100;
        AssetState::Data model;
        bool active=false,romReady=false;
        {
            std::lock_guard<std::mutex> lock(engineMutex_);
            sampleRate=rate_;
            model=state_;
            active=hostActive_;
            romReady=synth_ && synth_->Core().ChipVariant()==Emu8000Core::Chip::Box86;
        }
        std::string error;
        std::unique_ptr<Synth> replacement;
        bool loadedGm=false;
        if(active&&romReady) {
            try {
                replacement=std::make_unique<Synth>(sampleRate);
                replacement->Core().SetDriver(Awe32::Driver::Win95);
                if(!replacement->Core().UseBox86Chip(model.romPath,error) ||
                   replacement->Core().ChipVariant()!=Emu8000Core::Chip::Box86)
                    error="Wave ROM: "+(error.empty()?std::string("86Box nicht gestartet"):error);
                else {
                    replacement->Core().PowerOnInit();
                    for(int i=0;i<kGuiCount;++i)
                        replacement->SetGuiControl(
                            i,float(model.controls[i])/AssetState::kControlScale);
                    const auto banks=RomGmBank::LoadBanks(
                        *replacement,model.romPath,path);
                    loadedGm=banks.gm;
                    if(!banks.sf2)
                        error="SF2: "+banks.sf2Error;
                }
            } catch(const std::exception& e) {error=e.what();}
            if(!error.empty()) {
                sendTextMessage(("125A_SF2_STATUS:SF2-Ladefehler: "+error).c_str());
                sendTextMessage("125A_SF2_ACK:ERROR");
                return kResultOk;
            }
            replacement->SelectBrowserBank(static_cast<uint16_t>(model.bank));
            for(int c=0;c<16;++c)
                replacement->ProgramChange(static_cast<uint8_t>(c),
                                            static_cast<uint8_t>(model.program));
        }
        {
            std::lock_guard<std::mutex> lock(engineMutex_);
            if(replacement)synth_.swap(replacement);
            state_.sf2Path=path;
            state_.pathsSpecified=true;
            sf2Configured_=true;
            sf2Loaded_=active&&romReady;
            gmLoaded_=active&&romReady&&loadedGm;
        }
        std::string sysInfo;
        {
            std::lock_guard<std::mutex> lock(engineMutex_);
            sysInfo=HardwareDescriptor();
        }
        sendTextMessage(("125A_HW_INFO:"+sysInfo).c_str());
        sendTextMessage(active&&!romReady ?
            "125A_SF2_STATUS:SF2 gewaehlt. Original-Wave-ROM erforderlich: ROM LADEN." :
            (active ?
                "125A_SF2_STATUS:86Box-EMU8000: ROM und SF2 geladen." :
                "125A_SF2_STATUS:SF2 gewaehlt - Laden bei Aktivierung."));
        sendTextMessage("125A_SF2_ACK:OK");
        return kResultOk;
    }
    uint32 PLUGIN_API getLatencySamples() override {
        std::lock_guard<std::mutex> lock(engineMutex_);
        return synth_?synth_->Core().ChipLatencyFrames():0;
    }
    tresult PLUGIN_API getState(IBStream* stream) override {
        if(!stream)return kInvalidArgument;
        // P118: never keep the realtime engine mutex across host-supplied
        // IBStream::write() or a filesystem configuration lookup.
        AssetState::Data snapshot;
        {
            std::lock_guard<std::mutex> lock(engineMutex_);
            snapshot=state_;
        }
        if(!snapshot.pathsSpecified) {
            AssetConfig::Paths configured;
            if(AssetConfig::Load(configured)) {
                snapshot.romPath=std::move(configured.rom);
                snapshot.sf2Path=std::move(configured.sf2);
                snapshot.ibkPath=std::move(configured.ibk);
                snapshot.drumIbkPath=std::move(configured.drumIbk);
                snapshot.pathsSpecified=true;
            }
        }
        const auto send=[&](const void* buffer,size_t n) {
            int32 written=0;
            return n<=AssetState::kMaxPath &&
                stream->write(const_cast<void*>(buffer),static_cast<int32>(n),
                              &written)==kResultOk &&
                written==static_cast<int32>(n);
        };
        return AssetState::Write(send,snapshot) ? kResultOk:kResultFalse;
    }
    tresult PLUGIN_API setState(IBStream* stream) override {
        if(!stream)return kInvalidArgument;
        std::lock_guard<std::mutex> lock(engineMutex_);
        const auto receive=[&](void* buffer,size_t n) {
            int32 received=0;
            return n<=AssetState::kMaxPath &&
                stream->read(buffer,static_cast<int32>(n),&received)==kResultOk &&
                received==static_cast<int32>(n);
        };
        AssetState::Data candidate;
        if(!AssetState::Read(receive,candidate))return kResultFalse;
        candidate.engine=0; // legacy FM projects migrate to EMU8000.
        state_=std::move(candidate);
        volumeGain_.restore(state_.masterVolume); // no unexpected fade on project restore
        if(synth_)for(int i=0;i<kGuiCount;++i)
            synth_->SetGuiControl(i,float(state_.controls[i])/AssetState::kControlScale);
        if(synth_)synth_->SelectBrowserBank(static_cast<uint16_t>(state_.bank));
        if(synth_)for(int c=0;c<16;++c)
            synth_->ProgramChange(static_cast<uint8_t>(c),
                static_cast<uint8_t>(state_.program));
        // File replacement while active is deferred until reactivation.
        return kResultOk;
    }
    tresult PLUGIN_API process(ProcessData& data) override {
        if(data.numSamples<0 || uint32_t(data.numSamples)>capacity_)
            return kInvalidArgument;
        std::unique_lock<std::mutex> lock(engineMutex_,std::try_to_lock);
        if(!lock.owns_lock()) {
            // P117-03 remains an open architecture issue: do not pretend this
            // fallback preserves realtime notes/automation on a contention.
            if(data.numOutputs>0 && data.outputs &&
               data.outputs[0].channelBuffers32 &&
               data.symbolicSampleSize==kSample32) {
                for(int c=0;c<data.outputs[0].numChannels;++c)
                    if(auto* out=data.outputs[0].channelBuffers32[c])
                        std::fill_n(out,data.numSamples,0.f);
                data.outputs[0].silenceFlags=3u;
            }
            return kResultOk;
        }
        // P118: VST3 parameter points carry their own sampleOffset.
        // Keep one cursor per parameter queue and merge them with MIDI events.
        // No allocation or sorting on the audio thread. The number of known
        // parameters is bounded below the 1024 preallocated cursor slots.
        int32 activeQueues=0;
        const auto advance=[&](ParameterCursor& c)->bool {
            while(c.point<c.count) {
                int32 offset=0;
                ParamValue value=0.;
                if(c.queue->getPoint(c.point,offset,value)==kResultOk &&
                   std::isfinite(value)) {
                    c.offset=std::clamp(offset,0,data.numSamples);
                    c.value=std::clamp(value,0.,1.);
                    return true;
                }
                ++c.point;
            }
            return false;
        };
        if(auto* changes=data.inputParameterChanges) {
            const int32 count=std::max<int32>(0,changes->getParameterCount());
            for(int32 i=0;i<count && activeQueues<int32(paramCursors_.size());++i) {
                auto* q=changes->getParameterData(i);
                if(!q||q->getPointCount()<=0)continue;
                ParameterCursor cursor{};
                cursor.queue=q;
                cursor.id=q->getParameterId();
                cursor.count=q->getPointCount();
                if(advance(cursor))paramCursors_[activeQueues++]=cursor;
            }
        }
        auto apply=[&](ParamID id,ParamValue val) {
            if(id==kProgramID) {
                state_.program=static_cast<uint32_t>(std::clamp(
                    int(std::lround(val*127.)),0,127));
                if(synth_)for(int ch=0;ch<16;++ch)
                    synth_->ProgramChange(static_cast<uint8_t>(ch),
                        static_cast<uint8_t>(state_.program));
            } else if(id==kBankID) {
                const auto bank=static_cast<uint32_t>(std::clamp(
                    int(std::lround(val*AssetState::kMaxBank)),0,
                    int(AssetState::kMaxBank)));
                if(bank!=state_.bank) {
                    state_.bank=bank;
                    if(synth_)synth_->SelectBrowserBank(static_cast<uint16_t>(bank));
                }
            } else if(id==kVolumeID) {
                state_.masterVolume=static_cast<uint32_t>(std::lround(
                    val*MasterOutput::kScale));
                volumeGain_.setTarget(state_.masterVolume);
            } else if(id>=kGuiFirstID && id<kGuiFirstID+kGuiCount) {
                const int idx=int(id-kGuiFirstID);
                state_.controls[idx]=static_cast<uint32_t>(
                    std::lround(val*AssetState::kControlScale));
                if(synth_)synth_->SetGuiControl(idx,static_cast<float>(val));
            } else if(synth_) {
                const auto midi=MidiControlMapping::Decode(id);
                if(!midi.valid)return;
                const uint8_t channel=static_cast<uint8_t>(midi.channel);
                if(midi.number==129)
                    synth_->PitchBend(channel,MidiControlMapping::PitchBend(val));
                else if(midi.number==128)
                    synth_->ChannelPressure(channel,MidiControlMapping::Byte(val));
                else synth_->ControlChange(channel,static_cast<uint8_t>(midi.number),
                                           MidiControlMapping::Byte(val));
            }
        };

        const bool hasOutput=(data.numOutputs>0 && data.outputs &&
            data.symbolicSampleSize==kSample32 &&
            data.outputs[0].numChannels>0 &&
            data.outputs[0].channelBuffers32 &&
            data.outputs[0].channelBuffers32[0]);
        auto* left=hasOutput?data.outputs[0].channelBuffers32[0]:nullptr;
        auto* right=hasOutput&&data.outputs[0].numChannels>=2
            ?data.outputs[0].channelBuffers32[1]:nullptr;
        if(hasOutput) {
            std::fill_n(left,data.numSamples,0.f);
            if(right)std::fill_n(right,data.numSamples,0.f);
            data.outputs[0].silenceFlags=right?3u:1u;
        }
        const bool canRender=hasOutput&&bool(synth_);
        int32 position=0;
        const auto render=[&](int32 end) {
            end=std::clamp(end,position,data.numSamples);
            if(canRender&&end>position) {
                synth_->RenderBlock(scratch_.data()+2*size_t(position),
                                    static_cast<uint32_t>(end-position));
                for(int32 i=position;i<end;++i) {
                    const float gain=volumeGain_.next();
                    const float l=(scratch_[size_t(i)*2]/32768.f)*gain;
                    const float r=(scratch_[size_t(i)*2+1]/32768.f)*gain;
                    if(right){left[i]=l;right[i]=r;}
                    else left[i]=(l+r)*0.5f;
                }
            }
            position=end;
        };
        IEventList* events=data.inputEvents;
        const int32 eventCount=events?std::max<int32>(0,events->getEventCount()):0;
        int32 nextEvent=0;
        Event currentEvent{};
        bool eventReady=false;
        const auto advanceEvent=[&]() {
            eventReady=false;
            while(nextEvent<eventCount) {
                if(events->getEvent(nextEvent++,currentEvent)==kResultOk) {
                    eventReady=true;
                    break;
                }
            }
        };
        advanceEvent();
        while(activeQueues>0||eventReady) {
            int32 which=-1,at=data.numSamples;
            for(int32 i=0;i<activeQueues;++i) {
                const auto time=std::max(position,paramCursors_[i].offset);
                if(which<0||time<at) {which=i;at=time;}
            }
            const int32 midiAt=eventReady
                ?std::clamp(currentEvent.sampleOffset,position,data.numSamples)
                :data.numSamples;
            // Parameter changes at a given sample precede NoteOn at that sample.
            const bool useParameter=which>=0&&(!eventReady||at<=midiAt);
            render(useParameter?at:midiAt);
            if(useParameter) {
                auto& c=paramCursors_[which];
                apply(c.id,c.value);
                ++c.point;
                if(!advance(c)) {
                    c=paramCursors_[--activeQueues];
                }
            } else {
                const auto& e=currentEvent;
                if(synth_&&e.type==Event::kNoteOnEvent&&
                    e.noteOn.channel>=0&&e.noteOn.channel<16&&
                    e.noteOn.pitch>=0&&e.noteOn.pitch<=127&&
                    std::isfinite(e.noteOn.velocity)) {
                    const uint8_t vel=static_cast<uint8_t>(std::clamp(
                        int(std::lround(e.noteOn.velocity*127.f)),0,127));
                    if(AllowEmuNoteOn(sf2Configured_||gmLoaded_,
                        sf2Loaded_||gmLoaded_,
                        synth_->Core().ChipVariant()==Emu8000Core::Chip::Box86))
                        synth_->NoteOn(static_cast<uint8_t>(e.noteOn.channel),
                            static_cast<uint8_t>(e.noteOn.pitch),vel);
                } else if(synth_&&e.type==Event::kNoteOffEvent&&
                    e.noteOff.channel>=0&&e.noteOff.channel<16&&
                    e.noteOff.pitch>=0&&e.noteOff.pitch<=127) {
                    synth_->NoteOff(static_cast<uint8_t>(e.noteOff.channel),
                        static_cast<uint8_t>(e.noteOff.pitch));
                }
                advanceEvent();
            }
        }
        render(data.numSamples);
        if(hasOutput)for(int32 i=0;i<data.numSamples;++i)
            if(left[i]!=0.f||(right&&right[i]!=0.f)) {
                data.outputs[0].silenceFlags=0;
                break;
            }
        return kResultOk;
    }
private:
    struct ParameterCursor {
        IParamValueQueue* queue=nullptr;
        ParamID id=0;
        int32 point=0,count=0,offset=0;
        ParamValue value=0.;
    };
    std::array<ParameterCursor,1024> paramCursors_{};
    std::unique_ptr<Synth> synth_;
    std::vector<int16_t> scratch_;
    MasterOutput::Gain volumeGain_{};
    uint32_t rate_=44100,capacity_=0;
    AssetState::Data state_{};
    std::string assetError_;
    mutable std::mutex engineMutex_; // never block realtime rendering
    bool hostActive_=false; // may be true while no ROM / no core exists
    bool sf2Configured_=false,sf2Loaded_=false; // written outside process()
    bool gmLoaded_=false; // only true for validated ROM-backed 1MGM bank
    // Report the currently running chip, not merely paths in assets.cfg.
    // Call under engineMutex_ from non-realtime code only.
    std::string HardwareDescriptor() const {
        if(!synth_)return "RAM --  |  ROM: ERFORDERLICH  |  CORE: INAKTIV";
        const auto& core=synth_->Core();
        const bool box=core.ChipVariant()==Emu8000Core::Chip::Box86;
        if(!box)
            return state_.romPath.empty()
                ? "RAM --  |  ROM: NICHT GELADEN  |  CORE: INTERN"
                : "RAM --  |  ROM: LADEFEHLER  |  CORE: INTERN";
        size_t usedWords=0;
        for(size_t i=0;i<synth_->BankCount();++i)
            usedWords+=synth_->BankAt(i).sampleData.size();
        const double usedMiB=usedWords*2.0/1048576.0;
        const double totalMiB=core.ChipRamWords()*2.0/1048576.0;
        std::ostringstream info;
        info<<std::fixed<<std::setprecision(1)
            <<"SAMPLE-RAM "<<usedMiB<<"/"<<totalMiB<<" MiB"
            <<"   |   ROM: GELADEN   |   CORE: 86BOX";
        return info.str();
    }
    void ResolveAssets() {
        AssetConfig::Paths configured;
        if(!state_.pathsSpecified) {
            if(AssetConfig::Load(configured)) {
                state_.romPath=std::move(configured.rom);
                state_.sf2Path=std::move(configured.sf2);
                state_.ibkPath=std::move(configured.ibk);
                state_.drumIbkPath=std::move(configured.drumIbk);
                state_.pathsSpecified=true;
            } else assetError_="Invalid 125A assets.cfg";
        } else if((state_.ibkPath.empty()||state_.drumIbkPath.empty()) &&
                  AssetConfig::Load(configured)) {
            // Legacy V1-V4 state migration: leave project ROM/SF2 paths
            // untouched, only fill missing FM bank paths from configuration.
            if(state_.ibkPath.empty())state_.ibkPath=std::move(configured.ibk);
            if(state_.drumIbkPath.empty())
                state_.drumIbkPath=std::move(configured.drumIbk);
        }
    }
};
class Controller final : public EditControllerEx1, public IMidiMapping,
                         public VSTGUI::VST3EditorDelegate {
public:
    static FUnknown* createInstance(void*) {
        return static_cast<IEditController*>(new Controller);
    }
    // VST3 sends MIDI CC and pitchbend through mapped parameter queues.
    tresult PLUGIN_API queryInterface(const TUID iid, void** obj) override {
        QUERY_INTERFACE(iid,obj,IMidiMapping::iid,IMidiMapping)
        return EditControllerEx1::queryInterface(iid,obj);
    }
    uint32 PLUGIN_API addRef() override {return EditControllerEx1::addRef();}
    uint32 PLUGIN_API release() override {return EditControllerEx1::release();}
    tresult PLUGIN_API getMidiControllerAssignment(
        int32 busIndex,int16 midiChannel,CtrlNumber number,ParamID& id) override {
        if(busIndex!=0||midiChannel<0||midiChannel>=16)return kResultFalse;
        const int index=MidiControlMapping::Index(number);
        if(index<0)return kResultFalse;
        id=MidiControlMapping::ParamID(
            static_cast<uint32_t>(midiChannel),static_cast<uint32_t>(index));
        return kResultTrue;
    }
    tresult receiveText(const char8* msg) override {
        constexpr char ack[]="125A_SF2_ACK:";
        if(msg && std::strncmp(msg,ack,sizeof(ack)-1)==0) {
            std::lock_guard<std::mutex> lock(sf2StatusMutex_);
            sf2PendingAck_=msg+sizeof(ack)-1;
            return kResultOk;
        }
        constexpr char romAck[]="125A_ROM_ACK:";
        if(msg && std::strncmp(msg,romAck,sizeof(romAck)-1)==0) {
            std::lock_guard<std::mutex> lock(sf2StatusMutex_);
            romPendingAck_=msg+sizeof(romAck)-1;
            return kResultOk;
        }
        constexpr char hwInfoPrefix[]="125A_HW_INFO:";
        if(msg&&std::strncmp(msg,hwInfoPrefix,sizeof(hwInfoPrefix)-1)==0) {
            std::lock_guard<std::mutex> lock(sf2StatusMutex_);
            hardwareInfo_=msg+sizeof(hwInfoPrefix)-1;
            return kResultOk;
        }
        constexpr char prefix[]="125A_SF2_STATUS:";
        if(msg&&std::strncmp(msg,prefix,sizeof(prefix)-1)==0) {
            std::lock_guard<std::mutex> guard(sf2StatusMutex_);
            sf2AudioStatus_.assign(msg+sizeof(prefix)-1);
            return kResultOk;
        }
        return EditControllerEx1::receiveText(msg);
    }
    // Called only on the editor/UI thread. Keep the PresetCatalog object
    // stable: the VSTGUI browser stores a const reference to it.
    void AppendGmCatalog() {
        const auto gm=RomGmBank::AdjacentFile(romPath_);
        std::string error;
        if(!gm.empty() && RomGmBank::ValidDescriptor(gm,error))
            sfCatalog_.AppendRomGm(gm,error);
    }
    uint64_t CatalogRevision() {
        std::string ack,romAck;
        {
            std::lock_guard<std::mutex> lock(sf2StatusMutex_);
            ack.swap(sf2PendingAck_);
            romAck.swap(romPendingAck_);
        }
        if(ack=="OK" && !sf2PendingPath_.empty()) {
            sfCatalog_=std::move(sf2PendingCatalog_);
            sf2Path_=std::move(sf2PendingPath_);
            AppendGmCatalog();
            ++sfCatalogRevision_;
        } else if(!ack.empty()) sf2PendingPath_.clear();
        if(romAck=="OK" && !romPendingPath_.empty()) {
            romPath_=std::move(romPendingPath_);
            sfCatalog_=PresetCatalog{};
            std::string error;
            if(!sf2Path_.empty())sfCatalog_.LoadSoundFont(sf2Path_,error);
            AppendGmCatalog();
            ++sfCatalogRevision_;
        } else if(!romAck.empty()) romPendingPath_.clear();
        return sfCatalogRevision_;
    }
    std::string CurrentSf2Path() const {return sf2Path_;}
    bool RequestSf2Load(const std::string& path) {
        if(!AssetState::validPath(path)||path.empty()||!sf2PendingPath_.empty())
            return false;
        PresetCatalog candidate;
        std::string error;
        if(!candidate.LoadSoundFont(path,error)) {
            std::lock_guard<std::mutex> lock(sf2StatusMutex_);
            sf2AudioStatus_="SF2-Ladefehler: "+error;
            return false;
        }
        auto* msg=allocateMessage();
        if(!msg) {
            std::lock_guard<std::mutex> lock(sf2StatusMutex_);
            sf2AudioStatus_="SF2-Ladefehler: Host ohne Nachrichtenverbindung.";
            return false;
        }
        sf2PendingPath_=path;
        sf2PendingCatalog_=std::move(candidate);
        msg->setMessageID("125A_SF2_LOAD");
        msg->getAttributes()->setBinary("Path",path.data(),
                                         static_cast<uint32>(path.size()));
        const auto result=sendMessage(msg);
        msg->release();
        if(result!=kResultOk) {
            sf2PendingPath_.clear();
            std::lock_guard<std::mutex> lock(sf2StatusMutex_);
            sf2AudioStatus_="SF2-Ladefehler: Prozessor nicht erreichbar.";
            return false;
        }
        return true;
    }
    bool RequestRomLoad(const std::string& path) {
        if(!AssetState::validPath(path)||path.empty())return false;
        auto* msg=allocateMessage();
        if(!msg) {
            std::lock_guard<std::mutex> lock(sf2StatusMutex_);
            sf2AudioStatus_="ROM-Ladefehler: Kein VST3-Nachrichtenkanal.";
            return false;
        }
        romPendingPath_=path;
        msg->setMessageID("125A_ROM_LOAD");
        msg->getAttributes()->setBinary("Path",path.data(),
                                         static_cast<uint32>(path.size()));
        const auto result=sendMessage(msg);
        msg->release();
        if(result!=kResultOk) {
            romPendingPath_.clear();
            std::lock_guard<std::mutex> lock(sf2StatusMutex_);
            sf2AudioStatus_="ROM-Ladefehler: Audioprozessor nicht erreichbar.";
            return false;
        }
        // Asynchronous acknowledgement from the processor tells the user
        // whether ROM validation and the chip swap REALLY succeeded.
        return true;
    }
    void RequestHardwareInfo() {
        if(auto* message=allocateMessage()) {
            message->setMessageID("125A_HW_INFO_REQUEST");
            sendMessage(message);
            message->release();
        }
    }
    std::string HardwareInfo() const {
        std::lock_guard<std::mutex> lock(sf2StatusMutex_);
        return hardwareInfo_;
    }
    std::string Sf2AudioStatus() const {
        std::lock_guard<std::mutex> guard(sf2StatusMutex_);
        return sf2AudioStatus_;
    }
    tresult PLUGIN_API initialize(FUnknown* ctx) override {
        const auto r=EditControllerEx1::initialize(ctx);
        if(r!=kResultOk)return r;
        // COptionMenu displays and selects real steps only when the parameter
        // supplies readable values. The former generic numeric parameter
        // displayed normalized 0.000..1.000, not program numbers.
        // Keep ParamID 1000 and the unchanged 0..127 normalized mapping.
        auto* programs = new StringListParameter(STR16("Program"),kProgramID);
        for(int index=0;index<128;++index) {
            char ascii[8]{};
            std::snprintf(ascii,sizeof(ascii),"%03d",index);
            String128 label{};
            UString(label,128).fromAscii(ascii);
            programs->appendString(label);
        }
        parameters.addParameter(programs);
        // Stable discrete ID; GUI will display only banks from actual SF2 phdr.
        auto* banks=new RangeParameter(STR16("SF2 Bank"),kBankID,nullptr,
            0.,double(AssetState::kMaxBank),0.,
            static_cast<int32>(AssetState::kMaxBank));
        parameters.addParameter(banks);
        parameters.addParameter(new RangeParameter(STR16("Master Volume"),
            kVolumeID,STR16("%"),0.,100.,100.,0));
        // Stable hidden host parameters for 16 MIDI channels. Distinct IDs
        // prevent MIDI sustain or pitch bend on one channel changing another.
        for(uint32_t ch=0;ch<MidiControlMapping::kChannels;++ch)
            for(size_t i=0;i<MidiControlMapping::kControls.size();++i) {
                const auto& spec=MidiControlMapping::kControls[i];
                char label[128]{};
                std::snprintf(label,sizeof(label),"MIDI CH%02u %s",ch+1,spec.name);
                String128 title{};
                UString(title,128).fromAscii(label);
                parameters.addParameter(new RangeParameter(title,
                    MidiControlMapping::ParamID(ch,static_cast<uint32_t>(i)),
                    nullptr,0.,1.,MidiControlMapping::InitialNormalized(spec),0,
                    ParameterInfo::kCanAutomate|ParameterInfo::kIsHidden));
            }
        constexpr const char16* labels[kGuiCount]={
            STR16("Amp Attack"),STR16("Amp Decay"),STR16("Amp Sustain Reduction"),
            STR16("Amp Release"),STR16("Filter Attack"),STR16("Filter Decay"),
            STR16("Filter Sustain Reduction"),STR16("Filter Release"),
            STR16("Filter Cutoff Reduction"),STR16("Filter Resonance Boost"),
            STR16("Reverb Send Boost"),STR16("Chorus Send Boost")};
        for(int i=0;i<kGuiCount;++i)
            parameters.addParameter(new RangeParameter(labels[i],kGuiFirstID+i,
                STR16("%"),0.,100.,0.,100));
        ReloadPresetCatalogs(nullptr); // UI thread; indexed metadata only
        return kResultOk;
    }
    VSTGUI::CView* createCustomView(VSTGUI::UTF8StringPtr name,
        const VSTGUI::UIAttributes&,const VSTGUI::IUIDescription*,
        VSTGUI::VST3Editor*) override {
        if(name&&std::strcmp(name,"AwePresetBrowser")==0) {
            RequestHardwareInfo();
            return new PresetBrowserView({0,0,1200,780},this,sfCatalog_,fmCatalog_,
                FactoryBank(L"125A_Logo_Master_FINAL.svg"),
                [this]() {return Sf2AudioStatus();},
                [this]() {return HardwareInfo();},
                [this](const std::string& path) {return RequestRomLoad(path);},
                [this](const std::string& path) {return RequestSf2Load(path);},
                [this]() {return CurrentSf2Path();},
                [this]() {return CatalogRevision();});
        }
        return nullptr;
    }
    IPlugView* PLUGIN_API createView(FIDString name) override {
        if(name && std::strcmp(name,ViewType::kEditor)==0) {
            auto* editor=new VSTGUI::VST3Editor(this,"view","awe_test_panel.uidesc");
            editor->setDelegate(this);
            return editor;
        }
        return nullptr;
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
        for(int i=0;i<kGuiCount;++i)
            if(setParamNormalized(kGuiFirstID+i,
                double(model.controls[i])/AssetState::kControlScale)!=kResultOk)
                return kResultFalse;
        if(setParamNormalized(kBankID,
            static_cast<double>(model.bank)/AssetState::kMaxBank)!=kResultOk)
            return kResultFalse;
        if(setParamNormalized(kVolumeID,
            static_cast<double>(model.masterVolume)/MasterOutput::kScale)!=kResultOk)
            return kResultFalse;
        ReloadPresetCatalogs(&model); // no sound samples loaded
        return kResultOk;
    }
    // The future VSTGUI browser uses these exact names and bank indices.
    // They belong to the editor/controller, never the realtime processor.
    const PresetCatalog& SoundFontPresets() const noexcept {return sfCatalog_;}
    const PresetCatalog& FmPresets() const noexcept {return fmCatalog_;}
private:
    PresetCatalog sfCatalog_{},fmCatalog_{};
    std::string sf2Path_;
    std::string romPath_,romPendingPath_,romPendingAck_;
    std::string sf2PendingPath_;
    PresetCatalog sf2PendingCatalog_{};
    uint64_t sfCatalogRevision_=0;
    std::string sf2PendingAck_;
    mutable std::mutex sf2StatusMutex_;
    std::string sf2AudioStatus_="SF2-Audiostatus noch nicht vom Prozessor bestaetigt.";
    std::string hardwareInfo_;
    void ReloadPresetCatalogs(const AssetState::Data* model) {
        AssetConfig::Paths paths;
        if(!AssetConfig::ResolveController(model,paths))paths={};
        // Clear stale entries when a project points at a new/missing file.
        sfCatalog_=PresetCatalog{};
        fmCatalog_=PresetCatalog{};
        sf2Path_=paths.sf2;
        romPath_=paths.rom;
        std::string error;
        if(!paths.sf2.empty())sfCatalog_.LoadSoundFont(paths.sf2,error);
        AppendGmCatalog();
        ++sfCatalogRevision_;
        // Legacy FM preset data is no longer loaded into this AWE-only plugin.
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
