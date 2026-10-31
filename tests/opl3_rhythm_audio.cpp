#include "Opl3Midi.h"
#include "IbkBank.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
using AWE125::Opl3Midi;
using AWE125::IbkBank;
static bool ck(bool pass,const char* s){
    std::cout<<(pass?"PASS: ":"FAIL: ")<<s<<'\n';return pass;
}
static std::array<uint8_t,IbkBank::kFileBytes> makeDrums(bool enabled=true){
    std::array<uint8_t,IbkBank::kFileBytes> bank{};
    bank[0]='I';bank[1]='B';bank[2]='K';bank[3]=0x1a;
    const std::array<uint8_t,5> notes{36,38,45,49,42};
    for(size_t n=0;n<notes.size();++n){
        auto* p=bank.data()+4+size_t{16}*notes[n];
        p[0]=1;p[1]=1;p[2]=0x20;p[3]=0;
        p[4]=0xf4;p[5]=0xf4;p[6]=0x24;p[7]=0x24;
        p[8]=0;p[9]=0;p[10]=2;
        p[11]=enabled?static_cast<uint8_t>(6+n):0;
        p[13]=notes[n];
        const std::string name="DRUM"+std::to_string(n);
        std::copy_n(name.c_str(),name.size(),
                    reinterpret_cast<char*>(bank.data()+4+128*16+9*notes[n]));
    }
    return bank;
}
static bool write(const std::filesystem::path& path,
                  const std::array<uint8_t,IbkBank::kFileBytes>& bank){
    std::ofstream f(path,std::ios::binary|std::ios::trunc);
    f.write(reinterpret_cast<const char*>(bank.data()),bank.size());
    return f.good();
}
template<size_t N> static bool sound(const std::array<int16_t,N>& a){
    return std::any_of(a.begin(),a.end(),[](int16_t x){return x!=0;});
}
int main(){
    bool ok=true;std::string err;
    namespace fs=std::filesystem;
    const fs::path path=fs::temp_directory_path()/"125A_test_ymf262_drums.ibk";
    struct Cleanup{fs::path p;~Cleanup(){std::error_code ec;fs::remove(p,ec);}} cleanup{path};
    if(!write(path,makeDrums()))return 2;
    Opl3Midi chip(44100);
    ok&=ck(chip.LoadPercussionIbk(path.string(),err)&&
           chip.HasPercussionIbk()&&chip.RhythmRegister()==0x20,
           "real YMF262 0xBD rhythm mode enabled only with valid drum IBK");
    chip.NoteOn(9,36,120);
    ok&=ck(chip.RhythmRegister()==0x30&&chip.PressedVoices()==1,
           "GM channel 10 bassdrum -> real BD bit 0x10 (not melodic voice)");
    std::array<int16_t,8192> kick{};
    chip.RenderBlock(kick.data(),4096);
    ok&=ck(sound(kick),"physical bassdrum operators generate FM PCM");
    chip.NoteOn(9,38,127);
    ok&=ck(chip.RhythmRegister()==0x38&&chip.PressedVoices()==2,
           "snare uses independent 0x08 bit, overlaps active kick");
    chip.NoteOn(9,45,127);
    chip.NoteOn(9,49,127);
    chip.NoteOn(9,42,127);
    ok&=ck(chip.RhythmRegister()==0x3f&&chip.PressedVoices()==5,
           "real Tom/Cym/HiHat operators and all five 0xBD bits");
    std::array<int16_t,4096> all{};
    chip.RenderBlock(all.data(),2048);
    ok&=ck(sound(all),"five percussion voices render concurrent PCM");
    chip.NoteOff(9,38);
    ok&=ck(chip.RhythmRegister()==0x37&&chip.PressedVoices()==4,
           "snare note-off releases only snare hardware envelope");
    // New HH note note 46 must have its own IBK type 10 before retrigger.
    // Re-trigger same key should not leave two active envelopes.
    chip.NoteOn(9,42,127);
    ok&=ck(chip.RhythmRegister()==0x37&&chip.PressedVoices()==4,
           "same hi-hat retrigger is one hardware drum, not a 6th voice");
    chip.NoteOff(9,42);
    ok&=ck(chip.RhythmRegister()==0x36,
           "hi-hat note-off clears its own 0xBD bit");
    chip.NoteOn(9,70,127);
    ok&=ck(chip.RhythmRegister()==0x36,
           "unmapped percussion note remains silent, no invented kit patch");
    chip.AllNotesOff();
    ok&=ck(chip.RhythmRegister()==0x20&&chip.PressedVoices()==0,
           "all-notes-off clears all five keys but keeps rhythm mode");
    // Rhythm mode genuinely reserves channels 6,7,8: 15 melodic voices remain.
    for(int i=0;i<15;++i)chip.NoteOn(0,static_cast<uint8_t>(40+i),100);
    ok&=ck(chip.PressedVoices()==15,
           "15 melodic voices available when YMF262 6/7/8 are drums");
    chip.NoteOn(0,90,110);
    ok&=ck(chip.PressedVoices()==15,
           "16th melodic note steals; reserved rhythm channels not stolen");
    chip.AllNotesOff();

    // An invalid non-drum IBK must not replace a valid drum bank.
    if(!write(path,makeDrums(false)))return 3;
    ok&=ck(!chip.LoadPercussionIbk(path.string(),err)&&
           chip.HasPercussionIbk()&&chip.RhythmRegister()==0x20,
           "reject 128 silent/non-rhythm records without replacing good bank");
    chip.NoteOn(9,36,100);
    ok&=ck(chip.RhythmRegister()==0x30,
           "failed bank reload preserves previous valid drum mappings");
    chip.ControlChange(9,120,0);
    ok&=ck(chip.RhythmRegister()==0x20,
           "percussion MIDI CC120 all-sounds-off clears original keys");
    std::cout<<"NOT RUN: physical YMF262 reference, real Creative percussion IBK, Studio One\n";
    return ok?0:1;
}
