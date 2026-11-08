// P178 PRIVATE LOCAL MEDIA GATE — actual exported Windows VST3, not a mock.
// No user ROM/SF2 or rendered samples are uploaded, copied or embedded.
// Run through P178-LOCAL-TEST.bat on the user's Windows machine.
#define wmain p171_unused_entry
#include "p171_vst3_load_host.cpp"
#undef wmain
#include "PresetCatalog.h"
#include <cmath>
#include <fstream>
#include <iomanip>
#include <map>
#include <set>
#include <sstream>
#include <limits>

namespace {
std::ofstream report;
int passed=0,failed=0,inconclusive=0;
void line(const std::string& s) {
    std::cout<<s<<'\n'<<std::flush;
    if(report)report<<s<<'\n'<<std::flush;
}
void mark(const std::string& kind,const std::string& subject) {
    line(kind+" | "+subject);
    if(kind=="PASS")++passed;
    else if(kind=="FAIL")++failed;
    else ++inconclusive;
}
std::string utf8(const wchar_t* s) {
    if(!s)return {};
    const int n=WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,s,-1,
                                   nullptr,0,nullptr,nullptr);
    if(n<=1)return {};
    std::string out(static_cast<size_t>(n),'\0');
    if(WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,s,-1,
                          out.data(),n,nullptr,nullptr)!=n)return {};
    out.pop_back();
    return out;
}
bool exists(const std::string& name) {
    std::error_code ec;
    return std::filesystem::is_regular_file(std::filesystem::u8path(name),ec);
}
std::string fileName(const std::string& name) {
    auto path=std::filesystem::u8path(name);
    auto u=path.filename().u8string();
    return std::string(u.begin(),u.end());
}
struct Audio {
    std::vector<float> pcm;
    double rms=0.;
    float peak=0.f;
    bool finite=true;
};
Audio firstNote(IAudioProcessor* audio,int midiPitch) {
    Audio value;
    value.pcm.reserve(1024*8*2);
    for(int block=0;block<8;++block) {
        std::array<float,1024> left{},right{};
        float* channels[]{left.data(),right.data()};
        AudioBusBuffers out{};
        out.numChannels=2;out.channelBuffers32=channels;
        EventList events;
        if(!block) {
            Event on{};
            on.type=Event::kNoteOnEvent;
            on.noteOn.channel=0;
            on.noteOn.pitch=static_cast<int16>(midiPitch);
            on.noteOn.velocity=100.f/127.f;
            on.noteOn.noteId=23;
            require(events.addEvent(on)==kResultOk,"P178 first-note MIDI insert");
        }
        ProcessData data{};
        data.processMode=kRealtime;data.symbolicSampleSize=kSample32;
        data.numSamples=1024;data.numOutputs=1;data.outputs=&out;
        data.inputEvents=&events;
        require(audio->process(data)==kResultOk,"P178 actual DLL PCM process");
        value.pcm.insert(value.pcm.end(),left.begin(),left.end());
        value.pcm.insert(value.pcm.end(),right.begin(),right.end());
    }
    double energy=0.;
    for(float v:value.pcm) {
        if(!std::isfinite(v)) {value.finite=false;break;}
        value.peak=std::max(value.peak,std::abs(v));
        energy+=double(v)*double(v);
    }
    if(value.finite&&!value.pcm.empty())
        value.rms=std::sqrt(energy/double(value.pcm.size()));
    return value;
}
void loadViaProcessor(Instance& inst,const std::string& path) {
    auto* msg=new HostMessage;
    msg->setMessageID("125A_SF2_LOAD");
    msg->getAttributes()->setInt("RequestID",1);
    require(msg->getAttributes()->setBinary("Path",path.data(),
                 static_cast<uint32>(path.size()))==kResultOk,
            "P178 load-message payload");
    const auto response=inst.procConnection->notify(msg);
    msg->release();
    require(response==kResultOk,"P178 actual VST3 SF2 load message");
    // Processor may return kResultOk for a rejected SF2; verify committed
    // path via the exact serialized V11 project state instead.
    MemoryStream stream;
    require(inst.component->getState(&stream)==kResultOk,
            "P178 getState after load");
    stream.seek(0,IBStream::kIBSeekSet,nullptr);
    AWE125::AssetState::Data saved{};
    require(AWE125::AssetState::Read([&](void* p,size_t n) {
        int32 got=0;
        return stream.read(p,int32(n),&got)==kResultOk && got==int32(n);
    },saved),"P178 decode V11 state");
    require(saved.sf2Path==path,"P178 Processor did not commit selected SF2");
}
std::string resultText(const std::string& bank,int program,int pitch,
                       const Audio& ref,const Audio& first,bool equal) {
    std::ostringstream out;
    out<<bank<<" program="<<program<<" midi_note="<<pitch
       <<" direct_rms="<<std::setprecision(9)<<ref.rms
       <<" loaded_rms="<<first.rms
       <<" peak="<<first.peak
       <<" pcm_bit_identical="<<(equal?"YES":"NO");
    return out.str();
}
} // namespace

