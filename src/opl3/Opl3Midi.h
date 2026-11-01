#pragma once
#include "opl3.h"
#include "cqm.h"
#include "IbkBank.h"
#include <array>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <optional>
#include <string>
#include <vector>

// Actual Yamaha YMF262 register engine, separate from EMU8000 and from
// Creative CQM. The temporary 2-operator voice is NOT a Creative GM bank.
// Only constructor/destructor allocate. Note/render are bounded realtime work.
namespace AWE125 {
class Opl3Midi final {
public:
    explicit Opl3Midi(uint32_t sampleRate,uint32_t latencyFrames=0,bool cqmBackend=false);
    ~Opl3Midi();
    Opl3Midi(const Opl3Midi&)=delete;
    Opl3Midi& operator=(const Opl3Midi&)=delete;
    // Load a genuine Sound Blaster 128-patch melodic IBK bank before activation.
    // Failure leaves the previous bank intact; no audio-thread file operations.
    bool LoadMelodicIbk(const std::string& path,std::string& error);
    // Factory bank is enabled by the VST3, not by unit-test adapter defaults.
    // All allocations and preset generation happen outside the audio callback.
    void UseBuiltInMelodic();
    void UseBuiltInPercussion(); // Yamaha only. CQM rhythm remains disabled.
    void ProgramChange(uint8_t channel,uint8_t program);
    // User-supplied percussion IBK. 0xBD rhythm mode uses real YMF262
    // channel 6/7/8 operators, reducing melodic polyphony from 18 to 15.
    // Load at activation only; a failed bank does not replace the old one.
    bool LoadPercussionIbk(const std::string& path,std::string& error);
    bool HasPercussionIbk() const {return drumBank_.has_value();}
    uint8_t RhythmRegister() const {return rhythmRegister_;}
    static constexpr uint32_t kRhythmSounds=5;
    bool HasMelodicIbk() const {return bank_.has_value();}
    void NoteOn(uint8_t channel,uint8_t note,uint8_t velocity);
    void NoteOff(uint8_t channel,uint8_t note);
    void AllNotesOff();
    void ControlChange(uint8_t channel,uint8_t cc,uint8_t value);
    void PitchBend(uint8_t channel,int16_t value);
    void RenderBlock(int16_t* interleaved,uint32_t frames);
    uint32_t PressedVoices() const;
    static constexpr size_t kVoices=18;
    bool UsesCqmBackend() const {return cqm_!=nullptr;}

private:
    struct Voice {
        bool allocated=false, pressed=false, held=false;
        uint8_t channel=0,note=0,pitchNote=0,velocity=0,block=0;
        uint8_t carrierKslTl=0;
        uint16_t fnum=0;
        uint64_t age=0;
    };
    struct Channel {
        bool sustain=false;
        int16_t bend=0;
        uint8_t volume=100,expression=127,program=0;
    };
    std::unique_ptr<opl3_chip> chip_;
    std::unique_ptr<cqm_t> cqm_; // separate Creative quadratic modulation chipset
    std::optional<IbkBank> bank_{};
    std::optional<IbkBank> drumBank_{};
    struct Drum {bool pressed=false;uint8_t note=0;};
    std::array<Drum,kRhythmSounds> drums_{};
    uint8_t rhythmRegister_=0; // 0x20 mode | hardware BD/SD/TT/CY/HH keys
    void DrumNoteOn(uint8_t note,uint8_t velocity);
    void DrumNoteOff(uint8_t note);
    void AllDrumsOff();
    void SetDrumPitch(uint8_t hwChannel,uint8_t note);
    std::array<Voice,kVoices> voices_{};
    std::array<Channel,16> channels_{};
    std::array<uint8_t,128> velocityAtten_{};
    std::vector<int16_t> delayed_{};
    uint32_t latencyFrames_=0,delayIndex_=0;
    uint64_t age_=0;
    void Write(uint16_t reg,uint8_t value);
    void KeyOff(size_t voice);
    void StartVoice(size_t voice,uint8_t channel,uint8_t note,uint8_t velocity);
    void UpdatePitch(size_t voice);
    void UpdateLevel(size_t voice);
};
}
