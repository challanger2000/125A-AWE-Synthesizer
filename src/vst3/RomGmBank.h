#pragma once
// User-supplied 1MGM/SYNTHGM.SBK; never embed or distribute Creative media.
#include "Synth.h"
#include <array>
#include <filesystem>
#include <string>
namespace AWE125::RomGmBank {
inline constexpr uint16_t kBrowserBank=16383;
inline constexpr uint16_t kBrowserDrums=16382;
inline std::string AdjacentFile(const std::string& romPath) {
    if(romPath.empty())return {};
    try {
        const auto p=std::filesystem::u8path(romPath).parent_path()/"SYNTHGM.SBK";
        std::error_code ec;
        if(!std::filesystem::is_regular_file(p,ec))return {};
        const auto u8=p.u8string();
        return std::string(u8.begin(),u8.end());
    }catch(...) {return {};}
}
inline bool ValidDescriptor(const std::string& path,std::string& error) {
    if(path.empty()){error="SYNTHGM.SBK fehlt";return false;}
    auto bank=SoundFont::Load(path);
    if(!bank.valid){error="GM-ROM: "+bank.errorMessage;return false;}
    if(bank.version!=SoundFont::Version::Sf1 || bank.romName!="1MGM"
       || !bank.sampleData.empty() || bank.presets.size()!=129u) {
        error="Unpassende GM-ROM-Bank (erwartet 1MGM / 129 Presets)";
        return false;
    }
    std::array<bool,128> programs{};
    bool drums=false;
    for(const auto& p:bank.presets) {
        if(p.bank==0 && p.program>=0 && p.program<128)
            programs[static_cast<size_t>(p.program)]=true;
        else if(p.bank==128 && p.program==0)drums=true;
        else {error="GM-ROM mit unerwarteten Presets";return false;}
    }
    for(bool ok:programs)if(!ok){error="GM-ROM: unvollstaendige Instrumente";return false;}
    if(!drums){error="GM-ROM: Standard-Drumkit fehlt";return false;}
    return true;
}
struct Loaded {
    bool gm=false;
    bool sf2=false;
    std::string gmError,sf2Error;
};
inline Loaded LoadBanks(Synth& synth,const std::string& rom,const std::string& sf2) {
    Loaded result;
    const auto gm=AdjacentFile(rom);
    bool gmPrimary=false;
    if(!gm.empty()) {
        if(ValidDescriptor(gm,result.gmError)) {
            if(synth.LoadBank(gm,result.gmError,true,0))gmPrimary=true;
        }
    }
    if(!sf2.empty())
        result.sf2=synth.LoadBank(sf2,result.sf2Error);
    // Real GM bank 0 first, then user SF2 to override, finally virtual
    // browser banks 16383 + 16382. GM samples always address physical ROM.
    if(gmPrimary) {
        std::string error;
        if(synth.LoadBank(gm,error,true,kBrowserBank,kBrowserDrums))
            result.gm=true;
        else result.gmError="GM-ROM-Browser: "+error;
    }
    return result;
}
} // namespace AWE125::RomGmBank
