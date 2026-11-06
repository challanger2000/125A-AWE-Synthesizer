// AUDIT ONLY: deterministic native chip chorus A/B PCM characterization.
// Outputs exactly the raw stereo PCM from production emu8k_work_chorus(), not
// an independently implemented model. No hardware equivalence claim.
extern "C" {
#include <86box/86box.h>
#include <86box/sound.h>
#include <86box/snd_emu8k.h>
void emu8k_work_chorus(int32_t*,int32_t*,emu8k_chorus_eng_t*,int);
}
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
int main(int argc,char** argv) {
    if(argc!=2)return 2;
    constexpr int SR=44100,seconds=4,frames=SR*seconds,chunk=256;
    constexpr double pi=3.14159265358979323846;
    constexpr std::array<int,8> fb{0,8,16,32,128,224,0,192};
    constexpr std::array<int,8> center{1014,794,794,617,1235,1102,2822,2822};
    constexpr std::array<int,8> depth{44,110,132,110,166,55,0,0};
    constexpr std::array<int,8> lfo{109,380,131,380,91,38,131,131};
    const auto dir=std::filesystem::path(argv[1]);
    std::filesystem::create_directories(dir);
    for(int preset=0;preset<8;++preset) {
        auto e=std::make_unique<emu8k_chorus_eng_t>();
        e->feedback=fb[preset];
        e->delay_samples_central=center[preset];
        e->lfodepth_multip=depth[preset];
        e->lfo_inc.addr=uint64_t(lfo[preset])<<24;
        std::array<int32_t,chunk> in{};
        std::array<int32_t,chunk*2> out{};
        const auto file=dir/("chorus-"+std::to_string(preset)+".pcm");
        std::ofstream os(file,std::ios::binary);
        if(!os)return 3;
        for(int n=0;n<frames;n+=chunk) {
            for(int i=0;i<chunk;++i) {
                const int frame=n+i;
                const double decay=frame<SR/2
                  ? std::sin(pi*double(frame)/double(SR/2))*std::sin(pi*double(frame)/double(SR/2))
                  : 0.;
                in[i]=int32_t(std::lround(5000.*decay*
                    std::sin(2*pi*997.0*frame/SR)));
            }
            out.fill(0);
            emu8k_work_chorus(in.data(),out.data(),e.get(),chunk);
            os.write(reinterpret_cast<const char*>(out.data()),out.size()*sizeof(int32_t));
        }
        if(!os)return 4;
        std::cout<<"CHARACTERIZE preset="<<preset<<" feedback="<<fb[preset]
                 <<" samples="<<frames<<" raw_stereo="<<file.string()<<'\n';
    }
    return 0;
}
