// P25: Offline, actual 86Box EMU8000 audio capture of user-selected SF2.
// Reads paths from the same assets.cfg as the VST3; no ROM/SF2 is bundled.
#include "Synth.h"
#include "AssetConfig.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace {
void Put16(std::ofstream& f, uint16_t v) {
    const char b[2] = {static_cast<char>(v), static_cast<char>(v >> 8)};
    f.write(b, 2);
}
void Put32(std::ofstream& f, uint32_t v) {
    Put16(f, static_cast<uint16_t>(v));
    Put16(f, static_cast<uint16_t>(v >> 16));
}
bool SaveWav(const std::filesystem::path& path,
             const std::vector<int16_t>& stereo, uint32_t rate) {
    if (stereo.size() > (UINT32_MAX - 36u) / 2u) return false;
    std::ofstream f(path, std::ios::binary | std::ios::trunc);
    if (!f) return false;
    const auto bytes = static_cast<uint32_t>(stereo.size() * sizeof(int16_t));
    f.write("RIFF", 4); Put32(f, 36u + bytes); f.write("WAVE", 4);
    f.write("fmt ", 4); Put32(f, 16); Put16(f, 1); Put16(f, 2);
    Put32(f, rate); Put32(f, rate * 4); Put16(f, 4); Put16(f, 16);
    f.write("data", 4); Put32(f, bytes);
    for (int16_t word : stereo) Put16(f, static_cast<uint16_t>(word));
    return f.good();
}
void Help() {
    std::cerr << "Usage: awe32_sf2_timbre_probe [--rom path] [--sf2 path]"
              << " [--out folder] [--note 0..127] [--velocity 1..127]" 
              << " [--driver win95|sdk] [--port-trace yes|no]\n"
              << "Paths default to %APPDATA%/125A/AWE Synthesizer/assets.cfg."
              << " No source sound files are copied into the repository.\n";
}
bool Decimal(const std::string& s, int low, int high, int& dest) {
    try {
        size_t end = 0;
        const int v = std::stoi(s, &end);
        if (end != s.size() || v < low || v > high) return false;
        dest = v;
        return true;
    } catch (...) { return false; }
}
}

