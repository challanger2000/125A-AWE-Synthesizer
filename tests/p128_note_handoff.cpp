#include "Synth.h"
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>

static bool check(bool yes,const char* label) {
    std::cout<<(yes?"PASS ":"FAIL ")<<label<<'\n';
    return yes;
}
static size_t count(const Synth::HeldNotes& notes) {
    return std::count_if(notes.begin(),notes.end(),[](auto n){return n.sequence!=0;});
}
int main() {
    const auto rom=std::filesystem::temp_directory_path()/"125A_p128_note_handoff_zero.rom";
    struct Cleanup {std::filesystem::path p;~Cleanup(){std::error_code e;std::filesystem::remove(p,e);}} cleanup{rom};
    {std::ofstream f(rom,std::ios::binary);std::vector<char> zero(1048576);f.write(zero.data(),zero.size());if(!f)return 2;}
    const auto init=[&](Synth& s) {
        auto& core=s.Core();core.SetDriver(Awe32::Driver::Win95);
        std::string error;if(!core.UseBox86Chip(rom.string(),error))return false;
        core.PowerOnInit();std::copy_n(core.DramData(),72,core.ChipRam());return true;
    };
    bool ok=true;
    {
        Synth a(44100),b(44100),ref(44100);if(!init(a)||!init(b)||!init(ref))return 2;
        a.NoteOn(0,60,100,10);a.NoteOn(0,60,90,11);a.NoteOn(1,67,110,12);
        auto notes=a.CaptureHeldNotes();
        ok&=check(count(notes)==3,"duplicate-key NoteOns retain distinct ordered identities");
        b.RestoreHeldNotes(notes,10);ref.NoteOn(0,60,90,11);ref.NoteOn(1,67,110,12);
        std::vector<int16_t> actual(8192),expected(8192);b.RenderBlock(actual.data(),4096);ref.RenderBlock(expected.data(),4096);
        ok&=check(actual==expected&&std::any_of(actual.begin(),actual.end(),[](auto v){return v!=0;}),"handoff filters older-than-recall notes and restores exact audible PCM");
        a.NoteOff(0,60);ok&=check(count(a.CaptureHeldNotes())==1,"NoteOff removes every duplicate-key layer from handoff");
        a.ControlChange(1,64,127);a.NoteOff(1,67);notes=a.CaptureHeldNotes();
        ok&=check(count(notes)==1&&notes[0].sustained,"pedal-held note retained as released key");
        Synth held(44100);if(!init(held))return 2;held.ControlChange(1,64,127);held.RestoreHeldNotes(notes,0);
        auto captured=held.CaptureHeldNotes();ok&=check(count(captured)==1&&captured[0].sustained,"sustain status survives handoff");
        held.ControlChange(1,64,0);ok&=check(count(held.CaptureHeldNotes())==0,"pedal release prevents resurrection");
    }
    {
        Synth a(44100);if(!init(a))return 2;
        for(int i=0;i<40;++i)a.NoteOn(0,40+i,100,100+i);
        auto notes=a.CaptureHeldNotes();
        ok&=check(count(notes)==30&&notes[0].sequence==110&&notes[29].sequence==139,"fallback AllocateVoice (30 slots) excludes the ten stolen notes");
        a.ControlChange(0,120,0);ok&=check(count(a.CaptureHeldNotes())==0,"all-sounds-off cannot be replayed");
    }
    return ok?0:1;
}
