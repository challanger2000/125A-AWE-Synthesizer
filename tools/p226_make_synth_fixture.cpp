// P226 synthetic media only. Reuses the already exercised P166 ROM/SF2
// generator; no proprietary samples, original bank, or Creative driver media.
#define main p226_unused_p166_test_main
#include "../tests/p166_exact_sf2_rom.cpp"
#undef main
int main(int argc,char** argv) {
    if(argc!=2)return 2;
    const auto dir=fs::path(argv[1]);
    std::error_code error;
    fs::create_directories(dir,error);
    if(error)return 2;
    const auto rom=dir/"zero.rom", sf=dir/"bank.sf2";
    if(fs::exists(rom)||fs::exists(sf))return 2;
    if(!MakeSyntheticRom(rom) ||
       !Save(sf,MakeSoundFont({{0,0,0},{0,21,1}},false,true)))return 2;
    std::cout<<"P226_SYNTHETIC_ONLY_P000_P021_FIXTURES=CREATED\n";
    return 0;
}
