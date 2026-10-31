#pragma once
#include <array>
#include <cstdint>
#include <cstddef>
#include <span>
#include <string>

// Historical Creative Sound Blaster melodic IBK bank, exactly 3204 bytes:
// "IBK\x1A", 128 x 16-byte OPL2-compatible register patches,
// 128 x 9-byte instrument names. No Creative data is bundled.
// Byte layout follows the original IBK format documented by
// OPL3BankEditor (Wohlstand); no third-party parser code is copied.
namespace AWE125 {
class IbkBank final {
public:
    static constexpr size_t kProgramCount=128;
    static constexpr size_t kFileBytes=4+128*16+128*9;
    struct Instrument {
        std::array<uint8_t,16> registers{};
        std::array<char,10> name{};
    };
    bool Parse(std::span<const uint8_t> bytes,std::string& error);
    bool Load(const std::string& path,std::string& error);
    const Instrument& At(uint8_t program) const {return instruments_[program];}
    bool Valid() const {return valid_;}
private:
    std::array<Instrument,kProgramCount> instruments_{};
    bool valid_=false;
};
}
