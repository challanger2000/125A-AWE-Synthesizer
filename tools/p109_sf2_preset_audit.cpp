// P109: audit private SoundFont presets using the exact ROM-backed 86Box EMU8000.
// No user ROM, SoundFont samples or audio are copied into the report.
#include "Synth.h"
#include "AssetConfig.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
namespace {
struct Levels {int peak=0;double rms=0;};
Levels render(Synth& synth,int frames) {
  std::array<int16_t,8192> block{};
  double squares=0;
  int peak=0;
  int produced=0;
  while(produced<frames) {
    int n=std::min(4096,frames-produced);
    synth.RenderBlock(block.data(),static_cast<uint32_t>(n));
    for(int i=0;i<n*2;++i) {
      int s=block[static_cast<size_t>(i)];
      peak=std::max(peak,std::abs(s));
      squares+=double(s)*s;
    }
    produced+=n;
  }
  return {peak,std::sqrt(squares/(double(frames)*2.0))/32768.0};
}
std::string csv(const std::string& s) {
  std::string out="\"";
  for(char c:s){if(c=='"')out+='\"';out+=c;}
  return out+"\"";
}
}
int main(int argc,char** argv) {
  try {
    namespace fs=std::filesystem;
    AWE125::AssetConfig::Paths paths;
    if(!AWE125::AssetConfig::Load(paths))paths={};
    fs::path reportPath="125A-P109-Preset-Audit.csv";
    for(int i=1;i<argc;i+=2) {
      if(i+1>=argc){std::cerr<<"Missing argument value\n";return 2;}
      const std::string key=argv[i],value=argv[i+1];
      if(key=="--rom")paths.rom=value;
      else if(key=="--sf2")paths.sf2=value;
      else if(key=="--out")reportPath=fs::u8path(value);
      else {std::cerr<<"Unknown option\n";return 2;}
    }
    if(paths.rom.empty()||paths.sf2.empty()) {
      std::cerr<<"Original-ROM und SF2 muessen angegeben werden.\n";return 2;
    }
    Synth inventory(44100);
    inventory.Core().SetDriver(Awe32::Driver::Win95);
    std::string error;
    if(!inventory.Core().UseBox86Chip(paths.rom,error) ||
       inventory.Core().ChipVariant()!=Emu8000Core::Chip::Box86)
      throw std::runtime_error("ROM/86Box: "+error);
    inventory.Core().PowerOnInit();
    if(!inventory.LoadBank(paths.sf2,error))
      throw std::runtime_error("SF2: "+error);
    const auto presets=inventory.BankAt(0).presets;
    std::ofstream report(reportPath,std::ios::binary|std::ios::trunc);
    if(!report)throw std::runtime_error("Kann CSV nicht erstellen");
    report<<"Bank,Program,Name,Note,Layers,HoldPeak,HoldRMS,ReleasePeak,ReleaseRMS,Result\n";
    int audible=0,silent=0,releaseOnly=0,noZones=0,quiet=0;
    std::cout<<"P109 SF2 PRESET AUDIO AUDIT (Original-ROM + 86Box)\n";
    std::cout<<"Presets: "<<presets.size()<<"\n";
    for(const auto& preset:presets) {
      if(preset.bank<0||preset.bank>16383||preset.program<0||preset.program>127)
        continue;
      int key=-1,layerCount=0;
      for(int n:{48,60,72,36,84}) {
        auto regions=inventory.BankAt(0).Select(preset.bank,preset.program,n,100);
        if(!regions.empty()){key=n;layerCount=static_cast<int>(regions.size());break;}
      }
      Levels held{},released{};
      std::string verdict="KEINE_ZONE_BEI_V100";
      if(key>=0) {
        // Fresh chip for each instrument: no stale voice or effect state.
        Synth synth(44100);
        synth.Core().SetDriver(Awe32::Driver::Win95);
        error.clear();
        if(!synth.Core().UseBox86Chip(paths.rom,error) ||
           synth.Core().ChipVariant()!=Emu8000Core::Chip::Box86)
          throw std::runtime_error("ROM/86Box: "+error);
        synth.Core().PowerOnInit();
        if(!synth.LoadBank(paths.sf2,error))
          throw std::runtime_error("SF2: "+error);
        synth.SelectBrowserBank(static_cast<uint16_t>(preset.bank));
        synth.ProgramChange(0,static_cast<uint8_t>(preset.program));
        synth.NoteOn(0,static_cast<uint8_t>(key),100);
        held=render(synth,44100);  // 1 sec held
        synth.NoteOff(0,static_cast<uint8_t>(key));
        released=render(synth,22050); // 0.5 sec after release
        if(held.peak<=32 && released.peak>32)verdict="NUR_NACH_LOSLASSEN";
        else if(held.peak<=32 && released.peak<=32)verdict="STUMM";
        else if(held.rms<0.0005)verdict="SEHR_LEISE";
        else verdict="HOERBAR";
      }
      if(verdict=="HOERBAR")++audible;
      else if(verdict=="NUR_NACH_LOSLASSEN")++releaseOnly;
      else if(verdict=="STUMM")++silent;
      else if(verdict=="SEHR_LEISE")++quiet;
      else ++noZones;
      report<<preset.bank<<","<<preset.program<<","<<csv(preset.name)
            <<","<<key<<","<<layerCount<<","<<held.peak<<","
            <<held.rms<<","<<released.peak<<","<<released.rms
            <<","<<verdict<<"\n";
      std::cout<<preset.bank<<":"<<preset.program<<" "<<preset.name
               <<" -> "<<verdict<<" ("<<held.peak<<"/"<<released.peak<<")\n";
    }
    report.flush();
    if(!report)throw std::runtime_error("CSV write failed");
    std::cout<<"Audible "<<audible<<", silent "<<silent<<", release-only "
             <<releaseOnly<<", quiet "<<quiet<<", no-covered-note "<<noZones<<"\n";
    std::cout<<"CSV: "<<reportPath.string()<<"\n";
    return 0;
  }catch(const std::exception& ex){
    std::cerr<<"P109 ERROR: "<<ex.what()<<"\n";return 1;
  }
}
