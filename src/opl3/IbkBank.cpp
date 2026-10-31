#include "IbkBank.h"
#include <algorithm>
#include <fstream>

namespace AWE125 {
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
