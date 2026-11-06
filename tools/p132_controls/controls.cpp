// Additional controls use the EXACT already measured DLL artifact. This does
// not rebuild or alter the production or diagnostic processor.
#define main p132_original_host_main
#include "../../tests/p132/dll_host.cpp"
#undef main
int main(int argc,char** argv){try{
    must(argc==5,"normal DLL, diagnostic DLL, synthetic assets, output");
    const fs::path diagnostic=argv[2],assets=argv[3],out=argv[4];fs::create_directories(out);
    moduleMap.open(out/"modules.csv");moduleMap<<"base,size,path\n";timeBeginPeriod(1);
    std::vector<Row> rows;std::ofstream f(out/"recall-controls.csv");
    f<<"frames,requested,before_allocated,before_physical,before_held,first_allocated,first_physical,settled_allocated,settled_physical,settled_held,generation_before,generation_after\n";
    for(int frames:{128,256,512,1024})for(int n:{1,16,30}){
        Plugin p(diagnostic,model(assets));Row r;r.frames=frames;r.voices=n;seed(p,n,frames,&rows,r);auto before=p.voices();
        // No reprime: this is the natural host save/recall case omitted from
        // a load-matched timing comparison. Its older notes may be discarded.
        MemoryStream stream;encode(stream,p.save());must(p.component->setState(&stream)==kResultOk,"natural recall");
        Block first(frames);r.phase="natural_first";rows.push_back(invoke(p,first,r));auto initial=p.voices();
        for(int i=0;i<4096/frames;++i){Block b(frames);r.phase="natural_settle";r.index=i;rows.push_back(invoke(p,b,r));}
        auto after=p.voices();f<<frames<<','<<n<<','<<before.allocated<<','<<before.nonzero<<','<<before.held<<','<<initial.allocated<<','<<initial.nonzero<<','<<after.allocated<<','<<after.nonzero<<','<<after.held<<','<<before.generation<<','<<after.generation<<'\n';
    }
    std::ofstream reset(out/"reset-controls.csv");reset<<"retrigger,allocated,physical,envelopes,late_pcm_square_sum\n";
    for(int retrigger:{0,1}){
        Plugin p(diagnostic,model(assets));seed(p,1,128);Block stop(0);stop.cc(120,1);if(retrigger)stop.note(45);invoke(p,stop,{});
        double energy=0;for(int i=0;i<32;++i){Block b(128);auto r=invoke(p,b,{});if(i>=16)energy+=r.energy;}
        auto v=p.voices();reset<<retrigger<<','<<v.allocated<<','<<v.nonzero<<','<<v.envelopes<<','<<std::setprecision(17)<<energy<<'\n';
    }
    writeRows(out/"recall-callbacks.csv",rows,hz());timeEndPeriod(1);return 0;
}catch(const std::exception& e){std::cerr<<"P132_INCOMPLETE_CONTROL "<<e.what()<<std::endl;timeEndPeriod(1);return 1;}}
