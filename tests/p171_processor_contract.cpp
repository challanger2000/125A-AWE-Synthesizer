// Actual extracted VST3 Processor; reused host transport, new PCM decisions.
#define main p128_original_test_entry
#include "p128_processor_order.cpp"
#undef main
#include "public.sdk/source/vst/hosting/hostclasses.h"

bool loadSf2(Processor& processor,const std::string& path,int64 request=1) {
    auto* message=new HostMessage;
    message->setMessageID("125A_SF2_LOAD");
    message->getAttributes()->setInt("RequestID",request);
    message->getAttributes()->setBinary("Path",path.data(),uint32(path.size()));
    const auto result=processor.notify(message);message->release();
    return result==kResultOk;
}
void banksAndFirstNotes() {
    for(int ch=0;ch<16;++ch)for(int bank:{0,5}) {
        Rig reference(state(bank,7));const auto expected=sound(*reference.p,ch);
        Rig actual(state(128,7));
        Block select(0);
        select.param(MidiControlMapping::ParamID(ch,MidiControlMapping::Index(0)),bank/127.);
        select.param(MidiControlMapping::ParamID(ch,MidiControlMapping::Index(32)),0.);
        select.param(MidiProgramRouting::ParamID(ch),7./127.);
        select.run(*actual.p);
        // Repeat explicit zero, and publish a new engine between acceptance
        // and the first NoteOn: MidiLiveState must replay the touched zero.
        Block repeat(0);repeat.param(MidiControlMapping::ParamID(ch,MidiControlMapping::Index(0)),bank/127.);
        repeat.run(*actual.p);
        require(loadSf2(*actual.p,state().sf2Path),"load accepted");
        const auto got=sound(*actual.p,ch);
        check(audible(expected)&&got==expected,"P171 all-channel exact bank PCM after CC0/CC32/repeat/engine load ch="+
              std::to_string(ch+1)+" bank="+std::to_string(bank));
        // A newer recall deliberately supersedes the live channel bank.
        require(recall(*actual.p,state(5,9))==kResultOk,"newer recall");
        Rig wanted(state(5,9));
        check(sound(*actual.p,ch)==sound(*wanted.p,ch),"P171 recall supersedes older channel bank ch="+std::to_string(ch+1));
    }
    for(int rate:{44100,48000,96000})for(int program:{0,7,9}) {
        auto blank=state(0,program);blank.sf2Path.clear();
        Rig actual(blank,true,rate);
        require(loadSf2(*actual.p,state().sf2Path),"first SF2 accepted");
        Rig wanted(state(0,program),true,rate);
        auto got=sound(*actual.p),expected=sound(*wanted.p);
        check(audible(got)&&got==expected,"P171 first NoteOn after accepted SF2 load without second click rate="+
            std::to_string(rate)+" program="+std::to_string(program));
        check(save(*actual.p).sf2Path==state().sf2Path,"P171 accepted load persists asset");
    }
    // Successful old engine must survive malformed/unreadable replacement.
    Rig retained;
    const auto before=save(*retained.p);
    require(loadSf2(*retained.p,(assetsDir/"absent.sf2").string()),"error ACK path");
    check(same(before,save(*retained.p))&&sound(*retained.p)==referenceSound(before,0),
        "P171 rejected load preserves first-note PCM and project state");
}

void stress(const std::filesystem::path& output) {
    std::ofstream csv(output);require(bool(csv),"stress CSV open");
    csv<<"frames,notes,scenario,block,wall_us,deadline_us,held_identities,late,thread_cycles,start_core,end_core,qpc_start,qpc_end,qpc_frequency,pid,tid\n";
    for(int frames:{128,256,512,1024})for(int notes:{1,16,30})for(int scenario:{0,1,2,3}) {
        Rig rig;Block onset(0);for(int n=0;n<notes;++n)onset.note(0,40+n);onset.run(*rig.p);
        std::atomic<bool> done=false;std::atomic<unsigned> saves=0,recalls=0;std::atomic<bool> valid=true;
        std::thread control([&] {
            if(scenario==0)return;
            while(!done.load()) {
                try {const auto s=save(*rig.p);++saves;
                    if(scenario>=2){if(recall(*rig.p,s)!=kResultOk)valid=false;++recalls;}
                } catch(...) {valid=false;break;}
                std::this_thread::yield();
            }
        });
        unsigned late=0,heard=0,heldMin=unsigned(notes);
        for(int b=0;b<200;++b) {
            Block block(frames);
            if(scenario==3) {
                for(int n=0;n<16;++n) {
                    block.param(MidiControlMapping::ParamID(n,MidiControlMapping::Index(129)),.5+(b&1)*.02);
                    block.param(MidiProgramRouting::ParamID(n),7./127.);
                }
            }
            // Measure the real callback with its parameter queues. Host
            // construction, copies and metrics stay outside the timestamps.
#if defined(_WIN32)
            ULONG64 cycles0=0,cycles1=0;LARGE_INTEGER q0{},q1{},frequency{};
            QueryPerformanceFrequency(&frequency);
            QueryThreadCycleTime(GetCurrentThread(),&cycles0);
            const auto core0=GetCurrentProcessorNumber();QueryPerformanceCounter(&q0);
#endif
            auto t0=std::chrono::steady_clock::now();
            const auto result=rig.p->process(block.data);
            auto t1=std::chrono::steady_clock::now();
#if defined(_WIN32)
            QueryPerformanceCounter(&q1);const auto core1=GetCurrentProcessorNumber();
            QueryThreadCycleTime(GetCurrentThread(),&cycles1);
#endif
            require(result==kResultOk,"timed process");
            heard+=std::any_of(block.l.begin(),block.l.begin()+frames,
                              [](float v){return v!=0.f;});
            auto pin=rig.p->engines_.Read();unsigned held=0;
            if(pin&&pin->synth)for(auto n:pin->synth->CaptureHeldNotes())held+=n.sequence!=0;
            heldMin=std::min(heldMin,held);
            const double us=std::chrono::duration<double,std::micro>(t1-t0).count(),budget=frames*1e6/44100.;
            late+=us>budget;
            csv<<frames<<','<<notes<<','<<scenario<<','<<b<<','<<us<<','<<budget<<','<<held<<','<<(us>budget);
#if defined(_WIN32)
            csv<<','<<(cycles1-cycles0)<<','<<core0<<','<<core1<<','<<q0.QuadPart<<','<<q1.QuadPart
               <<','<<frequency.QuadPart<<','<<GetCurrentProcessId()<<','<<GetCurrentThreadId();
#else
            csv<<",0,0,0,0,0,0,0,0";
#endif
            csv<<'\n';
        }
        done=true;control.join();
        check(valid&& (scenario? saves>0:true),"P171 concurrent state stress transport frames="+
              std::to_string(frames)+" notes="+std::to_string(notes)+" scenario="+std::to_string(scenario));
        if(scenario<2)check(heldMin==unsigned(notes)&&heard>0,"P171 sounding workload preserves held identities");
        std::cout<<"RT frames="<<frames<<" notes="<<notes<<" scenario="<<scenario<<" late="<<late
            <<" held_min="<<heldMin<<" saves="<<saves<<" recalls="<<recalls<<'\n';
    }
    require(bool(csv),"stress CSV write");
}
int main(int argc,char** argv) {
    try {
        if(argc<3)return 2;assetsDir=argv[2];
        if(std::string(argv[1])=="stress"&&argc==4)stress(argv[3]);
        else banksAndFirstNotes();
        std::cout<<"RESULT checks="<<checks<<" failed="<<failures<<'\n';
        return failures?1:0;
    } catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}
}
