#include "opl3.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>

// Tests the actual original Yamaha OPL3 FM core. This is NOT a MIDI player,
// CQM emulation or a DAW/VST3 test.
namespace {
bool expect(bool good, const char* name)
{
    std::cout << (good ? "PASS: " : "FAIL: ") << name << '\n';
    return good;
}

void patch(opl3_chip& chip)
{
    OPL3_Reset(&chip, 44100);
    OPL3_WriteReg(&chip, 0x105, 0x01); // OPL3 mode
    // Two-operator FM patch, voice 0 (operators 0 and 3).
    OPL3_WriteReg(&chip, 0x020, 0x01);
    OPL3_WriteReg(&chip, 0x023, 0x01);
    OPL3_WriteReg(&chip, 0x040, 0x20);
    OPL3_WriteReg(&chip, 0x043, 0x00);
    OPL3_WriteReg(&chip, 0x060, 0xF4);
    OPL3_WriteReg(&chip, 0x063, 0xF4);
    OPL3_WriteReg(&chip, 0x080, 0x24);
    OPL3_WriteReg(&chip, 0x083, 0x24);
    OPL3_WriteReg(&chip, 0x0C0, 0x32); // feedback, L+R
    OPL3_WriteReg(&chip, 0x0A0, 0x98); // FNUM low
    OPL3_WriteReg(&chip, 0x0B0, 0x31); // key on, block 4, FNUM high
}
} // namespace

int main()
{
    bool ok = true;
    // Reset/unkeyed chip must remain silent.
    opl3_chip silent{};
    OPL3_Reset(&silent, 44100);
    std::array<int16_t, 2048> empty{};
    OPL3_GenerateStream(&silent, empty.data(), 1024);
    ok &= expect(std::all_of(empty.begin(), empty.end(),
                         [](int16_t s){ return s == 0; }),
                 "unkeyed chip renders digital silence");

    opl3_chip continuous{}, split{};
    patch(continuous);
    patch(split);
    constexpr size_t frames = 4096;
    std::array<int16_t, frames * 2> audio{}, partitioned{};
    OPL3_GenerateStream(&continuous, audio.data(), frames);
    OPL3_GenerateStream(&split, partitioned.data(), 137);
    OPL3_GenerateStream(&split, partitioned.data() + 137 * 2, frames - 137);
    ok &= expect(audio == partitioned,
                 "register-driven FM output is exactly block-partition invariant");

    size_t audibleL = 0, audibleR = 0;
    for (size_t i = 0; i < frames; ++i) {
        audibleL += (audio[i * 2] != 0);
        audibleR += (audio[i * 2 + 1] != 0);
    }
    ok &= expect(audibleL > 100 && audibleR > 100,
                 "real FM register patch generates audible stereo PCM");

    // Voice/programming independence: a second reset instance is unaffected.
    std::array<int16_t, 512> stillSilent{};
    OPL3_GenerateStream(&silent, stillSilent.data(), 256);
    ok &= expect(std::all_of(stillSilent.begin(), stillSilent.end(),
                         [](int16_t s){ return s == 0; }),
                 "two chip instances retain independent audio state");
    std::cout << "NOT RUN: Creative CQM, hardware parity, MIDI patch translator, Studio One\n";
    return ok ? 0 : 1;
}
