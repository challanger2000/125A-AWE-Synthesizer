// P113: output-rail diagnostic on nine P112 high-peak SF2 presets.
// Collects counts, durations and velocities, WITHOUT changing any audio samples.
// The original private ROM, SYNTHGM.SBK and user's SF2 stay on the local PC.
// A 16-bit rail hit alone is not proof of audible distortion.
#include "Synth.h"
#include "SoundFont.h"
#include "RomGmBank.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
struct Meter {
    int peak=0;
    double squares=0.0;
    uint64_t samples=0, frames=0, railSamples=0, railFrames=0;
    uint64_t nearRailSamples=0, longestRun=0, currentRun=0;
    int64_t firstRailFrame=-1;

    void observe(const int16_t* stereo, size_t count) {
        for(size_t frame=0;frame<count;++frame) {
            bool frameRail=false;
            for(size_t ch=0;ch<2;++ch) {
                const int value=static_cast<int>(stereo[2*frame+ch]);
                const int magnitude=std::abs(value); // -32768 -> 32768 (int)
                peak=std::max(peak,magnitude);
                squares+=static_cast<double>(value)*value;
                ++samples;
                if(value==32767 || value==-32768) {
                    ++railSamples;
                    frameRail=true;
                }
                if(magnitude>=32700)++nearRailSamples;
            }
            if(frameRail) {
                ++railFrames;
                if(firstRailFrame<0)firstRailFrame=static_cast<int64_t>(frames);
                ++currentRun;
                longestRun=std::max(longestRun,currentRun);
            } else currentRun=0;
            ++frames;
        }
    }
    double rms() const {
        return samples ? std::sqrt(squares/static_cast<double>(samples))/32768.0 : 0.0;
    }
};
Meter capture(Synth& synth,int frameCount) {
    Meter result;
    std::array<int16_t,4096*2> pcm{};
    for(int remaining=frameCount;remaining>0;) {
        const int frames=std::min<int>(remaining,4096);
        synth.RenderBlock(pcm.data(),static_cast<uint32_t>(frames));
        result.observe(pcm.data(),static_cast<size_t>(frames));
        remaining-=frames;
    }
    return result;
}
std::string csv(std::string_view input) {
    std::string out="\"";
    for(char c:input){if(c=='\"')out+='\"';out+=c;}
    return out+"\"";
}
void writeMeter(std::ostream& out,const Meter& m) {
    out<<m.peak<<","<<m.rms()<<","<<m.railSamples<<","
       <<m.railFrames<<","<<m.longestRun<<","<<m.nearRailSamples
       <<","<<m.firstRailFrame;
}
bool selfTest() {
    Meter m;
    constexpr std::array<int16_t,8> data{
        32767,-32768, 0,-32768, 1,2, 32699,-32699
    };
    m.observe(data.data(),4);
    const bool ok=m.peak==32768 && m.samples==8 && m.frames==4 &&
                  m.railSamples==3 && m.railFrames==2 &&
                  m.longestRun==2 && m.nearRailSamples==3 &&
                  m.firstRailFrame==0 && m.rms()>0.0;
    std::cout<<(ok?"P113_SELFTEST_PASS":"P113_SELFTEST_FAIL")<<"\n";
    return ok;
}
struct Program {int id;const char* label;};
constexpr Program kTargets[] {
    {0,"control"},{2,"high"},{4,"high"},{7,"near-full-scale"},
    {33,"high"},{45,"high"},{54,"high"},{56,"high"},
    {58,"high"},{61,"high"},{69,"control"}
};
constexpr int kVelocities[]={64,100,127};

void usage() {
    std::cerr<<"P113 --rom awe32.raw --gm SYNTHGM.SBK --sf2 bank.sf2 --out report.csv\n"
             <<"       or: P113 --selftest\n";
}
}

