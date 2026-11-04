#include "PresetBrowserModel.h"
#include <algorithm>
#include <iostream>
#include <vector>
using AWE125::PresetBrowserModel;
using AWE125::PresetEntry;
static bool test(bool ok,const char* label) {
    std::cout<<(ok?"PASS: ":"FAIL: ")<<label<<"\n";
    return ok;
}
int main() {
    bool ok=true;
    // Mimics a real SF2 with absent program 63, plus GM and ROM-only banks.
    const std::vector<PresetEntry> entries{
        {0,7,"TX81Z Lately Bass",false},
        {0,3,"Grunge Bass",false},
        {0,2,"Bass",false},
        {0,7,"TX81Z Lately Bass",false}, // duplicate defensive normalization
        {128,0,"Drums",true},
        {16382,0,"ROM Drumkit",true},
        {16383,0,"ROM Piano",false},
        {16383,127,"ROM Gunshot",false}
    };
    auto b0=PresetBrowserModel::Programs(entries,0);
    ok&=test(b0==std::vector<uint8_t>({2,3,7}),
        "program combo lists actual noncontiguous presets, sorted and unique");
    ok&=test(PresetBrowserModel::ChooseExistingProgram(entries,0,7)==7,
        "change bank preserves current program when it exists");
    ok&=test(PresetBrowserModel::ChooseExistingProgram(entries,0,63)==2,
        "missing program falls back to first existing bank program");
    ok&=test(PresetBrowserModel::Programs(entries,16383)==
             std::vector<uint8_t>({0,127}),
        "GM ROM explicit virtual bank is addressable");
    ok&=test(PresetBrowserModel::Programs(entries,16382)==
             std::vector<uint8_t>({0}),
        "GM ROM drums explicit virtual bank is addressable");
    ok&=test(PresetBrowserModel::Programs(entries,128)==
             std::vector<uint8_t>({0}),
        "SoundFont drum bank 128 remains addressable");
    ok&=test(PresetBrowserModel::Programs(entries,90).empty(),
        "absent banks present no false selectable entries");
    ok&=test(PresetBrowserModel::ChooseExistingProgram(entries,90,77)==77,
        "missing bank never fabricates a program; UI suppresses edit");
    ok&=test(PresetBrowserModel::ChooseExistingProgram(entries,16383,127)==127,
        "bank switch can preserve last GM ROM program");
    std::cout<<(ok?"P117_PRESET_SELECT_PASS":"P117_PRESET_SELECT_FAIL")<<"\n";
    return ok?0:1;
}
