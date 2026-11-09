// P97: MIDI playback through 125A's real 86Box EMU8000 core at 44.1 kHz.
// No replacement synthesizer or proprietary ROM is embedded.
#include "Synth.h"
#include "Emu8000Effects.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace {
struct Event { uint64_t frame; std::string type; int channel,a,b; };
void u16(std::ofstream& f,uint16_t n) {
    const char c[2]={char(n&255),char((n>>8)&255)};f.write(c,2);
}
void u32(std::ofstream& f,uint32_t n) {u16(f,uint16_t(n));u16(f,uint16_t(n>>16));}
void header(std::ofstream& f,uint64_t frames) {
    if(frames>(UINT32_MAX-36u)/4u)throw std::runtime_error("WAV too long");
    auto bytes=uint32_t(frames*4);
    f.write("RIFF",4);u32(f,36+bytes);f.write("WAVEfmt ",8);
    u32(f,16);u16(f,1);u16(f,2);u32(f,44100);u32(f,176400);u16(f,4);u16(f,16);
    f.write("data",4);u32(f,bytes);
}
std::vector<Event> events(const std::string& name) {
    std::ifstream f(name); if(!f)throw std::runtime_error("Event TSV unavailable");
    std::string s;std::getline(f,s);
    // Python csv writes CRLF rows; std::getline removes only LF.
    if(!s.empty() && s.back()=='\r')s.pop_back();
    if(s!="frame\ttime_sec\ttype\tchannel\ta\tb")
        throw std::runtime_error("Unknown event TSV schema");
    std::vector<Event> result;uint64_t last=0;
    while(std::getline(f,s)) {
        if(s.empty())continue;
        std::istringstream a(s);
        std::string frame,sec,type,ch,n,v;
        if(!std::getline(a,frame,'\t')||!std::getline(a,sec,'\t')||
           !std::getline(a,type,'\t')||!std::getline(a,ch,'\t')||
           !std::getline(a,n,'\t')||!std::getline(a,v))
            throw std::runtime_error("Bad event TSV row");
        Event e{std::stoull(frame),type,std::stoi(ch),std::stoi(n),std::stoi(v)};
        if(e.frame<last || e.channel<0 || e.channel>15)
            throw std::runtime_error("Unsorted events or invalid channel");
        last=e.frame;result.push_back(e);
    }
    if(result.empty())throw std::runtime_error("No MIDI events");
    return result;
}
// The published CT4390 recording uses Hall 1 / Chorus 1, whereas the native
// engine defaults to Hall 2 / Chorus 3. Program the actual EMU8000 INIT
// register banks and HWCF5 LFO speed on the 86Box chip. No production DSP
// code is altered and no post-EQ is used to fit the analog reference.
void physicalFxPreset(Emu8000Core& core) {
    using Emu8000::Reg;
    for(size_t i=0;i<28;++i) {
        const auto slot=Emu8000Fx::kReverbSlots[i];
        Reg reg=Reg::INIT1;
        if(slot.init==2)reg=Reg::INIT2;
        else if(slot.init==3)reg=Reg::INIT3;
        else if(slot.init==4)reg=Reg::INIT4;
        else if(slot.init!=1)throw std::runtime_error("Invalid Creative reverb INIT bank");
        core.Write(reg,slot.slot,Emu8000Fx::kReverbParm[3][i]);
    }
    const auto& chorus=Emu8000Fx::kChorusPresets[0]; // Creative Chorus 1
    core.Write(Reg::INIT3,0x09,chorus.feedback);
    core.Write(Reg::INIT3,0x0c,chorus.delaySamples);
    core.Write(Reg::INIT4,0x03,chorus.depth);
    core.WriteReg32(Emu8000::MakeSel(1,Emu8000::Port::Data1,
                                    Emu8000::Hwcf::kHWCF5),
                    chorus.lfoFreq);
    std::cout<<"P97 CT4390 reference effect registers: Hall 1, Chorus 1"
             <<", HWCF5 "<<chorus.lfoFreq<<"\n";
}

