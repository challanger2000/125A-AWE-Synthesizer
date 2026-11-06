// P129 permanent direct-chip DSP regression: synthetic integer samples only.
// Tests the native production emu8k_work_chorus() with zero input and an
// initialized signed one-LSB delay line. Does not use ROM, SF2 or a DAW.
extern "C" {
#include <86box/86box.h>
#include <86box/sound.h>
#include <86box/snd_emu8k.h>
void emu8k_work_chorus(int32_t*,int32_t*,emu8k_chorus_eng_t*,int);
}
#include <array>
#include <algorithm>
#include <cstdint>
#include <iostream>
#include <memory>

struct Result {int64_t lastTotal=0; int32_t tailMin=0,tailMax=0; int32_t storageMin=0,storageMax=0;};

Result run(int initial,int feedback) {
    auto e=std::make_unique<emu8k_chorus_eng_t>();
    e->feedback=feedback;
    e->delay_samples_central=64;
    e->lfodepth_multip=0.;
    e->delay_offset_samples_right=0.;
    std::fill(std::begin(e->chorus_left_buffer),
              std::end(e->chorus_left_buffer),initial);
    constexpr int kChunk=256;
    std::array<int32_t,kChunk> in{};
    std::array<int32_t,kChunk*2> out{};
    Result result;
    for(int frame=0;frame<32768;frame+=kChunk) {
        out.fill(0);
        emu8k_work_chorus(in.data(),out.data(),e.get(),kChunk);
        if(frame>=32768-kChunk) {
            result.tailMin=*std::min_element(out.begin(),out.end());
            result.tailMax=*std::max_element(out.begin(),out.end());
            for(auto s:out)result.lastTotal+=s;
        }
    }
    result.storageMin=*std::min_element(std::begin(e->chorus_left_buffer),
                                        std::end(e->chorus_left_buffer));
    result.storageMax=*std::max_element(std::begin(e->chorus_left_buffer),
                                        std::end(e->chorus_left_buffer));
    return result;
}
int main() {
    // feedback bytes for the 8 real SBAWE32 Chorus presets
    constexpr std::array<int,8> feedback{0,8,16,32,128,224,0,192};
    int failed=0,checked=0;
    for(int preset=0;preset<8;++preset) {
        const auto negative=run(-1,feedback[preset]);
        const auto positive=run(+1,feedback[preset]);
        const bool negativeSilent=negative.tailMin==0&&negative.tailMax==0&&
            negative.storageMin==0&&negative.storageMax==0;
        const bool positiveSilent=positive.tailMin==0&&positive.tailMax==0&&
            positive.storageMin==0&&positive.storageMax==0;
        ++checked;if(!negativeSilent)++failed;
        ++checked;if(!positiveSilent)++failed;
        std::cout<<"CHORUS_CORE preset="<<preset
                 <<" feedback="<<feedback[preset]
                 <<" minus1_tail=["<<negative.tailMin<<","<<negative.tailMax<<"]"
                 <<" minus1_buffer=["<<negative.storageMin<<","<<negative.storageMax<<"]"
                 <<" plus1_tail=["<<positive.tailMin<<","<<positive.tailMax<<"]"
                 <<" plus1_buffer=["<<positive.storageMin<<","<<positive.storageMax<<"]"
                 <<" expected_zero_after_32768="<<negativeSilent
                 <<" positive_control_zero="<<positiveSilent<<'\n';
    }
    std::cout<<"CHORUS_CORE checks="<<checked<<" failures="<<failed<<'\n';
    return failed?1:0;
}
