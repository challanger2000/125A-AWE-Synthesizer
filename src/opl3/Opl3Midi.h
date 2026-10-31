#pragma once
#include "opl3.h"
#include <array>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <vector>

// Actual Yamaha YMF262 register engine, separate from EMU8000 and from
// Creative CQM. The temporary 2-operator voice is NOT a Creative GM bank.
// Only constructor/destructor allocate. Note/render are bounded realtime work.
namespace AWE125 {
class Opl3Midi final {
public:
    explicit Opl3Midi(uint32_t sampleRate,uint32_t latencyFrames=0);
    ~Opl3Midi();
    Opl3Midi(const Opl3Midi&)=delete;
    Opl3Midi& operator=(const Opl3Midi&)=delete;
    void NoteOn(uint8_t channel,uint8_t note,uint8_t velocity);
    void NoteOff(uint8_t channel,uint8_t note);
    void AllNotesOff();
    void ControlChange(uint8_t channel,uint8_t cc,uint8_t value);
    void PitchBend(uint8_t channel,int16_t value);
    void RenderBlock(int16_t* interleaved,uint32_t frames);
    uint32_t PressedVoices() const;
    static constexpr size_t kVoices=18;

private:
    struct Voice {
        bool allocated=false, pressed=false, held=false;
        uint8_t channel=0,note=0,velocity=0,block=0;
        uint16_t fnum=0;
        uint64_t age=0;
    };
    struct Channel {
        bool sustain=false;
        int16_t bend=0;
        uint8_t volume=100,expression=127;
    };
    std::unique_ptr<opl3_chip> chip_;
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
