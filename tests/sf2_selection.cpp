#include "SoundFont.h"
#include <array>
#include <atomic>
#include <cstdlib>
#include <iostream>
#include <new>
#include <vector>

static std::atomic<unsigned long long> g_allocations{0};
void* operator new(std::size_t n) {
    if (void* p = std::malloc(n ? n : 1)) {
        g_allocations.fetch_add(1, std::memory_order_relaxed);
        return p;
    }
    throw std::bad_alloc();
}
void operator delete(void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t) noexcept { std::free(p); }

static bool Check(bool b, const char* description) {
    if (!b) std::cerr << "FAIL: " << description << '\n';
    else std::cout << "PASS: " << description << '\n';
    return b;
}
static bool Same(const SoundFont::Region& a, const SoundFont::Region& b) {
    return a.sample == b.sample &&
           a.gen.value == b.gen.value &&
           a.gen.present == b.gen.present &&
           a.sf1AttenUnits == b.sf1AttenUnits;
}
int main() {
    using namespace SoundFont;
    bool ok = true;
    Bank bank;
    bank.version = Version::Sf2;
    bank.samples.resize(80);
    bank.instruments.resize(1);
    bank.presets.resize(1);
    auto& in = bank.instruments.front();
    auto& p = bank.presets.front();
    p.bank = 12; p.program = 7;
    p.global.Set(Gen::InitialFilterFc, 4000);
    p.global.Set(Gen::CoarseTune, -1);
    in.global.Set(Gen::CoarseTune, 3);
    Zone pz;
    pz.instrument = 0;
    pz.keyLo = 60;
    pz.keyHi = 72;
    pz.velLo = 10;
    pz.velHi = 110;
    p.zones.push_back(pz);
    for (int i = 0; i < 80; ++i) {
        Zone iz;
        iz.sampleId = i;
        iz.keyLo = 60; iz.keyHi = 72;
        iz.velLo = 10; iz.velHi = 110;
        iz.gen.Set(Gen::Pan, static_cast<int16_t>(i - 40));
        in.zones.push_back(iz);
    }

    std::array<Region, 64> buffer{};
    const auto expected = bank.Select(12, 7, 66, 90);
    ok &= Check(expected.size() == 80, "80 matching layers in baseline");
    ok &= Check(expected.front().gen.Get(Gen::CoarseTune,-999)==2,
        "SF2: instrument coarseTune +3 and preset offset -1 combine to +2");
    ok &= Check(expected.front().gen.Get(Gen::InitialFilterFc,-999)==13500,
        "SF2: positive preset cutoff offset clamps against default 13500");
    // Real-world pattern recreated without copying proprietary bank data:
    // preset offsets must affect audible pitch, chorus, resonance and envelopes.
    {
        Bank bass;
        bass.version=Version::Sf2;
        bass.samples.resize(1);
        bass.instruments.resize(1);
        bass.presets.resize(1);
        auto& ins=bass.instruments.front();
        ins.global.Set(Gen::InitialFilterQ,100);
        ins.global.Set(Gen::ChorusEffectsSend,0);
        ins.global.Set(Gen::AttackVolEnv,-7973);
        ins.global.Set(Gen::DecayVolEnv,0);
        ins.global.Set(Gen::FineTune,-5);
        ins.global.Set(Gen::ReleaseVolEnv,0);
        Zone iz;
        iz.sampleId=0;
        ins.zones.push_back(iz);
        auto& patch=bass.presets.front();
        patch.program=7;patch.bank=0;
        Zone pz2;
        pz2.instrument=0;
        pz2.gen.Set(Gen::InitialFilterQ,-110);
        pz2.gen.Set(Gen::ChorusEffectsSend,400);
        pz2.gen.Set(Gen::AttackVolEnv,-3986);
        pz2.gen.Set(Gen::DecayVolEnv,814);
        pz2.gen.Set(Gen::ReleaseVolEnv,814);
        pz2.gen.Set(Gen::FineTune,-1);
        // Recreate the actual bass-bank failure: the instrument omits
        // delayVolEnv, but the preset contains a negative offset. Before
        // P26, -3986 was treated as an ABSOLUTE 100 ms delay.
        pz2.gen.Set(Gen::DelayVolEnv,-3986);
        pz2.gen.Set(Gen::DelayModLFO,3000);
        pz2.gen.Set(Gen::DecayModEnv,3986);
        pz2.gen.Set(Gen::InitialFilterFc,-2000);
        patch.zones.push_back(pz2);
        const auto sound=bass.Select(0,7,60,100);
        const bool composed=sound.size()==1&&
            sound[0].gen.Get(Gen::InitialFilterQ,-999)==-10&&
            sound[0].gen.Get(Gen::ChorusEffectsSend,-999)==400&&
            sound[0].gen.Get(Gen::AttackVolEnv,-999)==-11959&&
            sound[0].gen.Get(Gen::DecayVolEnv,-999)==814&&
            sound[0].gen.Get(Gen::ReleaseVolEnv,-999)==814&&
            sound[0].gen.Get(Gen::FineTune,-999)==-6 &&
            sound[0].gen.Get(Gen::DelayVolEnv,-999)==-12000 &&
            sound[0].gen.Get(Gen::DelayModLFO,-999)==-9000 &&
            sound[0].gen.Get(Gen::DecayModEnv,-999)==-8014 &&
            sound[0].gen.Get(Gen::InitialFilterFc,-999)==11500;
        ok &= Check(composed,"SF2 real-bank-style filter, envelope, chorus and tuning offsets combine");
        // Sound 000 in the actual bank contains no sustain generators.
        // In SF2 absence means full sustain, NOT decay-to-zero as for SF1.
        if (!sound.empty()) {
            const auto full=MakeVoiceParams(bass,sound[0],60,100,0x200010,0,
                                           Awe32::Driver::Win95);
            ok &= Check((full.dcysusv>>8)==0x7F&&(full.dcysus>>8)==0x7F,
                "SF2 absent volume AND modulation sustain -> full 127");
            ok &= Check(full.envvol==0x8000,
                "SF2 preset -3986 delay offset over implicit -12000 starts immediately");
            // P110: actual bank program 7 combines attack -7973 and -3986
            // into -11959 timecents. Never emit 128 into a 7-bit register:
            // 128 becomes attack 0 (infinite silence until release).
            ok &= Check((full.atkhldv & 0x7F)==0x7F,
                "P110 SF2 fast attack -11959 stays 0x7F, not wrapped to zero");
            Region fastLimit=sound[0];
            fastLimit.gen.Set(Gen::AttackVolEnv,-12000);
            fastLimit.gen.Set(Gen::AttackModEnv,-12000);
            const auto fastest=MakeVoiceParams(bass,fastLimit,60,100,
                0x200010,0,Awe32::Driver::Win95);
            ok &= Check((fastest.atkhldv & 0x7F)==0x7F &&
                        (fastest.atkhld & 0x7F)==0x7F,
                "P110 SF2 minimum timecents never overflow volume/mod attack");
            ok &= Check(full.ifatn!=0xFF00,
                "SF2 preset cutoff offset over default is converted to chip register");
            Region adjusted=sound[0];
            adjusted.gen.Set(Gen::SustainVolEnv,120); // 12 dB -> 16 steps
            adjusted.gen.Set(Gen::SustainModEnv,600); // 60% below peak
            const auto explicitSustain=MakeVoiceParams(
                bass,adjusted,60,100,0x200010,0,Awe32::Driver::Win95);
            ok &= Check((explicitSustain.dcysusv>>8)==111 &&
                        (explicitSustain.dcysus>>8)==51,
                "SF2 explicit volume 120 centibels and mod 600 permille use distinct units");
            adjusted.gen.Set(Gen::SustainVolEnv,960);
            adjusted.gen.Set(Gen::SustainModEnv,1000);
            const auto zeroSustain=MakeVoiceParams(
                bass,adjusted,60,100,0x200010,0,Awe32::Driver::Win95);
            ok &= Check((zeroSustain.dcysusv>>8)==0 &&
                        (zeroSustain.dcysus>>8)==0,
                "SF2 explicit high attenuation decays to zero as intended");
        }
        // Protect the previously proven SBK/SF1 driver semantics.
        bass.version=Version::Sf1;
        const auto legacy=bass.Select(0,7,60,100);
        if (!legacy.empty()) {
            const auto original=MakeVoiceParams(bass,legacy[0],60,100,0x200010,0,
                                                 Awe32::Driver::Win95);
            ok &= Check((original.dcysusv>>8)==0&&(original.dcysus>>8)==0,
                "SF1 missing sustain retains original hardware register default zero");
        }
        ok &= Check(legacy.size()==1&&
            legacy[0].gen.Get(Gen::InitialFilterQ,-999)==100&&
            legacy[0].gen.Get(Gen::ChorusEffectsSend,-999)==0&&
            legacy[0].gen.Get(Gen::AttackVolEnv,-999)==-7973&&
            legacy[0].gen.Get(Gen::FineTune,-999)==-5,
            "SF1 historical driver precedence remains unchanged");
        // A malformed preset must not wrap an int16 sum.
        GenSet saturating;
        GenSet offset;
        saturating.Set(Gen::FineTune,32760);
        offset.Set(Gen::FineTune,200);
        saturating.AddFrom(offset);
        ok &= Check(saturating.Get(Gen::FineTune,-1)==32767,
            "SF2 additive overflow saturates instead of wrapping");
    }

    // P59: a *synthetic metadata-only* regression for the four-layer/octave
    // architecture observed in the user's SF2 bass. Neither any waveform,
    // original bank file, nor the user's reference recording is included.
    // The reference WAV contains D3 (MIDI50) and E3 (MIDI52), NOT the C3
    // note played in previous automated single-note probes.
    {
        Bank octaveBass;
        octaveBass.version = Version::Sf2;
        octaveBass.samples.resize(1);
        octaveBass.samples[0].name = "synthetic 2-cycle source";
        octaveBass.samples[0].originalKey = 60;
        octaveBass.samples[0].sampleRate = 44100;
        octaveBass.samples[0].start = 100;
        octaveBass.samples[0].end = 420;
        octaveBass.samples[0].loopStart = 120;
        octaveBass.samples[0].loopEnd = 400;
        octaveBass.instruments.resize(1);
        octaveBass.presets.resize(1);
        auto& instrument = octaveBass.instruments[0];
        instrument.global.Set(Gen::OverridingRootKey, 72);
        instrument.global.Set(Gen::FineTune, -5);
        instrument.global.Set(Gen::SampleModes, 1);
        Zone sampleZone;
        sampleZone.sampleId = 0;
        instrument.zones.push_back(sampleZone);
        auto& patch = octaveBass.presets[0];
        patch.bank = 0; patch.program = 7;
        for (int index = 0; index < 4; ++index) {
            Zone layer;
            layer.instrument = 0;
            layer.keyLo = 0; layer.keyHi = 69;
            layer.gen.Set(Gen::Pan, index < 2 ? -1000 : 1000);
            layer.gen.Set(Gen::CoarseTune, (index == 1 || index == 2) ? 12 : 0);
            layer.gen.Set(Gen::FineTune, index < 2 ? -1 : 0);
            patch.zones.push_back(layer);
        }
        // Expected pitch offsets in cents relative to a 44.1kHz source,
        // including four distinct detunings and two octave choices.
        constexpr std::array<int, 4> d3Cents = {-2206, -1006, -1005, -2205};
        constexpr std::array<int, 4> e3Cents = {-2006, -806, -805, -2005};
        for (const int note : {50, 52}) {
            const auto regions = octaveBass.Select(0, 7, note, 100);
            const auto expectedPitch = note == 50 ? d3Cents : e3Cents;
            bool match = regions.size() == 4;
            if (match) {
                for (size_t k = 0; k < regions.size(); ++k) {
                    const auto voice = MakeVoiceParams(
                        octaveBass, regions[k], note, 100, 0x200010, 0,
                        Awe32::Driver::Win95);
                    match &= voice.ipCents == expectedPitch[k];
                    match &= voice.patchPan == (k < 2 ? 0 : 127);
                    match &= regions[k].sample == &octaveBass.samples[0];
                }
            }
            ok &= Check(match, note == 50
                ? "P59: bass D3 correctly splits into two fine-detuned octave pairs"
                : "P59: bass E3 preserves four layers and correct pitch intervals");
        }
        ok &= Check(octaveBass.Select(0,7,70,100).empty(),
            "P59: original-style layer key range excludes MIDI note 70");
    }

    auto result = bank.SelectInto(12, 7, 66, 90, buffer);
    ok &= Check(result.overflow && result.count == buffer.size(), "oversized preset reports overflow instead of silently truncating");
    for (size_t i = 0; i < result.count; ++i)
        ok &= Check(Same(expected[i], buffer[i]), "SF2 layer identical to original selector");

    std::array<Region, 80> full{};
    // A hot path must not call operator new, including for layered presets.
    const auto before = g_allocations.load(std::memory_order_relaxed);
    result = bank.SelectInto(12, 7, 66, 90, full);
    const auto after = g_allocations.load(std::memory_order_relaxed);
    ok &= Check(!result.overflow && result.count == expected.size(), "full-capacity selector retains all layers");
    ok &= Check(before == after, "SelectInto has zero dynamic allocations");
    for (size_t i = 0; i < result.count; ++i)
        if (!Same(expected[i], full[i])) {
            ok &= Check(false, "SF2 parity for all matching regions");
            break;
        }
    auto miss = bank.SelectInto(12, 7, 50, 90, buffer);
    ok &= Check(miss.count == 0 && !miss.overflow, "key range rejects nonmatching note");
    miss = bank.SelectInto(12, 7, 66, 1, buffer);
    ok &= Check(miss.count == 0 && !miss.overflow, "velocity range rejects nonmatching note");
    miss = bank.SelectInto(128, 7, 66, 90, buffer);
    ok &= Check(miss.count == 0 && !miss.overflow, "no implicit bank fallback");
    miss = bank.SelectInto(12, 7, 66, 90, std::span<Region>{});
    ok &= Check(miss.count == 0 && miss.overflow, "zero-capacity output reports overflow");

    bank.version = Version::Sf1;
    in.global.Set(Gen::InitialAttenuation, 121);
    p.global.Set(Gen::InitialAttenuation, 112);
    const auto sf1 = bank.Select(12, 7, 66, 90);
    result = bank.SelectInto(12, 7, 66, 90, full);
    ok &= Check(!result.overflow && result.count == sf1.size(), "SF1 selection remains supported");
    ok &= Check(full[0].sf1AttenUnits == (127-121)+(127-112),
                "SF1 attenuation matches driver unit-summing rule");
    for (size_t i = 0; i < result.count; ++i)
        if (!Same(sf1[i], full[i])) {
            ok &= Check(false, "SF1 parity for all matching regions");
            break;
        }

    std::cout << (ok ? "SF2/SBK BOUNDED SELECTION PASS" : "SF2/SBK BOUNDED SELECTION FAIL") << '\n';
    std::cout << "NOT RUN: audible SF2 rendering, complete Synth runtime, hardware parity, Studio One" << '\n';
    return ok ? 0 : 1;
}
