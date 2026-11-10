// P220: real, exported Windows VST3 -> actual process() -> PCM WAV.
// Reuses the P171 proven VST3 host factory/state/audio lifecycle.
// This recorder generates *NO* reference Creative Win95 audio; 'probe'
// operates on synthetic public assets and must never be a release receipt.
#define wmain p171_unused_entry
#include "p171_vst3_load_host.cpp"
#undef wmain
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <limits>
#include <sstream>
#include <cmath>
#include <bit>

namespace {
std::string utf8_path(const std::filesystem::path& path) {
    const auto p=path.u8string();
    return {p.begin(),p.end()};
}
void word(std::ofstream& out,std::uint32_t n,int bytes) {
    for(int i=0;i<bytes;++i) {
        const unsigned char c=static_cast<unsigned char>((n>>(8*i))&255u);
        out.put(static_cast<char>(c));
    }
}
void write_wave(const std::filesystem::path& file,const std::vector<int16_t>& pcm) {
    constexpr std::uint32_t rate=44100;
    require(!pcm.empty()&&pcm.size()%2==0,"P220 WAV stereo frame count");
    require(pcm.size()<std::numeric_limits<std::uint32_t>::max()/2,
            "P220 WAV larger than RIFF classic");
    std::ofstream out(file,std::ios::binary|std::ios::trunc);
    require(bool(out),"P220 cannot create WAV file");
    const std::uint32_t dataBytes=std::uint32_t(pcm.size()*2);
    out.write("RIFF",4);word(out,36u+dataBytes,4);out.write("WAVEfmt ",8);
    word(out,16,4);word(out,1,2);word(out,2,2);
    word(out,rate,4);word(out,rate*4,4);word(out,4,2);word(out,16,2);
    out.write("data",4);word(out,dataBytes,4);
    for(auto value:pcm)word(out,static_cast<std::uint16_t>(value),2);
    require(bool(out),"P220 WAV write failed");
}
// Preserve unscaled ORIGINAL float data when the VST3 exceeds 0 dBFS.
 // 16-bit PCM would irreversibly clip and conceal the actual diagnostic.
void write_float_wave(const std::filesystem::path& file,const std::vector<float>& pcm) {
    require(!pcm.empty()&&pcm.size()%2==0,"P220 forensic WAV stereo frame count");
    require(pcm.size()<std::numeric_limits<std::uint32_t>::max()/4,
            "P220 forensic WAV RIFF size");
    std::ofstream out(file,std::ios::binary|std::ios::trunc);
    require(bool(out),"P220 cannot create ORIGINAL-FLOAT forensic WAV");
    const auto dataBytes=static_cast<std::uint32_t>(pcm.size()*sizeof(float));
    out.write("RIFF",4);word(out,36u+dataBytes,4);out.write("WAVEfmt ",8);
    word(out,16,4);word(out,3,2);word(out,2,2);
    word(out,44100,4);word(out,44100*8,4);word(out,8,2);word(out,32,2);
    out.write("data",4);word(out,dataBytes,4);
    for(float v:pcm) {
        require(std::isfinite(v),"P220 forensic PCM contains nonfinite");
        word(out,std::bit_cast<std::uint32_t>(v),4);
    }
    require(bool(out),"P220 forensic float WAV write failed");
}
struct RenderResult {
    int frames=0,callbacks=0,overrangeSamples=0,firstOverrangeFrame=-1,
        firstOverrangeChannel=-1;
    float peak=0,firstOverrangeValue=0;
    double rms=0;
    bool valid=false;
};
RenderResult render_one(IPluginFactory* factory,const std::string& rom,
                         const std::string& sf2,int program,bool modfx,
                         const std::filesystem::path& target) {
    AWE125::AssetState::Data wanted{};
    wanted.pathsSpecified=true;wanted.romPath=rom;wanted.sf2Path=sf2;
    wanted.bank=0;wanted.engine=0;
    wanted.program=static_cast<std::uint32_t>(program);
    wanted.channelPrograms.fill(static_cast<std::uint32_t>(program));
    // P190 global sends are independently controllable; turn them on
    // only for the FX trial so CC91/CC93 have a chance to be audible.
    wanted.controls[10]=modfx?10000:0;
    wanted.controls[11]=modfx?10000:0;
    Instance instance(factory,44100,wanted);
    // Verify actual exported component has committed the requested
    // SF2 path, bank, and program. This is not a Creative-ROM proof.
    MemoryStream stream;
    require(instance.component->getState(&stream)==kResultOk,
            "P220 actual exported VST3 getState");
    stream.seek(0,IBStream::kIBSeekSet,nullptr);
    AWE125::AssetState::Data observed{};
    require(AWE125::AssetState::Read([&](void* dest,std::size_t n) {
        int32 got=0;
        return stream.read(dest,static_cast<int32>(n),&got)==kResultOk
               &&got==static_cast<int32>(n);
    },observed),"P220 exported VST3 state decode");
    require(observed.romPath==rom&&observed.sf2Path==sf2&&
            observed.bank==0&&int(observed.program)==program,
            "P220 actual VST3 asset path/bank/program state not acknowledged");
    const int note=modfx?72:48,velocity=modfx?120:64;
    constexpr int framesTotal=44100*3, blockSize=1024;
    std::vector<int16_t> pcm;
    pcm.reserve(framesTotal*2);
    std::vector<float> originalFloat;
    originalFloat.reserve(framesTotal*2);
    RenderResult report{};
    double energy=0;
    for(int pos=0;pos<framesTotal;pos+=blockSize) {
        const int n=std::min(blockSize,framesTotal-pos);
        std::array<float,blockSize> left{},right{};
        float* channels[]={left.data(),right.data()};
        AudioBusBuffers output{};
        output.numChannels=2;output.channelBuffers32=channels;
        EventList ev;
        ParameterChanges params(16);
        if(pos==0) {
            const auto setcc=[&](int cc,int value) {
                const int index=AWE125::MidiControlMapping::Index(cc);
                require(index>=0,"P220 CC absent from VST3 MidiControlMapping");
                int32 queueIndex=0,pointIndex=0;
                auto* queue=params.addParameterData(
                    AWE125::MidiControlMapping::ParamID(0u,
                           static_cast<std::uint32_t>(index)),queueIndex);
                require(queue&&queue->addPoint(0,double(value)/127.,pointIndex)==kResultOk,
                        "P220 CC parameter queue failed");
            };
            setcc(7,100);setcc(11,127);setcc(1,modfx?96:0);
            setcc(91,modfx?48:0);setcc(93,modfx?32:0);
            Event on{};on.type=Event::kNoteOnEvent;on.sampleOffset=0;
            on.noteOn.channel=0;on.noteOn.pitch=static_cast<int16>(note);
            on.noteOn.velocity=float(velocity)/127.f;on.noteOn.noteId=29;
            require(ev.addEvent(on)==kResultOk,"P220 VST3 NoteOn event failed");
        }
        if(pos<=44100&&44100<pos+n) {
            Event off{};off.type=Event::kNoteOffEvent;
            off.sampleOffset=44100-pos;off.noteOff.channel=0;
            off.noteOff.pitch=static_cast<int16>(note);
            off.noteOff.velocity=0;off.noteOff.noteId=29;
            require(ev.addEvent(off)==kResultOk,"P220 VST3 NoteOff event failed");
        }
        ProcessData data{};
        data.processMode=kRealtime;data.symbolicSampleSize=kSample32;
        data.numSamples=n;data.numOutputs=1;data.outputs=&output;
        data.inputEvents=&ev;data.inputParameterChanges=&params;
        require(instance.audio->process(data)==kResultOk,
                "P220 actual exported VST3 process failed");
        ++report.callbacks;
        for(int i=0;i<n;++i) {
            const float samples[]={left[i],right[i]};
            for(int ch=0;ch<2;++ch) {
                const float v=samples[ch];
                require(std::isfinite(v),"P220 nonfinite real VST3 output");
                report.peak=std::max(report.peak,std::abs(v));
                if(std::abs(v)>=0.99997f) {
                    ++report.overrangeSamples;
                    if(report.firstOverrangeFrame<0) {
                        report.firstOverrangeFrame=pos+i;
                        report.firstOverrangeChannel=ch;
                        report.firstOverrangeValue=v;
                    }
                }
                energy+=double(v)*double(v);
                originalFloat.push_back(v); // exact un-normalized VST3 output
                const float q=std::clamp(v,-1.f,1.f);
                pcm.push_back(static_cast<int16_t>(std::lround(q*32767.f)));
            }
        }
        report.frames+=n;
    }
    report.rms=std::sqrt(energy/double(pcm.size()));
    require(report.frames==framesTotal&&report.callbacks>0,
            "P220 incomplete actual VST3 audio callback timeline");
    report.valid=report.overrangeSamples==0 && report.peak<0.99997f
                 &&report.rms>0.00015;
    if(!report.valid) {
        const auto forensic=target.parent_path()/
                            (target.stem().string()+"-FAILED-UNCLIPPED-F32.wav");
        require(!std::filesystem::exists(forensic),
                "P220 refuses to overwrite existing forensic float WAV");
        write_float_wave(forensic,originalFloat);
        // This must NEVER produce the expected 16-bit filename: it is a
        // failed, out-of-range or silent ORIGINAL float output, not a PASS.
    } else {
        write_wave(target,pcm);
    }
    return report;
}
} // namespace

