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
    {
        // P190 deliberate exception: FX send controls 10/11 write actual
        // EMU8000 send registers while a note is held. ADSR/filter 0..9
        // remain strictly NoteOn-only; preserve their existing contract.
        Rig edited,original;
        bool beforeIdentical=true,afterDifferent=false,heard=false;
        for(int n=0;n<8;++n) {
            Block a,b;
            if(!n){a.note();b.note();}
            if(n==3)for(int k=0;k<12;++k)a.param(kGuiFirstID+k,.8);
            const auto x=a.run(*edited.p),y=b.run(*original.p);
            if(n<3)beforeIdentical&=x==y;
            else afterDifferent|=x!=y;
            heard|=audible(x);
        }
        const auto saved=save(*edited.p);
        check(beforeIdentical&&afterDifferent&&heard&&
              std::all_of(saved.controls.begin(),saved.controls.end(),
                          [](auto v){return v==8000;}),
              "P190 live FX send changes held-note PCM and saves controls");
    }
    {
        Rig edited,original;bool identical=true,heard=false;
        for(int n=0;n<8;++n) {
            Block a,b;
            if(!n){a.note();b.note();}
            if(n==3)for(int k=0;k<10;++k)a.param(kGuiFirstID+k,.8);
            const auto x=a.run(*edited.p),y=b.run(*original.p);
            identical&=x==y;heard|=audible(x);
        }
        const auto saved=save(*edited.p);
        bool persisted=true;
        for(int k=0;k<12;++k)persisted&=
            saved.controls[size_t(k)]==static_cast<uint32_t>(k<10?8000:0);
        check(identical&&heard&&persisted,
              "P171 non-FX overlays preserve held-note NoteOn-only PCM");
    }
}



void testP191LegacyV11RecallAndAutomation() {
    // Build actual legacy V11 binary bytes, including old program/FX layout.
    const auto project=state();
    std::vector<unsigned char> bytes;
    auto sink=[&](const void* v,size_t n){
        const auto* p=static_cast<const unsigned char*>(v);
        bytes.insert(bytes.end(),p,p+n);return true;
    };
    require(AssetState::Write(sink,project)&&bytes.size()>16,"V11 basis");
    bytes.resize(bytes.size()-4);bytes[4]=11;
    MemoryStream oldState;
    int32 written=0;
    require(oldState.write(bytes.data(),int32(bytes.size()),&written)==kResultOk
            &&written==int32(bytes.size()),"write historical V11 stream");
    require(oldState.seek(0,IBStream::kIBSeekSet,nullptr)==kResultOk,"rewind V11");
    Rig legacy(project),modern(project);
    require(legacy.p->setState(&oldState)==kResultOk,"V11 project recall");
    check(save(*legacy.p).legacyFx&&!save(*modern.p).legacyFx,
          "P191 V11 legacy additive and new V12 absolute dry");
    // Note-level wet inputs are host MIDI CC91/93, never a fake DSP flag.
    auto enableMidi=[](Processor& p){
        Block cc(0);
        cc.param(MidiControlMapping::ParamID(0,MidiControlMapping::Index(91)),1.);
        cc.param(MidiControlMapping::ParamID(0,MidiControlMapping::Index(93)),1.);
        cc.run(p);
    };
    enableMidi(*legacy.p);enableMidi(*modern.p);
    const auto legacyPcm=sound(*legacy.p),dryPcm=sound(*modern.p);
    check(audible(legacyPcm)&&audible(dryPcm)&&legacyPcm!=dryPcm,
          "P191 old V11 CC wet PCM vs new absolute 0%=dry");
    const auto saved=save(*legacy.p);
    Rig reopened(saved);enableMidi(*reopened.p);
    const auto reopenedPcm=sound(*reopened.p);
    check(saved.legacyFx&&reopenedPcm==legacyPcm,
          "P191 old V11 recall -> V12 save/reopen preserves PCM");
    Block upgrade(0);upgrade.param(kFxSemanticsID,0.);upgrade.run(*legacy.p);
    const auto upgraded=save(*legacy.p);
    check(!upgraded.legacyFx&&upgraded.controls[10]==0&&upgraded.controls[11]==0,
          "P191 explicit host mode automation selects absolute dry");
    Rig converted(upgraded);enableMidi(*converted.p);
    check(sound(*converted.p)==dryPcm,
          "P191 upgraded V12 reproduces new absolute-dry PCM");
}