int wmain(int argc,wchar_t** argv) {
    if(argc<4||argc>8) {
        std::cerr<<"Usage: 125A-P178-Media-Probe.exe VST3_DLL ROM.raw Bank1.sf2 [Bank2.sf2 ...]\n";
        return 2;
    }
    const auto exe=std::filesystem::path(argv[0]);
    report.open(exe.parent_path()/L"P178-LOCAL-RESULT.txt",std::ios::binary|std::ios::trunc);
    line("P178 PRIVATE WINDOWS ORIGINAL-MEDIA FIRST NOTE REGRESSION");
    line("SCOPE: real exported VST3, genuine local private media; 44,100 Hz, no DAW/ASIO/hardware parity");
    line("PRIVACY: only a local text result; no audio files, ROM, SF2, uploads, or network calls");
    auto dllPath=std::filesystem::path(argv[1]);
    if(!std::filesystem::is_regular_file(dllPath)) {
        mark("FAIL","VST3 DLL not found in candidate bundle");
        return 2;
    }
    auto rom=utf8(argv[2]);
    if(!exists(rom)) {
        mark("FAIL","Private Wave-ROM path missing or invalid");
        return 2;
    }
    const auto romSize=std::filesystem::file_size(std::filesystem::u8path(rom));
    if(romSize!=1048576u) {
        mark("FAIL","Wave-ROM size is not 1,048,576 bytes (does not prove authenticity)");
        return 2;
    }
    mark("PASS","Wave-ROM file present with expected 1 MiB size (authenticity NOT asserted)");
    const auto initCo=CoInitializeEx(nullptr,COINIT_APARTMENTTHREADED);
    if(FAILED(initCo)) {
        mark("FAIL","Windows COM initialization");
        return 2;
    }
    HMODULE dll=nullptr;IPluginFactory* factory=nullptr;
    bool moduleInit=false;
    try {
        dll=LoadLibraryW(dllPath.c_str());
        require(dll!=nullptr,"VST3 module LoadLibraryW failed");
        using Init=bool (PLUGIN_API*)();
        if(auto init=reinterpret_cast<Init>(GetProcAddress(dll,"InitDll"))) {
            require(init(),"SDK VST3 InitDll rejected module");
            moduleInit=true;
        }
        using GetFactory=IPluginFactory*(*)();
        auto get=reinterpret_cast<GetFactory>(GetProcAddress(dll,"GetPluginFactory"));
        require(get!=nullptr,"GetPluginFactory missing");
        factory=get();
        require(factory!=nullptr,"Actual exported VST3 factory missing");
        mark("PASS","Loaded actual Windows x64 VST3 DLL with SDK module lifecycle");
        for(int arg=3;arg<argc;++arg) {
            const auto sf2=utf8(argv[arg]);
            const auto name=fileName(sf2);
            if(!exists(sf2)) {mark("FAIL","SF2 path not present: "+name);continue;}
            AWE125::PresetCatalog catalog;
            std::string error;
            if(!catalog.LoadSoundFont(sf2,error)){
                mark("FAIL","SF2 RIFF/preset catalog invalid: "+name+" "+error);
                continue;
            }
            const auto& entries=catalog.Entries();
            mark("PASS",name+" real SF2 preset inventory="+std::to_string(entries.size()));
            std::map<uint16_t,std::vector<AWE125::PresetEntry>> banks;
            for(const auto& entry:entries)banks[entry.bank].push_back(entry);
            for(const auto& [bank,items]:banks) {
                line("INVENTORY "+name+" bank="+std::to_string(bank)+
                     " available="+std::to_string(items.size())+
                     " (strict: no missing GM programs inserted)");
            }
            // End-user first-click reproduction: sample available real bank
            // entries at beginning, center and end, not an invented 128-GM sweep.
            std::set<std::pair<uint16_t,uint8_t>> selected;
            for(const auto& [bank,items]:banks) {
                for(size_t index:{size_t(0),items.size()/2,items.size()-1})
                    selected.emplace(items[index].bank,items[index].program);
            }
            for(auto [bank,program]:selected) {
                try {
                    AWE125::AssetState::Data expectedState{};
                    expectedState.pathsSpecified=true;expectedState.romPath=rom;
                    expectedState.sf2Path=sf2;expectedState.bank=bank;
                    expectedState.program=program;expectedState.channelPrograms.fill(program);
                    auto unloaded=expectedState;
                    unloaded.sf2Path.clear();
                    // Both instances use real ROM/voice core. First note is
                    // rendered AFTER the direct SF2 load into the active one.
                    Instance reference(factory,44100,expectedState);
                    Instance actual(factory,44100,unloaded);
                    loadViaProcessor(actual,sf2);
                    const auto ref=firstNote(reference.audio,48);
                    const auto got=firstNote(actual.audio,48);
                    const bool equal=got.pcm==ref.pcm;
                    const auto detail=resultText(name,int(program),48,ref,got,equal);
                    if(!got.finite||!ref.finite||!equal)
                        mark("FAIL",detail);
                    else if(got.peak>0.f)
                        mark("PASS",detail);
                    else mark("NOT_VERIFIED",detail+" (preset may have different key/velocity map)");
                }catch(const std::exception& e) {
                    mark("FAIL",name+" bank="+std::to_string(bank)+
                         " program="+std::to_string(program)+": "+e.what());
                }
            }
            // Strict 77-program SF2 must not borrow patch 63 from ROM/GM.
            if(entries.size()==77 && banks.contains(0)) {
                const bool missing63=std::none_of(entries.begin(),entries.end(),
                    [](const auto& p){return p.bank==0&&p.program==63;});
                if(!missing63) {
                    mark("NOT_VERIFIED",name+" 77 presets: bank0 program63 actually present");
                } else try {
                    AWE125::AssetState::Data silent{};
                    silent.pathsSpecified=true;silent.romPath=rom;silent.sf2Path=sf2;
                    silent.bank=0;silent.program=63;
                    silent.channelPrograms.fill(63);
                    Instance real(factory,44100,silent);
                    const auto pcm=firstNote(real.audio,48);
                    if(pcm.finite&&pcm.peak==0.f)
                        mark("PASS",name+" missing bank0/program63 exactly silent, no ROM substitute");
                    else
                        mark("FAIL",name+" missing bank0/program63 generated audio (illegal fallback)");
                } catch(const std::exception& e) {
                    mark("FAIL",name+" missing program63 probe "+e.what());
                }
            }
        }
    }catch(const std::exception& e){
        mark("FAIL",std::string("Fatal Windows original-media probe: ")+e.what());
    }
    if(factory)factory->release();
    if(dll) {
        using Exit=bool (PLUGIN_API*)();
        if(moduleInit) {
            if(auto exit=reinterpret_cast<Exit>(GetProcAddress(dll,"ExitDll")))
                if(!exit())mark("FAIL","VST3 ExitDll failed");
        }
        FreeLibrary(dll);
    }
    CoUninitialize();
    line("P178_RESULT passes="+std::to_string(passed)+" failures="+
         std::to_string(failed)+" not_verified="+std::to_string(inconclusive));
    line("IMPORTANT: no full audit, no actual DAW/ASIO, no hardware audio fidelity");
    line("LOCAL_REPORT=P178-LOCAL-RESULT.txt");
    return failed?1:inconclusive?3:0;
}