int main(int argc,char** argv) {
    try {
        namespace fs=std::filesystem;
        if(argc==2 && std::string(argv[1])=="--selftest")
            return selfTest()?0:1;
        std::string rom,gm,sf2;
        fs::path dest="125A-P113-Pegel-Diagnose.csv";
        for(int i=1;i<argc;i+=2) {
            if(i+1>=argc){usage();return 2;}
            const std::string flag=argv[i],value=argv[i+1];
            if(flag=="--rom")rom=value;
            else if(flag=="--gm")gm=value;
            else if(flag=="--sf2")sf2=value;
            else if(flag=="--out")dest=fs::u8path(value);
            else {usage();return 2;}
        }
        if(rom.empty()||gm.empty()||sf2.empty()){usage();return 2;}
        std::string err;
        if(!AWE125::RomGmBank::ValidDescriptor(gm,err))
            throw std::runtime_error("GM descriptor invalid: "+err);
        const auto source=SoundFont::Load(sf2);
        if(!source.valid)throw std::runtime_error("Private SF2 cannot be loaded: "+source.errorMessage);
        const auto gmSource=SoundFont::Load(gm);
        if(!gmSource.valid)throw std::runtime_error("GM bank cannot be loaded: "+gmSource.errorMessage);
        if(source.presets.size()!=77)
            throw std::runtime_error("This exact P112 follow-up expects the tested 77-preset SF2; refusing mismatched bank");
        // Do not write a success-looking CSV unless all assets can actually be loaded.
        {
            Synth s(44100);
            s.Core().SetDriver(Awe32::Driver::Win95);
            if(!s.Core().UseBox86Chip(rom,err)||
                s.Core().ChipVariant()!=Emu8000Core::Chip::Box86)
                throw std::runtime_error("86Box ROM not active: "+err);
            s.Core().PowerOnInit();
            if(!s.LoadBank(gm,err,true,0) ||
               !s.LoadBank(sf2,err) ||
               !s.LoadBank(gm,err,true,AWE125::RomGmBank::kBrowserBank,
                                       AWE125::RomGmBank::kBrowserDrums))
                throw std::runtime_error("P112 bank layering failed: "+err);
        }
        std::ofstream output(dest,std::ios::binary|std::ios::trunc);
        if(!output)throw std::runtime_error("Cannot write CSV");
        output<<"Program,Name,Note,Velocity,Group,"
                 "HoldPeak,HoldRMS,HoldRailSamples,HoldRailFrames,"
                 "HoldLongestRailRunFrames,HoldNearRailSamples,HoldFirstRailFrame,"
                 "ReleasePeak,ReleaseRMS,ReleaseRailSamples,ReleaseRailFrames,"
                 "ReleaseLongestRailRunFrames,ReleaseNearRailSamples,ReleaseFirstRailFrame,"
                 "Status\n";
        int measured=0,rails=0;
        for(const auto& p:kTargets) {
            const auto* preset=source.FindPreset(0,p.id);
            if(!preset)throw std::runtime_error("Missing exact SF2 program "+std::to_string(p.id));
            for(int vel:kVelocities) {
                constexpr int note=48; // identical to P112
                const auto regions=source.Select(0,p.id,note,vel);
                if(regions.empty()) {
                    output<<p.id<<","<<csv(preset->name)<<",48,"<<vel<<","
                          <<p.label<<",,,,,,,,,,,,,,,NO_REGION\n";
                    continue;
                }
                // Fresh ROM-backed synth per test: no voice/preset leakage.
                Synth s(44100);
                s.Core().SetDriver(Awe32::Driver::Win95);
                if(!s.Core().UseBox86Chip(rom,err) ||
                    s.Core().ChipVariant()!=Emu8000Core::Chip::Box86)
                    throw std::runtime_error("86Box chip init failed: "+err);
                s.Core().PowerOnInit();
                if(!s.LoadBank(gm,err,true,0) ||
                   !s.LoadBank(sf2,err) ||
                   !s.LoadBank(gm,err,true,AWE125::RomGmBank::kBrowserBank,
                                           AWE125::RomGmBank::kBrowserDrums))
                    throw std::runtime_error("P112 bank loading failed: "+err);
                s.SelectBrowserBank(0);
                s.ProgramChange(0,static_cast<uint8_t>(p.id));
                s.NoteOn(0,note,static_cast<uint8_t>(vel));
                const auto held=capture(s,44100);
                s.NoteOff(0,note);
                const auto released=capture(s,22050);
                const bool rail=(held.railSamples+released.railSamples)>0;
                ++measured;
                rails+=rail?1:0;
                output<<p.id<<","<<csv(preset->name)<<",48,"<<vel<<","
                      <<p.label<<",";
                writeMeter(output,held); output<<",";
                writeMeter(output,released);
                output<<","<<(rail?"RAIL_PRESENT":"NO_RAIL")<<"\n";
                std::cout<<"P113 "<<p.id<<" "<<preset->name<<" velocity "<<vel
                         <<" hold_peak="<<held.peak<<" hold_rail_samples="
                         <<held.railSamples<<" max_run_frames="<<held.longestRun
                         <<" => "<<(rail?"RAIL_PRESENT":"NO_RAIL")<<"\n";
            }
        }
        output.flush();
        if(!output)throw std::runtime_error("Failed while writing diagnostic CSV");
        std::cout<<"P113_RESULT measured="<<measured<<" with_rails="<<rails
                 <<" report="<<dest.string()<<"\n"
                 <<"RAIL_PRESENT indicates 16-bit full-scale samples, NOT automatically audible clipping.\n";
        return measured==33?0:3;
    } catch(const std::exception& e) {
        std::cerr<<"P113_ERROR: "<<e.what()<<"\n";
        return 1;
    }
}