void testP190WetTailBypass() {
    // Previously 0 only zeroed NEW voice sends. Reverb/chorus feedback
    // from existing audio still escaped. Prove the real Box86 PCM return
    // matches an independently dry clone after the chip FIFO has drained.
    for(int mode=0;mode<3;++mode) {
        auto initial=state();
        if(mode!=1)initial.controls[10]=10000;
        if(mode!=0)initial.controls[11]=10000;
        Rig switched(initial),reference(state());
        bool wetBefore=false,matchedAfter=true,heardDry=false;
        for(int block=0;block<22;++block) {
            Block a,b;
            if(block==0){a.note();b.note();}
            if(block==8) {
                if(mode!=1)a.param(kGuiFirstID+10,0.);
                if(mode!=0)a.param(kGuiFirstID+11,0.);
            }
            const auto x=a.run(*switched.p),y=b.run(*reference.p);
            if(block>=4&&block<8)wetBefore |= x!=y;
            // Original 980-frame chip FIFO delays the knob action;
            // make the assertion well after two 1024-frame blocks.
            if(block>=11){matchedAfter &= (x==y);heardDry |= audible(y);}
        }
        const auto saved=save(*switched.p);
        check(wetBefore&&matchedAfter&&heardDry&&
              saved.controls[10]==0&&saved.controls[11]==0,
              "P190 prior wet tails become fully dry after FIFO latency, FX case="+std::to_string(mode));
    }
}

void stress(const std::filesystem::path& output) {
    std::ofstream csv(output);require(bool(csv),"stress CSV open");
    csv<<"frames,notes,scenario,block,wall_us,deadline_us,held_identities,late,thread_cycles,start_core,end_core,qpc_start,qpc_end,qpc_frequency,pid,tid\n";
    for(int frames:{128,256,512,1024})for(int notes:{1,16,30})for(int scenario:{0,1,2,3,4,5}) {
        auto initial=state();
        if(scenario>=4) {
            // An originally slow MOD attack keeps the new PEFE route moving
            // through the full held-note measurement (also at 1024 frames).
            initial.sf2Path=(assetsDir/"bank-filter-stress.sf2").string();
            initial.controls[4]=100;initial.controls[5]=100;
            initial.controls[6]=8000;initial.controls[7]=10000;
            initial.controls[9]=5000;initial.controls[10]=5000;initial.controls[11]=5000;
        }
        Rig rig(initial);Block onset(0);for(int n=0;n<notes;++n)onset.note(0,40+n);onset.run(*rig.p);
        std::atomic<bool> done=false;std::atomic<unsigned> saves=0,recalls=0;std::atomic<bool> valid=true;
        std::thread control([&] {
            if(scenario==0||scenario==4)return;
            while(!done.load()) {
                try {const auto s=save(*rig.p);++saves;
                    if(scenario==2||scenario==3||scenario==5){if(recall(*rig.p,s)!=kResultOk)valid=false;++recalls;}
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
            if(scenario>=4) {
                // Control automation accompanies an already active route.
                // Case 4 holds its exact 1/16/30 identities throughout. Case
                // 5 additionally retriggers and recalls; Creative stealing
                // and recall can reduce that load, recorded rather than hidden.
                for(int k=4;k<8;++k)block.param(kGuiFirstID+k,k==7?1.:(k==6?.8:.01));
                block.param(kGuiFirstID+9,.5); // hardware resonance
                block.param(kGuiFirstID+10,.5);block.param(kGuiFirstID+11,.5);
                if(scenario==5) {
                    block.param(kReverbPresetID,double(b%8)/7.);
                    block.param(kChorusPresetID,double((b/8)%8)/7.);
                }
                if(scenario==5)for(int n=0;n<std::min(notes,4);++n) {
                    const int pitch=40+(4*b+n)%notes;
                    block.note(0,pitch,0,false);block.note(0,pitch);
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
        check(valid&& ((scenario==0||scenario==4)?true:saves>0),"P171 concurrent state stress transport frames="+
              std::to_string(frames)+" notes="+std::to_string(notes)+" scenario="+std::to_string(scenario));
        if(scenario<2||scenario==4)check(heldMin==unsigned(notes)&&heard>0,"P171 sounding workload preserves held identities");
        std::cout<<"RT frames="<<frames<<" notes="<<notes<<" scenario="<<scenario<<" late="<<late
            <<" held_min="<<heldMin<<" saves="<<saves<<" recalls="<<recalls<<'\n';
    }
    require(bool(csv),"stress CSV write");
}
int main(int argc,char** argv) {
    try {
        if(argc<3)return 2;assetsDir=argv[2];
        if(std::string(argv[1])=="stress"&&argc==4)stress(argv[3]);
        else {banksAndFirstNotes();testP190WetTailBypass();testP191LegacyV11RecallAndAutomation();}
        std::cout<<"RESULT checks="<<checks<<" failed="<<failures<<'\n';
        return failures?1:0;
    } catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}
}
