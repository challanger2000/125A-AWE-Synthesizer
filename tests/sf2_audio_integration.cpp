#include "Synth.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

// This is a generated, copyright-free SF2 test fixture; no Creative sample
// data, no private SoundFonts, no user ROMs are included in the repository.
namespace {
using Bytes = std::vector<std::uint8_t>;
void u16(Bytes& b, unsigned v) { b.push_back(v & 255); b.push_back((v >> 8) & 255); }
void u32(Bytes& b, std::uint32_t v) { u16(b,v); u16(b,v >> 16); }
void name20(Bytes& b, const char* s) {
    const size_t length = std::strlen(s);
    for (size_t i=0; i<20; ++i)
        b.push_back(i<length ? static_cast<std::uint8_t>(s[i]) : 0);
}
void chunk(Bytes& b, const char* name, const Bytes& payload) {
    b.insert(b.end(), name, name + 4);
    u32(b, static_cast<uint32_t>(payload.size()));
    b.insert(b.end(), payload.begin(), payload.end());
    if (payload.size() & 1u) b.push_back(0);
}
void list(Bytes& b, const char* listType, const Bytes& contents) {
    Bytes p(listType, listType+4);
    p.insert(p.end(), contents.begin(), contents.end());
    chunk(b, "LIST", p);
}
Bytes makeBank(size_t sampleWords) {
    Bytes info, ifil, inam, sdta, pdta, smpl;
    u16(ifil,2);u16(ifil,1);
    chunk(info,"ifil",ifil);
    inam.insert(inam.end(),{'1','2','5','A',' ','S','i','n','e',0});
    chunk(info,"INAM",inam);

    constexpr double pi = 3.1415926535897932384626433832795;
    for (size_t n=0;n<sampleWords;++n) {
        const auto sample = static_cast<std::int16_t>(
            std::sin(2.0*pi*(n%64u)/64.0)*11000.0);
        u16(smpl,static_cast<std::uint16_t>(sample));
    }
    // The SF2 specification requires 46 guard words after a sample.
    for (int n=0;n<46;++n)u16(smpl,0);
    chunk(sdta,"smpl",smpl);

    Bytes phdr,pbag,pgen,inst,ibag,igen,shdr;
    name20(phdr,"125A Sine"); u16(phdr,0);u16(phdr,0);u16(phdr,0);
    u32(phdr,0);u32(phdr,0);u32(phdr,0);
    name20(phdr,"EOP"); u16(phdr,0);u16(phdr,0);u16(phdr,1);
    u32(phdr,0);u32(phdr,0);u32(phdr,0);

    u16(pbag,0);u16(pbag,0);u16(pbag,1);u16(pbag,0);
    u16(pgen,41);u16(pgen,0); // Instrument 0

    name20(inst,"125A Wave");u16(inst,0);
    name20(inst,"EOI");u16(inst,1);
    u16(ibag,0);u16(ibag,0);u16(ibag,2);u16(ibag,0);
    u16(igen,54);u16(igen,1); // Loop continuously
    u16(igen,53);u16(igen,0); // Sample 0

    name20(shdr,"125A Wave");u32(shdr,0);
    u32(shdr,static_cast<uint32_t>(sampleWords));
    u32(shdr,16);u32(shdr,static_cast<uint32_t>(sampleWords-16));
    u32(shdr,44100);
    shdr.push_back(69);shdr.push_back(0);
    u16(shdr,0);u16(shdr,1);
    name20(shdr,"EOS");
    for (int n=0;n<6;++n)u32(shdr,0);
    shdr.push_back(0);shdr.push_back(0);u16(shdr,0);u16(shdr,1);

    chunk(pdta,"phdr",phdr);
    chunk(pdta,"pbag",pbag);
    chunk(pdta,"pmod",Bytes(10,0));
    chunk(pdta,"pgen",pgen);
    chunk(pdta,"inst",inst);
    chunk(pdta,"ibag",ibag);
    chunk(pdta,"imod",Bytes(10,0));
    chunk(pdta,"igen",igen);
    chunk(pdta,"shdr",shdr);

    Bytes body{'s','f','b','k'};
    list(body,"INFO",info);
    list(body,"sdta",sdta);
    list(body,"pdta",pdta);
    Bytes result{'R','I','F','F'};u32(result,static_cast<uint32_t>(body.size()));
    result.insert(result.end(),body.begin(),body.end());
    return result;
}
bool writeFile(const std::filesystem::path& path,const Bytes& data) {
    std::ofstream f(path,std::ios::binary|std::ios::trunc);
    f.write(reinterpret_cast<const char*>(data.data()),
            static_cast<std::streamsize>(data.size()));
    return f.good();
}
bool check(bool yes,const char* label) {
    std::cout<<(yes?"PASS: ":"FAIL: ")<<label<<'\n';return yes;
}
}
int main() {
    namespace fs=std::filesystem;
    const fs::path directory=fs::temp_directory_path();
    const fs::path sf=directory/"125A_synthetic_sf2_audio.sf2";
    const fs::path huge=directory/"125A_synthetic_sf2_overflow.sf2";
    const fs::path rom=directory/"125A_synthetic_sf2_audio.raw";
    struct Cleanup {
        fs::path a,b,c;
        ~Cleanup(){std::error_code ec;fs::remove(a,ec);fs::remove(b,ec);fs::remove(c,ec);}
    } cleanup{sf,huge,rom};
    if (!writeFile(sf,makeBank(2048)) ||
        !writeFile(huge,makeBank(300000)) ||
        !writeFile(rom,Bytes(1048576,0)))return 2;
    bool ok=true;
    std::string error;
    constexpr size_t reserve=16;
    constexpr size_t copiedWords=2048+46;
    {
        Synth synth(44100);
        synth.Core().SetDriver(Awe32::Driver::Win95);
        ok &= check(synth.LoadBank(sf.string(),error),"standard SF2 loads into native synthesizer");
        ok &= check(synth.BankCount()==1,"native loaded-bank count");
        synth.NoteOn(0,69,100);
        std::vector<int16_t> pcm(8192,0);
        synth.RenderBlock(pcm.data(),4096);
        ok &= check(std::any_of(pcm.begin(),pcm.end(),
            [](int16_t x){return x!=0;}),"real SoundFont NoteOn creates audible PCM");
        const auto saved=synth.Core().DramData()[reserve+64];
        error.clear();
        ok &= check(!synth.LoadBank((directory/"125A_unavailable.sf2").string(),error),
                    "missing SF2 is rejected") &&
              check(synth.BankCount()==1 && synth.Core().DramData()[reserve+64]==saved,
                    "failed load preserves prior SF2 and DRAM");
    }
    {
        Synth synth(48000);
        synth.Core().SetDriver(Awe32::Driver::Win95);
        synth.Core().SetChipRamKb(512);
        error.clear();
        ok &= check(synth.Core().UseBox86Chip(rom.string(),error),
                    "actual 86Box EMU8000 accepts synthetic ROM");
        synth.Core().PowerOnInit();
        error.clear();
        ok &= check(synth.LoadBank(sf.string(),error),
                    "SF2 loads into active 86Box chip");
        ok &= check(synth.BankCount()==1 &&
                    synth.Core().ChipRamWords()>=reserve+copiedWords,
                    "chip RAM capacity and bank count");
        int16_t* chip=synth.Core().ChipRam();
        ok &= check(chip != nullptr &&
                    std::equal(chip+reserve,chip+reserve+copiedWords,
                               synth.Core().DramData()+reserve),
                    "SF2 upload copied bit-for-bit into chip DRAM");
        error.clear();
        const auto before=synth.Core().DramData()[reserve+64];
        ok &= check(!synth.LoadBank(huge.string(),error),
                    "oversized SF2 rejected by 512KB chip capacity");
        ok &= check(synth.BankCount()==1 &&
                    synth.Core().DramData()[reserve+64]==before &&
                    synth.Core().ChipRam()[reserve+64]==before,
                    "failed upload preserves native/chip RAM");
        synth.NoteOn(0,69,110);
        std::vector<int16_t> pcm(12000,0);
        synth.RenderBlock(pcm.data(),6000);
        ok &= check(std::any_of(pcm.begin()+2500,pcm.end(),
            [](int16_t v){return v!=0;}),
                    "uploaded SF2 produces audible 86Box output after FIFO");
    }
    {
        // Loading a bank before switching chip must transfer existing DRAM.
        Synth synth(44100);
        synth.Core().SetDriver(Awe32::Driver::Win95);
        error.clear();
        ok &= check(synth.LoadBank(sf.string(),error),"pre-switch SF2 load");
        synth.Core().SetChipRamKb(512);
        ok &= check(synth.Core().UseBox86Chip(rom.string(),error),"switch to 86Box after bank load");
        int16_t* chip=synth.Core().ChipRam();
        ok &= check(chip != nullptr &&
                    std::equal(chip+reserve,chip+reserve+copiedWords,
                               synth.Core().DramData()+reserve),
                    "mode switch migrates existing bank into chip RAM");
    }
    std::cout<<(ok?"SF2/EMU8000 END-TO-END PASS":"SF2/EMU8000 END-TO-END FAIL")<<'\n';
    std::cout<<"NOT RUN: licensed/user SF2, original ROM timbre parity, Studio One"<<'\n';
    return ok?0:1;
}