int wmain(int argc,wchar_t** argv) {
    // 125A-P220-VST3-Recorder.exe 125A_AWE_Synthesizer.vst3
    //    awe32.raw "Synth 512 Bank.sf2" PRIVATE_OUT_DIR probe|full
    if(argc!=6) {
        std::cerr<<"P220 usage: recorder.exe DLL ROM SF2 PRIVATE_OUTPUT_DIR probe|full\n";
        return 2;
    }
    const bool full=std::wstring(argv[5])==L"full";
    const bool probe=std::wstring(argv[5])==L"probe";
    if(!full&&!probe)return 2;
    const auto dllPath=std::filesystem::path(argv[1]);
    const auto romPath=std::filesystem::path(argv[2]);
    const auto sf2Path=std::filesystem::path(argv[3]);
    const auto outDir=std::filesystem::path(argv[4]);
    if(!std::filesystem::is_regular_file(dllPath)||
       !std::filesystem::is_regular_file(romPath)||
       !std::filesystem::is_regular_file(sf2Path)) {
        std::cerr<<"P220 missing real VST3, ROM or SF2\n";return 2;
    }
    if(std::filesystem::file_size(romPath)!=1048576u) {
        std::cerr<<"P220 wrong ROM size\n";return 2;
    }
    std::filesystem::create_directories(outDir);
    const auto rom=utf8_path(romPath),sf2=utf8_path(sf2Path);
    if(FAILED(CoInitializeEx(nullptr,COINIT_APARTMENTTHREADED)))return 2;
    auto* dll=LoadLibraryW(dllPath.c_str());
    if(!dll){CoUninitialize();return 2;}
    using Init=bool (PLUGIN_API*)();
    using Exit=bool (PLUGIN_API*)();
    const auto init=reinterpret_cast<Init>(GetProcAddress(dll,"InitDll"));
    const auto exit=reinterpret_cast<Exit>(GetProcAddress(dll,"ExitDll"));
    const bool initialized=!init||init();
    IPluginFactory* factory=nullptr;
    int ret=1;
    try {
        require(initialized,"P220 VST3 InitDll");
        const auto getter=reinterpret_cast<IPluginFactory*(*)()>(
            GetProcAddress(dll,"GetPluginFactory"));
        require(getter!=nullptr,"P220 real VST3 factory export");
        factory=getter();
        require(factory!=nullptr,"P220 VST3 factory null");
        int tested=0,failed=0,attempts=0;
        for(int p=0;p<=77;++p) {
            if(p==63)continue;
            if(probe&&p!=0)continue; // synthetic **negative-proof only**
            for(bool fx:{false,true}) {
                const auto name=std::string("P")+
                    (p<10?"00":p<100?"0":"")+std::to_string(p)+
                    (fx?"-MODFX":"-DRY");
                const auto dest=outDir/(name+".wav");
                const auto staleError=std::string("P220 refuses stale/overwritten prior capture ")+name;
                require(!std::filesystem::exists(dest),staleError.c_str());
                const auto measurement=render_one(factory,rom,sf2,p,fx,dest);
                ++attempts;
                if(!measurement.valid) {
                    ++failed;
                    std::cout<<"P220_VST3_AUDIO_FAIL "<<name
                        <<" program="<<p<<" note="<<(fx?72:48)
                        <<" velocity="<<(fx?120:64)
                        <<" fx_gui_send="<<(fx?10000:0)
                        <<" CC91="<<(fx?48:0)<<" CC93="<<(fx?32:0)
                        <<" peak="<<std::setprecision(10)<<measurement.peak
                        <<" rms="<<measurement.rms
                        <<" overrange_samples="<<measurement.overrangeSamples
                        <<" first_overrange_frame="<<measurement.firstOverrangeFrame
                        <<" first_overrange_channel="<<measurement.firstOverrangeChannel
                        <<" first_overrange_value="<<measurement.firstOverrangeValue
                        <<" forensic_float_wav="<<name<<"-FAILED-UNCLIPPED-F32.wav"
                        <<" RESULT=FAIL_NOT_AUDIO_ACCEPTANCE\n"<<std::flush;
                    continue;
                }
                std::cout<<"P220_VST3_PCM "<<name
                         <<" program="<<p<<" note="<<(fx?72:48)
                         <<" velocity="<<(fx?120:64)
                         <<" frames="<<measurement.frames
                         <<" callbacks="<<measurement.callbacks
                         <<" rms="<<std::setprecision(9)<<measurement.rms
                         <<" peak="<<measurement.peak
                         <<" private_wav=YES\n"<<std::flush;
                ++tested;
            }
        }
        require(attempts==(probe?2:154),"P220 missing actual VST3 process() trials");
        if(failed) {
            std::cout<<"P220_VST3_SUMMARY ATTEMPTED="<<attempts
                     <<" PASS_PCM16="<<tested<<" FAILED="<<failed
                     <<" REASON=REAL_VST3_AUDIO_OVERLOAD_OR_SILENCE"
                     <<" SONIC_RELEASE=BLOCKED\n"<<std::flush;
            throw std::runtime_error("P220 independent WAV failures: "+
                    std::to_string(failed)+"/"+std::to_string(attempts)+
                    " ; detailed original float diagnostic WAVs saved");
        }
        std::cout<<"P220_MODE="<<(probe?"SYNTHETIC_PROBE_NOT_ORIGINAL_SF2":
                                      "OWNER_PRIVATE_77_VST3_RECORDINGS_NOT_CREATIVE")
                 <<" ACTUAL_VST3_AUDIO_PAIRS="<<tested
                 <<" ACTUAL_CREATIVE_DRIVER_RUN=NO\n";
        ret=0;
    }catch(const std::exception& e) {
        std::cerr<<"P220_VST3_FAIL "<<e.what()<<'\n';
    }
    if(factory)factory->release();
    if(initialized&&exit&&!exit())ret=1;
    FreeLibrary(dll);CoUninitialize();
    return ret;
}
