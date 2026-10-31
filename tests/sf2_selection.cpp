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
