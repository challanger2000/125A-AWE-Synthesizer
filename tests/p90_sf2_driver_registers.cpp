// P90: regression of REAL original-Creative Win95 SF2 generator conversions.
// Uses synthetic generator values, not any user's proprietary SoundFont.
#include "SoundFont.h"
#include "Emu8000Regs.h"
#include <cstdint>
#include <iostream>
using namespace SoundFont;
namespace {
bool check(bool ok,const char* name) {
    std::cout<<(ok?"PASS ":"FAIL ")<<name<<"\n";return ok;
}
}
int main() {
    Bank sf2;
    sf2.version=Version::Sf2;
    Sample src;
    src.name="synthetic";
    src.start=1000;src.end=1500;src.loopStart=1100;src.loopEnd=1400;
    src.originalKey=60;src.sampleRate=44100;
    Region r;
    r.sample=&src;
    r.gen.Set(Gen::SampleModes,1);
    r.gen.Set(Gen::InitialFilterQ,100);      // measured original CCCA Q=8
    r.gen.Set(Gen::ModLfoToVolume,20);      // measured TREMFRQ high 0x15
    r.gen.Set(Gen::ChorusEffectsSend,500);  // measured CSL high 0x7F
    const uint32_t base=Emu8000::kDramOffset+32u;
    const auto gold=MakeVoiceParams(sf2,r,60,100,base,0,Awe32::Driver::Win95);
    const auto dos=MakeVoiceParams(sf2,r,60,100,base,0,Awe32::Driver::Dos);
    bool ok=true;
    ok&=check(gold.looping && !gold.loopOpensOnRelease,
              "Win95 SF2 mode 1 continuous loop survives NoteOff");
    r.gen.Set(Gen::SampleModes,3);
    const auto releaseLoop=MakeVoiceParams(sf2,r,60,100,base,0,Awe32::Driver::Win95);
    ok&=check(releaseLoop.looping && releaseLoop.loopOpensOnRelease,
              "Win95 SF2 mode 3 opens loop on NoteOff");
    r.gen.Set(Gen::SampleModes,0);
    const auto oneShot=MakeVoiceParams(sf2,r,60,100,base,0,Awe32::Driver::Win95);
    ok&=check(!oneShot.looping && !oneShot.loopOpensOnRelease,
              "Win95 SF2 mode 0 is one-shot");
    r.gen.Set(Gen::SampleModes,1);
    // P92 independent original Creative converter code / P91 genuine
    // register measurement: note 48, velocity 100, two generated test layers.
    r.gen.Set(Gen::FreqModLFO,-617);
    r.gen.Set(Gen::AttackVolEnv,-8828);
    const auto p92=MakeVoiceParams(sf2,r,60,100,base,0,Awe32::Driver::Win95);
    ok&=check((p92.tremfrq&0xFF)==0x8B,
              "P92 original Win95 freqModLFO -617 cents -> 0x8B");
    ok&=check((p92.fm2frq2&0xFF)==0xCD,
              "P92 original Win95 missing freqVibLFO (0 cents) -> 0xCD");
    ok&=check((p92.atkhldv&0xFF)==0x7E,
              "P92 original Win95 attackVolEnv -8828 tc -> 0x7E");
    r.gen.Set(Gen::FreqModLFO,-16000);
    const auto minimumLfo=MakeVoiceParams(sf2,r,60,100,base,0,Awe32::Driver::Win95);
    ok&=check((minimumLfo.tremfrq&0xFF)==0,
              "P92 negative 16000-cent LFO lower clamp -> 0");
    r.gen.Set(Gen::FreqModLFO,4500);
    const auto maximumLfo=MakeVoiceParams(sf2,r,60,100,base,0,Awe32::Driver::Win95);
    ok&=check((maximumLfo.tremfrq&0xFF)==255,
              "P92 high LFO frequency clamps to 255");
    r.gen.Set(Gen::FreqModLFO,0);
    r.gen.Set(Gen::AttackVolEnv,-1200);
    r.gen.Set(Gen::AttackModEnv,-1200);
    const auto halfSecond=MakeVoiceParams(sf2,r,60,100,base,0,Awe32::Driver::Win95);
    ok&=check((halfSecond.atkhldv&0xFF)==0x18 &&
              (halfSecond.atkhld&0xFF)==0x18,
              "P92 both SF2 envelope attack converters -1200 tc -> 0x18");
    r.gen.Set(Gen::AttackVolEnv,-600);
    const auto branchEdge=MakeVoiceParams(sf2,r,60,100,base,0,Awe32::Driver::Win95);
    ok&=check((branchEdge.atkhldv&0xFF)==0x10,
              "P92 original Creative attack piecewise transition -600 -> 16");
    r.gen.Set(Gen::AttackVolEnv,-599);
    const auto branchNext=MakeVoiceParams(sf2,r,60,100,base,0,Awe32::Driver::Win95);
    ok&=check((branchNext.atkhldv&0xFF)==0x0F,
              "P92 original Creative attack piecewise transition -599 -> 15");
    r.gen.Set(Gen::AttackVolEnv,-8828);
    r.gen.Set(Gen::FreqModLFO,-617);
    const auto legacy=MakeVoiceParams(sf2,r,60,100,base,0,Awe32::Driver::Dos);
    ok&=check((legacy.tremfrq&0xFF)==0x88 && 
              (legacy.fm2frq2&0xFF)==0xC3 &&
              (legacy.atkhldv&0xFF)==0x7D,
              "P92 DOS SF2 path retains prior Hz/ms conversion unchanged");
    ok&=check(gold.ccca>>28==8,"Win95 SF2 initialFilterQ=100 -> Q8");
    ok&=check((gold.tremfrq>>8)==0x15,"Win95 SF2 modLfoToVolume=20 -> tremolo depth21");
    ok&=check(gold.csl>>24==0x7F,"Win95 SF2 chorus=500 -> send127");
    ok&=check(gold.sampleStart==base+src.start,"Win95 SF2 sample address +1");
    ok&=check((gold.psst&0xFFFFFFu)==base+src.loopStart-1,"Win95 SF2 loop start +1");
    ok&=check((gold.csl&0xFFFFFFu)==base+src.loopEnd-1,"Win95 SF2 loop end +1");
    ok&=check(dos.ccca>>28==6,"DOS SF2 legacy Q6 unchanged");
    ok&=check(dos.tremfrq>>8==0x2A,"DOS SF2 legacy tremolo42 unchanged");
    ok&=check(dos.csl>>24==0x80,"DOS SF2 legacy chorus128 unchanged");
    ok&=check(dos.sampleStart==base+src.start-1,"DOS SF2 sample address unchanged");
    // In unmodified SF2 both families should stay equivalent at zero Q
    // and with no modulation; avoid manufacturing extra hardware voice state.
    r.gen.Set(Gen::InitialFilterQ,0);
    r.gen.Set(Gen::ModLfoToVolume,0);
    r.gen.Set(Gen::ChorusEffectsSend,0);
    const auto neutral=MakeVoiceParams(sf2,r,60,100,base,0,Awe32::Driver::Win95);
    ok&=check(neutral.ccca>>28==0,"Win95 SF2 zero Q remains zero");
    ok&=check(neutral.tremfrq>>8==0,"Win95 SF2 zero tremolo remains zero");
    ok&=check(neutral.csl>>24==0,"Win95 SF2 zero chorus remains zero");
    // P96 measured original Win95 SF2 P94 pitch sweep (same sample/zone
    // across notes 45..61) and two independent original program-7 voices.
    // The raw user SoundFont is never needed for these regression vectors.
    r.gen.Set(Gen::OverridingRootKey,45);
    r.gen.Set(Gen::CoarseTune,-12);
    struct PitchVector { int note; uint16_t plus; uint16_t minus; };
    const PitchVector sweep[] = {
        {45,0xD010,0xCFEE}, {46,0xD165,0xD143},
        {47,0xD2BB,0xD298}, {48,0xD410,0xD3EE},
        {49,0xD565,0xD543}, {50,0xD6BB,0xD699},
        {51,0xD810,0xD7EE}, {52,0xD966,0xD943},
        {53,0xDABB,0xDA99}, {54,0xDC10,0xDBEE},
        {55,0xDD66,0xDD44}, {56,0xDEBB,0xDE99},
        {60,0xE411,0xE3EF}, {61,0xE566,0xE544}
    };
    bool sweepCorrect=true;
    for (const auto& v : sweep)
    {
        r.gen.Set(Gen::FineTune,5);
        const auto a=MakeVoiceParams(sf2,r,v.note,100,base,0,Awe32::Driver::Win95);
        r.gen.Set(Gen::FineTune,-5);
        const auto b=MakeVoiceParams(sf2,r,v.note,100,base,0,Awe32::Driver::Win95);
        sweepCorrect &= a.ip==v.plus && b.ip==v.minus;
    }
    ok&=check(sweepCorrect,
              "P96 candidate matches 28 original Creative program0 pitch writes");
    r.gen.Set(Gen::OverridingRootKey,72);
    r.gen.Set(Gen::CoarseTune,0);
    r.gen.Set(Gen::FineTune,-6);
    const auto p7a=MakeVoiceParams(sf2,r,48,100,base,0,Awe32::Driver::Win95);
    r.gen.Set(Gen::CoarseTune,12);
    const auto p7b=MakeVoiceParams(sf2,r,48,100,base,0,Awe32::Driver::Win95);
    r.gen.Set(Gen::FineTune,-5);
    const auto p7c=MakeVoiceParams(sf2,r,48,100,base,0,Awe32::Driver::Win95);
    r.gen.Set(Gen::CoarseTune,0);
    const auto p7d=MakeVoiceParams(sf2,r,48,100,base,0,Awe32::Driver::Win95);
    ok&=check(p7a.ip==0xBFE9 && p7b.ip==0xCFEA &&
              p7c.ip==0xCFEE && p7d.ip==0xBFED,
              "P96 candidate matches 4 original Creative program7 pitch writes");
    return ok?0:1;
}
