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
    if(argc!=11) {
        std::cerr<<"Usage: awe32_p97_midi_renderer --rom ROM --sf2 SF2 --events TSV"
                   " --out WAV --seconds 1..300\n";return 2;
    }
    try {
        std::string rom,sf2,tsv,out;int seconds=0;
        for(int i=1;i<argc;i+=2) {
            std::string k=argv[i],v=argv[i+1];
            if(k=="--rom")rom=v;else if(k=="--sf2")sf2=v;
            else if(k=="--events")tsv=v;else if(k=="--out")out=v;
            else if(k=="--seconds")seconds=std::stoi(v);
            else throw std::runtime_error("Unknown argument "+k);
        }
        if(seconds<1||seconds>300)throw std::runtime_error("Invalid duration");
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
        if(!synth.LoadBank(sf2,error))
            throw std::runtime_error("Real test SoundFont failed: "+error);
        synth.SelectBrowserBank(0);
        std::ofstream wav(out,std::ios::binary|std::ios::trunc);
        if(!wav)throw std::runtime_error("Output WAV cannot be created");
        header(wav,count);
        std::vector<int16_t> buffer(2048);
        uint64_t at=0,nz=0,peak=0,applied=0;
        long double total=0;
        auto render=[&](uint64_t end) {
            end=std::min(end,count);
            while(at<end) {
                auto n=uint32_t(std::min<uint64_t>(1024,end-at));
                synth.RenderBlock(buffer.data(),n);
                wav.write(reinterpret_cast<const char*>(buffer.data()),
                          n*2*sizeof(int16_t));
                for(size_t i=0;i<size_t(n)*2;++i) {
                    int64_t x=buffer[i];nz+=x!=0;
                    peak=std::max<uint64_t>(peak,uint64_t(std::abs(x)));
                    total+=static_cast<long double>(x)*x;
                }
                at+=n;
            }
        };
        for(const auto& e:midi) {
            if(e.frame>=count)break;
            render(e.frame);dispatch(synth,e);++applied;
        }
        render(count);
        if(!wav.good()||nz==0)throw std::runtime_error("PCM output missing/silent");
        std::cout<<"P97 true 86Box EMU8000; "<<seconds<<"sec, "<<applied
                 <<" MIDI events, "<<nz<<" nonzero stereo PCM samples"
                 <<", peak "<<peak<<", RMS16 "
                 <<double(std::sqrt(total/(count*2)))<<"\n";
        return 0;
    } catch(const std::exception& ex) {
        std::cerr<<"P97 FAIL: "<<ex.what()<<"\n";return 1;
    }
}
