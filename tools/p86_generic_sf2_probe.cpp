// P86: offline 125A native 86Box EMU8000 audition of any user SF2.
// Does NOT run original Win95 Creative driver, and is not yet the VST3 host.
// No proprietary waveform or ROM embedded; all outputs remain local.
#include "Synth.h"
#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

namespace {
void W16(std::ofstream& f, uint16_t n) {
    char b[2]{static_cast<char>(n),static_cast<char>(n>>8)};
    f.write(b,2);
}
void W32(std::ofstream& f, uint32_t n) {
    W16(f,static_cast<uint16_t>(n)); W16(f,static_cast<uint16_t>(n>>16));
}
bool Wav(const std::filesystem::path& path,const std::vector<int16_t>& pcm) {
    if(pcm.size()>(UINT32_MAX-36)/2)return false;
    std::ofstream out(path,std::ios::binary|std::ios::trunc);
    if(!out)return false;
    const auto size=static_cast<uint32_t>(pcm.size()*2u);
    out.write("RIFF",4); W32(out,36+size); out.write("WAVEfmt ",8);
    W32(out,16); W16(out,1); W16(out,2); W32(out,44100);
    W32(out,44100*4); W16(out,4); W16(out,16);
    out.write("data",4); W32(out,size);
    for(int16_t value:pcm)W16(out,static_cast<uint16_t>(value));
    return out.good();
}
bool Number(const std::string& value,int min,int max,int& result) {
    try {
        size_t pos=0;
        int n=std::stoi(value,&pos);
        if(pos!=value.size()||n<min||n>max)return false;
        result=n;return true;
    } catch (...) {return false;}
}
std::string Safe(const std::string& raw) {
    std::string name;
    for(unsigned char c:raw) {
        if(name.size()>=36)break;
        if(std::isalnum(c)||c=='-'||c=='_')name+=static_cast<char>(c);
        else if(c==' '&&name.size()>0)name+='_';
    }
    return name.empty()?"Unnamed":name;
}
void Usage() {
    std::cerr<<"Usage: awe32_p86_generic_sf2_probe --sf2 bank.sf2 --rom awe32.raw"
             <<" --out directory [--bank 0..16383] [--programs 0,17]"
             <<" [--note 0..127] [--velocity 1..127]\n";
}
}
int main(int argc,char** argv) {
    namespace fs=std::filesystem;
    fs::path sf2,rom,out="125A-P86-Original-SF2-Audition";
    int bank=0,note=36,velocity=100;
    std::vector<int> programs{0,17};
    for(int arg=1;arg<argc;arg+=2) {
        if(arg+1>=argc){Usage();return 2;}
        const std::string flag=argv[arg],value=argv[arg+1];
        if(flag=="--sf2")sf2=value;
        else if(flag=="--rom")rom=value;
        else if(flag=="--out")out=value;
        else if(flag=="--bank"&&Number(value,0,16383,bank)){}
        else if(flag=="--note"&&Number(value,0,127,note)){}
        else if(flag=="--velocity"&&Number(value,1,127,velocity)){}
        else if(flag=="--programs"){
            programs.clear(); size_t start=0;
            do {
                size_t comma=value.find(',',start);
                int program=0;
                const auto item=value.substr(start,comma==std::string::npos
                                            ?comma:comma-start);
                if(!Number(item,0,127,program)) {Usage();return 2;}
                programs.push_back(program);
                if(comma==std::string::npos)break;
                start=comma+1;
            } while(programs.size()<129);
            if(programs.empty()||programs.size()>128){Usage();return 2;}
        } else {Usage();return 2;}
    }
    if(sf2.empty()||rom.empty()||!fs::is_regular_file(sf2)||!fs::is_regular_file(rom)){
        std::cerr<<"ERROR: real private SF2 and 86Box ROM paths required\n";
        return 3;
    }
    std::error_code ec;fs::create_directories(out,ec);
    if(ec){std::cerr<<"ERROR: output directory: "<<ec.message()<<'\n';return 4;}
    std::cout<<"P86: native 86Box EMU8000 (NOT original Win95-driver playback), "
             <<"44.1kHz stereo PCM16, bank "<<bank<<", MIDI note "<<note<<'\n';
    for(int program:programs){
        Synth synth(44100);
        synth.Core().SetDriver(Awe32::Driver::Win95);
        std::string error;
        if(!synth.Core().UseBox86Chip(rom.string(),error)||
           synth.Core().ChipVariant()!=Emu8000Core::Chip::Box86) {
            std::cerr<<"ERROR: 86Box chip/ROM: "<<error<<'\n';return 5;
        }
        synth.Core().PowerOnInit();
        if(!synth.LoadBank(sf2.string(),error)) {
            std::cerr<<"ERROR: original SF2 load: "<<error<<'\n';return 6;
        }
        const auto& sf=synth.BankAt(synth.BankCount()-1);
        const SoundFont::Preset* preset=sf.FindPreset(bank,program);
        if(!preset){std::cerr<<"ERROR: no SF2 bank "<<bank
                             <<" program "<<program<<'\n';return 7;}
        auto regions=sf.Select(bank,program,note,velocity);
        if(regions.empty()){
            std::cerr<<"ERROR: "<<preset->name<<" does not cover MIDI note "
                     <<note<<'\n';return 8;
        }
        synth.SelectBrowserBank(static_cast<uint16_t>(bank));
        synth.ProgramChange(0,static_cast<uint8_t>(program));
        synth.NoteOn(0,static_cast<uint8_t>(note),
                     static_cast<uint8_t>(velocity));
        constexpr uint32_t frames=88200;
        std::vector<int16_t> pcm(static_cast<size_t>(frames)*2,0);
        synth.RenderBlock(pcm.data(),frames);
        synth.NoteOff(0,static_cast<uint8_t>(note));
        int peak=0; double energy=0;
        for(const int16_t v:pcm) {
            int x=v;peak=std::max(peak,std::abs(x));
            energy+=static_cast<double>(x)*x;
        }
        const double rms=std::sqrt(energy/pcm.size())/32768.;
        if(peak==0){std::cerr<<"ERROR: generated zero PCM despite SF2 note\n";return 9;}
        const auto filename="B"+std::to_string(bank)+"_P"+
                std::to_string(program)+"_N"+std::to_string(note)+"_"+
                Safe(preset->name)+"_native-EMU8000.wav";
        const auto target=out/filename;
        if(!Wav(target,pcm)){
            std::cerr<<"ERROR: cannot save private WAV "<<target<<'\n';
            return 10;
        }
        std::cout<<"PASS bank "<<bank<<" program "<<program<<" "<<preset->name
                 <<" | regions "<<regions.size()<<" | peak "<<peak
                 <<" | rms "<<rms<<" | output "<<target.string()<<'\n';
    }
    std::cout<<"P86 native audible test PASS. Win95 Creative driver and physical "
             <<"AWE64 tonal parity NOT asserted.\n";
    return 0;
}
