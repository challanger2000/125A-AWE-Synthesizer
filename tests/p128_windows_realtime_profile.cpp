// P128 audit-only native Windows performance reproduction. Real production
// Synth->Emu8000Core->86Box sound chip, public synthetic ROM/SF2. NEVER a
// Windows ASIO, DAW or guaranteed RT deadline acceptance.
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

struct Reading {std::string caseName; int block; double wallMs;};
static constexpr int kRate=44100,kFrames=1024,kSamples=500;
static constexpr double kBudgetMs=1000.0*double(kFrames)/double(kRate);
using Clock=std::chrono::steady_clock;

static bool measure(const std::string& name,int voices,bool bends,
                   const std::filesystem::path& dir,
                   std::vector<Reading>& readings) {
    Synth synth(kRate);
    std::string error;
    synth.Core().SetDriver(Awe32::Driver::Win95);
    if(!synth.Core().UseBox86Chip((dir/"zero.rom").string(),error)) {
        std::cerr<<"ROM failed: "<<error<<"\n"; return false;
    }
    synth.Core().PowerOnInit();
    if(!synth.LoadBank((dir/"bank.sf2").string(),error)) {
        std::cerr<<"SF2 failed: "<<error<<"\n"; return false;
    }
    synth.SelectBrowserBank(0);
    synth.ProgramChange(0,0);
    for(int i=0;i<voices;++i)
        synth.NoteOn(0,static_cast<uint8_t>(45+i),110,static_cast<uint64_t>(i+1));
    const auto held=synth.CaptureHeldNotes();
    const int captured=static_cast<int>(std::count_if(held.begin(),held.end(),
                         [](const auto& n){return n.sequence!=0;}));
    if(captured<voices) {
        std::cerr<<"Insufficient actual held voice allocations: "<<captured
                 <<" wanted "<<voices<<"\n";
        return false;
    }
    std::array<int16_t,kFrames*2> pcm{};
    const auto block=[&](int sequence) {
        if(!bends) synth.RenderBlock(pcm.data(),kFrames);
        else {
            // 128 independent bend points at 8-frame boundaries;
            // no artificial pitchbend index processing shortcut.
            for(int p=0;p<128;++p) {
                const int bend=((p+sequence)&1)?4096:-4096;
                synth.PitchBendAutomated(0,static_cast<int16_t>(bend));
                synth.RenderBlock(pcm.data()+16*p,8);
            }
        }
    };
    for(int warm=0;warm<8;++warm)block(warm);
    bool audible=false;int missed=0;
    std::vector<double> samples;
    samples.reserve(kSamples);
    for(int n=0;n<kSamples;++n) {
        const auto t0=Clock::now();
        block(n+8);
        const auto t1=Clock::now();
        const double ms=std::chrono::duration<double,std::milli>(t1-t0).count();
        samples.push_back(ms);
        readings.push_back({name,n,ms});
        missed+=ms>kBudgetMs;
        if(n==0||n==kSamples-1)
            audible|=std::any_of(pcm.begin(),pcm.end(),[](int16_t x){return x!=0;});
    }
    std::sort(samples.begin(),samples.end());
    const auto percentile=[&](double pct) {
        const auto i=static_cast<size_t>(std::ceil(pct*double(samples.size())))-1;
        return samples.at(i);
    };
    const double average=std::accumulate(samples.begin(),samples.end(),0.)/
                         double(samples.size());
    std::cout<<std::fixed<<std::setprecision(4)
             <<"RT_PROFILE case="<<name
             <<" voices="<<voices<<" captured_held_notes="<<captured
             <<" bend_points_per_block="<<(bends?128:0)
             <<" sample_rate="<<kRate<<" frames="<<kFrames
             <<" callbacks="<<kSamples<<" budget_ms="<<kBudgetMs
             <<" mean_ms="<<average
             <<" p95_ms="<<percentile(.95)<<" p99_ms="<<percentile(.99)
             <<" max_ms="<<samples.back()
             <<" exceeded="<<missed<<" audible="<<audible
             <<" ENV=GITHUB_WINDOWS_SHARED_VM_NO_ASIO\n";
    return audible;
}

int main(int argc,char** argv) {
    if(argc!=3)return 2;
    const auto dir=std::filesystem::path(argv[1]);
    std::vector<Reading> readings;
    readings.reserve(4*kSamples);
    bool valid=true;
    valid&=measure("one_voice",1,false,dir,readings);
    valid&=measure("sixteen_voices",16,false,dir,readings);
    valid&=measure("thirty_voices",30,false,dir,readings);
    valid&=measure("sixteen_voices_128_bends",16,true,dir,readings);
    std::ofstream csv(argv[2],std::ios::trunc);
    csv<<"case,callback,wall_ms\n";
    csv<<std::fixed<<std::setprecision(6);
    for(const auto& r:readings)
        csv<<r.caseName<<","<<r.block<<","<<r.wallMs<<"\n";
    return valid&&csv.good()&&readings.size()==4*kSamples?0:1;
}