int main(int argc, char** argv) {
    namespace fs = std::filesystem;
    AWE125::AssetConfig::Paths paths;
    if (!AWE125::AssetConfig::Load(paths)) {
        std::cerr << "WARNING: assets.cfg could not be parsed; explicit paths required.\n";
        paths = {};
    }
    fs::path output = fs::current_path() / "125A-SF2-Timbre-Probe";
    int note = 48, velocity = 100;
    Awe32::Driver driver = Awe32::Driver::Win95;
    bool tracePorts = false;
    for (int i = 1; i < argc; i += 2) {
        if (i + 1 >= argc) { Help(); return 2; }
        const std::string flag(argv[i]), value(argv[i + 1]);
        if      (flag == "--rom") paths.rom = value;
        else if (flag == "--sf2") paths.sf2 = value;
        else if (flag == "--out") output = fs::path(value);
        else if (flag == "--note" && Decimal(value, 0, 127, note)) {}
        else if (flag == "--velocity" && Decimal(value, 1, 127, velocity)) {}
        else if (flag == "--driver" && value == "win95")
            driver = Awe32::Driver::Win95;
        else if (flag == "--driver" && value == "sdk")
            driver = Awe32::Driver::Sdk;
        else if (flag == "--port-trace" && value == "yes") tracePorts = true;
        else if (flag == "--port-trace" && value == "no") tracePorts = false;
        else { Help(); return 2; }
    }
    if (paths.rom.empty() || paths.sf2.empty()) {
        std::cerr << "ERROR: ROM and SF2 must be configured. No fallback backend.\n";
        Help(); return 2;
    }

    std::error_code fsError;
    fs::create_directories(output, fsError);
    if (fsError) {
        std::cerr << "ERROR: output directory: " << fsError.message() << '\n';
        return 3;
    }
    std::cout << "125A authentic EMU8000 audio probe | 44100 Hz / stereo PCM16"
              << " | MIDI note " << note << " velocity " << velocity
              << " | driver " << (driver==Awe32::Driver::Sdk ? "sdk" : "win95")
              << (tracePorts ? " | trace enabled" : "") << '\n';
    bool ok = true;
    for (const int program : {0, 7}) {
        Synth synth(44100);
        synth.Core().SetDriver(driver);
        std::string error;
        if (!synth.Core().UseBox86Chip(paths.rom, error) ||
            synth.Core().ChipVariant() != Emu8000Core::Chip::Box86) {
            std::cerr << "ERROR: wave ROM / 86Box activation FAILED: " << error
                      << "; no alternate synthesis rendered.\n";
            return 4;
        }
        synth.Core().PowerOnInit();
        error.clear();
        if (!synth.LoadBank(paths.sf2, error)) {
            std::cerr << "ERROR: SoundFont load FAILED: " << error << '\n';
            return 5;
        }

        const auto regions = synth.BankAt(synth.BankCount() - 1).Select(
            0, program, note, velocity);
        const size_t expected = (program == 0) ? 2u : 4u;
        std::cout << "Program " << program << ": " << regions.size()
                  << " SF2 layers (expected for Synth 512 Bank.sf2: "
                  << expected << ")\n";
        if (regions.size() != expected) {
            std::cerr << "WARNING: unexpected layer count. Is the selected SF2"
                      << " actually Synth 512 Bank.sf2?\n";
            ok = false;
        }
        for (size_t i = 0; i < regions.size(); ++i) {
            const auto& region = regions[i];
            const auto& gen = region.gen;
            std::cout << "  voice " << i << " sample="
                      << (region.sample ? region.sample->name : "[null]")
                      << " coarseTune=" << gen.Get(SoundFont::Gen::CoarseTune, 0)
                      << " fineTune=" << gen.Get(SoundFont::Gen::FineTune, 0)
                      << " filterQ=" << gen.Get(SoundFont::Gen::InitialFilterQ, 0)
                      << " sustainVol=" << gen.Get(SoundFont::Gen::SustainVolEnv, 0)
                      << '\n';
        }
        const std::string id = (program == 0)
            ? "000_Grungy_Ramp_Bass" : "007_TX81Z_Lately_Bass";
        const fs::path notes = output / (id + "_voices.csv");
        if (!synth.OpenNoteDump(notes.string())) {
            std::cerr << "ERROR: cannot create note dump " << notes << '\n';
            return 6;
        }
        // Capture only MIDI->EMU8000 port activity after initialization
        // and bank loading. This is the portion comparable to the Creative
        // SDK (or Windows VxD) note-on from a separately instrumented VM.
        // The trace deliberately does NOT include chip initialization or
        // DRAM uploads; the original SDK may upload the bank differently.
        const fs::path portTrace = output / (id +
            (driver==Awe32::Driver::Sdk ? "_sdk" : "_win95") + "_noteon.trace");
        if (tracePorts && !synth.Core().OpenTrace(portTrace.string().c_str())) {
            std::cerr << "ERROR: cannot create port-write trace " << portTrace << '\n';
            return 9;
        }
        synth.ProgramChange(0, static_cast<uint8_t>(program));
        synth.NoteOn(0, static_cast<uint8_t>(note),
                     static_cast<uint8_t>(velocity));
        constexpr uint32_t frames = 88200; // Hold for 2 s, as in the reference.
        std::vector<int16_t> samples(size_t{frames} * 2, 0);
        synth.RenderBlock(samples.data(), frames);
        synth.CloseNoteDump();
        if (tracePorts) {
            synth.Core().CloseTrace();
            std::cout << "  port trace: " << portTrace << '\n';
        }
        const bool audible = std::any_of(samples.begin(), samples.end(),
                                        [](int16_t x) { return x != 0; });
        double sum = 0.;
        int peak = 0;
        for (auto s : samples) {
            const int value = static_cast<int>(s);
            peak = std::max(peak, std::abs(value));
            sum += static_cast<double>(value) * value;
        }
        const double rms = std::sqrt(sum / samples.size()) / 32768.;
        std::cout << "  backend=86Box; audible=" << audible
                  << " peak=" << peak << "/32768 rms=" << rms
                  << " latency=" << synth.Core().ChipLatencyFrames()
                  << " frames\n";
        const fs::path wav = output / (id + "_EMU8000.wav");
        if (!audible || !SaveWav(wav, samples, 44100)) {
            std::cerr << "ERROR: failed to render " << wav << '\n';
            return 7;
        }
        std::cout << "  output: " << wav << '\n';
    }
    std::cout << (ok ? "PROBE COMPLETE" : "PROBE COMPLETE WITH WARNINGS")
              << " | Audio is NOT claimed to match FluidSynth without"
              << " an actual WAV comparison.\n";
    return ok ? 0 : 8;
}
