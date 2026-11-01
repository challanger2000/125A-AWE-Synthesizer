#include "Opl3Midi.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <string>
using AWE125::Opl3Midi;
static bool check(bool yes,const char* text) {
    std::cout<<(yes?"PASS: ":"FAIL: ")<<text<<'\n';
    return yes;
}
static bool audible(const std::array<int16_t,8192>& a) {
    return std::any_of(a.begin(),a.end(),[](int16_t v){return v!=0;});
}
int main(int argc,char** argv) {
    if(argc!=3)return 3;
    std::string error;
    bool ok=true;
    Opl3Midi opl0(44100),opl1(44100),cqm0(44100,0,true),cqm1(44100,0,true);
    ok&=check(opl0.LoadMelodicIbk(argv[1],error)&&
              opl1.LoadMelodicIbk(argv[1],error)&&
              cqm0.LoadMelodicIbk(argv[1],error)&&
              cqm1.LoadMelodicIbk(argv[1],error),
              "Historical MAUIFM.IBK loads into BOTH FM hardware models");
    if(!ok)return 1;
    opl0.ProgramChange(0,0);opl1.ProgramChange(0,48);
    cqm0.ProgramChange(0,0);cqm1.ProgramChange(0,48);
    opl0.NoteOn(0,60,120);opl1.NoteOn(0,60,120);
    cqm0.NoteOn(0,60,120);cqm1.NoteOn(0,60,120);
    std::array<int16_t,8192> a{},b{},c{},d{};
    opl0.RenderBlock(a.data(),4096);opl1.RenderBlock(b.data(),4096);
    cqm0.RenderBlock(c.data(),4096);cqm1.RenderBlock(d.data(),4096);
    ok&=check(audible(a)&&audible(b)&&a!=b,
              "Yamaha OPL3 program 000/048 produce distinct actual PCM");
    ok&=check(audible(c)&&audible(d)&&c!=d,
              "Creative CQM program 000/048 produce distinct actual PCM");
    Opl3Midi rhythm(44100);
    rhythm.LoadMelodicIbk(argv[1],error);
    ok&=check(rhythm.LoadPercussionIbk(argv[2],error),
              "Historical DRUM.IBK loads for Yamaha OPL3 rhythm");
    if(!ok)return 1;
    rhythm.NoteOn(9,35,127);
    std::array<int16_t,8192> drums{};
    rhythm.RenderBlock(drums.data(),4096);
    ok&=check(audible(drums),"Yamaha historical bass drum renders audible PCM");
    Opl3Midi cqmRhythm(44100,0,true);
    ok&=check(!cqmRhythm.LoadPercussionIbk(argv[2],error),
              "Creative CQM percussion remains disabled until verified");
    std::cout<<"NOT RUN: Windows Studio One live GUI and project recall\n";
    return ok?0:1;
}
