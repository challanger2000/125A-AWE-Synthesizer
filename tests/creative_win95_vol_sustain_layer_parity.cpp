// Source-derived actual original Creative SBAWE.VXD Win95 28/28 volume-sustain
// register oracle, from private Creative AWE64 Gold original-driver execution
// #42911162639. Source is public SoundFont-Spec-Test v3.0, with 44 source
// samples unchanged; no original wave ROM, proprietary binary or PCM included.
#include "SoundFont.h"
#include "Emu8000Regs.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
using SoundFont::Bank;
using SoundFont::Sample;
using SoundFont::Region;
namespace Gen=SoundFont::Gen;
using SoundFont::Version;
using SoundFont::MakeVoiceParams;
namespace {
constexpr std::array<int,4> bases={0,250,500,1000};
constexpr std::array<int,7> targets={0,1,249,250,500,750,1000};
constexpr std::array<std::array<int,7>,4> realCreative={{
   {{127,127,96,96,64,32,0}},
   {{127,127,96,96,65,33,1}},
   {{127,127,95,95,64,33,1}},
   {{127,126,95,95,63,31,0}}
}};
int trunc0(int n,int d){return n>=0?n/d:-((-n)/d);}
int T(int n){return 127+trunc0(-127*n,1000);}
int direct(int total){return std::clamp(T(std::clamp(total,0,1000)),0,127);}
int layered(int base,int delta){
  return std::clamp(T(std::clamp(base,0,1000))+
                    T(std::clamp(delta,-1000,1000))-127,0,127);
}
void test(bool condition,const char* msg,bool& okay){
    if(!condition){std::cerr<<"FAIL "<<msg<<"\n";okay=false;}
}
int sustain(const Bank& bank,const Region& region,Awe32::Driver drv){
    auto actual=MakeVoiceParams(bank,region,59,100,
                                Emu8000::kDramOffset+256u,0,drv);
    return (actual.dcysusv>>8)&127;
}
}
int main(){
    bool ok=true;
    Bank bank;bank.version=Version::Sf2;
    Bank bankSf1;bankSf1.version=Version::Sf1;
    Sample sample;sample.name="synthetic no-user-media";
    sample.start=0;sample.end=8192;
    sample.loopStart=1024;sample.loopEnd=8000;
    sample.originalKey=60;sample.sampleRate=44100;
    int exact=0,oldFail=0,syntheticFallback=0,dosUnchanged=0,sf1Unchanged=0;
    for(size_t i=0;i<bases.size();++i){
      for(size_t j=0;j<targets.size();++j){
        const int base=bases[i],total=targets[j],delta=total-base;
        Region r;r.sample=&sample;
        r.gen.Set(Gen::SustainVolEnv,static_cast<int16_t>(total));
        r.gen.Set(Gen::HoldModEnv,0);
        r.sf2VolSustainInstrument=base;
        r.sf2VolSustainPresetOffset=delta;
        r.sf2VolSustainLayerProvenance=true;
        const int actual=sustain(bank,r,Awe32::Driver::Win95);
        const int expected=realCreative[i][j]; // independent ORIGINAL-driver data
        if(actual!=expected){
          std::cerr<<"CREATIVE_VOLUME_SUSTAIN_2STAGE_MISMATCH base="<<base
                   <<" delta="<<delta<<" total="<<total<<" original="<<expected
                   <<" current="<<actual<<"\n";ok=false;
        }else ++exact;
        test(expected==layered(base,delta),"original VxD two-stage arithmetic",ok);
        oldFail+=direct(total)!=expected;
        // Programmatic Region with no provenance, or stale provenance
        // after host-side automation override, MUST use current merged value.
        Region synthetic=r;
        synthetic.sf2VolSustainLayerProvenance=false;
        if(sustain(bank,synthetic,Awe32::Driver::Win95)==direct(total))
          ++syntheticFallback;
        else test(false,"missing-provenance fallback must use merged value",ok);
        Region stale=r;
        stale.sf2VolSustainPresetOffset=delta+2; // deliberately inconsistent
        test(sustain(bank,stale,Awe32::Driver::Win95)==direct(total),
             "stale layer provenance must not override merged automated SF2 value",ok);
        // Preserve intentionally separate DOS and SF1 conversions:
        const int dos=sustain(bank,r,Awe32::Driver::Dos);
        const int expectedDos=std::clamp(
          127-static_cast<int>(std::lround((total/10.0)/0.75)),0,127);
        if(dos==expectedDos)++dosUnchanged;
        else test(false,"DOS/SF2 volume sustain regression",ok);
        if(sustain(bankSf1,r,Awe32::Driver::Win95)==
           std::clamp(total*4/3,0,127))++sf1Unchanged;
        else test(false,"SF1 volume sustain regression",ok);
      }
    }
    test(exact==28,"all 28 actual source-original Win95 Creative register values",ok);
    test(oldFail==12,"previous direct merged formula must fail 12 original cases",ok);
    test(syntheticFallback==28,"synthetic Regions without provenance fallback",ok);
    test(dosUnchanged==28,"DOS original sustain path independent",ok);
    test(sf1Unchanged==28,"SF1 original sustain path independent",ok);
    Region missing;missing.sample=&sample;
    test(sustain(bank,missing,Awe32::Driver::Win95)==127,
         "missing SF2 SustainVolEnv defaults to full sustain",ok);
    std::cout<<(ok?"PASS":"FAIL")
             <<" ORIGINAL_Creative_Win95_volume_sustain_crossed= "<<exact
             <<"/28 old_merged_fail="<<oldFail
             <<" fallback="<<syntheticFallback
             <<" DOS="<<dosUnchanged<<" SF1="<<sf1Unchanged
             <<" provenance=original_Creative_Actions_42911162639\n";
    return ok?0:1;
}