// The physical CT4390 recording was made with the AWE Control Panel bass
// AND treble controls at 0 dB. The Win95 driver power-on arrays on our test
// bench leave treble at +7.9 dB (factory index 9). Apply the actual Creative
// flat-EQ register words here, not a corrective post-render EQ: both sources
// must use the same hardware setting before a spectral comparison is valid.
// This is a P97-only test setup; production engine and presets are untouched.
void physicalFlatEq(Emu8000Core& core) {
    using Emu8000::Reg;
    constexpr int kFlat = 5;
    struct Slot { Reg reg; int slot; };
    static constexpr Slot bassSlots[] = {
        {Reg::INIT4,0x01},{Reg::INIT4,0x11}
    };
    static constexpr Slot trebleSlots[] = {
        {Reg::INIT3,0x11},{Reg::INIT3,0x13},{Reg::INIT3,0x1b},
        {Reg::INIT4,0x07},{Reg::INIT4,0x0b},{Reg::INIT4,0x0d},
        {Reg::INIT4,0x17},{Reg::INIT4,0x19}
    };
    for(size_t i=0;i<2;++i)
        core.Write(bassSlots[i].reg,bassSlots[i].slot,
                   Emu8000Fx::kEqBassParm[kFlat][i]);
    for(size_t i=0;i<8;++i)
        core.Write(trebleSlots[i].reg,trebleSlots[i].slot,
                   Emu8000Fx::kEqTrebleParm[kFlat][i]);
    uint16_t words[10];
    for(size_t i=0;i<2;++i)
        words[i]=static_cast<uint16_t>(core.Read(bassSlots[i].reg,bassSlots[i].slot));
    for(size_t i=0;i<8;++i)
        words[2+i]=static_cast<uint16_t>(core.Read(trebleSlots[i].reg,trebleSlots[i].slot));
    int decodedBass=-1,decodedTreble=-1;
    Emu8000Fx::EqIndexFromInit(words,decodedBass,decodedTreble);
    if(decodedBass!=kFlat || decodedTreble!=kFlat)
        throw std::runtime_error("P97 flat EQ register verification failed");
    std::cout<<"P97 CT4390 matched 0 dB equalizer: bass 5/5, treble 5/5; "
             <<"Creative INIT3/INIT4 registers verified\n";
}

