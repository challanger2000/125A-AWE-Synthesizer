// Identical analytic sine, two storage paths; not an original ROM oracle.
#define main p166_original_test_entry
#include "p166_exact_sf2_rom.cpp"
#undef main
int main() {
    const auto dir=fs::temp_directory_path()/"125a-p171-rom-level";
    fs::create_directories(dir);
    struct Clean {fs::path p;~Clean(){std::error_code e;fs::remove_all(p,e);}} cleanup{dir};
    const auto rom=dir/"synthetic.raw",font=dir/"level.sf2",gm=dir/"SYNTHGM.SBK";
    if(!MakeSyntheticRom(rom)||!Save(font,MakeSoundFont({{0,0,0}},false,true))||
       !Save(gm,MakeSoundFont(RomShape(),true,true)))return 2;
    auto level=[&](unsigned bank) {
        Synth synth(44100);synth.Core().SetDriver(Awe32::Driver::Win95);std::string error;
        if(!synth.Core().UseBox86Chip(rom.string(),error))throw std::runtime_error(error);
        synth.Core().PowerOnInit();
        auto loaded=AWE125::RomGmBank::LoadBanks(synth,rom.string(),font.string());
        if(!loaded.gm||!loaded.sf2)throw std::runtime_error("level banks");
        synth.SelectBrowserBank(uint16_t(bank));synth.NoteOn(0,69,127,1);
        std::vector<int16_t> pcm(44100*2);synth.RenderBlock(pcm.data(),44100);
        double sum=0,peak=0;
        for(size_t i=22050*2;i<pcm.size();++i){const double x=pcm[i]/32768.;sum+=x*x;peak=std::max(peak,std::abs(x));}
        return std::pair{std::sqrt(sum/44100),peak};
    };
    try {
        auto sf=level(0),wave=level(16383);
        const double delta=20*std::log10(wave.first/sf.first);
        // Source ROM sine has amplitude 14000; SF2 sine amplitude 12500.
        // The Win95 1MGM path adds exactly sixteen .375-dB IFATN steps.
        const double expected=20*std::log10(14000./12500.)-6.;
        bool ok=Check(sf.first>.001&&wave.first>.001&&std::abs(delta-expected)<.3,
            "ROM attenuation PCM follows source amplitude and Win95 16-unit compensation");
        std::cout<<"{\"synthetic_only\":true,\"sf2_rms\":"<<sf.first<<",\"rom_rms\":"<<wave.first
            <<",\"sf2_peak\":"<<sf.second<<",\"rom_peak\":"<<wave.second
            <<",\"delta_db\":"<<delta<<",\"expected_db\":"<<expected<<"}\n";
        return ok?0:1;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}
}
