#pragma once
// P118: VST3 IMidiMapping assigns per-channel, non-UI VST parameters
// to the MIDI events the EMU8000 Synth already understands.
// This is pure metadata: no SDK dependency, allocation, or audio processing.
#include <array>
#include <cstddef>
#include <cstdint>
namespace AWE125::MidiControlMapping {
inline constexpr uint32_t kBase = 2000;
inline constexpr uint32_t kStride = 32;
inline constexpr uint32_t kChannels = 16;
struct Control {
    int number;
    const char* name;
    int resetValue;  // raw 0..127; 128=pitch bend center, special below
};
inline constexpr std::array<Control,17> kControls{{
    {0,"Bank Select MSB",0},
    {1,"Modulation",0},
    {6,"Data Entry MSB",0},
    {7,"Channel Volume",100},
    {10,"Pan",64},
    {11,"Expression",127},
    {32,"Bank Select LSB",0},
    {64,"Sustain",0},
    {91,"Reverb Send",0},
    {93,"Chorus Send",0},
    {100,"RPN LSB",127},
    {101,"RPN MSB",127},
    {120,"All Sounds Off",0},
    {121,"Reset Controllers",0},
    {123,"All Notes Off",0},
    {128,"Channel Pressure",0},
    {129,"Pitch Bend",64}
}};
constexpr int Index(int number) noexcept {
    for(std::size_t i=0;i<kControls.size();++i)
        if(kControls[i].number==number)return static_cast<int>(i);
    return -1;
}
constexpr uint32_t ParamID(uint32_t channel,uint32_t index) noexcept {
    return kBase + channel*kStride + index;
}
struct Decoded {bool valid=false;int channel=0;int number=0;};
constexpr Decoded Decode(uint32_t id) noexcept {
    if(id<kBase || id>=kBase+kChannels*kStride)return {};
    const uint32_t delta=id-kBase;
    const uint32_t channel=delta/kStride,index=delta%kStride;
    if(index>=kControls.size())return {};
    return {true,static_cast<int>(channel),kControls[index].number};
}
constexpr double InitialNormalized(const Control& c) noexcept {
    return c.number==129?0.5:double(c.resetValue)/127.0;
}
constexpr uint8_t Byte(double normalized) noexcept {
    const double x=normalized<0?0:normalized>1?1:normalized;
    return static_cast<uint8_t>(x*127.0+0.5);
}
constexpr int16_t PitchBend(double normalized) noexcept {
    const double x=normalized<0?0:normalized>1?1:normalized;
    const int n=static_cast<int>(x*16383.0+0.5)-8192;
    return static_cast<int16_t>(n);
}
} // namespace AWE125::MidiControlMapping
