// P192 A/B instrument: original EMU8000 engine, synthetic ROM + SF2.
// Same source, same test fixture and chip; only the shadow pitch cache
// differs via AWE125_TEST_DISABLE_MIRROR_PITCH_CACHE. No DAW or SDK.
#include "Synth.h"
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

int main(int argc,char** argv) {
    try {
        if(argc!=8)throw std::runtime_error("usage: p192_bench ROM SF2 PCM CSV rate frames voices");
        const unsigned rate=std::stoul(argv[5]),frames=std::stoul(argv[6]),voices=std::stoul(argv[7]);
        if(rate<44100||rate>96000||frames<64||frames>1024||voices<1||voices>30)return 2;
        Synth s(rate);
        s.Core().SetDriver(Awe32::Driver::Win95);
        std::string error;
        if(!s.Core().UseBox86Chip(argv[1],error))throw std::runtime_error(error);
        s.Core().PowerOnInit();
        s.SetStrictPresetSelection(true);
        if(!s.LoadBank(argv[2],error))throw std::runtime_error(error);
        s.SelectBrowserBank(0);
        s.ProgramChange(0,0);
        s.SetGuiControl(4,1.0f);s.SetGuiControl(5,1.0f);
        s.SetGuiControl(6,.8f);s.SetGuiControl(7,1.0f);
        s.SetGuiControl(9,.5f);s.SetGuiControl(10,.5f);s.SetGuiControl(11,.5f);
        for(unsigned n=0;n<voices;++n)s.NoteOn(0,uint8_t(40+n),100,n+1);
        constexpr unsigned kBlocks=220;
        std::vector<int16_t> pcm(size_t(kBlocks)*frames*2u);
        std::vector<double> usec(kBlocks);
        for(unsigned b=0;b<kBlocks;++b) {
            const auto t0=std::chrono::steady_clock::now();
            s.RenderBlock(pcm.data()+size_t(b)*frames*2,frames);
            const auto t1=std::chrono::steady_clock::now();
            usec[b]=std::chrono::duration<double,std::micro>(t1-t0).count();
        }
        if(!std::any_of(pcm.begin(),pcm.end(),[](int16_t x){return x!=0;}))
            throw std::runtime_error("30-voice audio unexpectedly silent");
        std::ofstream audio(argv[3],std::ios::binary);
        audio.write(reinterpret_cast<const char*>(pcm.data()),
                    std::streamsize(pcm.size()*sizeof(int16_t)));
        if(!audio)throw std::runtime_error("PCM output failed");
        std::ofstream csv(argv[4]);
        csv<<"block,wall_us\n";
        for(unsigned b=0;b<kBlocks;++b)csv<<b<<','<<usec[b]<<'\n';
        if(!csv)throw std::runtime_error("CSV output failed");
        std::ofstream regs(std::string(argv[3])+".registers");
        using Emu8000::Reg;
        for(unsigned v=0;v<32;++v)
            regs<<v<<','<<s.Core().ReadDriver(Reg::CCCA,int(v))<<','
                <<s.Core().ReadDriver(Reg::CPF,int(v))<<','
                <<s.Core().ReadDriver(Reg::VTFT,int(v))<<','
                <<s.Core().ReadDriver(Reg::CSL,int(v))<<','
                <<s.Core().ReadDriver(Reg::PTRX,int(v))<<'\n';
        if(!regs)throw std::runtime_error("register output failed");
        std::cout<<"P192 real chip "<<rate<<" Hz "<<frames<<" frames "<<voices
                 <<" voices; PCM frames="<<kBlocks*frames<<"\n";
        return 0;
    }catch(const std::exception& e){std::cerr<<"P192 ERROR "<<e.what()<<"\n";return 2;}
}