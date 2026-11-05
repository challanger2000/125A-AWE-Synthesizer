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
#include "MidiProgramRouting.h"
#include "MidiQueueOrdering.h"
#include "MidiLiveState.h"
#include "RealtimeEngineExchange.h"
#include "public.sdk/source/vst/vstparameters.h"
#include "public.sdk/source/main/moduleinit.h"
#include "pluginterfaces/base/ustring.h"
#include "vstgui/plugin-bindings/vst3editor.h"
#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <charconv>
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
#include "WinUiDispatch.h"
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
        addEventInput(STR16("MIDI"),16);
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
        {
            std::lock_guard<std::mutex> lock(engineMutex_);
            engines_.Publish({});
            activeRomReady_=false;
            reportedLatency_=0;
            hardwareStatus_="RAM --  |  ROM: ERFORDERLICH  |  CORE: INAKTIV";
            ++assetGeneration_;
        }
        return kResultOk;
    }
    tresult PLUGIN_API setActive(TBool active) override {
        // P119: the audio callback owns the running synth. Control threads
        // prepare and publish a new engine; they never mutate an active one.
        if(!active) {
            {
                std::lock_guard<std::mutex> lock(engineMutex_);
                hostActive_=false;
                ++assetGeneration_;
                engines_.Publish({});
                activeRomReady_=false;
                reportedLatency_=0;
                hardwareStatus_="RAM --  |  ROM: ERFORDERLICH  |  CORE: INAKTIV";
            }
            return AudioEffect::setActive(active);
        }
        AssetState::Data model;
        uint32_t sampleRate=44100;
        uint64_t epoch=0;
        {
            std::lock_guard<std::mutex> lock(engineMutex_);
            if(!capacity_)return kResultFalse;
            ResolveAssets();
            model=state_;
            sampleRate=rate_;
            epoch=assetGeneration_;
        }
        std::unique_ptr<Synth> prepared;
        bool loadedGm=false,loadedSf2=false;
        std::string status,error;
        if(model.romPath.empty())
            status="Original-Wave-ROM erforderlich: ROM LADEN. Bis dahin kein Audio.";
        else {
            try {
                prepared=std::make_unique<Synth>(sampleRate);
                prepared->Core().SetDriver(Awe32::Driver::Win95);
                if(!prepared->Core().UseBox86Chip(model.romPath,error) ||
                   prepared->Core().ChipVariant()!=Emu8000Core::Chip::Box86) {
                    error="ROM-Ladefehler: "+(error.empty() ?
                        std::string("86Box-EMU8000 konnte nicht starten"):error);
                    prepared.reset();
                } else {
                    prepared->Core().PowerOnInit();
                    const auto banks=RomGmBank::LoadBanks(
                        *prepared,model.romPath,model.sf2Path);
                    loadedGm=banks.gm;loadedSf2=banks.sf2;
                    if(!model.sf2Path.empty()&&!loadedSf2)
                        status="SF2-Ladefehler: "+banks.sf2Error;
                    else if(loadedGm&&loadedSf2)
                        status="86Box: originale GM-ROM-Bank und SF2 geladen.";
                    else if(loadedGm)
                        status="86Box: originale 1MGM-Bank (SYNTHGM.SBK) geladen.";
                    else if(loadedSf2)
                        status="86Box: SF2 geladen. SYNTHGM.SBK fehlt neben ROM.";
                    else status="86Box: ROM bereit. SYNTHGM.SBK neben ROM oder SF2 laden.";
                }
            } catch(const std::exception& e) {
                error="ROM-Ladefehler: "+std::string(e.what());
                prepared.reset();
            }
            if(!error.empty())status=error;
        }
        const auto info=DescribePrepared(prepared.get());
        const uint32_t latency=prepared?prepared->Core().ChipLatencyFrames():0u;
        std::string hardware;
        {
            std::lock_guard<std::mutex> lock(engineMutex_);
            if(epoch!=assetGeneration_||rate_!=sampleRate)return kResultFalse;
            hostActive_=true;
            const bool valid=bool(prepared);
            engines_.Publish(Pack(std::move(prepared),loadedGm,loadedSf2,
                                  !state_.sf2Path.empty()));
            activeRomReady_=valid;
            reportedLatency_=latency;
            hardwareStatus_=info;
            ++assetGeneration_;
            assetError_=error;
            hardware=hardwareStatus_;
        }
        sendTextMessage(("125A_SF2_STATUS:"+status).c_str());
        sendTextMessage(("125A_HW_INFO:"+hardware).c_str());
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
            int64 requestID=0;
            if(!msg->getAttributes() ||
               msg->getAttributes()->getInt("RequestID",requestID)!=kResultOk ||
               requestID<=0)return kInvalidArgument;
            const auto romAck=[&](const char* outcome) {
                sendTextMessage((std::string("125A_ROM_ACK:")+outcome+":"+
                                 std::to_string(requestID)).c_str());
            };
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
            uint64_t epoch=0;
            {
                std::lock_guard<std::mutex> lock(engineMutex_);
                model=state_;
                sampleRate=rate_;
                active=hostActive_;
                epoch=assetGeneration_;
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
                romAck("ERROR");
                return kResultOk;
            }
            std::string info;
            bool stale=false;
            const auto preparedInfo=DescribePrepared(prepared.get());
            const uint32_t latency=prepared?prepared->Core().ChipLatencyFrames():0u;
            {
                std::lock_guard<std::mutex> lock(engineMutex_);
                stale=(epoch!=assetGeneration_||active!=hostActive_||
                       sampleRate!=rate_);
                if(!stale) {
                    if(active) {
                        engines_.Publish(Pack(std::move(prepared),loadedGm,loadedSf2,
                                              !state_.sf2Path.empty()));
                        activeRomReady_=true;
                        reportedLatency_=latency;
                        hardwareStatus_=preparedInfo;
                    }
                    state_.romPath=path;
                    state_.pathsSpecified=true;
                    ++assetGeneration_;
                    info=HardwareDescriptor();
                }
            }
            if(stale) {
                sendTextMessage("125A_SF2_STATUS:ROM-Ladevorgang durch neueren Zustand ersetzt.");
                romAck("ERROR");
                return kResultOk;
            }
            sendTextMessage(("125A_HW_INFO:"+info).c_str());
            const std::string status=active ?
                (!sf2Error.empty() ?
                    ("ROM geladen. SF2-Ladefehler: "+sf2Error) :
                    (loadedGm ? "ROM + originale 1MGM GM-Bank geladen." :
                     "ROM geladen. SYNTHGM.SBK neben ROM ablegen.")) :
                "ROM validiert. Wird bei Aktivierung geladen.";
            sendTextMessage(("125A_SF2_STATUS:"+status).c_str());
            romAck("OK");
            return kResultOk;
        }
        if(!msg || !FIDStringsEqual(msg->getMessageID(),"125A_SF2_LOAD"))
            return AudioEffect::notify(msg);
        int64 requestID=0;
        if(!msg->getAttributes() ||
           msg->getAttributes()->getInt("RequestID",requestID)!=kResultOk ||
           requestID<=0)return kInvalidArgument;
        const auto sf2Ack=[&](const char* outcome) {
            sendTextMessage((std::string("125A_SF2_ACK:")+outcome+":"+
                             std::to_string(requestID)).c_str());
        };
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
        uint64_t epoch=0;
        {
            std::lock_guard<std::mutex> lock(engineMutex_);
            sampleRate=rate_;
            model=state_;
            active=hostActive_;
            epoch=assetGeneration_;
            romReady=activeRomReady_;
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
                sf2Ack("ERROR");
                return kResultOk;
            }
            replacement->SelectBrowserBank(static_cast<uint16_t>(model.bank));
            for(int c=0;c<16;++c)
                replacement->ProgramChange(static_cast<uint8_t>(c),
                                            static_cast<uint8_t>(model.program));
        }
        bool stale=false;
        const auto preparedInfo=replacement?DescribePrepared(replacement.get()):
            std::string{};
        const uint32_t latency=replacement?
            replacement->Core().ChipLatencyFrames():0u;
        {
            std::lock_guard<std::mutex> lock(engineMutex_);
            stale=(epoch!=assetGeneration_||active!=hostActive_||
                   sampleRate!=rate_);
            if(!stale) {
                if(replacement) {
                    engines_.Publish(Pack(std::move(replacement),loadedGm,true,true));
                    activeRomReady_=true;
                    reportedLatency_=latency;
                    hardwareStatus_=preparedInfo;
                }
                state_.sf2Path=path;
                state_.pathsSpecified=true;
                ++assetGeneration_;
            }
        }
        if(stale) {
            sendTextMessage("125A_SF2_STATUS:SF2-Ladevorgang durch neueren Zustand ersetzt.");
            sf2Ack("ERROR");
            return kResultOk;
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
        sf2Ack("OK");
        return kResultOk;
    }
    uint32 PLUGIN_API getLatencySamples() override {
        std::lock_guard<std::mutex> lock(engineMutex_);
        return reportedLatency_;
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
        // The audio callback publishes numeric host parameters atomically.
        // This snapshot has the same V1-V9 binary layout, without reading
        // mutable audio-thread memory on a control thread.
        snapshot.program=rtProgram_.load(std::memory_order_acquire);
        snapshot.bank=rtBank_.load(std::memory_order_acquire);
        snapshot.masterVolume=rtMaster_.load(std::memory_order_acquire);
        snapshot.channelProgramMask=
            rtChannelProgramMask_.load(std::memory_order_acquire);
        for(int ch=0;ch<16;++ch)
            snapshot.channelPrograms[ch]=rtChannelPrograms_[ch].load(
                std::memory_order_acquire);
        for(int i=0;i<kGuiCount;++i)
            snapshot.controls[i]=rtControls_[i].load(std::memory_order_acquire);
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
        // P118-04: read an entire candidate without an audio mutex and
        // prepare any new ROM/SF2 engine BEFORE publishing saved paths.
        const auto receive=[&](void* buffer,size_t n) {
            int32 received=0;
            return n<=AssetState::kMaxPath &&
                stream->read(buffer,static_cast<int32>(n),&received)==kResultOk &&
                received==static_cast<int32>(n);
        };
        AssetState::Data candidate;
        if(!AssetState::Read(receive,candidate))return kResultFalse;
        candidate.engine=0; // Old FM projects migrate to EMU8000.
        if(!candidate.pathsSpecified) {
            AssetConfig::Paths configured;
            if(AssetConfig::Load(configured)) {
                candidate.romPath=std::move(configured.rom);
                candidate.sf2Path=std::move(configured.sf2);
                candidate.ibkPath=std::move(configured.ibk);
                candidate.drumIbkPath=std::move(configured.drumIbk);
                candidate.pathsSpecified=true;
            }
        }
        uint32_t sampleRate=44100;
        bool active=false;
        uint64_t epoch=0;
        {
            std::lock_guard<std::mutex> lock(engineMutex_);
            sampleRate=rate_;
            active=hostActive_;
            epoch=assetGeneration_;
        }
        std::unique_ptr<Synth> prepared;
        bool loadedSf2=false,loadedGm=false;
        if(active && !candidate.romPath.empty()) {
            try {
                prepared=std::make_unique<Synth>(sampleRate);
                prepared->Core().SetDriver(Awe32::Driver::Win95);
                std::string error;
                if(!prepared->Core().UseBox86Chip(candidate.romPath,error) ||
                   prepared->Core().ChipVariant()!=Emu8000Core::Chip::Box86)
                    return kResultFalse; // old playing assets remain coherent
                prepared->Core().PowerOnInit();
                const auto banks=RomGmBank::LoadBanks(
                    *prepared,candidate.romPath,candidate.sf2Path);
                loadedSf2=banks.sf2;
                loadedGm=banks.gm;
                if(!candidate.sf2Path.empty()&&!loadedSf2)
                    return kResultFalse;
                for(int i=0;i<kGuiCount;++i)
                    prepared->SetGuiControl(
                        i,float(candidate.controls[i])/AssetState::kControlScale);
                prepared->SelectBrowserBank(static_cast<uint16_t>(candidate.bank));
                for(int ch=0;ch<16;++ch)
                    prepared->ProgramChange(static_cast<uint8_t>(ch),
                        static_cast<uint8_t>(candidate.program));
            } catch(const std::exception&) {return kResultFalse;}
        }
        std::string info,status;
        const auto preparedInfo=DescribePrepared(prepared.get());
        const uint32_t latency=prepared?prepared->Core().ChipLatencyFrames():0u;
        {
            std::lock_guard<std::mutex> lock(engineMutex_);
            if(epoch!=assetGeneration_||active!=hostActive_||rate_!=sampleRate)
                return kResultFalse;
            // Publish control values before the new engine is visible to the
            // audio callback; that callback restores MIDI state itself.
            rtProgram_.store(candidate.program,std::memory_order_release);
            rtBank_.store(candidate.bank,std::memory_order_release);
            rtMaster_.store(candidate.masterVolume,std::memory_order_release);
            rtChannelProgramMask_.store(
                candidate.channelProgramMask,std::memory_order_release);
            for(int ch=0;ch<16;++ch)
                rtChannelPrograms_[ch].store(
                    candidate.channelPrograms[ch],std::memory_order_release);
            // A recalled browser bank supersedes any older touched CC0.
            browserSelectionEpoch_.fetch_add(1,std::memory_order_acq_rel);
            for(int i=0;i<kGuiCount;++i)
                rtControls_[i].store(candidate.controls[i],std::memory_order_release);
            gainRestoreValue_.store(candidate.masterVolume,std::memory_order_release);
            gainRestoreEpoch_.fetch_add(1,std::memory_order_acq_rel);
            if(active) {
                const bool valid=bool(prepared);
                engines_.Publish(Pack(std::move(prepared),loadedGm,loadedSf2,
                                      !candidate.sf2Path.empty()));
                activeRomReady_=valid;
                reportedLatency_=latency;
                hardwareStatus_=preparedInfo;
            }
            state_=std::move(candidate);
            ++assetGeneration_;
            info=HardwareDescriptor();
            status=active
                ?(activeRomReady_
                    ?(loadedGm?"ROM + original GM loaded.":"Wave-ROM loaded.")
                    :"Original-Wave-ROM erforderlich: ROM LADEN. Bis dahin kein Audio.")
                :"Project assets restored; ready on activation.";
        }
        sendTextMessage(("125A_HW_INFO:"+info).c_str());
        sendTextMessage(("125A_SF2_STATUS:"+status).c_str());
        return kResultOk;
    }
    tresult PLUGIN_API process(ProcessData& data) override {
        if(data.numSamples<0 || uint32_t(data.numSamples)>capacity_)
            return kInvalidArgument;
        // P119: no control mutex is acquired on the audio callback.
        // The guard prevents a live synth being destroyed during this block.
        auto engineRead=engines_.Read();
        Engine* const entry=engineRead.get();
        Synth* const synth_=entry?entry->synth.get():nullptr;
        const uint64_t restore=gainRestoreEpoch_.load(std::memory_order_acquire);
        if(restore!=lastGainRestoreEpoch_) {
            volumeGain_.restore(gainRestoreValue_.load(std::memory_order_acquire));
            lastGainRestoreEpoch_=restore;
        }
        const uint64_t bankEpoch=
            browserSelectionEpoch_.load(std::memory_order_acquire);
        if(bankEpoch!=lastBrowserSelectionEpoch_) {
            liveMidi_.BrowserBankSelected();
            lastBrowserSelectionEpoch_=bankEpoch;
        }
        const uint64_t revision=entry?entry->revision:0;
        if(revision!=lastRtRevision_) {
            if(synth_)ApplyRtParameters(*synth_);
            lastRtRevision_=revision;
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
                cursor.sourceOrdinal=i;
                if(advance(cursor))paramCursors_[activeQueues++]=cursor;
            }
        }
        // Continuous VST3 parameters are interpolated between points.
        // Master runs per output frame; SF2 overlay curves are sampled at
        // each NoteOn (the hardware overlay is applied to new voices).
        MasterOutput::Curve masterCurve;
        bool masterCurveActive=false;
        std::array<MasterOutput::Curve,kGuiCount> overlayCurves{};
        std::array<bool,kGuiCount> overlayEnabled{};
        std::array<MasterOutput::Curve,16> pitchCurves{};
        std::array<bool,16> pitchEnabled{};
        std::array<bool,16> pitchMoving{}; // quantized pitch changes inside block
        // Pitch queues are consumed as a mathematical curve, NOT as separate
        // queue events: even 128 redundant constant points must never split
        // a PanVxd/86Box render into 128 one-frame register transactions.
        const auto readPoint=+[](void* context,int32_t index,
                                 int32_t& offset,double& value)->bool {
            auto* queue=static_cast<IParamValueQueue*>(context);
            ParamValue normalized=0.;
            if(queue->getPoint(index,offset,normalized)!=kResultOk)return false;
            value=normalized;
            return true;
        };
        int32 retainedQueues=0;
        for(int32 i=0;i<activeQueues;++i) {
            const auto c=paramCursors_[i];
            if(c.id==kVolumeID) {
                masterCurve.reset(c.queue,readPoint,c.count,
                    double(rtMaster_.load(std::memory_order_relaxed))/
                    MasterOutput::kScale);
                masterCurveActive=true;
            } else if(c.id>=kGuiFirstID&&c.id<kGuiFirstID+kGuiCount) {
                const int idx=int(c.id-kGuiFirstID);
                overlayCurves[idx].reset(c.queue,readPoint,c.count,
                    double(rtControls_[idx].load(std::memory_order_relaxed))/
                    AssetState::kControlScale);
                overlayEnabled[idx]=true;
            }
            const auto midi=MidiControlMapping::Decode(c.id);
            if(midi.valid&&midi.number==129) {
                const int ch=midi.channel;
                const auto previous=liveMidi_.Get(
                    static_cast<unsigned>(ch)).values[
                    MidiControlMapping::Index(129)];
                pitchCurves[ch].reset(c.queue,readPoint,c.count,previous);
                pitchEnabled[ch]=true;
                // A constant queue (including a single change at frame 0)
                // does not require one-sample render calls. Detect *all*
                // knots, not only endpoints; a triangular bend could start
                // and end at the same value but move in between.
                auto probe=pitchCurves[ch];
                const auto base=MidiControlMapping::PitchBend(probe.valueAt(0));
                bool moving=MidiControlMapping::PitchBend(probe.valueAt(
                    std::max<int32>(0,data.numSamples-1)))!=base;
                for(int32 p=0;p<c.count && !moving;++p) {
                    int32 offset=0;ParamValue value=0.;
                    if(c.queue->getPoint(p,offset,value)!=kResultOk ||
                       !std::isfinite(value)||offset<0||
                       offset>=data.numSamples)continue;
                    moving=MidiControlMapping::PitchBend(value)!=base;
                }
                pitchMoving[ch]=moving;
                // Do not retain PitchBend points in the generic queue:
                // they are consumed by pitchCurves below. This prevents
                // dense points on a silent channel splitting audio blocks.
                continue;
            }
            paramCursors_[retainedQueues++]=c;
        }
        activeQueues=retainedQueues;
        auto apply=[&](ParamID id,ParamValue val) {
            if(id==kProgramID) {
                const auto program=static_cast<uint32_t>(std::clamp(
                    int(std::lround(val*127.)),0,127));
                rtProgram_.store(program,std::memory_order_release);
                rtChannelProgramMask_.store(0,std::memory_order_release);
                for(int ch=0;ch<16;++ch)
                    rtChannelPrograms_[ch].store(program,std::memory_order_release);
                if(synth_)for(int ch=0;ch<16;++ch)
                    synth_->ProgramChange(static_cast<uint8_t>(ch),
                        static_cast<uint8_t>(program));
            } else if(id==kBankID) {
                const auto bank=static_cast<uint32_t>(std::clamp(
                    int(std::lround(val*AssetState::kMaxBank)),0,
                    int(AssetState::kMaxBank)));
                if(bank!=rtBank_.load(std::memory_order_relaxed)) {
                    // A later browser selection invalidates earlier CC0/32.
                    liveMidi_.BrowserBankSelected();
                    rtBank_.store(bank,std::memory_order_release);
                    if(synth_)synth_->SelectBrowserBank(static_cast<uint16_t>(bank));
                }
            } else if(const int ch=MidiProgramRouting::Channel(id);ch>=0) {
                const auto program=static_cast<uint32_t>(
                    std::clamp(int(std::lround(val*127.)),0,127));
                rtChannelPrograms_[ch].store(program,std::memory_order_release);
                rtChannelProgramMask_.fetch_or(1u<<ch,std::memory_order_acq_rel);
                if(synth_)synth_->ProgramChange(static_cast<uint8_t>(ch),
                                                static_cast<uint8_t>(program));
            } else if(id==kVolumeID) {
                const auto gain=static_cast<uint32_t>(std::lround(
                    val*MasterOutput::kScale));
                rtMaster_.store(gain,std::memory_order_release);
                volumeGain_.setTarget(gain);
            } else if(id>=kGuiFirstID && id<kGuiFirstID+kGuiCount) {
                const int idx=int(id-kGuiFirstID);
                rtControls_[idx].store(static_cast<uint32_t>(
                    std::lround(val*AssetState::kControlScale)),
                    std::memory_order_release);
                if(synth_)synth_->SetGuiControl(idx,static_cast<float>(val));
            } else {
                const auto midi=MidiControlMapping::Decode(id);
                if(!midi.valid)return;
                // Remember parameter-only MIDI even without a ROM/engine.
                // One-shot CC 120/123 are forwarded but never replayed.
                liveMidi_.Accept(static_cast<unsigned>(midi.channel),
                                 midi.number,val);
                if(!synth_)return;
                const uint8_t channel=static_cast<uint8_t>(midi.channel);
                if(midi.number==129)
                    synth_->PitchBendAutomated(channel,MidiControlMapping::PitchBend(val));
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
                bool movingPlayingVoices=false;
                for(int ch=0;ch<16;++ch)
                    if(pitchMoving[ch]&&
                       synth_->HasPlayingVoicesOnChannel(static_cast<uint8_t>(ch)))
                        movingPlayingVoices=true;
                if(movingPlayingVoices) {
                    // Preserve real-time interpolation *only* where a voice
                    // is actually playing a changing bend. Completely silent
                    // MIDI channels never write IP or fragment the renderer.
                    for(int32 frame=position;frame<end;++frame) {
                        for(int ch=0;ch<16;++ch)
                            if(pitchEnabled[ch]&&synth_->HasPlayingVoicesOnChannel(
                                static_cast<uint8_t>(ch))) {
                                const int16_t bend=MidiControlMapping::PitchBend(
                                    pitchCurves[ch].valueAt(frame));
                                synth_->PitchBendAutomated(static_cast<uint8_t>(ch),bend);
                            }
                        synth_->RenderBlock(
                            scratch_.data()+2*size_t(frame),1);
                    }
                } else {
                    for(int ch=0;ch<16;++ch)if(pitchEnabled[ch])
                        synth_->PitchBendAutomated(static_cast<uint8_t>(ch),
                            MidiControlMapping::PitchBend(
                                pitchCurves[ch].valueAt(position)));
                    synth_->RenderBlock(
                        scratch_.data()+2*size_t(position),
                        static_cast<uint32_t>(end-position));
                }
                for(int32 i=position;i<end;++i) {
                    // Host automation is already a continuous curve.
                    // Manual/discrete changes retain the 64-frame dezipper.
                    const float gain=masterCurveActive
                        ?volumeGain_.nextAutomated(masterCurve.valueAt(i))
                        :volumeGain_.next();
                    const float l=(scratch_[size_t(i)*2]/32768.f)*gain;
                    const float r=(scratch_[size_t(i)*2+1]/32768.f)*gain;
                    if(right){left[i]=l;right[i]=r;}
                    else left[i]=(l+r)*0.5f;
                }
            }
            // Advance the stored pitch even if its channel had no voices.
            // A subsequent NoteOn at the next event uses this bend.
            if(end>position)
                for(int ch=0;ch<16;++ch)if(pitchEnabled[ch]) {
                    const auto normalized=pitchCurves[ch].valueAt(end-1);
                    if(synth_)synth_->PitchBendAutomated(
                        static_cast<uint8_t>(ch),
                        MidiControlMapping::PitchBend(normalized));
                    liveMidi_.Accept(static_cast<unsigned>(ch),129,normalized);
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
                const auto& cur=paramCursors_[i];
                if(which<0||MidiQueueOrdering::Earlier(
                    time,cur.id,cur.sourceOrdinal,
                    at,paramCursors_[which].id,
                    paramCursors_[which].sourceOrdinal)) {
                    which=i;at=time;
                }
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
                    for(int k=0;k<kGuiCount;++k)if(overlayEnabled[k]) {
                        const auto value=overlayCurves[k].valueAt(position);
                        rtControls_[k].store(static_cast<uint32_t>(std::lround(
                            value*AssetState::kControlScale)),
                            std::memory_order_relaxed);
                        synth_->SetGuiControl(k,static_cast<float>(value));
                    }
                    // Pitch at NoteOn must match the continuous curve at
                    // this exact sample even if there were no older voices.
                    const unsigned channel=static_cast<unsigned>(e.noteOn.channel);
                    if(pitchEnabled[channel])synth_->PitchBendAutomated(
                        static_cast<uint8_t>(channel),
                        MidiControlMapping::PitchBend(
                            pitchCurves[channel].valueAt(position)));
                    const uint8_t vel=static_cast<uint8_t>(std::clamp(
                        int(std::lround(e.noteOn.velocity*127.f)),0,127));
                    if(AllowEmuNoteOn(entry&&(entry->sf2Configured||entry->gmLoaded),
                        entry&&(entry->sf2Loaded||entry->gmLoaded),
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
        int32 point=0,count=0,offset=0,sourceOrdinal=0;
        ParamValue value=0.;
    };
    std::array<ParameterCursor,1024> paramCursors_{};
    struct Engine {
        std::unique_ptr<Synth> synth;
        bool sf2Configured=false,sf2Loaded=false,gmLoaded=false;
        uint64_t revision=0;
    };
    RealtimeEngineExchange<Engine> engines_;
    uint64_t lastRtRevision_=0; // audio-thread-only engine revision
    uint64_t nextRevision_=0;
    std::vector<int16_t> scratch_;
    MasterOutput::Gain volumeGain_{};
    uint32_t rate_=44100,capacity_=0;
    AssetState::Data state_{};  // non-RT asset-path domain only
    std::string assetError_;
    mutable std::mutex engineMutex_; // control threads only, never audio process
    bool hostActive_=false;
    bool activeRomReady_=false;
    uint32_t reportedLatency_=0;
    std::string hardwareStatus_="RAM --  |  ROM: ERFORDERLICH  |  CORE: INAKTIV";
    uint64_t assetGeneration_=0;
    MidiLiveState liveMidi_{}; // exclusively audio-thread owned
    // Real-time parameters are single-word atomics; getState/load paths never
    // touch a mutable synth or wait for a reader to release a mutex.
    std::atomic<uint32_t> rtProgram_{0},rtBank_{0};
    std::atomic<uint32_t> rtMaster_{MasterOutput::kDefault};
    std::array<std::atomic<uint32_t>,16> rtChannelPrograms_{};
    std::atomic<uint32_t> rtChannelProgramMask_{0};
    std::atomic<uint64_t> browserSelectionEpoch_{0};
    uint64_t lastBrowserSelectionEpoch_=0; // audio thread only
    std::array<std::atomic<uint32_t>,kGuiCount> rtControls_{};
    std::atomic<uint64_t> gainRestoreEpoch_{0};
    std::atomic<uint32_t> gainRestoreValue_{MasterOutput::kDefault};
    uint64_t lastGainRestoreEpoch_=0;
    std::unique_ptr<Engine> Pack(std::unique_ptr<Synth> synth,
                                 bool gm,bool sf2,bool configured) {
        if(!synth)return {};
        auto e=std::make_unique<Engine>();
        e->synth=std::move(synth);
        e->gmLoaded=gm;e->sf2Loaded=sf2;e->sf2Configured=configured;
        e->revision=++nextRevision_;
        return e;
    }
    void ApplyRtParameters(Synth& target) noexcept {
        for(int i=0;i<kGuiCount;++i)
            target.SetGuiControl(i,
                float(rtControls_[i].load(std::memory_order_relaxed))/
                      AssetState::kControlScale);
        target.SelectBrowserBank(static_cast<uint16_t>(
            rtBank_.load(std::memory_order_relaxed)));
        const uint32_t mask=rtChannelProgramMask_.load(std::memory_order_relaxed);
        for(int ch=0;ch<16;++ch)
            target.ProgramChange(static_cast<uint8_t>(ch),
                static_cast<uint8_t>(
                    (mask&(1u<<ch))
                        ?rtChannelPrograms_[ch].load(std::memory_order_relaxed)
                        :rtProgram_.load(std::memory_order_relaxed)));
        liveMidi_.Replay(target);
    }
    static std::string DescribePrepared(Synth* synth) {
        if(!synth)return "RAM --  |  ROM: ERFORDERLICH  |  CORE: INAKTIV";
        const auto& core=synth->Core();
        if(core.ChipVariant()!=Emu8000Core::Chip::Box86)
            return "RAM --  |  ROM: LADEFEHLER  |  CORE: INTERN";
        size_t usedWords=0;
        for(size_t i=0;i<synth->BankCount();++i)
            usedWords+=synth->BankAt(i).sampleData.size();
        const double usedMiB=usedWords*2.0/1048576.0;
        const double totalMiB=core.ChipRamWords()*2.0/1048576.0;
        std::ostringstream info;
        info<<std::fixed<<std::setprecision(1)
            <<"SAMPLE-RAM "<<usedMiB<<"/"<<totalMiB<<" MiB"
            <<"   |   ROM: GELADEN   |   CORE: 86BOX";
        return info.str();
    }
    std::string HardwareDescriptor() const {
        return hardwareStatus_; // cached on control thread before publication
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
    tresult PLUGIN_API getUnitByBus(
        MediaType type,BusDirection dir,int32 busIndex,
        int32 channel,UnitID& unitId) override {
        if(type!=kEvent||dir!=kInput||busIndex!=0||
           channel<0||channel>=MidiProgramRouting::kChannels)
            return kResultFalse;
        unitId=static_cast<UnitID>(
            MidiProgramRouting::Unit(static_cast<unsigned>(channel)));
        return kResultTrue;
    }
    tresult PLUGIN_API setParamNormalized(
        ParamID id,ParamValue value) override {
        const auto result=EditControllerEx1::setParamNormalized(id,value);
        if(result==kResultOk&&id==kProgramID) {
            // Legacy GUI-wide Program control still selects all channels.
            // Keep the 16 new Program Change parameters in sync for host
            // inspection; the processor receives just the original ID 1000.
            for(unsigned ch=0;ch<16;++ch)
                EditControllerEx1::setParamNormalized(
                    MidiProgramRouting::ParamID(ch),value);
        }
        return result;
    }
    tresult receiveText(const char8* msg) override {
        // P119: ACKs are correlated to their original request and ignored
        // after a newer host project recall. Thread synchronization covers
        // the pending IDs; the owning UI thread applies only matched replies.
        const auto parseAck=[](const char* raw,const char* prefix)
            -> std::pair<int64,std::string> {
            const size_t len=std::strlen(prefix);
            if(!raw||std::strncmp(raw,prefix,len)!=0)return {0,{}};
            const char* result=raw+len;
            const char* colon=std::strchr(result,':');
            if(!colon)return {0,{}};
            const std::string status(result,colon);
            if(status!="OK"&&status!="ERROR")return {0,{}};
            int64 id=0;
            const char* number=colon+1;
            const auto parsed=std::from_chars(number,
                number+std::strlen(number),id);
            if(parsed.ec!=std::errc{} || *number=='\0' ||
               parsed.ptr!=number+std::strlen(number) || id<=0)
                return {0,{}};
            return {id,status};
        };
        if(msg && std::strncmp(msg,"125A_SF2_ACK:",13)==0) {
            const auto [id,status]=parseAck(msg,"125A_SF2_ACK:");
            bool post=false;
            {
                std::lock_guard<std::mutex> lock(sf2StatusMutex_);
                if(id>0&&id==sf2PendingRequestID_) {
                    sf2PendingAck_=status;
                    if(status=="OK") {
                        hostDirtyPending_=true;
                        ++hostDirtySeq_;
                        post=true;
                    }
                }
            }
            if(post)hostDispatch_.Post();
            return kResultOk;
        }
        if(msg && std::strncmp(msg,"125A_ROM_ACK:",13)==0) {
            const auto [id,status]=parseAck(msg,"125A_ROM_ACK:");
            bool post=false;
            {
                std::lock_guard<std::mutex> lock(sf2StatusMutex_);
                if(id>0&&id==romPendingRequestID_) {
                    romPendingAck_=status;
                    if(status=="OK") {
                        hostDirtyPending_=true;
                        ++hostDirtySeq_;
                        post=true;
                    }
                }
            }
            if(post)hostDispatch_.Post();
            return kResultOk;
        }
        constexpr char hwInfoPrefix[]="125A_HW_INFO:";
        if(msg&&std::strncmp(msg,hwInfoPrefix,sizeof(hwInfoPrefix)-1)==0) {
            bool post=false;
            {
                std::lock_guard<std::mutex> lock(sf2StatusMutex_);
                const bool wasReady=hardwareInfo_.find("ROM: GELADEN")!=std::string::npos;
                const std::string newInfo=msg+sizeof(hwInfoPrefix)-1;
                const bool nowReady=newInfo.find("ROM: GELADEN")!=std::string::npos;
                if(wasReady!=nowReady) {
                    latencyChangePending_=true;
                    ++hostLatencySeq_;
                    post=true;
                }
                hardwareInfo_=newInfo;
            }
            if(post)hostDispatch_.Post();
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
            if(!ack.empty())sf2PendingRequestID_=0;
            if(!romAck.empty())romPendingRequestID_=0;
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
        // Host notifications run through a persistent UI message-only window
        // even when the PresetBrowser editor has already been closed.
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
        int64 requestID=0;
        {
            std::lock_guard<std::mutex> guard(sf2StatusMutex_);
            requestID=++nextRequestID_;
            sf2PendingRequestID_=requestID;
            sf2PendingAck_.clear();
        }
        msg->setMessageID("125A_SF2_LOAD");
        msg->getAttributes()->setInt("RequestID",requestID);
        msg->getAttributes()->setBinary("Path",path.data(),
                                         static_cast<uint32>(path.size()));
        const auto result=sendMessage(msg);
        msg->release();
        if(result!=kResultOk) {
            sf2PendingPath_.clear();
            std::lock_guard<std::mutex> lock(sf2StatusMutex_);
            sf2PendingRequestID_=0;
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
        int64 requestID=0;
        {
            std::lock_guard<std::mutex> guard(sf2StatusMutex_);
            requestID=++nextRequestID_;
            romPendingRequestID_=requestID;
            romPendingAck_.clear();
        }
        msg->setMessageID("125A_ROM_LOAD");
        msg->getAttributes()->setInt("RequestID",requestID);
        msg->getAttributes()->setBinary("Path",path.data(),
                                         static_cast<uint32>(path.size()));
        const auto result=sendMessage(msg);
        msg->release();
        if(result!=kResultOk) {
            romPendingPath_.clear();
            std::lock_guard<std::mutex> lock(sf2StatusMutex_);
            romPendingRequestID_=0;
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
#if defined(_WIN32)
        if(!hostDispatch_.Start(this,&Controller::HostSignalThunk,
            reinterpret_cast<HINSTANCE>(Steinberg::getPlatformModuleHandle()),
            +[](void* owner){static_cast<Controller*>(owner)->addRef();},
            +[](void* owner){static_cast<Controller*>(owner)->release();}))
            return kResultFalse; // never silently lose host notifications
#endif
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
        // Standard VST3 multitimbral MIDI Program Change contract:
        // 16 event-channel Units, each referencing a stable ProgramList and
        // an automatable, discrete kIsProgramChange parameter. The historic
        // GUI-wide Program parameter ID 1000 is preserved independently.
        addUnit(new Unit(STR16("125A AWE Synthesizer"),
            kRootUnitId,kNoParentUnitId,kNoProgramListId));
        for(unsigned ch=0;ch<16;++ch) {
            char channelLabel[64]{};
            std::snprintf(channelLabel,sizeof(channelLabel),
                "MIDI Channel %u",ch+1);
            String128 unitName{};
            UString(unitName,128).fromAscii(channelLabel);
            const auto unitId=static_cast<UnitID>(MidiProgramRouting::Unit(ch));
            const auto listId=static_cast<ProgramListID>(
                MidiProgramRouting::ProgramList(ch));
            addUnit(new Unit(unitName,unitId,kRootUnitId,listId));
            auto* list=new ProgramList(STR16("MIDI Programs"),listId,unitId);
            for(int programIndex=0;programIndex<128;++programIndex) {
                char programLabel[8]{};
                std::snprintf(programLabel,sizeof(programLabel),
                    "%03d",programIndex);
                String128 title{};
                UString(title,128).fromAscii(programLabel);
                list->addProgram(title);
            }
            addProgramList(list);
            char controlLabel[80]{};
            std::snprintf(controlLabel,sizeof(controlLabel),
                "MIDI CH%02u Program Change",ch+1);
            String128 title{};
            UString(title,128).fromAscii(controlLabel);
            parameters.addParameter(new RangeParameter(
                title,MidiProgramRouting::ParamID(ch),nullptr,
                0.,127.,0.,127,
                ParameterInfo::kCanAutomate|ParameterInfo::kIsProgramChange,
                unitId));
        }
        // Stable discrete ID; GUI will display only banks from actual SF2 phdr.
        auto* banks=new RangeParameter(STR16("SF2 Bank"),kBankID,nullptr,
            0.,double(AssetState::kMaxBank),0.,
            static_cast<int32>(AssetState::kMaxBank));
        parameters.addParameter(banks);
        parameters.addParameter(new RangeParameter(STR16("Master Volume"),
            kVolumeID,STR16("%"),0.,100.,100.,0));
        // Stable automatable host parameters for 16 MIDI channels. VST3
        // kIsHidden would imply read-only and break IMidiMapping. Distinct IDs
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
                    nullptr,0.,1.,MidiControlMapping::InitialNormalized(spec),
                    spec.number==129?0:127, // CC values are discrete; pitch bend is continuous
                    ParameterInfo::kCanAutomate));
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
        for(unsigned ch=0;ch<16;++ch) {
            const auto program=(model.channelProgramMask&(1u<<ch))
                ?model.channelPrograms[ch]:model.program;
            if(setParamNormalized(MidiProgramRouting::ParamID(ch),
                static_cast<double>(program)/127.)!=kResultOk)
                return kResultFalse;
        }
        // A delayed ACK for the previously loaded bank may arrive later:
        // it must not roll this freshly restored project back.
        {
            std::lock_guard<std::mutex> guard(sf2StatusMutex_);
            ++nextRequestID_;
            romPendingRequestID_=sf2PendingRequestID_=0;
            sf2PendingAck_.clear();
            romPendingAck_.clear();
            hostDirtyPending_=false; // old ACK predates this new project
            ++hostDirtySeq_;
        }
        romPendingPath_.clear();
        sf2PendingPath_.clear();
        sf2PendingCatalog_=PresetCatalog{};
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
    int64 nextRequestID_=0;
    int64 romPendingRequestID_=0,sf2PendingRequestID_=0;
    mutable std::mutex sf2StatusMutex_;
    std::string sf2AudioStatus_="SF2-Audiostatus noch nicht vom Prozessor bestaetigt.";
    std::string hardwareInfo_;
    bool latencyChangePending_=false;
    bool hostDirtyPending_=false;
    uint64_t hostDirtySeq_=0,hostLatencySeq_=0;
    WinUiDispatch hostDispatch_{};
    static bool HostSignalThunk(void* self) {
        return static_cast<Controller*>(self)->DeliverHostSignals();
    }
    bool DeliverHostSignals() {
        // A host may synchronously drop its last controller reference inside
        // restartComponent(); this method itself must own a reference until
        // it has finished inspecting the pending state.
        addRef();
        bool dirty=false,latency=false;
        uint64_t dirtySeq=0,latencySeq=0;
        {
            std::lock_guard<std::mutex> guard(sf2StatusMutex_);
            dirty=hostDirtyPending_;
            latency=latencyChangePending_;
            dirtySeq=hostDirtySeq_;
            latencySeq=hostLatencySeq_;
        }
        bool dirtyOk=!dirty,latencyOk=!latency;
        // Called exclusively by the persistent Win32 UI message window.
        // IComponentHandler2/setDirty is optional: absent support must not
        // run an endless 250 ms UI timer. A later handler re-connection can
        // initiate a fresh notification for future edits.
        if(dirty)
            dirtyOk=!componentHandler2||setDirty(true)==kResultOk;
        if(latency) {
            if(auto* handler=getComponentHandler())
                latencyOk=handler->restartComponent(kLatencyChanged)==kResultOk;
        }
        bool retry=false;
        {
            std::lock_guard<std::mutex> guard(sf2StatusMutex_);
            if(dirtyOk&&dirtySeq==hostDirtySeq_)hostDirtyPending_=false;
            if(latencyOk&&latencySeq==hostLatencySeq_)latencyChangePending_=false;
            retry=hostDirtyPending_||latencyChangePending_;
        }
        release(); // possibly destroys this; do not access members afterward
        return retry;
    }
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
