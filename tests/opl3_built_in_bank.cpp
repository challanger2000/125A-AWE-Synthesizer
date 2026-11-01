#include "IbkBank.h"
#include "Opl3Midi.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <string>
using AWE125::IbkBank;
using AWE125::Opl3Midi;
static bool check(bool ok,const char* what) {
    std::cout<<(ok?"PASS: ":"FAIL: ")<<what<<'\n';return ok;
}
template<size_t N> static bool audible(const std::array<int16_t,N>& data) {
    return std::any_of(data.begin(),data.end(),[](int16_t s){return s!=0;});
}
int main() {
    bool ok=true;
    const auto melodic=IbkBank::BuiltInMelodic();
    const auto rhythm=IbkBank::BuiltInPercussion();
    ok&=check(melodic.Valid()&&rhythm.Valid(),"built-in melodic and rhythm register banks valid");
    bool unique=true;
    for(int i=0;i<128;++i)for(int j=0;j<i;++j)
        unique&=melodic.At(static_cast<uint8_t>(i)).registers!=
                melodic.At(static_cast<uint8_t>(j)).registers;
    ok&=check(unique,"128 distinct 125A programmed FM register patches");
    ok&=check(rhythm.At(35).registers[11]==6&&
              rhythm.At(38).registers[11]==7&&
              rhythm.At(45).registers[11]==8&&
              rhythm.At(49).registers[11]==9&&
              rhythm.At(42).registers[11]==10&&
              rhythm.At(12).registers[11]==0,
              "GM channel-10 notes map only to actual five YMF262 percussion paths");

    Opl3Midi p0(44100),p65(44100),c0(44100,0,true),c65(44100,0,true);
    p0.UseBuiltInMelodic();p65.UseBuiltInMelodic();
    c0.UseBuiltInMelodic();c65.UseBuiltInMelodic();
    ok&=check(p0.HasMelodicIbk()&&c0.HasMelodicIbk(),
              "both independent FM chip adapters contain a full built-in bank");
    p0.ProgramChange(0,0);p65.ProgramChange(0,65);
    c0.ProgramChange(0,0);c65.ProgramChange(0,65);
    p0.NoteOn(0,60,120);p65.NoteOn(0,60,120);
    c0.NoteOn(0,60,120);c65.NoteOn(0,60,120);
    std::array<int16_t,8192> a{},b{},ca{},cb{};
    p0.RenderBlock(a.data(),4096);p65.RenderBlock(b.data(),4096);
    c0.RenderBlock(ca.data(),4096);c65.RenderBlock(cb.data(),4096);
    ok&=check(audible(a)&&audible(b)&&a!=b,
              "Yamaha OPL3 built-in programs select different real chip PCM");
    ok&=check(audible(ca)&&audible(cb)&&ca!=cb,
              "Creative CQM built-in programs select different real chip PCM");

    Opl3Midi drums(44100);
    drums.UseBuiltInMelodic();
    drums.UseBuiltInPercussion();
    ok&=check(drums.HasPercussionIbk()&&drums.RhythmRegister()==0x20,
              "Yamaha true OPL3 rhythm mode enabled by built-in percussion bank");
    drums.NoteOn(9,35,120);
    std::array<int16_t,8192> d{};
    drums.RenderBlock(d.data(),4096);
    ok&=check(audible(d),"Yamaha built-in bass drum renders real hardware percussion PCM");
    drums.NoteOff(9,35);
    drums.AllNotesOff();
    Opl3Midi cDrum(44100,0,true);
    cDrum.UseBuiltInMelodic();
    cDrum.UseBuiltInPercussion();
    ok&=check(!cDrum.HasPercussionIbk(),
              "CQM beta does not enable unverified rhythm or simulated percussion");
    std::cout<<"NOT RUN: authentic Creative ROM, original factory IBK, Studio One/host recall\n";
    return ok?0:1;
}
