#include "Synth.h"
#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <new>
#include <vector>

static std::atomic<uint64_t> g_news{0};
void* operator new(std::size_t size) {
    if (void* p = std::malloc(size ? size : 1)) {
        g_news.fetch_add(1, std::memory_order_relaxed);
        return p;
    }
    throw std::bad_alloc();
}
void operator delete(void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t) noexcept { std::free(p); }

static bool Check(bool value, const char* name) {
    std::cout << (value ? "PASS: " : "FAIL: ") << name << '\n';
    return value;
}

static bool Render(uint32_t rate, bool partitioned, std::vector<int16_t>& pcm,
                   uint64_t& heapNews) {
    // Control thread: all memory, oscillator, effect and bank preparations.
    Synth instrument(rate);
    instrument.Core().SetDriver(Awe32::Driver::Win95);
    instrument.NoteOn(0, 69, 120);
    const uint64_t before = g_news.load(std::memory_order_relaxed);
    const uint32_t total = static_cast<uint32_t>(pcm.size() / 2);
    if (!partitioned) {
        instrument.RenderBlock(pcm.data(), total);
    } else {
        constexpr uint32_t chunks[] = {1, 3, 7, 64, 5, 127, 31, 512, 2, 19};
        uint32_t off = 0, i = 0;
        while (off < total) {
            const uint32_t n = std::min(chunks[i++ % 10], total - off);
            instrument.RenderBlock(pcm.data() + 2 * off, n);
            off += n;
        }
    }
    heapNews = g_news.load(std::memory_order_relaxed) - before;
    return true;
}

int main() {
    constexpr uint32_t kFrames = 4096;
    bool ok = true;
    for (const uint32_t rate : {44100u, 48000u, 96000u}) {
        std::vector<int16_t> whole(2u * kFrames, 0);
        std::vector<int16_t> sliced(2u * kFrames, 0);
        uint64_t a = ~uint64_t{0}, b = ~uint64_t{0};
        Render(rate, false, whole, a);
        Render(rate, true, sliced, b);
        ok &= Check(a == 0 && b == 0, "zero heap allocations in RenderBlock at all tested rates");
        ok &= Check(whole == sliced, "PCM output invariant under irregular host block splits");
        ok &= Check(std::any_of(whole.begin(), whole.end(), [](int16_t x) {return x != 0;}),
                    "fallback MIDI note produces audible native/SRC PCM");
    }

    // Latency conversion is for the 980-sample 86Box FIFO. Without a
    // selected 86Box chip, native/48k/96k instances must report zero.
    for (const uint32_t rate : {44100u, 48000u, 96000u}) {
        Synth instrument(rate);
        ok &= Check(instrument.Core().ChipLatencyFrames() == 0,
                    "native synthetic core reports no 86Box FIFO latency");
    }
    std::cout << (ok ? "NATIVE AUDIO RATE TESTS PASS" : "NATIVE AUDIO RATE TESTS FAIL") << '\n';
    std::cout << "NOT RUN: authentic ROM tone parity, VST3 host latency reporting, Studio One" << '\n';
    return ok ? 0 : 1;
}
