// Real 86Box PCM transport. The Python test owns stimuli and audio decisions.
#include "Synth.h"
#include <algorithm>
#include <array>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
int main(int argc,char** argv) {
    try {
        // rom sf2 pcm rate block off(seconds) control0..11
        if(argc!=19&&argc!=20)return 2;
        const unsigned rate=std::stoul(argv[4]),block=std::stoul(argv[5]);
        const unsigned off=unsigned(std::stod(argv[6])*rate),total=rate*3;
        const unsigned pedalOff=argc==20?unsigned(std::stod(argv[19])*rate):total;
        if(!block||block>4096||off>total||pedalOff<off||pedalOff>total)return 2;
        Synth synth(rate);std::string error;
        synth.Core().SetDriver(Awe32::Driver::Win95);
        if(!synth.Core().UseBox86Chip(argv[1],error))throw std::runtime_error(error);
        synth.Core().PowerOnInit();
        synth.SetStrictPresetSelection(true);
        if(!synth.LoadBank(argv[2],error))throw std::runtime_error(error);
        // Oracle transport setup only, never read by production process().
        for(auto control:std::array<std::pair<int,const char*>,2>{{
            {91,"P170_ORACLE_CC91"},{93,"P170_ORACLE_CC93"}}}) {
            if(const char* raw=std::getenv(control.second)) {
                const int value=std::stoi(raw);
                if(value<0||value>127)return 2;
                synth.ControlChange(0,uint8_t(control.first),uint8_t(value));
            }
        }
        for(int i=0;i<12;++i)synth.SetGuiControl(i,std::stof(argv[7+i]));
        synth.SelectBrowserBank(0);
        if(argc==20)synth.ControlChange(0,64,127);
        synth.NoteOn(0,60,127,1);
        using Emu8000::Reg;
        const auto reg=[&](Reg id){return synth.Core().ReadDriver(id,0);};
        const auto env=reg(Reg::ENVVOL),ah=reg(Reg::ATKHLDV),ds=reg(Reg::DCYSUSV);
        const auto fc=reg(Reg::IFATN),pe=reg(Reg::PEFE),c0=reg(Reg::CSL),p0=reg(Reg::PSST),px=reg(Reg::PTRX);
        std::vector<int16_t> pcm(size_t(total)*2);
        unsigned afterC=0,afterP=0;
        for(unsigned at=0;at<total;) {
            if(at==off){synth.NoteOff(0,60);afterC=reg(Reg::CSL);afterP=reg(Reg::PSST);}
            if(argc==20&&at==pedalOff)synth.ControlChange(0,64,0);
            unsigned n=std::min(block,total-at);
            if(at<off)n=std::min(n,off-at);
            if(at<pedalOff)n=std::min(n,pedalOff-at);
            synth.RenderBlock(pcm.data()+size_t(at)*2,n);at+=n;
        }
        std::ofstream out(argv[3],std::ios::binary);
        out.write(reinterpret_cast<char*>(pcm.data()),std::streamsize(pcm.size()*2));
        if(!out)throw std::runtime_error("PCM output failed");
        std::cout<<"{\"env\":"<<env<<",\"attack_hold\":"<<ah
            <<",\"decay_sustain\":"<<ds<<",\"ifatn\":"<<fc<<",\"pefe\":"<<pe
            <<",\"ptrx\":"<<px
            <<",\"csl\":"<<c0<<",\"psst\":"<<p0
            <<",\"off_csl\":"<<afterC<<",\"off_psst\":"<<afterP<<"}\n";
        return 0;
    } catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}
}
