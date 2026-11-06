// AUDIT ONLY: same deterministic ROM/SF2, note events, real 86Box render
// and read-back register mirror in TWO separately compiled copies of P128.
// This is a strict PCM + mirrored-register equivalence oracle, not a
// hardware-reference capture. Timings on a shared VM are indicative only.
#include "Synth.h"
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <string>
#include <vector>

using Emu8000::Reg;
using Clock=std::chrono::steady_clock;
constexpr int kSampleRate=44100,kCalls=400;
constexpr uint64_t kFNVOffset=14695981039346656037ULL;
constexpr uint64_t kFNVPrime=1099511628211ULL;
static uint64_t update(uint64_t hash,uint16_t word) {
    hash^=(word&0xFFu);hash*=kFNVPrime;
    hash^=((word>>8)&0xFFu);hash*=kFNVPrime;
    return hash;
}
int main(int argc,char** argv) {
    if(argc!=3)return 2;
    const auto dir=std::filesystem::path(argv[1]);
    std::ofstream csv(argv[2],std::ios::trunc);
    if(!csv)return 3;
    csv<<"case,frames,callback,wall_ms\n";
    bool allAudible=true;
    for(const int frames:{128,1024}) {
        for(const int voices:{1,16,30}) {
            for(const bool bends:{false,true}) {
                // Dense pitch points are intentionally checked at 16 voices,
                // where they were measured in the original release audit.
                if(bends&&voices!=16)continue;
                Synth synth(kSampleRate);
                synth.Core().SetDriver(Awe32::Driver::Win95);
                std::string error;
                if(!synth.Core().UseBox86Chip((dir/"zero.rom").string(),error)) {
                    std::cerr<<"box chip: "<<error<<'\n'; return 4;
                }
                synth.Core().PowerOnInit();
                if(!synth.LoadBank((dir/"bank.sf2").string(),error)) {
                    std::cerr<<"soundfont: "<<error<<'\n';return 5;
                }
                synth.SelectBrowserBank(0);
                synth.ProgramChange(0,0);
                for(int i=0;i<voices;++i)
                    synth.NoteOn(0,static_cast<uint8_t>(45+i),110,
                                 static_cast<uint64_t>(i+1));
                const auto held=synth.CaptureHeldNotes();
                const auto count=std::count_if(held.begin(),held.end(),
                    [](const auto& n){return n.sequence!=0;});
                if(count!=voices)return 6;
                std::vector<int16_t> pcm(static_cast<size_t>(frames)*2);
                const auto block=[&](int step) {
                    if(!bends) {
                        synth.RenderBlock(pcm.data(),static_cast<uint32_t>(frames));
                    } else {
                        // 128 frames = 16 pitch points. 1024 = 128.
                        for(int pos=0;pos<frames;pos+=8) {
                            const int bend=(((pos/8)+step)&1)?4096:-4096;
                            synth.PitchBendAutomated(0,static_cast<int16_t>(bend));
                            synth.RenderBlock(pcm.data()+2*pos,8);
                        }
                    }
                };
                for(int warm=0;warm<8;++warm)block(warm);
                uint64_t pcmHash=kFNVOffset;
                int heard=0;
                std::vector<double> times;
                times.reserve(kCalls);
                for(int n=0;n<kCalls;++n) {
                    const auto a=Clock::now();
                    block(n+8);
                    const auto b=Clock::now();
                    const double ms=std::chrono::duration<double,std::milli>(b-a).count();
                    times.push_back(ms);
                    bool audible=false;
                    for(const auto sample:pcm) {
                        pcmHash=update(pcmHash,static_cast<uint16_t>(sample));
                        audible|=sample!=0;
                    }
                    heard+=audible;
                    csv<<(bends?"bend":"steady")<<"_"<<voices<<","
                       <<frames<<","<<n<<","
                       <<std::fixed<<std::setprecision(6)<<ms<<"\n";
                }
                allAudible &= heard>=300;
                uint64_t mirrorHash=kFNVOffset;
                for(int ch=0;ch<32;++ch) {
                    for(const auto reg:{Reg::CCCA,Reg::CPF,Reg::CVCF,Reg::VTFT,
                                        Reg::IP,Reg::PTRX,Reg::PSST,Reg::CSL}) {
                        const uint32_t val=synth.Core().Read(reg,ch);
                        mirrorHash=update(mirrorHash,uint16_t(val));
                        mirrorHash=update(mirrorHash,uint16_t(val>>16));
                    }
                }
                std::sort(times.begin(),times.end());
                const double avg=std::accumulate(times.begin(),times.end(),0.0)/
                                 double(kCalls);
                std::cout<<std::fixed<<std::setprecision(4)
                    <<"DSP_AB case="<<(bends?"bend":"steady")<<"_"<<voices
                    <<" frames="<<frames
                    <<" callbacks="<<kCalls
                    <<" audible_blocks="<<heard
                    <<" mean_ms="<<avg
                    <<" p99_ms="<<times[static_cast<size_t>(std::ceil(.99*kCalls))-1]
                    <<" max_ms="<<times.back()
                    <<" pcm_fnv64="<<std::hex<<pcmHash
                    <<" reg_fnv64="<<mirrorHash<<std::dec<<"\n";
            }
        }
    }
    csv.flush();
    return allAudible&&csv.good()?0:7;
}
