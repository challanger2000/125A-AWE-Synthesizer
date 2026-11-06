#include "Synth.h"
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>

// Both executables receive the SAME public synthetic bank. The reference
// differs only by forcing coefficient recomputation on every sample.
int main(int argc,char** argv) {
    if(argc!=3)return 2;
    const auto assets=std::filesystem::path(argv[1]);
    std::ofstream out(argv[2],std::ios::binary);
    bool heard=false;
    for(int rate:{44100,48000,96000}) {
        Synth synth(rate);std::string error;
        synth.Core().SetDriver(Awe32::Driver::Win95);
        if(!synth.Core().UseBox86Chip((assets/"zero.rom").string(),error))return 2;
        synth.Core().PowerOnInit();
        if(!synth.LoadBank((assets/"bank.sf2").string(),error))return 2;
        for(int i=0;i<16;++i)synth.NoteOn(i%4,48+i,100);
        std::vector<int16_t> pcm(2048);
        for(int block=0;block<160;++block) {
            // Change cutoff and Q independently, including bypass/re-entry,
            // key/velocity modulation and every legal resonance value.
            for(int voice=0;voice<32;++voice) {
                auto& c=synth.Core();
                if(block%4==0) {
                    const int cutoff=(block/4)%4==0?255:((block*13+voice*7)%256);
                    c.Write(Emu8000::Reg::IFATN,voice,cutoff<<8);
                }
                if(block%4==1) {
                    const auto address=c.Read(Emu8000::Reg::CCCA,voice);
                    c.Write(Emu8000::Reg::CCCA,voice,(address&0x0FFFFFFFu)|((block/4%16u)<<28));
                }
                if(block%4==2) {
                    c.Write(Emu8000::Reg::PEFE,voice,block<64?0:0x7F80);
                    c.Write(Emu8000::Reg::FMMOD,voice,block<64?0:0x007F);
                }
            }
            if(block%7==0)synth.PitchBendAutomated(block%4,block*41-4096);
            if(block%11==0)synth.NoteOn(block%4,48+block%32,100);
            synth.RenderBlock(pcm.data(),1024);
            heard|=std::any_of(pcm.begin(),pcm.end(),[](auto v){return v!=0;});
            out.write(reinterpret_cast<char*>(pcm.data()),pcm.size()*sizeof(int16_t));
        }
    }
    std::cout<<"rate/Q/cutoff/modulation/voice-stealing PCM generated, audible="<<heard<<'\n';
    return out&&heard?0:1;
}
