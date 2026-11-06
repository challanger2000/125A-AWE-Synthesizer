// P132 AUDIT ONLY. Call the actual 86Box chorus kernel, not a reimplementation.
// The original and the P129 signed-division candidate are built separately
// from ONE pinned base with only the arithmetic expression changed in CI.
// This is synthetic internal-PCM evidence; NOT physical EMU8000 parity.
extern "C" {
#include <86box/86box.h>
#include <86box/sound.h>
#include <86box/snd_emu8k.h>
void emu8k_work_chorus(int32_t*,int32_t*,emu8k_chorus_eng_t*,int);
}
#include "Emu8000Effects.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
constexpr int kRate=44100;
constexpr int kDuration=4*kRate;
constexpr int kBlock=256;
constexpr int kZeroFrames=32768;
struct Observation {
    int32_t tailMin=0,tailMax=0;
    int32_t ringMin=0,ringMax=0;
};
std::unique_ptr<emu8k_chorus_eng_t> engine(int preset) {
    const auto& cfg=Emu8000Fx::kChorusPresets[preset];
    auto e=std::make_unique<emu8k_chorus_eng_t>();
    e->feedback=int(cfg.feedback&0xFF);
    e->delay_samples_central=int(cfg.delaySamples&0x1FFF);
    e->lfodepth_multip=double(cfg.depth&0xFF);
    e->delay_offset_samples_right=preset>=6 ? double(0x0006E000)/256. : 0.;
    e->lfo_inc.addr=uint64_t(cfg.lfoFreq)<<24;
    return e;
}
Observation zeroTail(int preset,int initial) {
    auto e=engine(preset);
    std::fill(std::begin(e->chorus_left_buffer),
              std::end(e->chorus_left_buffer),initial);
    std::array<int32_t,kBlock> in{};
    std::array<int32_t,kBlock*2> out{};
    Observation o{std::numeric_limits<int32_t>::max(),
                  std::numeric_limits<int32_t>::min(),0,0};
    for(int pos=0;pos<kZeroFrames;pos+=kBlock) {
        out.fill(0);
        emu8k_work_chorus(in.data(),out.data(),e.get(),kBlock);
        if(pos>=kZeroFrames-kBlock) {
            for(auto x:out) {
                o.tailMin=std::min(o.tailMin,x);
                o.tailMax=std::max(o.tailMax,x);
            }
        }
    }
    o.ringMin=*std::min_element(std::begin(e->chorus_left_buffer),
                                 std::end(e->chorus_left_buffer));
    o.ringMax=*std::max_element(std::begin(e->chorus_left_buffer),
                                 std::end(e->chorus_left_buffer));
    return o;
}
bool silent(const Observation& o) {
    return o.tailMin==0&&o.tailMax==0&&o.ringMin==0&&o.ringMax==0;
}
void render(int preset,const std::filesystem::path& outPath) {
    auto e=engine(preset);
    std::ofstream out(outPath,std::ios::binary|std::ios::trunc);
    if(!out)throw std::runtime_error("cannot open raw PCM output");
    std::array<int32_t,kBlock> in{};
    std::array<int32_t,kBlock*2> stereo{};
    for(int pos=0;pos<kDuration;pos+=kBlock) {
        in.fill(0);
        stereo.fill(0);
        const int count=std::min(kBlock,kDuration-pos);
        // Bipolar fixed-point impulses with long silence; these values
        // are internal synthetic effect-send units, not WAV samples.
        const std::array<std::pair<int,int>,4> impulses{{
            {0,+4096},{kRate/3,-4096},{2*kRate/3,+8192},{kRate,-8192}
        }};
        for(const auto& [sample,amp]:impulses)
            if(sample>=pos && sample<pos+count)
                in[size_t(sample-pos)]=amp;
        emu8k_work_chorus(in.data(),stereo.data(),e.get(),count);
        out.write(reinterpret_cast<const char*>(stereo.data()),
                  std::streamsize(count)*2*sizeof(int32_t));
    }
    if(!out.good())throw std::runtime_error("failed writing raw effect PCM");
}
}
int main(int argc,char** argv) {
    try {
        if(argc!=3)throw std::runtime_error("usage: p132_chorus_probe OUTDIR original|candidate");
        const std::string mode=argv[2];
        if(mode!="original"&&mode!="candidate")
            throw std::runtime_error("invalid expected mode");
        const auto path=std::filesystem::path(argv[1]);
        std::filesystem::create_directories(path);
        std::ofstream stats(path/(mode+"-tail.csv"));
        if(!stats)throw std::runtime_error("unable to write summary");
        stats<<"preset,feedback,negative_silent,positive_silent,negative_tail_min,"
                "negative_tail_max,negative_ring_min,negative_ring_max,"
                "positive_tail_min,positive_tail_max,positive_ring_min,positive_ring_max\n";
        bool valid=true;
        int affected=0;
        for(int preset=0;preset<8;++preset) {
            const auto& cfg=Emu8000Fx::kChorusPresets[preset];
            const int feedback=int(cfg.feedback&0xFF);
            const auto minus=zeroTail(preset,-1);
            const auto plus=zeroTail(preset,+1);
            const bool m=silent(minus),p=silent(plus);
            // Original flooring retains the -1 LSB tail for feedback>0.
            // Candidate signed division removes it. Neither is hardware
            // proof; this check assures our candidate is isolated.
            const bool expectNegative=mode=="candidate"||feedback==0;
            valid=valid && (m==expectNegative) && p;
            affected+=feedback>0;
            stats<<preset<<','<<feedback<<','<<m<<','<<p<<','
                 <<minus.tailMin<<','<<minus.tailMax<<','
                 <<minus.ringMin<<','<<minus.ringMax<<','
                 <<plus.tailMin<<','<<plus.tailMax<<','
                 <<plus.ringMin<<','<<plus.ringMax<<'\n';
            const auto pcm=path/(mode+"-preset-"+std::to_string(preset)+".raw");
            render(preset,pcm);
            std::cout<<"P132_CHORUS mode="<<mode<<" preset="<<preset
                     <<" feedback="<<feedback
                     <<" negative_silent="<<m
                     <<" positive_silent="<<p
                     <<" expected_negative_silent="<<expectNegative
                     <<" pcm_frames="<<kDuration
                     <<'\n';
        }
        stats.flush();
        valid=valid && stats.good() && affected==6;
        std::cout<<"P132_VERDICT mode="<<mode
                 <<" tests_complete="<<valid
                 <<" feedback_presets="<<affected
                 <<" hardware_parity_proven=0\n";
        return valid?0:1;
    } catch(const std::exception& e) {
        std::cerr<<"P132_INVALID "<<e.what()<<'\n';
        return 2;
    }
}
