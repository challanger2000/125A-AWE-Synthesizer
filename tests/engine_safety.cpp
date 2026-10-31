#include "Emu8000Box.h"

#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace fs = std::filesystem;

static bool WriteFile(const fs::path& path, size_t bytes)
{
    std::vector<char> data(bytes, 0);
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    output.write(data.data(), static_cast<std::streamsize>(data.size()));
    return output.good();
}

static bool Check(bool expression, const char* name)
{
    if (!expression) std::cerr << "FAIL: " << name << '\n';
    else std::cout << "PASS: " << name << '\n';
    return expression;
}

int main()
{
    const fs::path rom = fs::temp_directory_path() / "125A_AWE32_synthetic_probe.raw";
    struct Cleanup {
        fs::path path;
        ~Cleanup() { std::error_code ec; fs::remove(path, ec); }
    } cleanup{rom};
    std::string error;
    bool okay = true;

    {
        Emu8000Box empty;
        okay &= Check(!empty.Init("125A_ROM_intentionally_missing.raw", 0x620, 512, error),
                      "missing ROM rejects without process termination");
        okay &= Check(!empty.Ready(), "missing ROM remains uninitialized");
        std::int32_t l = 99, r = 99;
        empty.RenderFrame(l, r);
        okay &= Check(l == 0 && r == 0, "uninitialized chip renders silence");
    }

    if (!WriteFile(rom, 128)) return 2;
    {
        Emu8000Box truncated;
        error.clear();
        okay &= Check(!truncated.Init(rom.string(), 0x620, 512, error),
                      "short ROM rejects safely");
        okay &= Check(!truncated.Ready(), "short ROM doesn't publish ready state");
    }
    if (!WriteFile(rom, 1048576)) return 2;
    {
        Emu8000Box invalidCapacity;
        error.clear();
        okay &= Check(!invalidCapacity.Init(rom.string(), 0x620, -1, error),
                      "negative RAM size is rejected before allocation");
        okay &= Check(!invalidCapacity.Init(rom.string(), 0x620, 28673, error),
                      "oversized RAM is rejected before allocation");
    }

    Emu8000Box first;
    Emu8000Box second;
    error.clear();
    okay &= Check(first.Init(rom.string(), 0x620, 512, error), "synthetic ROM first instance initialization");
    if (!first.Ready()) { std::cerr << error << '\n'; return 1; }
    error.clear();
    okay &= Check(second.Init(rom.string(), 0x620, 512, error), "synthetic ROM second instance initialization");
    if (!second.Ready()) { std::cerr << error << '\n'; return 1; }
    okay &= Check(first.Ram() != second.Ram(), "isolated per-instance DRAM");
    okay &= Check(first.RamWords() == second.RamWords() && first.RamWords() > 0,
                  "both chip RAM regions valid");

    // Both engines must be able to advance independently, interleaved.
    for (int n = 0; n < 1960; ++n)
    {
        std::int32_t l = 7, r = 8;
        first.RenderFrame(l, r);
        if (n < 980 && (l != 0 || r != 0)) okay &= Check(false, "initial FIFO latency silence");
        second.RenderFrame(l, r);
        if (n < 980 && (l != 0 || r != 0)) okay &= Check(false, "second FIFO latency silence");
    }
    okay &= Check(first.Ready() && second.Ready(), "interleaved instance render survives");
    
    // Queue overflow must never resize or crash. This is a deliberate
    // pathological MIDI burst; the adapter then fails closed to silence.
    for (int i = 0; i < 32769; ++i)
        first.PortWrite(0x620, static_cast<uint16_t>(i));
    std::int32_t l = 123, r = 123;
    first.RenderFrame(l, r);
    okay &= Check(l == 0 && r == 0, "overflow produces deterministic safe silence");
    okay &= Check(first.PortRead(0x620) == 0xFFFF, "overflow returns safe register value");
    for (int i = 0; i < 1960; ++i) first.RenderFrame(l, r);
    okay &= Check(l == 0 && r == 0, "post-overflow remains fail-closed");

    std::cout << (okay ? "ENGINE SAFETY PROBES PASS" : "ENGINE SAFETY PROBES FAIL") << '\n';
    std::cout << "NOT RUN: original hardware parity, SF2/voice allocation, VST3, Studio One, realtime allocation hook" << '\n';
    return okay ? 0 : 1;
}
