#include "IbkBank.h"
#include <algorithm>
#include <fstream>
#include <cstdio>

namespace AWE125 {

// Each 11-byte record is authored for this project using the published
// YMF262 2-operator register layout (20/40/60/80/E0/C0). No Creative,
// game, Schism or DMXOPL preset bytes are reproduced here. The 16
// timbral families each have eight independently parameterized variations.
// This is an intentionally modest 125A fallback bank, not the original GM
// or Creative AWE32 FM instrument bank.
namespace {
using Patch = std::array<uint8_t,11>;
constexpr std::array<Patch,16> kFamilies{{
    {{0x01,0x01,0x20,0x03,0xf4,0xf5,0x55,0x34,0x00,0x00,0x02}}, // keyed
    {{0x02,0x01,0x19,0x05,0xe4,0xf4,0x45,0x24,0x00,0x00,0x02}}, // struck
    {{0x05,0x01,0x28,0x04,0xf6,0xd3,0x47,0x44,0x00,0x00,0x04}}, // mallet
    {{0x03,0x02,0x12,0x09,0xe6,0xc5,0x73,0x63,0x00,0x00,0x06}}, // reed
    {{0x01,0x01,0x26,0x02,0xf1,0xd4,0x34,0x34,0x00,0x00,0x03}}, // organ
    {{0x04,0x02,0x30,0x04,0xf3,0xb2,0x65,0x72,0x01,0x00,0x04}}, // pluck
    {{0x06,0x01,0x11,0x03,0xe4,0xe4,0x46,0x36,0x00,0x00,0x02}}, // string
    {{0x02,0x02,0x22,0x05,0xb4,0xc6,0x54,0x43,0x01,0x00,0x06}}, // brass
    {{0x05,0x01,0x0c,0x02,0xd3,0xe5,0x44,0x34,0x00,0x00,0x04}}, // bell
    {{0x09,0x01,0x22,0x05,0xf7,0xf4,0x23,0x34,0x03,0x00,0x06}}, // glass
    {{0x02,0x01,0x14,0x03,0xa3,0xe3,0x55,0x35,0x02,0x01,0x03}}, // pad
    {{0x01,0x02,0x23,0x04,0xe5,0xe5,0x45,0x45,0x00,0x02,0x07}}, // synth
    {{0x0a,0x01,0x34,0x05,0xf5,0xf3,0x43,0x43,0x02,0x02,0x04}}, // percussive
    {{0x07,0x01,0x18,0x06,0xd7,0xf6,0x65,0x43,0x02,0x02,0x04}}, // metallic
    {{0x03,0x01,0x30,0x02,0xf3,0xe4,0x54,0x34,0x00,0x00,0x00}}, // bass
    {{0x0b,0x02,0x17,0x07,0xe7,0xb5,0x37,0x45,0x03,0x01,0x06}}  // fx
}};
void Name(IbkBank::Instrument& patch,const char* prefix,unsigned n) {
    std::snprintf(patch.name.data(),patch.name.size(),"%s%03u",prefix,n);
}
// Actual YMF262 percussion type values: 6=BD 7=SD 8=TT 9=CY 10=HH.
uint8_t HardwareDrumFor(uint8_t note) {
    switch(note) {
    case 35:case 36: return 6;
    case 37:case 38:case 39:case 40: return 7;
    case 41:case 43:case 45:case 47:case 48:case 50:case 60:
    case 61:case 62:case 63:case 64:case 65:case 66: return 8;
    case 42:case 44:case 46:case 54:case 69:case 70:
    case 71:case 72:case 73:case 74:case 75:case 76:case 77:
    case 78:case 79:case 80:case 81: return 10;
    default: return note>=35&&note<=81?9:0;
    }
}
} // namespace

IbkBank IbkBank::BuiltInMelodic() {
    IbkBank b;
    for(size_t i=0;i<kProgramCount;++i) {
        auto& dest=b.instruments_[i];
        const auto& base=kFamilies[i/8];
        std::copy(base.begin(),base.end(),dest.registers.begin());
        const uint8_t variant=static_cast<uint8_t>(i%8);
        // Modulator total level, attacks, feedback and wave shape are OPL
        // register values; the carrier is kept audible for all 128 entries.
        dest.registers[2]=static_cast<uint8_t>(
            (dest.registers[2]&0xc0)|std::min(63,int(dest.registers[2]&0x3f)+int(variant)*2));
        dest.registers[4]=static_cast<uint8_t>(
            (dest.registers[4]&0xf0)|((dest.registers[4]+variant)%15+1));
        dest.registers[8]=static_cast<uint8_t>((dest.registers[8]+variant)%8);
        dest.registers[10]=static_cast<uint8_t>((dest.registers[10]&8)|
            ((dest.registers[10]+variant)%8));
        Name(dest,"FM",static_cast<unsigned>(i));
    }
    b.valid_=true;
    return b;
}

IbkBank IbkBank::BuiltInPercussion() {
    IbkBank b;
    for(size_t i=0;i<kProgramCount;++i) {
        auto& dest=b.instruments_[i];
        const uint8_t type=HardwareDrumFor(static_cast<uint8_t>(i));
        if(type==0)continue; // unsupported GM drum notes remain silent
        const auto& base=kFamilies[type==6?14:type==7?12:type==8?5:type==9?13:9];
        std::copy(base.begin(),base.end(),dest.registers.begin());
        dest.registers[11]=type;
        // Physical OPL3 rhythm has only five percussion oscillator paths.
        // Their pitches are deliberately fixed, not invented GM samples.
        dest.registers[13]=type==6?48:type==7?67:type==8?53:type==9?82:91;
        Name(dest,"DR",static_cast<unsigned>(i));
    }
    b.valid_=true;
    return b;
}

bool IbkBank::Parse(std::span<const uint8_t> bytes,std::string& error) {
    if(bytes.size()!=kFileBytes) {
        error="IBK: expected exactly 3204 bytes";return false;
    }
    if(bytes[0]!='I'||bytes[1]!='B'||bytes[2]!='K'||bytes[3]!=0x1a) {
        error="IBK: invalid Creative Sound Blaster bank signature";return false;
    }
    // Commit all 128 records atomically only after validating the entire input.
    std::array<Instrument,kProgramCount> candidate{};
    for(size_t i=0;i<kProgramCount;++i) {
        const size_t p=4+i*16,n=4+128*16+i*9;
        std::copy_n(bytes.data()+p,16,candidate[i].registers.data());
        for(size_t j=0;j<9;++j)
            candidate[i].name[j]=static_cast<char>(bytes[n+j]);
        candidate[i].name[9]='\0';
    }
    instruments_=std::move(candidate);
    valid_=true;
    error.clear();
    return true;
}
bool IbkBank::Load(const std::string& path,std::string& error) {
    // Called only on VST3 activation, never on the realtime callback.
    std::ifstream f(path,std::ios::binary|std::ios::ate);
    if(!f.is_open()) {error="IBK: cannot open FM bank";return false;}
    const auto sz=f.tellg();
    if(sz!=static_cast<std::streamoff>(kFileBytes)) {
        error="IBK: invalid file size (expected 3204 bytes)";return false;
    }
    f.seekg(0,std::ios::beg);
    std::array<uint8_t,kFileBytes> bytes{};
    if(!f.read(reinterpret_cast<char*>(bytes.data()),bytes.size())) {
        error="IBK: unable to read entire FM bank";return false;
    }
    return Parse(bytes,error);
}
}
