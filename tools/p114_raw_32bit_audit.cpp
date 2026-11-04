// P114: measure the genuine final 32-bit EMU8000 sum before int16 clamping.
// Uses the user's private ROM/SBK/SF2 only on the user's PC.
// Output is per-preset scalar metadata; no audio or proprietary samples exported.
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
#include <limits>
#include <stdexcept>
#include <string>
#include <string_view>

namespace {
using Raw = Emu8000Core::RawOutputStats;
struct PcmMeter {
    int peak=0;
    double squared=0;
    uint64_t frames=0, samples=0, railSamples=0, railFrames=0;
    uint64_t longestRun=0, currentRun=0, nearRailSamples=0;
    int64_t firstRailFrame=-1;
    uint64_t hash=14695981039346656037ULL; // portable FNV-1a over int16 words

    void observe(const int16_t* pcm,size_t n) {
        for(size_t f=0;f<n;++f) {
            bool rail=false;
            for(size_t ch=0;ch<2;++ch) {
                const int value=static_cast<int>(pcm[2*f+ch]);
                const int magnitude=std::abs(value); // -32768 -> 32768
                peak=std::max(peak,magnitude);
                squared+=static_cast<double>(value)*value;
                ++samples;
                if(value==32767 || value==-32768) {
                    ++railSamples;rail=true;
                }
                if(magnitude>=32700)++nearRailSamples;
                const auto word=static_cast<uint16_t>(pcm[2*f+ch]);
                hash^=static_cast<uint8_t>(word);hash*=1099511628211ULL;
                hash^=static_cast<uint8_t>(word>>8);hash*=1099511628211ULL;
            }
            if(rail) {
                ++railFrames;
                if(firstRailFrame<0)firstRailFrame=static_cast<int64_t>(frames);
                ++currentRun;
                longestRun=std::max(longestRun,currentRun);
            } else currentRun=0;
            ++frames;
        }
    }
    double rms() const {
        return samples?std::sqrt(squared/static_cast<double>(samples))/32768.0:0.0;
    }
};
struct Phase {PcmMeter pcm; Raw raw;};
struct Result {Phase held;Phase released;};
Phase render(Synth& synth,int frames,bool tap) {
    Phase phase;
    synth.Core().SetRawOutputTap(tap?&phase.raw:nullptr);
    std::array<int16_t,4096*2> buffer{};
    for(int remaining=frames;remaining>0;) {
        const int n=std::min(remaining,4096);
        synth.RenderBlock(buffer.data(),static_cast<uint32_t>(n));
        phase.pcm.observe(buffer.data(),static_cast<size_t>(n));
        remaining-=n;
    }
    synth.Core().SetRawOutputTap(nullptr); // no dangling observer pointer
    if(tap && phase.raw.frames!=phase.pcm.frames)
        throw std::runtime_error("P114 raw frame count does not match PCM frame count");
    return phase;
}
std::string quote(std::string_view s) {
    std::string v="\"";
    for(char c:s) {if(c=='\"')v+='\"';v+=c;}
    return v+"\"";
}
void writePcm(std::ostream& out,const PcmMeter& m) {
    out<<m.peak<<","<<m.rms()<<","<<m.railSamples<<","<<m.railFrames
       <<","<<m.longestRun<<","<<m.nearRailSamples<<","<<m.firstRailFrame;
}
double excessDb(const Raw& m) {
    return m.maxAbsRaw>32768
        ? 20.0*std::log10(static_cast<double>(m.maxAbsRaw)/32768.0):0.0;
}
void writeRaw(std::ostream& out,const Raw& m) {
    out<<m.minRaw<<","<<m.maxRaw<<","<<m.maxAbsRaw<<","
       <<m.exceededSamples<<","<<m.exceededFrames<<","
       <<m.longestExceededRun<<","<<m.firstExceededFrame<<","
       <<m.overshootSum<<","<<excessDb(m);
}
void check(bool condition,const char* description) {
    if(!condition)throw std::runtime_error(description);
}
bool selftest() {
    try {
        Raw r;
        r.RecordFrame(32767,-32768); // at rails but no loss
        r.RecordFrame(32768,-32769); // two samples exceed by one each
        r.RecordFrame(33000,0); // one more, by 233
        r.RecordFrame(0,0);
        check(r.frames==4 && r.exceededSamples==3 &&
              r.exceededFrames==2 && r.longestExceededRun==2 &&
              r.firstExceededFrame==1 && r.minRaw==-32769 &&
              r.maxRaw==33000 && r.maxAbsRaw==33000 &&
              r.overshootSum==235,"raw tap threshold/duration incorrect");
        Raw edge;edge.RecordFrame(std::numeric_limits<int32_t>::min(),0);
        check(edge.maxAbsRaw==2147483648LL &&
              edge.exceededSamples==1 &&
              edge.overshootSum==2147450880LL,"INT32_MIN abs/overage overflow");
        PcmMeter m;
        const std::array<int16_t,8> data{32767,-32768,0,-32768,1,2,32699,-32699};
        m.observe(data.data(),4);
        check(m.peak==32768 && m.samples==8 && m.frames==4 &&
              m.railSamples==3 && m.railFrames==2 &&
              m.longestRun==2 && m.nearRailSamples==3 &&
              m.firstRailFrame==0 && m.rms()>0,"P113 compatibility meter incorrect");
        std::cout<<"P114_SELFTEST_PASS (32bit threshold, run length, int32 edge, P113 PCM meter)\n";
        return true;
    } catch(const std::exception& e) {
        std::cerr<<"P114_SELFTEST_FAIL: "<<e.what()<<"\n";
        return false;
    }
}
struct Program {int id;const char* group;};
constexpr Program targets[]{
    {0,"control"},{2,"high"},{4,"high"},{7,"near-full-scale"},
    {33,"high"},{45,"high"},{54,"high"},{56,"high"},
    {58,"high"},{61,"high"},{69,"control"}
};
constexpr int velocities[]{64,100,127};
Result play(const std::string& rom,const std::string& gm,
            const std::string& sf2,int program,int velocity,bool tap) {
    Synth synth(44100); // native rate: tap is exact pre-int16, no resampler
    synth.Core().SetDriver(Awe32::Driver::Win95);
    std::string error;
    check(synth.Core().UseBox86Chip(rom,error) &&
          synth.Core().ChipVariant()==Emu8000Core::Chip::Box86,
          "86Box original ROM could not be opened");
    synth.Core().PowerOnInit();
    check(synth.LoadBank(gm,error,true,0) &&
          synth.LoadBank(sf2,error) &&
          synth.LoadBank(gm,error,true,AWE125::RomGmBank::kBrowserBank,
                                        AWE125::RomGmBank::kBrowserDrums),
          "P112/P113 original bank loading failed");
    synth.SelectBrowserBank(0);
    synth.ProgramChange(0,static_cast<uint8_t>(program));
    synth.NoteOn(0,48,static_cast<uint8_t>(velocity));
    Result r;
    r.held=render(synth,44100,tap);
    synth.NoteOff(0,48);
    r.released=render(synth,22050,tap);
    return r;
}
void usage() {
    std::cerr<<"P114 --rom awe32.raw --gm SYNTHGM.SBK --sf2 original.sf2 --out report.csv\n"
             <<"P114 --selftest\n";
}
}
int main(int argc,char** argv) {
    try {
        if(argc==2 && std::string(argv[1])=="--selftest")
            return selftest()?0:1;
        std::string rom,gm,sf2;
        std::filesystem::path out="125A-P114-Rohpegel-Diagnose.csv";
        for(int i=1;i<argc;i+=2) {
            if(i+1>=argc){usage();return 2;}
            const std::string flag=argv[i],value=argv[i+1];
            if(flag=="--rom")rom=value;
            else if(flag=="--gm")gm=value;
            else if(flag=="--sf2")sf2=value;
            else if(flag=="--out")out=std::filesystem::u8path(value);
            else {usage();return 2;}
        }
        if(rom.empty()||gm.empty()||sf2.empty()){usage();return 2;}
        std::string error;
        check(AWE125::RomGmBank::ValidDescriptor(gm,error),
              "SYNTHGM.SBK is not a valid original GM ROM descriptor");
        const auto sf=SoundFont::Load(sf2);
        check(sf.valid && sf.presets.size()==77,
              "Expected original tested 77-program SF2 (P112/P113)");
        const auto gmBank=SoundFont::Load(gm);
        check(gmBank.valid,"GM-ROM descriptor is unreadable");
        // Strict preflight of all assets before creating a report.
        {
            Synth s(44100);s.Core().SetDriver(Awe32::Driver::Win95);
            check(s.Core().UseBox86Chip(rom,error) &&
                  s.Core().ChipVariant()==Emu8000Core::Chip::Box86,
                  "Original 86Box chip / ROM initialization failed");
            s.Core().PowerOnInit();
            check(s.LoadBank(gm,error,true,0) &&
                  s.LoadBank(sf2,error) &&
                  s.LoadBank(gm,error,true,AWE125::RomGmBank::kBrowserBank,
                                            AWE125::RomGmBank::kBrowserDrums),
                  "Preflight: GM+SF2+GM browser load failed");
        }
        for(const auto& preset:targets) {
            check(sf.FindPreset(0,preset.id)!=nullptr,
                  "Expected P113 program is missing from user's SF2");
            for(int v:velocities)
                check(!sf.Select(0,preset.id,48,v).empty(),
                      "Missing MIDI 48 region at an expected P113 velocity");
        }
        std::ofstream report(out,std::ios::binary|std::ios::trunc);
        check(static_cast<bool>(report),"Cannot create P114 report");
        report<<"Program,Name,Note,Velocity,Group,"
              <<"HoldPeak,HoldRMS,HoldRailSamples,HoldRailFrames,"
              <<"HoldLongestRailRunFrames,HoldNearRailSamples,HoldFirstRailFrame,"
              <<"ReleasePeak,ReleaseRMS,ReleaseRailSamples,ReleaseRailFrames,"
              <<"ReleaseLongestRailRunFrames,ReleaseNearRailSamples,ReleaseFirstRailFrame,"
              <<"Status,HoldRawMin,HoldRawMax,HoldRawAbsPeak,"
              <<"HoldRawExceededSamples,HoldRawExceededFrames,"
              <<"HoldRawLongestRunFrames,HoldRawFirstExceededFrame,"
              <<"HoldRawOvershootSum,HoldExcessDb,"
              <<"ReleaseRawMin,ReleaseRawMax,ReleaseRawAbsPeak,"
              <<"ReleaseRawExceededSamples,ReleaseRawExceededFrames,"
              <<"ReleaseRawLongestRunFrames,ReleaseRawFirstExceededFrame,"
              <<"ReleaseRawOvershootSum,ReleaseExcessDb,"
              <<"AB_PCM_BitExact\n";
        int cases=0,withExcess=0,atRailOnly=0;
        for(const auto& program:targets) {
            const auto* preset=sf.FindPreset(0,program.id);
            for(int vel:velocities) {
                const Result current=play(rom,gm,sf2,program.id,vel,true);
                const bool rawExcess=current.held.raw.exceededSamples ||
                                     current.released.raw.exceededSamples;
                const bool atRail=current.held.pcm.railSamples ||
                                  current.released.pcm.railSamples;
                if(rawExcess)++withExcess;
                if(atRail && !rawExcess)++atRailOnly;
                // Verify that enabling P114 has not changed a single PCM word
                // on one control case and one known hot case.
                const bool ab=(program.id==0 && vel==100) ||
                              (program.id==2 && vel==127);
                if(ab) {
                    const Result reference=play(rom,gm,sf2,program.id,vel,false);
                    check(current.held.pcm.hash==reference.held.pcm.hash &&
                          current.released.pcm.hash==reference.released.pcm.hash &&
                          current.held.pcm.samples==reference.held.pcm.samples &&
                          current.released.pcm.samples==reference.released.pcm.samples,
                          "P114 raw capture changed PCM relative to disabled tap");
                }
                const char* status=rawExcess?"RAW_EXCEEDS_INT16":
                                   atRail?"RAIL_WITHOUT_RAW_EXCESS":"NO_RAIL";
                report<<program.id<<","<<quote(preset->name)<<",48,"
                      <<vel<<","<<program.group<<",";
                writePcm(report,current.held.pcm);report<<",";
                writePcm(report,current.released.pcm);report<<","<<status<<",";
                writeRaw(report,current.held.raw);report<<",";
                writeRaw(report,current.released.raw);report<<","
                      <<(ab?"PASS":"NOT_RUN")<<"\n";
                std::cout<<"P114 "<<++cases<<"/33 program "<<program.id
                         <<" velocity "<<vel<<" hold raw peak "
                         <<current.held.raw.maxAbsRaw<<" (excess="
                         <<current.held.raw.exceededSamples<<") status "
                         <<status<<"\n";
            }
        }
        report.flush();check(static_cast<bool>(report),"P114 CSV output write failed");
        check(cases==33,"Not all original P113 cases were tested");
        std::cout<<"P114_COMPLETE cases="<<cases<<" actual_raw_excess="<<withExcess
                 <<" rail_without_raw_excess="<<atRailOnly
                 <<" AB_PCM=2/2_PASS\n"
                 <<"Do not infer hardware-faithfulness from this software-only measurement.\n"
                 <<"Report: "<<out.string()<<"\n";
        return 0;
    } catch(const std::exception& e) {
        std::cerr<<"P114_ERROR: "<<e.what()<<"\n";
        return 1;
    }
}
