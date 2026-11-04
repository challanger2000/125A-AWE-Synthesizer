#pragma once
#include <cstdint>
namespace AWE125::MidiProgramRouting {
inline constexpr std::uint32_t kFirstId=3000;
inline constexpr int kChannels=16;
inline constexpr std::uint32_t kFirstUnitId=1;
inline constexpr std::uint32_t kFirstProgramListId=1;
constexpr std::uint32_t ParamID(unsigned channel) noexcept {
    return kFirstId+channel;
}
constexpr int Channel(std::uint32_t id) noexcept {
    return id>=kFirstId&&id<kFirstId+kChannels
        ?static_cast<int>(id-kFirstId):-1;
}
constexpr std::uint32_t Unit(unsigned channel) noexcept {
    return kFirstUnitId+channel;
}
constexpr std::uint32_t ProgramList(unsigned channel) noexcept {
    return kFirstProgramListId+channel;
}
} // namespace AWE125::MidiProgramRouting
