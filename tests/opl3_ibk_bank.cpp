#include "IbkBank.h"
#include "Opl3Midi.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
using AWE125::IbkBank;
using AWE125::Opl3Midi;
static bool ck(bool b,const char* m){std::cout<<(b?"PASS: ":"FAIL: ")<<m<<'\n';return b;}
template<size_t N> bool sound(const std::array<int16_t,N>& a){
    return std::any_of(a.begin(),a.end(),[](int16_t x){return x!=0;});
}
int main(){
    bool ok=true;std::string err;
    std::array<uint8_t,IbkBank::kFileBytes> b{};
    b[0]='I';b[1]='B';b[2]='K';b[3]=0x1a;
    for(size_t i=0;i<128;++i){
        auto* p=b.data()+4+16*i;
        p[0]=1;p[1]=1;p[2]=0x20;p[3]=0;p[4]=0xf4;p[5]=0xf4;
        p[6]=0x24;p[7]=0x24;p[8]=0;p[9]=0;p[10]=2;
        std::string name="Patch"+std::to_string(i);
        auto* n=b.data()+4+128*16+i*9;
        std::copy_n(name.c_str(),std::min(size_t{8},name.size()),n);
    }
    b[4+16+0]=5;b[4+16+8]=3;b[4+16+10]=4;
    b[4+2*16+12]=12;
    IbkBank bank;
    ok&=ck(bank.Parse(b,err)&&bank.Valid()&&
        std::string(bank.At(0).name.data())=="Patch0"&&
        std::string(bank.At(127).name.data())=="Patch127"&&
        bank.At(1).registers[0]==5,"128 authentic IBK register layouts and names");
    auto corrupt=b;corrupt[3]=0;
    ok&=ck(!bank.Parse(corrupt,err)&&bank.At(1).registers[0]==5,
           "invalid signature rejected without changing prior bank");
    ok&=ck(!bank.Parse({b.data(),b.size()-1},err)&&bank.Valid(),
           "truncated bank rejected atomically");
    std::array<uint8_t,IbkBank::kFileBytes+1> extra{};
    std::copy(b.begin(),b.end(),extra.begin());
    ok&=ck(!bank.Parse(extra,err),"oversize bank rejected");
    namespace fs=std::filesystem;
    const auto path=fs::temp_directory_path()/"125A_generated_opl3_bank_qa.ibk";
    struct Cleanup{fs::path p;~Cleanup(){std::error_code e;fs::remove(p,e);}} cleanup{path};
    {std::ofstream f(path,std::ios::binary|std::ios::trunc);
     f.write(reinterpret_cast<const char*>(b.data()),b.size());
     if(!f.good())return 2;}
    Opl3Midi a(44100),z(44100),tr(44100);
    ok&=ck(a.LoadMelodicIbk(path.string(),err)&&
           z.LoadMelodicIbk(path.string(),err)&&
           tr.LoadMelodicIbk(path.string(),err)&&a.HasMelodicIbk(),
           "IBK user file loads into independent Yamaha chips");
    a.ProgramChange(0,0);z.ProgramChange(0,1);tr.ProgramChange(0,2);
    a.NoteOn(0,69,127);z.NoteOn(0,69,127);tr.NoteOn(0,57,127);
    std::array<int16_t,8192> outA{},outB{},outT{};
    a.RenderBlock(outA.data(),4096);
    z.RenderBlock(outB.data(),4096);
    tr.RenderBlock(outT.data(),4096);
    ok&=ck(sound(outA)&&sound(outB)&&outA!=outB,
           "MIDI programs produce different original register-driven PCM");
    ok&=ck(outA==outT,"IBK transpose produces exact original note pitch");
    tr.NoteOff(0,57);
    ok&=ck(tr.PressedVoices()==0,"transposed patch note-off matches MIDI key");
    ok&=ck(!a.LoadMelodicIbk(path.string()+".missing",err)&&a.HasMelodicIbk(),
           "failed bank swap preserves prior valid instrument bank");
    std::cout<<"NOT RUN: owner-provided original Creative IBK, FM drum rhythm, Studio One\n";
    return ok?0:1;
}
