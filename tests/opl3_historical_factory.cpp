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
    // The previous tests used separate fresh chips for each program, so
    // they missed several-second release tails masking preset browsing in
    // the same continuously running plugin instance.
    const auto quickSwitch=[&](bool creative) {
        Opl3Midi switched(44100,0,creative),unchanged(44100,0,creative);
        std::string err;
        if(!switched.LoadMelodicIbk(argv[1],err)||
           !unchanged.LoadMelodicIbk(argv[1],err))return false;
        std::array<int16_t,1024> work{};
        for(int i=0;i<8;++i) {
            // Eight short preview notes on one channel, each leaving
            // a released old-patch FM envelope before the program switch.
            switched.NoteOn(0,60,127);
            unchanged.NoteOn(0,60,127);
            switched.RenderBlock(work.data(),512);
            unchanged.RenderBlock(work.data(),512);
            switched.NoteOff(0,60);
            unchanged.NoteOff(0,60);
            switched.RenderBlock(work.data(),512);
            unchanged.RenderBlock(work.data(),512);
        }
        if(switched.AllocatedVoices()!=8)return false;
        switched.ProgramChange(0,48);
        // All eight released voices from the old program are retired; a
        // newly pressed voice takes the selected patch immediately.
        if(switched.AllocatedVoices()!=0)return false;
        switched.NoteOn(0,60,127);
        unchanged.NoteOn(0,60,127);
        if(switched.AllocatedVoices()!=1||switched.PressedVoices()!=1)
            return false;
        std::array<int16_t,8192> newSound{},oldSound{};
        switched.RenderBlock(newSound.data(),4096);
        unchanged.RenderBlock(oldSound.data(),4096);
        return audible(newSound)&&audible(oldSound)&&newSound!=oldSound;
    };
    ok&=check(quickSwitch(false),
              "Yamaha: first new note after 8 old tails plays selected program");
    ok&=check(quickSwitch(true),
              "Creative: first new note after 8 old tails plays selected program");

    // The fix should NOT stop actively held MIDI notes, or wrongly apply
    // the chosen program to a different MIDI channel.
    Opl3Midi held(44100);
    ok&=check(held.LoadMelodicIbk(argv[1],error),
              "program switch regression bank loads");
    held.NoteOn(0,60,127);
    held.NoteOn(1,64,127);
    held.ProgramChange(0,48);
    ok&=check(held.PressedVoices()==2&&held.AllocatedVoices()==2,
              "held notes and other MIDI channels survive program selection");
    held.NoteOff(0,60);
    held.ProgramChange(0,49);
    ok&=check(held.PressedVoices()==1&&held.AllocatedVoices()==1,
              "released old voice retires without interrupting other channel");

    std::cout<<"NOT RUN: Windows Studio One live GUI and project recall\n";
    return ok?0:1;
}
