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
#include "PresetCatalog.h"
#include "PresetBrowserView.h"
#include "Sf2LoadPolicy.h"
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
            synth_=std::make_unique<Synth>(rate_);
            synth_->Core().SetDriver(Awe32::Driver::Win95);
            assetError_.clear();
            ResolveAssets();
            sf2Configured_=!state_.sf2Path.empty();
            sf2Loaded_=false;
            std::string sf2Status="SF2 nicht konfiguriert: kein echter SoundFont-Klang.";
            if(!state_.romPath.empty()) {
                std::string error;
                if(!synth_->Core().UseBox86Chip(state_.romPath,error))
                    assetError_=std::move(error);
            }
            synth_->Core().PowerOnInit();
            for(int i=0;i<kGuiCount;++i)
                synth_->SetGuiControl(i,float(state_.controls[i])/AssetState::kControlScale);
            if(sf2Configured_) {
                std::string error;
                if(synth_->LoadBank(state_.sf2Path,error)) {
                    sf2Loaded_=true;
                    sf2Status="SF2-Audio geladen.";
                } else {
                    assetError_="SF2-Ladefehler: "+(error.empty() ?
                        std::string("unbekannter Grund"):error);
                    sf2Status=assetError_;
                }
            }
            synth_->SelectBrowserBank(static_cast<uint16_t>(state_.bank));
            for(int c=0;c<16;++c)synth_->ProgramChange(static_cast<uint8_t>(c),
                static_cast<uint8_t>(state_.program));
            // This is a non-realtime activation callback. The VST3 connection
            // passes the actual processor loading outcome to the GUI, not
            // just the SF2 phdr names the controller happened to parse.
            sendTextMessage(("125A_SF2_STATUS:"+sf2Status).c_str());
            sendTextMessage(("125A_HW_INFO:"+HardwareDescriptor()).c_str());
        } else {synth_.reset();}
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
        bool active=false;
        {
            std::lock_guard<std::mutex> lock(engineMutex_);
            sampleRate=rate_;
            model=state_;
            active=bool(synth_);
        }
        std::string error;
        std::unique_ptr<Synth> replacement;
        if(active) {
            try {
                replacement=std::make_unique<Synth>(sampleRate);
                replacement->Core().SetDriver(Awe32::Driver::Win95);
                if(!model.romPath.empty() &&
                   !replacement->Core().UseBox86Chip(model.romPath,error))
                    error="Wave ROM: "+error;
                else {
                    replacement->Core().PowerOnInit();
                    for(int i=0;i<kGuiCount;++i)
                        replacement->SetGuiControl(
                            i,float(model.controls[i])/AssetState::kControlScale);
                    if(!replacement->LoadBank(path,error))
                        error="SF2: "+error;
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
            sf2Loaded_=active;
        }
        std::string sysInfo;
        {
            std::lock_guard<std::mutex> lock(engineMutex_);
            sysInfo=HardwareDescriptor();
        }
        sendTextMessage(("125A_HW_INFO:"+sysInfo).c_str());
        sendTextMessage(active ?
            "125A_SF2_STATUS:SF2 geladen - SoundFont aktiv." :
            "125A_SF2_STATUS:SF2 gewaehlt - Laden bei Aktivierung.");
        sendTextMessage("125A_SF2_ACK:OK");
        return kResultOk;
    }
    uint32 PLUGIN_API getLatencySamples() override {
        std::lock_guard<std::mutex> lock(engineMutex_);
        return synth_?synth_->Core().ChipLatencyFrames():0;
    }
    tresult PLUGIN_API getState(IBStream* stream) override {
        if(!stream)return kInvalidArgument;
        std::lock_guard<std::mutex> lock(engineMutex_);
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
        if(data.numSamples<0)return kInvalidArgument;
        std::unique_lock<std::mutex> lock(engineMutex_,std::try_to_lock);
        if(!lock.owns_lock()) {
            if(data.numOutputs>0&&data.outputs&&data.outputs[0].channelBuffers32&&
               data.symbolicSampleSize==kSample32) {
                for(int c=0;c<data.outputs[0].numChannels;++c)
                    if(auto* b=data.outputs[0].channelBuffers32[c])
                        std::fill_n(b,data.numSamples,0.f);
                data.outputs[0].silenceFlags=3u;
            }
            return kResultOk;
        }
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
                    } else if(q->getParameterId()==kBankID) {
                        const auto bank=static_cast<uint32_t>(std::clamp(
                            int(std::lround(val*AssetState::kMaxBank)),0,
                            int(AssetState::kMaxBank)));
                        if(bank!=state_.bank) {
                            state_.bank=bank;
                            if(synth_)synth_->SelectBrowserBank(static_cast<uint16_t>(bank));
                        }
                    } else if(q->getParameterId()>=kGuiFirstID &&
                              q->getParameterId()<kGuiFirstID+kGuiCount) {
                        const int index=int(q->getParameterId()-kGuiFirstID);
                        const float amount=static_cast<float>(std::clamp(val,0.,1.));
                        state_.controls[index]=static_cast<uint32_t>(
                            std::lround(amount*AssetState::kControlScale));
                        if(synth_)synth_->SetGuiControl(index,amount);
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
        if(!synth_||uint32(data.numSamples)>capacity_)
            return kResultOk;

        const auto render=[&](int32 from,int32 to) {
            if(to<=from)return;
            synth_->RenderBlock(scratch_.data()+size_t{2}*from,
                                static_cast<uint32_t>(to-from));
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
                if(AllowEmuNoteOn(sf2Configured_,sf2Loaded_))
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
    AssetState::Data state_{};
    std::string assetError_;
    mutable std::mutex engineMutex_; // never block realtime rendering
    bool sf2Configured_=false,sf2Loaded_=false; // written outside process()
    // Report the currently running chip, not merely paths in assets.cfg.
    // Call under engineMutex_ from non-realtime code only.
    std::string HardwareDescriptor() const {
        if(!synth_)return "RAM --  |  ROM: INAKTIV  |  CORE: INAKTIV";
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
class Controller final : public EditControllerEx1, public VSTGUI::VST3EditorDelegate {
public:
    static FUnknown* createInstance(void*) {
        return static_cast<IEditController*>(new Controller);
    }
    tresult receiveText(const char8* msg) override {
        constexpr char ack[]="125A_SF2_ACK:";
        if(msg && std::strncmp(msg,ack,sizeof(ack)-1)==0) {
            std::lock_guard<std::mutex> lock(sf2StatusMutex_);
            sf2PendingAck_=msg+sizeof(ack)-1;
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
    uint64_t CatalogRevision() {
        std::string ack;
        {
            std::lock_guard<std::mutex> lock(sf2StatusMutex_);
            ack.swap(sf2PendingAck_);
        }
        if(ack=="OK" && !sf2PendingPath_.empty()) {
            sfCatalog_=std::move(sf2PendingCatalog_);
            sf2Path_=std::move(sf2PendingPath_);
            ++sfCatalogRevision_;
        } else if(!ack.empty()) sf2PendingPath_.clear();
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
            return new PresetBrowserView({0,0,1040,680},this,sfCatalog_,fmCatalog_,
                FactoryBank(L"125A_Logo_Master_FINAL.svg"),
                [this]() {return Sf2AudioStatus();},
                [this]() {return HardwareInfo();},
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
    std::string sf2PendingPath_;
    PresetCatalog sf2PendingCatalog_{};
    uint64_t sfCatalogRevision_=0;
    std::string sf2PendingAck_;
    mutable std::mutex sf2StatusMutex_;
    std::string sf2AudioStatus_="SF2-Audiostatus noch nicht vom Prozessor bestaetigt.";
    std::string hardwareInfo_;
    void ReloadPresetCatalogs(const AssetState::Data* model) {
        AssetConfig::Paths paths;
        if(model&&model->pathsSpecified) {
            paths.sf2=model->sf2Path;
            paths.ibk=model->ibkPath;
        } else if(!AssetConfig::Load(paths)) {
            paths={};
        }
        // Clear stale entries when a project points at a new/missing file.
        sfCatalog_=PresetCatalog{};
        fmCatalog_=PresetCatalog{};
        sf2Path_=paths.sf2;
        std::string error;
        if(!paths.sf2.empty())sfCatalog_.LoadSoundFont(paths.sf2,error);
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
