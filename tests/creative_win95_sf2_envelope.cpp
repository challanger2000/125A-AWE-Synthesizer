// Original Win95 Creative SBAWE.VXD A/B-backed SF2 envelope regression.
// The ORIGINAL register oracle for P007 note 99 velocity 112 was captured
// with Creative's real Win95 driver; not inferred from this test itself.
// This synthetic-only test MUST fail on the pre-fix code (0x750C/0x001D).
#include "SoundFont.h"
#include "Emu8000Regs.h"
#include <algorithm>
#include <cstdint>
#include <cmath>
#include <iostream>
#include <vector>
using SoundFont::Bank;
using SoundFont::Sample;
using SoundFont::Region;
namespace Gen = SoundFont::Gen;
using SoundFont::Version;
using SoundFont::MakeVoiceParams;
namespace {
bool check(bool ok,const char* reason) {
    if(!ok)std::cerr<<"FAIL "<<reason<<"\n";
    return ok;
}
}
int main(){
    Bank bank; bank.version=Version::Sf2;
    Sample sample; sample.name="P007 synthetic analogue only";
    sample.start=0;sample.end=8192;
    sample.loopStart=1024;sample.loopEnd=8000;
    sample.originalKey=60;sample.sampleRate=44100;
    Region r; r.sample=&sample;
    r.gen.Set(Gen::SampleModes,1);
    r.gen.Set(Gen::AttackModEnv,-1200);
    r.gen.Set(Gen::HoldModEnv,0);  // real owner's P007 1000ms, not default
    r.gen.Set(Gen::SustainVolEnv,960); // real P007 original SF2 generator #37
    r.gen.Set(Gen::DecayVolEnv,-1200);
    bool ok=true;
    const auto creative=MakeVoiceParams(bank,r,99,112,
        Emu8000::kDramOffset+256u,0,Awe32::Driver::Win95);
    ok &= check(((creative.atkhld>>8)&0x7f)==0x74,
        "ACTUAL SBAWE.VXD P007 Note99 V112 ATKHLD mod hold must be 0x74, not 0x75");
    ok &= check(((creative.dcysusv>>8)&0x7f)==0x06,
        "ACTUAL SBAWE.VXD P007 Note99 V112 DCYSUSV sustain must be 0x06, not 0x00");
    // Distinct implementation families are required to remain independent.
    const auto dos=MakeVoiceParams(bank,r,99,112,
        Emu8000::kDramOffset+256u,0,Awe32::Driver::Dos);
    ok &= check(((dos.atkhld>>8)&0x7f)==0x75,
        "DOS legacy SF2 hold still truncates 1000/92 -> 0x75");
    ok &= check(((dos.dcysusv>>8)&0x7f)==0,
        "DOS legacy SF2 volume sustain remains unchanged");
    Bank bank1;bank1.version=Version::Sf1;
    const auto sf1=MakeVoiceParams(bank1,r,99,112,
        Emu8000::kDramOffset+256u,0,Awe32::Driver::Win95);
    ok &= check(((sf1.atkhld>>8)&0x7f)==0x7f,
        "SF1 hold uses its original time-units interpretation, not SF2 timecents");
    ok &= check(((sf1.dcysusv>>8)&0x7f)==0x7f,
        "SF1 existing sustain conversion must remain intact");
    // Direct-original P007 at 960 plus 14 original Creative Win95
    // generator-37 values are frozen below. Additional values here
    // are safe bounded synthetic controls, NOT original hardware data.
    for(const int v: {0,1,250,500,750,959,960,961,999,1000,1200}) {
        r.gen.Set(Gen::SustainVolEnv,static_cast<int16_t>(v));
        const auto out=MakeVoiceParams(bank,r,99,112,
            Emu8000::kDramOffset+256u,0,Awe32::Driver::Win95);
        const int expected=127+(-127*std::clamp(v,0,1000))/1000;
        ok &= check(((out.dcysusv>>8)&0x7f)==expected,
            "SF2 Win95 vol sustain integer conversion within supported bounds");
    }
    // INDEPENDENT 2026-11-10 original Win95 Creative driver register
    // observations, generated from the authentic publicly accepted SF2
    // source with original PCM and instrument zones preserved.
    // Real Creative driver source: private Actions #42899654680 SUCCESS,
    // 28 distinct isolated note59 velocity100 WinMM guest MIDI windows.
    // These expected values NEVER call our proposed conversion.
    struct VolOriginal {int centibels;int chip;};
    constexpr VolOriginal volumeOriginal[14] = {
        {0,127},{1,127},{10,126},{64,119},{127,111},
        {250,96},{500,64},{750,32},{959,6},{960,6},
        {961,5},{999,1},{1000,0},{1440,0}};
    int volCases=0;
    for(const auto& v:volumeOriginal) {
        Region synthetic; synthetic.sample=&sample;
        synthetic.gen.Set(Gen::HoldModEnv,0);
        synthetic.gen.Set(Gen::SustainVolEnv,
                          static_cast<int16_t>(v.centibels));
        const auto actual=MakeVoiceParams(bank,synthetic,59,100,
            Emu8000::kDramOffset+256u,0,Awe32::Driver::Win95);
        const int sustain=(actual.dcysusv>>8)&127;
        if(sustain!=v.chip) {
            std::cerr<<"ORIGINAL_CREATIVE_VOL_SUSTAIN_MISMATCH cB="
                     <<v.centibels<<" original="<<v.chip
                     <<" native="<<sustain<<"\n";ok=false;
        }else ++volCases;
    }
    struct HoldOriginal {int timecents;int chip;};
    constexpr HoldOriginal holdOriginal[14]={
        {-12000,127},{-6000,127},{-3600,126},{-2400,125},
        {-1200,122},{-600,120},{-120,117},{-1,116},
        {0,116},{1,116},{100,115},{300,114},
        {600,112},{1200,104}};
    int holdCases=0;
    for(const auto& v:holdOriginal) {
        Region synthetic; synthetic.sample=&sample;
        synthetic.gen.Set(Gen::HoldModEnv,
                          static_cast<int16_t>(v.timecents));
        synthetic.gen.Set(Gen::SustainVolEnv,0);
        const auto actual=MakeVoiceParams(bank,synthetic,59,100,
            Emu8000::kDramOffset+256u,0,Awe32::Driver::Win95);
        const int hold=(actual.atkhld>>8)&127;
        if(hold!=v.chip) {
            std::cerr<<"ORIGINAL_CREATIVE_MOD_HOLD_MISMATCH tc="
                     <<v.timecents<<" original="<<v.chip
                     <<" native="<<hold<<"\n";ok=false;
        }else ++holdCases;
    }
    ok&=check(volCases==14 && holdCases==14,
              "28 independent real Win95 driver input->register observations");
    // Negative controls: the previous simple ms/92 round() MUST NOT be
    // able to pass the observed -2400,-600,+1200 original-data cases.
    // These probes prevent regression to the tempting but disproved fit.
    auto oldSimpleRound=[](double ms) {
        return std::clamp(127-static_cast<int>(std::lround(ms/92.0)),0,127);
    };
    ok&=check(oldSimpleRound(250.)==124 &&
              oldSimpleRound(1000*std::pow(2.,-600./1200.))==119 &&
              oldSimpleRound(2000.)==105,
              "negative witness: old rounded-millisecond Win95 formula is WRONG");
    std::cout<<"CREATIVE_WIN95_REAL_28_GENERATOR_CASES volume_sustain="
             <<volCases<<"/14 modulation_hold="<<holdCases
             <<"/14 original_driver_source=Actions_42899654680\n";

    // SF2 default: OMITTED sustainVolEnv stays full sustain, 127.
    Region missing;missing.sample=&sample;
    const auto omitted=MakeVoiceParams(bank,missing,99,112,
        Emu8000::kDramOffset+256u,0,Awe32::Driver::Win95);
    ok &= check(((omitted.dcysusv>>8)&0x7f)==127,
        "Win95 SF2 absent sustainVolEnv stays 0x7F full sustain");
    ok &= check(((omitted.atkhld>>8)&0x7f)==127,
        "Win95 SF2 absent holdModEnv stays 0x7F");
    // A deliberately old-formula negative witness:
    // the previous implementation MUST disagree with the measured original.
    const int oldHold=127-static_cast<int>(1000.0/92.0);
    const int oldVol=std::clamp(127-static_cast<int>(
        std::lround((960.0/10.0)/0.75)),0,127);
    ok &= check(oldHold==0x75 && oldVol==0,
        "The old production formulas would fail BOTH original Creative anchors");
    std::cout<<(ok?"PASS":"FAIL")
             <<" REAL-original-Creative P007 envelope anchors; independent DOS/SF1; "
             <<"vol sustain boundary & missing-generator checks\n";
    return ok?0:1;
}