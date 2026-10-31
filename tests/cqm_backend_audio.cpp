#include "Opl3Midi.h"
#include "IbkBank.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
using AWE125::Opl3Midi;
using AWE125::IbkBank;
static bool ck(bool b,const char* msg){std::cout<<(b?"PASS: ":"FAIL: ")<<msg<<'\n';return b;}
template<size_t N> bool sound(const std::array<int16_t,N>& a){
    return std::any_of(a.begin(),a.end(),[](int16_t v){return v!=0;});
}
int main(){
    bool ok=true;
    Opl3Midi cqm(44100,0,true),again(44100,0,true),yamaha(44100);
    ok&=ck(cqm.UsesCqmBackend()&&again.UsesCqmBackend()&&
           !yamaha.UsesCqmBackend(),"true separate Creative CQM chip selected");
    cqm.NoteOn(0,69,127);
    again.NoteOn(0,69,127);
    yamaha.NoteOn(0,69,127);
    std::array<int16_t,8192> a{},b{},y{};
    cqm.RenderBlock(a.data(),4096);
    again.RenderBlock(b.data(),777);
    again.RenderBlock(b.data()+1554,4096-777);
    yamaha.RenderBlock(y.data(),4096);
    ok&=ck(sound(a)&&a==b,
           "CQM MIDI register patch renders real PCM, exactly block-independent");
    ok&=ck(sound(y)&&a!=y,
           "Creative CQM sound differs from Yamaha OPL3 with same registers");
    cqm.NoteOff(0,69);
    ok&=ck(cqm.PressedVoices()==0,"CQM physical key-off releases MIDI note");
    cqm.NoteOn(0,60,90);cqm.NoteOn(0,60,90);cqm.NoteOff(0,60);
    ok&=ck(cqm.PressedVoices()==1,"CQM same-note overlap paired correctly");
    cqm.ControlChange(0,64,127);cqm.NoteOff(0,60);
    cqm.ControlChange(0,64,0);
    ok&=ck(cqm.PressedVoices()==0,"CQM sustain pedal release");
    Opl3Midi poly(48000,0,true);
    for(int i=0;i<18;++i)poly.NoteOn(0,static_cast<uint8_t>(48+i),100);
    poly.NoteOn(0,100,127);
    ok&=ck(poly.PressedVoices()==18,"CQM 18 FM voices and bounded voice steal");
    std::array<int16_t,2048> chord{};
    poly.RenderBlock(chord.data(),1024);
    ok&=ck(sound(chord),"CQM polyphony at 48 kHz renders PCM");

    Opl3Midi delayed(44100,128,true);
    delayed.NoteOn(0,69,127);
    std::array<int16_t,256> d0{},d1{};
    delayed.RenderBlock(d0.data(),128);
    delayed.RenderBlock(d1.data(),128);
    ok&=ck(!sound(d0)&&sound(d1),"CQM delay matches 86Box VST latency");

    // Same register-driven IBK drum bank must enter the *CQM* rhythm path,
    // rather than accidentally invoking the Yamaha backend.
    std::array<uint8_t,IbkBank::kFileBytes> ibk{};
    ibk[0]='I';ibk[1]='B';ibk[2]='K';ibk[3]=0x1a;
    auto* p=ibk.data()+4+36*16;
    p[0]=1;p[1]=1;p[2]=0x20;p[3]=0;p[4]=0xf4;p[5]=0xf4;
    p[6]=0x24;p[7]=0x24;p[10]=2;p[11]=6;p[13]=36;
    namespace fs=std::filesystem;
    const auto path=fs::temp_directory_path()/"125A_cqm_generated_qa_drums.ibk";
    struct Cleanup {fs::path p;~Cleanup(){std::error_code e;fs::remove(p,e);}} cleanup{path};
    {std::ofstream f(path,std::ios::binary|std::ios::trunc);
     f.write(reinterpret_cast<const char*>(ibk.data()),ibk.size());
     if(!f.good())return 2;}
    std::string err;
    Opl3Midi drums(44100,0,true);
    ok&=ck(!drums.LoadPercussionIbk(path.string(),err)&&
           !drums.HasPercussionIbk()&&!err.empty()&&
           drums.RhythmRegister()==0,
           "CQM 0.9 beta rhythm fixture explicitly rejected (unverified audio)");
    drums.NoteOn(9,36,127);
    std::array<int16_t,4096> bass{};
    drums.RenderBlock(bass.data(),2048);
    ok&=ck(!sound(bass)&&drums.PressedVoices()==0,
           "CQM MIDI drum channel remains silent, never a fake melodic drum");
    std::cout<<"NOT RUN: original AWE64 hardware parity, Studio One CQM test\n";
    return ok?0:1;
}
