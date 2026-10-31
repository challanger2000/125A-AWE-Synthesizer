#include "Synth.h"
#include <algorithm>
#include <atomic>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <new>
#include <vector>

static std::atomic<uint64_t> g_allocations{0};
void* operator new(std::size_t n) {
    if (void* p=std::malloc(n ? n : 1)) {
        g_allocations.fetch_add(1, std::memory_order_relaxed);
        return p;
    }
    throw std::bad_alloc();
}
void operator delete(void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t) noexcept { std::free(p); }

static bool Check(bool yes, const char* name) {
    std::cout << (yes ? "PASS: " : "FAIL: ") << name << '\n';
    return yes;
}

static bool RenderBox(uint32_t rate, const std::filesystem::path& rom,
                      bool chunks, std::vector<int16_t>& pcm,
                      uint32_t& latency, uint64_t& heapNews) {
    Synth synth(rate);
    auto& core = synth.Core();
    core.SetChipRamKb(512);
    std::string error;
    if (!core.UseBox86Chip(rom.string(), error)) {
        std::cerr << "chip initialization failed: " << error << '\n';
        return false;
    }
    core.SetDriver(Awe32::Driver::Win95);
    core.PowerOnInit(); // Feed the real 86Box chip the driver init arrays.
    latency = core.ChipLatencyFrames();

    // No copyrighted ROM contents. Put the original fallback sine oscillator
    // in chip DRAM (BuildDefaultWaveform built it in the native model DRAM).
    int16_t* chip = core.ChipRam();
    if (!chip || core.ChipRamWords() < 72 || core.DramSize() < 72) {
        std::cerr << "missing chip DRAM for synthetic oscillator" << '\n';
        return false;
    }
    std::copy_n(core.DramData(), 72, chip);
    synth.NoteOn(0, 69, 120);
    const uint64_t before = g_allocations.load(std::memory_order_relaxed);

    const uint32_t total = static_cast<uint32_t>(pcm.size()/2);
    if (!chunks) {
        synth.RenderBlock(pcm.data(), total);
    } else {
        constexpr uint32_t sizes[] = {1,2,11,47,3,127,5,512,19,71};
        uint32_t i=0, off=0;
        while (off < total) {
            const uint32_t n = std::min(sizes[i++%10],total-off);
            synth.RenderBlock(pcm.data()+2*off,n);
            off+=n;
        }
    }
    heapNews = g_allocations.load(std::memory_order_relaxed)-before;
    return true;
}

int main() {
    namespace fs = std::filesystem;
    const auto rom = fs::temp_directory_path()/"125A_AWE32_box_rate_probe.raw";
    struct Cleanup {
        fs::path path;
        ~Cleanup(){std::error_code ec;fs::remove(path,ec);}
    } cleanup{rom};
    {
        std::ofstream file(rom, std::ios::binary|std::ios::trunc);
        std::vector<char> zeros(1048576,0);
        file.write(zeros.data(),static_cast<std::streamsize>(zeros.size()));
        if (!file.good()) return 2;
    }
    bool ok=true;
    for (uint32_t rate : {44100u,48000u}) {
        constexpr uint32_t count=4096;
        std::vector<int16_t> whole(count*2,0), segmented(count*2,0);
        uint32_t lat0=0,lat1=0;
        uint64_t alloc0=999,alloc1=999;
        ok &= Check(RenderBox(rate,rom,false,whole,lat0,alloc0),
                    "initialize and render 86Box synthetic wave");
        ok &= Check(RenderBox(rate,rom,true,segmented,lat1,alloc1),
                    "render 86Box in irregular host blocks");
        ok &= Check(whole==segmented,"86Box output is invariant under host block splits");
        ok &= Check(alloc0==0 && alloc1==0,"86Box RenderBlock has zero heap allocations");
        const uint32_t latencyExpected=(uint64_t{980}*rate+44099)/44100;
        ok &= Check(lat0==latencyExpected && lat1==latencyExpected,
                    "86Box reports conservative native-to-host FIFO latency");
        const uint32_t zeroFrames=(lat0>2) ? (lat0-2):0;
        ok &= Check(std::all_of(whole.begin(),whole.begin()+2*zeroFrames,
                               [](int16_t x){return x==0;}),
                    "86Box FIFO initially emits silence through expected delay");
        ok &= Check(std::any_of(whole.begin()+2*lat0,whole.end(),
                               [](int16_t x){return x!=0;}),
                    "post-FIFO synthetic EMU8000 tone becomes audible");
    }
    std::cout << (ok ? "86BOX RATE/FIFO CHECKS PASS" : "86BOX RATE/FIFO CHECKS FAIL") << '\n';
    std::cout << "NOT RUN: reference-hardware sound parity or VST3 latency host integration" << '\n';
    return ok ? 0 : 1;
}
