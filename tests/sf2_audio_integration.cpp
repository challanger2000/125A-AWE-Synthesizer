#include "Synth.h"
#include "Sf2LoadPolicy.h"
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
Bytes makeBank(size_t sampleWords,bool multipleBanks=false,bool pluckEnvelope=false) {
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
    if(multipleBanks) {
        // Distinct sample WAVEFORMS, not merely different pitch generators.
        // This guarantees that selecting the wrong SF2 bank cannot pass
        // merely because two presets happen to share an identical sample.
        for(size_t n=0;n<sampleWords;++n)
            u16(smpl,static_cast<uint16_t>(static_cast<int16_t>(
                std::sin(2.0*pi*(n%37u)/37.0)*13000.0)));
        for(size_t n=0;n<sampleWords;++n)
            u16(smpl,static_cast<uint16_t>(static_cast<int16_t>(
                std::sin(2.0*pi*(n%83u)/83.0)*8000.0)));
    }
    // The SF2 specification requires 46 guard words after a sample.
    for (int n=0;n<46;++n)u16(smpl,0);
    chunk(sdta,"smpl",smpl);

    Bytes phdr,pbag,pgen,inst,ibag,igen,shdr;
    name20(phdr,"125A Sine"); u16(phdr,0);u16(phdr,0);u16(phdr,0);
    u32(phdr,0);u32(phdr,0);u32(phdr,0);
    if(multipleBanks) {
        name20(phdr,"125A High"); u16(phdr,0);u16(phdr,5);u16(phdr,1);
        u32(phdr,0);u32(phdr,0);u32(phdr,0);
        name20(phdr,"125A Drum"); u16(phdr,0);u16(phdr,128);u16(phdr,2);
        u32(phdr,0);u32(phdr,0);u32(phdr,0);
    }
    name20(phdr,"EOP"); u16(phdr,0);u16(phdr,0);
    u16(phdr,multipleBanks?3:1);
    u32(phdr,0);u32(phdr,0);u32(phdr,0);

    u16(pbag,0);u16(pbag,0);u16(pbag,1);u16(pbag,0);
    if(multipleBanks) {
        u16(pbag,4);u16(pbag,0);u16(pbag,6);u16(pbag,0);
    }
    u16(pgen,41);u16(pgen,0); // Instrument 0
    if(multipleBanks) {
        u16(pgen,41);u16(pgen,1);u16(pgen,51);u16(pgen,12);
        u16(pgen,52);u16(pgen,20); // preset +20 cents over instrument -30
        u16(pgen,41);u16(pgen,2);u16(pgen,51);u16(pgen,24); // different sample 2
    }

    name20(inst,"125A Wave");u16(inst,0);
    if(multipleBanks) {
        name20(inst,"125A Wave B");u16(inst,1);
        name20(inst,"125A Wave C");u16(inst,2);
    }
    name20(inst,"EOI");u16(inst,multipleBanks?3:1);
    u16(ibag,0);u16(ibag,0);u16(ibag,pluckEnvelope?5:2);u16(ibag,0);
    if(multipleBanks) {
        u16(ibag,5);u16(ibag,0);u16(ibag,7);u16(ibag,0);
    }
    if (pluckEnvelope) {
        // Instrument-zone generator values are absolute. Putting negative
        // timecents in a PRESET would add them to the default -12000,
        // producing a nearly instantaneous attack+decay instead of the
        // intended musical 10ms attack / 500ms decay.
        u16(igen,34);u16(igen,static_cast<unsigned>(-7973 & 0xffff));
        u16(igen,36);u16(igen,static_cast<unsigned>(-1200 & 0xffff));
        u16(igen,37);u16(igen,960);
    }
    u16(igen,54);u16(igen,1); // Loop continuously
    u16(igen,53);u16(igen,0); // Sample 0
    if(multipleBanks) {
        // A real SF2 may specify instrument tuning and an additional
        // preset-level relative tuning: BOTH must apply to the same layer.
        // With the old SF1-only FillFrom rule, +12 was silently discarded
        // as soon as instrument fineTune was present.
        u16(igen,54);u16(igen,1);u16(igen,52);u16(igen,static_cast<unsigned>(-30 & 0xffff));
        u16(igen,53);u16(igen,1);
        u16(igen,54);u16(igen,1);u16(igen,53);u16(igen,2);
    }

    name20(shdr,"125A Wave");u32(shdr,0);
    u32(shdr,static_cast<uint32_t>(sampleWords));
    u32(shdr,16);u32(shdr,static_cast<uint32_t>(sampleWords-16));
    u32(shdr,44100);
    shdr.push_back(69);shdr.push_back(0);
    u16(shdr,0);u16(shdr,1);
    if(multipleBanks) {
        for(uint32_t n=1;n<=2;++n) {
            name20(shdr,n==1?"125A Wave B":"125A Wave C");
            u32(shdr,static_cast<uint32_t>(sampleWords*n));
            u32(shdr,static_cast<uint32_t>(sampleWords*(n+1)));
            u32(shdr,static_cast<uint32_t>(sampleWords*n+16));
            u32(shdr,static_cast<uint32_t>(sampleWords*(n+1)-16));
            u32(shdr,44100);
            shdr.push_back(69);shdr.push_back(0);u16(shdr,0);u16(shdr,1);
        }
    }
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
    const fs::path multi=directory/"125A_synthetic_sf2_banks.sf2";
    const fs::path pluck=directory/"125A_synthetic_sf2_plucked_bass.sf2";
    const fs::path huge=directory/"125A_synthetic_sf2_overflow.sf2";
    const fs::path large=directory/"125A_synthetic_sf2_8mb_plus.sf2";
    const fs::path rom=directory/"125A_synthetic_sf2_audio.raw";
    struct Cleanup {
        fs::path a,b,c,d,e,f;
        ~Cleanup(){std::error_code ec;fs::remove(a,ec);fs::remove(b,ec);fs::remove(c,ec);fs::remove(d,ec);fs::remove(e,ec);fs::remove(f,ec);}
    } cleanup{sf,huge,rom,large,multi,pluck};
    if (!writeFile(sf,makeBank(2048)) ||
        !writeFile(pluck,makeBank(2048,false,true)) ||
        !writeFile(multi,makeBank(2048,true)) ||
        !writeFile(huge,makeBank(300000)) ||
        !writeFile(large,makeBank(4'300'000)) ||
        !writeFile(rom,Bytes(1048576,0)))return 2;
    bool ok=true;
    std::string error;
    // P20: A phdr name can be visible even when full SF2 sample loading
    // fails (e.g. a >28 MiB sample pool). In that case, a substitute sine
    // would wrongly sound like the selected "TX81Z Lately Bass" patch.
    {
        Synth notLoaded(44100);
        notLoaded.Core().SetDriver(Awe32::Driver::Win95);
        const bool loaded=notLoaded.LoadBank(
            (directory/"125A_missing_configured.sf2").string(),error);
        ok &= check(!loaded&&!error.empty()&&
                    !AWE125::AllowEmuNoteOn(true,loaded),
                    "failed configured SF2 suppresses misleading substitute-sine NoteOn");
        std::vector<int16_t> silent(8192);
        if(AWE125::AllowEmuNoteOn(true,loaded))
            notLoaded.NoteOn(0,69,127);
        notLoaded.RenderBlock(silent.data(),4096);
        ok &= check(std::all_of(silent.begin(),silent.end(),
                    [](int16_t x){return x==0;}),
                    "failed SF2 produces silence instead of playing a fake patch");
        ok &= check(AWE125::AllowEmuNoteOn(false,false) &&
                    AWE125::AllowEmuNoteOn(true,true),
                    "unconfigured demo fallback and successfully loaded SF2 remain usable");
    }
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
        // End-to-end bank routing. Each SF2 bank has an independent pitch
        // generator, so actual rendered PCM must change, not just a field.
        const auto renderForBank=[&](uint16_t bank,bool useMidiCC0) {
            Synth synth(44100);
            synth.Core().SetDriver(Awe32::Driver::Win95);
            std::string err;
            if(!synth.LoadBank(multi.string(),err))return std::vector<int16_t>{};
            synth.SelectBrowserBank(bank);
            if(useMidiCC0)synth.ControlChange(0,0,0);
            synth.ProgramChange(0,0);
            synth.NoteOn(0,69,127);
            std::vector<int16_t> pcm(8192);
            synth.RenderBlock(pcm.data(),4096);
            return pcm;
        };
        const auto bank0=renderForBank(0,false);
        const auto bank5=renderForBank(5,false);
        const auto bank128=renderForBank(128,false);
        const auto midiOverride=renderForBank(5,true);
        const auto audible=[](const auto& pcm) {
            return std::any_of(pcm.begin(),pcm.end(),
                              [](int16_t x){return x!=0;});
        };
        const auto sound=SoundFont::Load(multi.string());
        const auto r0=sound.Select(0,0,69,127);
        const auto r5=sound.Select(5,0,69,127);
        const auto r128=sound.Select(128,0,69,127);
        ok &= check(sound.valid&&sound.presets.size()==3&&
                    r0.size()==1&&r5.size()==1&&r128.size()==1&&
                    r0[0].sample!=r5[0].sample&&r5[0].sample!=r128[0].sample,
                    "generated SF2 banks select physically distinct sample records");
        ok &= check(!r0.empty()&&!r5.empty()&&!r128.empty()&&
                    r0[0].gen.Get(SoundFont::Gen::CoarseTune,0)==0&&
                    r5[0].gen.Get(SoundFont::Gen::CoarseTune,-999)==12&&
                    r5[0].gen.Get(SoundFont::Gen::FineTune,-999)==-10&&
                    r128[0].gen.Get(SoundFont::Gen::CoarseTune,-999)==24,
                    "SF2 bank 5 combines instrument -30 and preset +20 fineTune to -10");
        ok &= check(bank0.size()==8192&&bank5.size()==8192&&
                    bank128.size()==8192&&audible(bank0)&&audible(bank5)&&
                    audible(bank128),
                    "generated SF2 banks 0, 5 and 128 all render audible PCM");
        ok &= check(bank0!=bank5,"actual EMU8000 audio changes for bank 0 -> 5");
        ok &= check(bank5!=bank128,"actual EMU8000 audio changes for bank 5 -> drums 128");
        ok &= check(midiOverride==bank0,
                    "MIDI CC0 explicitly overrides the browser-selected SF2 bank");
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
    {
        // This VST3 project's default is now the full 28 MiB EMU8000 RAM.
        // A >8 MiB generated SF2 must load via the real 86Box chip renderer,
        // without private Creative data in Git or the CI artifacts.
        Synth synth(44100);
        synth.Core().SetDriver(Awe32::Driver::Win95);
        error.clear();
        ok &= check(synth.Core().UseBox86Chip(rom.string(),error),
                    "fixed-default EMU8000 28 MiB chip initialization");
        ok &= check(synth.Core().ChipRamWords()==28672u*512u,
                    "default EMU8000 is exactly 28 MiB, not old 8 MiB");
        synth.Core().PowerOnInit();
        error.clear();
        ok &= check(synth.LoadBank(large.string(),error),
                    ">8 MiB synthetic SoundFont uploads into 28 MiB chip");
        ok &= check(synth.BankCount()==1 &&
                    synth.Core().ChipRam()[reserve+64]==synth.Core().DramData()[reserve+64],
                    "large SF2 copies into actual hardware-emulated chip RAM");
    }
    {
        // P27: A direct, synthetic sound test of the authentic 86Box chip's
        // stereo pan and hardware effects. This is NOT comparison with
        // FluidSynth, which uses different effect algorithms and levels.
        // Use a zero ROM and a generated, copyrighted-asset-free SF2.
        auto capture=[&](unsigned pan,unsigned chorus,unsigned reverb) {
            Synth synth(44100);
            synth.Core().SetDriver(Awe32::Driver::Win95);
            std::string err;
            if(!synth.Core().UseBox86Chip(rom.string(),err) ||
               synth.Core().ChipVariant()!=Emu8000Core::Chip::Box86)
                return std::vector<int16_t>{};
            synth.Core().PowerOnInit();
            if(!synth.LoadBank(sf.string(),err)) return std::vector<int16_t>{};
            synth.ProgramChange(0,0);
            synth.NoteOn(0,69,110);
            // The first single voice in a newly initialized Win95 chip is
            // voice zero. Only change chip registers AFTER the actual
            // Synth/driver note-on. The native DSP/FX code stays untouched.
            constexpr int voice=0;
            auto& chip=synth.Core();
            const uint32_t psst=chip.Read(Emu8000::Reg::PSST,voice);
            const uint32_t csl=chip.Read(Emu8000::Reg::CSL,voice);
            const uint32_t ptrx=chip.Read(Emu8000::Reg::PTRX,voice);
            chip.Write(Emu8000::Reg::PSST,voice,
                       ((pan&255u)<<24) | (psst&0xFFFFFFu));
            chip.Write(Emu8000::Reg::CSL,voice,
                       ((chorus&255u)<<24) | (csl&0xFFFFFFu));
            chip.Write(Emu8000::Reg::PTRX,voice,
                       (ptrx&0xFFFF00FFu) | ((reverb&255u)<<8));
            constexpr size_t frames=44100;
            std::vector<int16_t> audio(frames*2,0);
            synth.RenderBlock(audio.data(),static_cast<uint32_t>(frames));
            return audio;
        };
        const auto dry=capture(128,0,0);
        const auto left=capture(255,0,0);
        const auto right=capture(0,0,0);
        const auto wetChorus=capture(128,255,0);
        const auto wetReverb=capture(128,0,255);
        const bool sizes=dry.size()==88200&&left.size()==88200&&
                         right.size()==88200&&wetChorus.size()==88200&&
                         wetReverb.size()==88200;
        ok &= check(sizes,"P27 five genuine 86Box wet/dry/pan captures rendered");
        if(sizes) {
            const auto energy=[](const std::vector<int16_t>& a,int channel) {
                uint64_t sum=0;
                // Ignore the 980-frame chip FIFO; inspect 0.04 to 0.25s.
                for(size_t f=1764;f<11025;++f)
                    sum+=static_cast<uint64_t>(
                        std::abs(static_cast<int>(a[2*f+channel])));
                return sum;
            };
            const auto change=[](const std::vector<int16_t>& a,
                                 const std::vector<int16_t>& b) {
                uint64_t sum=0;
                for(size_t f=1764;f<44100;++f)
                    for(int c=0;c<2;++c)
                        sum+=static_cast<uint64_t>(
                          std::abs(static_cast<int>(a[2*f+c])-
                                   static_cast<int>(b[2*f+c])));
                return sum;
            };
            const uint64_t eDry=energy(dry,0)+energy(dry,1);
            ok &= check(eDry>100000,"P27 dry generated SF2 produces real chip PCM");
            ok &= check(energy(left,0)>10u*energy(left,1) &&
                        energy(right,1)>10u*energy(right,0),
                        "P27 PSST hardware left and right pans route PCM correctly");
            ok &= check(change(dry,wetChorus)>1000,
                        "P27 CSL chorus send changes 86Box DSP output");
            ok &= check(change(dry,wetReverb)>1000,
                        "P27 PTRX reverb send changes 86Box DSP output");
        }
    }
    // P61: Audible envelope acceptance in the real 86Box EMU8000 DSP,
    // not merely a successful SF2 generator parse. The user's reference
    // bass has a short attack/decay, unlike a held organ-like tone.
    // This fixture contains *generated sine PCM only*; no user's bank.
    {
        const auto renderBass=[&](const fs::path& bankPath) {
            Synth synth(44100);
            synth.Core().SetDriver(Awe32::Driver::Win95);
            std::string err;
            if (!synth.Core().UseBox86Chip(rom.string(),err) ||
                synth.Core().ChipVariant()!=Emu8000Core::Chip::Box86)
                return std::vector<int16_t>{};
            synth.Core().PowerOnInit();
            if (!synth.LoadBank(bankPath.string(),err))
                return std::vector<int16_t>{};
            if (bankPath==pluck) {
                const auto probe=SoundFont::Load(pluck.string());
                const auto layers=probe.Select(0,0,69,100);
                std::cout<<"P61 soundfont valid="<<probe.valid
                    <<" layers="<<layers.size()<<'\n';
                if (!layers.empty()) {
                    const auto& g=layers[0].gen;
                    const auto vp=SoundFont::MakeVoiceParams(
                        probe,layers[0],69,100,0x200010,0,Awe32::Driver::Win95);
                    std::cout<<"P61 generators sustain="<<g.Get(SoundFont::Gen::SustainVolEnv,-999)
                        <<" decay="<<g.Get(SoundFont::Gen::DecayVolEnv,-999)
                        <<" attack="<<g.Get(SoundFont::Gen::AttackVolEnv,-999)
                        <<" DCYSUSV=0x"<<std::hex<<vp.dcysusv
                        <<" ATKHLDV=0x"<<vp.atkhldv
                        <<" ENVVOL=0x"<<vp.envvol<<std::dec<<'\n';
                }
            }
            synth.ProgramChange(0,0);
            synth.NoteOn(0,69,100);
            std::vector<int16_t> samples(44100*2*2,0); // 2 s stereo
            synth.RenderBlock(samples.data(),88200);
            return samples;
        };
        const auto sustained=renderBass(sf);
        const auto plucked=renderBass(pluck);
        const auto rms=[](const std::vector<int16_t>& samples,
                          double first,double last) {
            const size_t a=static_cast<size_t>(first*44100);
            const size_t b=static_cast<size_t>(last*44100);
            if (samples.size()<b*2 || b<=a)
                return 0.0;
            double energy=0.0;
            for (size_t i=a;i<b;++i)
                for (size_t ch=0;ch<2;++ch) {
                    const double x=samples[i*2+ch]/32768.0;
                    energy+=x*x;
                }
            return std::sqrt(energy/(2*(b-a)));
        };
        const bool complete=sustained.size()==176400&&plucked.size()==176400;
        ok &= check(complete,
            "P61 generated sustained/plucked SF2s render full 2 s on 86Box");
        if (complete) {
            std::cout<<"P61 time window plucked RMS "
                <<"0.000-0.015="<<rms(plucked,0,.015)
                <<" 0.015-0.030="<<rms(plucked,.015,.030)
                <<" 0.030-0.060="<<rms(plucked,.030,.060)
                <<" 0.060-0.130="<<rms(plucked,.060,.130)<<'\n';
            const double pluckEarly=rms(plucked,.06,.13);
            const double pluckLate=rms(plucked,1.35,1.60);
            const double sustainEarly=rms(sustained,.06,.13);
            const double sustainLate=rms(sustained,1.35,1.60);
            const bool genuineDecay=pluckEarly>1e-5 &&
                pluckLate < pluckEarly*0.10 &&
                sustainEarly>1e-5 &&
                sustainLate > sustainEarly*0.20;
            std::cout<<"P61 measured 86Box RMS early/late plucked="
                <<pluckEarly<<"/"<<pluckLate
                <<" sustained="<<sustainEarly<<"/"<<sustainLate<<'\n';
            ok &= check(genuineDecay,
                "P61 SF2 sustain=960 and decay generator audibly stops the pluck");
        }
    }
    std::cout<<(ok?"SF2/EMU8000 END-TO-END PASS":"SF2/EMU8000 END-TO-END FAIL")<<'\n';
    std::cout<<"NOT RUN: licensed/user SF2, original ROM timbre parity, Studio One"<<'\n';
    return ok?0:1;
}