void dispatch(Synth& synth,const Event& e) {
    auto ch=uint8_t(e.channel);
    if(e.type=="note_on") {
        if(e.b==0)synth.NoteOff(ch,uint8_t(e.a));
        else synth.NoteOn(ch,uint8_t(e.a),uint8_t(e.b));
    } else if(e.type=="note_off")synth.NoteOff(ch,uint8_t(e.a));
    else if(e.type=="program_change")synth.ProgramChange(ch,uint8_t(e.a));
    else if(e.type=="control_change")synth.ControlChange(ch,uint8_t(e.a),uint8_t(e.b));
    else if(e.type=="pitchwheel")synth.PitchBend(ch,int16_t(e.a));
    else if(e.type=="aftertouch")synth.ChannelPressure(ch,uint8_t(e.a));
    else throw std::runtime_error("Unknown event type: "+e.type);
}
}
int main(int argc,char** argv) {
    if(argc!=11 && argc!=15) {
        std::cerr<<"Usage: awe32_p97_midi_renderer --rom ROM --sf2 SF2 --events TSV"
                   " --out WAV --seconds 1..300 [--p206-trace RAW --p206-readbacks TSV]\n";return 2;
    }
    try {
#if !defined(AWE125_P193_CT4390_REFERENCE_FX)
        // The current P190 product correctly mutes all sends at GUI 0%.
        // A dry render cannot be compared to the CT4390 Hall1/Chorus1
        // capture. Fail closed rather than publish misleading PCM metrics.
        throw std::runtime_error(
            "Physical CT4390 reference requires -DAWE125_P193_CT4390_REFERENCE_FX=ON; "
            "P190 default 0% FX is intentionally DRY");
#endif
        std::string rom,sf2,tsv,out,p206Trace,p206Readbacks;int seconds=0;
        for(int i=1;i<argc;i+=2) {
            std::string k=argv[i],v=argv[i+1];
            if(k=="--rom")rom=v;else if(k=="--sf2")sf2=v;
            else if(k=="--events")tsv=v;else if(k=="--out")out=v;
            else if(k=="--seconds")seconds=std::stoi(v);
            else if(k=="--p206-trace")p206Trace=v;
            else if(k=="--p206-readbacks")p206Readbacks=v;
            else throw std::runtime_error("Unknown argument "+k);
        }
        if(seconds<1||seconds>300)throw std::runtime_error("Invalid duration");
        const bool p206=!p206Trace.empty()&&!p206Readbacks.empty();
        if((!p206Trace.empty()||!p206Readbacks.empty())&&!p206)
            throw std::runtime_error("P206 requires both trace and readback paths");
        if(p206 && seconds<14)
            throw std::runtime_error("P206 needs at least 14 seconds of original MIDI");
        auto midi=events(tsv);
        const uint64_t count=uint64_t(seconds)*44100u;
        Synth synth(44100);
        synth.Core().SetDriver(Awe32::Driver::Win95);
        std::string error;
        if(!synth.Core().UseBox86Chip(rom,error)||
           synth.Core().ChipVariant()!=Emu8000Core::Chip::Box86)
            throw std::runtime_error("Actual 86Box EMU8000 / ROM failed: "+error);
        synth.Core().PowerOnInit();
        physicalFxPreset(synth.Core());
        physicalFlatEq(synth.Core());
        if(!synth.LoadBank(sf2,error))
            throw std::runtime_error("Real test SoundFont failed: "+error);
        synth.SelectBrowserBank(0);
        std::ofstream wav(out,std::ios::binary|std::ios::trunc);
        if(!wav)throw std::runtime_error("Output WAV cannot be created");
        header(wav,count);
        std::vector<int16_t> buffer(2048);
        uint64_t at=0,nz=0,peak=0,applied=0;
        uint64_t partialHall=0,partialChorus=0;
        long double total=0;
        constexpr uint64_t p206NoteOn=418950; // 9.5s at 44.1k
        constexpr uint64_t p206Step=4410;     // 100ms
        std::ofstream p206Out;
        uint64_t p206Next=0,p206Count=0;
        int p206Voice=-1;
        bool p206Active=false,p206Completed=false;
        if(p206) {
            p206Out.open(p206Readbacks,std::ios::binary|std::ios::trunc);
            if(!p206Out)throw std::runtime_error("P206 readback output unavailable");
            p206Out<<"relative_frame\tvoice\tatkhld\tenvval\tpefe\tip\tcpf\tptrx\tcvcf\n";
        }
        const auto p206Snapshot=[&]() {
            using Emu8000::Reg;
            auto& core=synth.Core();
            const auto atk=core.ReadDriver(Reg::ATKHLD,p206Voice);
            const auto env=core.ReadDriver(Reg::ENVVAL,p206Voice);
            const auto pefe=core.ReadDriver(Reg::PEFE,p206Voice);
            const auto ip=core.ReadDriver(Reg::IP,p206Voice);
            const auto cpf=core.ReadDriver(Reg::CPF,p206Voice);
            const auto ptrx=core.ReadDriver(Reg::PTRX,p206Voice);
            const auto cvcf=core.ReadDriver(Reg::CVCF,p206Voice);
            const auto hex=[&](uint32_t val,int n) {
                std::ostringstream os;
                os<<std::uppercase<<std::hex<<std::setfill('0')<<std::setw(n)<<val;
                return os.str();
            };
            p206Out<<(at-p206NoteOn)<<'\t'<<p206Voice<<'\t'
                    <<hex(atk,4)<<'\t'<<hex(env,4)<<'\t'
                    <<hex(pefe,4)<<'\t'<<hex(ip,4)<<'\t'
                    <<hex(cpf,8)<<'\t'<<hex(ptrx,8)<<'\t'
                    <<hex(cvcf,8)<<'\n';
            ++p206Count;
        };
        auto render=[&](uint64_t end) {
            end=std::min(end,count);
            while(at<end) {
                uint64_t stop=end;
                if(p206Active) stop=std::min(stop,p206Next);
                if(stop<=at)throw std::runtime_error("P206 readback clock stalled");
                auto n=uint32_t(std::min<uint64_t>(1024,stop-at));
                synth.RenderBlock(buffer.data(),n);
                wav.write(reinterpret_cast<const char*>(buffer.data()),
                          n*2*sizeof(int16_t));
                for(size_t i=0;i<size_t(n)*2;++i) {
                    int64_t x=buffer[i];nz+=x!=0;
                    peak=std::max<uint64_t>(peak,uint64_t(std::abs(x)));
                    total+=static_cast<long double>(x)*x;
                }
                at+=n;
                if(p206Active && at==p206Next) {
                    p206Snapshot();
                    p206Next+=p206Step;
                    if(p206Count==31) {
                        synth.Core().CloseTrace();
                        p206Active=false;
                        p206Completed=true;
                    }
                }
            }
        };
        for(const auto& e:midi) {
            if(e.frame>=count)break;
            render(e.frame);
            const bool p206Target = p206 && e.frame==p206NoteOn &&
                e.type=="note_on" && e.channel==0 && e.a==59 && e.b>0;
            if(p206Target) {
                if(p206Voice>=0)throw std::runtime_error("Repeated P206 note59 MIDI");
                if(!synth.Core().OpenTrace(p206Trace.c_str()))
                    throw std::runtime_error("Cannot open P206 native chip trace");
            }
            dispatch(synth,e);++applied;
            if(p206Target) {
                using Emu8000::Reg;
                const auto& sf=synth.BankAt(synth.BankCount()-1);
                const auto regions=sf.Select(0,0,59,e.b);
                if(regions.size()!=1)
                    throw std::runtime_error("P206 original note59 must select exactly one sample zone");
                for(int v=0;v<32;++v) {
                    const auto atk=synth.Core().Read(Reg::ATKHLD,v);
                    const auto pefe=synth.Core().Read(Reg::PEFE,v);
                    if((atk&127u)==0x0Cu && ((pefe>>8)&255u)==0x7Fu) {
                        if(p206Voice>=0)
                            throw std::runtime_error("P206 multiple matching EG1 note59 voices");
                        p206Voice=v;
                    }
                }
                if(p206Voice<0)
                    throw std::runtime_error("P206 active note59 missing attack=0x0C/PEFE=0x7F");
                if(synth.Core().Read(Reg::ENVVAL,p206Voice)!=0x7A48u)
                    throw std::runtime_error("P206 original delay tc0 not ENVVAL=0x7A48");
                p206Snapshot();
                p206Next=at+p206Step;
                p206Active=true;
            }
            // Test the actual chip registers AFTER the SF2/MIDI driver
            // assigned voices. Both send dimensions must retain at least
            // one hardware-like intermediate 1..254 value: forcing all
            // nonzero sends to 255 (GUI at 100%) is not a valid oracle.
            if(e.type=="note_on" && e.b>0) {
                using Emu8000::Reg;
                for(int v=0;v<32;++v) {
                    const uint32_t ptrx=synth.Core().ReadDriver(Reg::PTRX,v);
                    const uint32_t csl=synth.Core().ReadDriver(Reg::CSL,v);
                    const uint32_t hall=(ptrx>>Emu8000::kReverbShift)&255u;
                    const uint32_t chorus=(csl>>Emu8000::kChorusShift)&255u;
                    partialHall+=(hall>0 && hall<255);
                    partialChorus+=(chorus>0 && chorus<255);
                }
            }
        }
        render(count);
        if(p206 && (!p206Completed || p206Count!=31 || !p206Out.good()))
            throw std::runtime_error("P206 note59 sample-clock register readback incomplete");
        if(!wav.good()||nz==0)throw std::runtime_error("PCM output missing/silent");
        if(!partialHall || !partialChorus)
            throw std::runtime_error(
                "P193 FX oracle invalid: no intermediate physical Hall/Chorus "
                "send registers were observed (check test SoundFont and driver)");
        std::cout<<"P193 CT4390 historical FX reference; intermediate Hall="
                 <<partialHall<<" Chorus="<<partialChorus<<" register observations\n";
        std::cout<<"P97 true 86Box EMU8000; "<<seconds<<"sec, "<<applied
                 <<" MIDI events, "<<nz<<" nonzero stereo PCM samples"
                 <<", peak "<<peak<<", RMS16 "
                 <<double(std::sqrt(total/(count*2)))<<"\n";
        return 0;
    } catch(const std::exception& ex) {
        std::cerr<<"P97 FAIL: "<<ex.what()<<"\n";return 1;
    }
}
