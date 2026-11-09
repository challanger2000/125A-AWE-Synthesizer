// Exact production Processor + Steinberg SDK; no mock state/render implementation.
#include <functional>
#include <iostream>
#include <fstream>
#include <chrono>
static thread_local std::function<void(const char*)> hook;
static thread_local bool inRT=false;
void auditHook(const char* name){if(hook)hook(name);}
// SDK moduleinit.cpp expects the platform entry translation unit's handle.
void* moduleHandle=nullptr;
#include "ProcessorUnderTest.h"
#include "public.sdk/source/common/memorystream.h"
#include "public.sdk/source/vst/hosting/parameterchanges.h"
#include "public.sdk/source/vst/hosting/eventlist.h"
#include "Emu8000Effects.h"
using namespace Steinberg;using namespace Steinberg::Vst;using namespace AWE125;
using State=AssetState::Data;
static std::filesystem::path assetsDir;
static int failures=0,checks=0;
void check(bool yes,const std::string& label){++checks;if(!yes)++failures;std::cout<<(yes?"PASS ":"FAIL ")<<label<<std::endl;}
void require(bool b,const char* s){if(!b)throw std::runtime_error(s);}
State state(unsigned b=0,unsigned p=0,bool assets=true){State s;s.pathsSpecified=true;s.bank=b;s.program=p;s.channelPrograms.fill(p);if(assets){s.romPath=(assetsDir/"zero.rom").string();s.sf2Path=(assetsDir/"bank.sf2").string();}return s;}
bool writeState(MemoryStream& out,const State& s){auto sink=[&](const void* d,size_t n){int32 w=0;return out.write(const_cast<void*>(d),n,&w)==kResultOk&&w==int32(n);};return AssetState::Write(sink,s)&&out.seek(0,IBStream::kIBSeekSet,nullptr)==kResultOk;}
bool readState(MemoryStream& in,State& s){in.seek(0,IBStream::kIBSeekSet,nullptr);auto source=[&](void* d,size_t n){int32 r=0;return in.read(d,n,&r)==kResultOk&&r==int32(n);};return AssetState::Read(source,s);}
State save(Processor& p){MemoryStream out;require(p.getState(&out)==kResultOk,"getState");State s;require(readState(out,s),"read V10");return s;}
tresult recall(Processor& p,const State& s){MemoryStream stream;require(writeState(stream,s),"write V10");return p.setState(&stream);}
bool same(const State& a,const State& b){return a.bank==b.bank&&a.program==b.program&&a.channelPrograms==b.channelPrograms&&a.channelProgramMask==b.channelProgramMask&&a.masterVolume==b.masterVolume&&a.controls==b.controls&&a.reverbPreset==b.reverbPreset&&a.chorusPreset==b.chorusPreset&&a.pathsSpecified==b.pathsSpecified&&a.romPath==b.romPath&&a.sf2Path==b.sf2Path&&a.engine==b.engine;}
struct Rig{
 std::unique_ptr<Processor> p=std::make_unique<Processor>();bool active=false;
 Rig(State s=state(),bool a=true,int rate=44100){require(p->initialize(nullptr)==kResultOk,"initialize");ProcessSetup setup{kRealtime,kSample32,1024,double(rate)};require(p->setupProcessing(setup)==kResultOk,"setup");require(recall(*p,s)==kResultOk,"initial recall");if(a){require(p->setActive(true)==kResultOk,"active");require(p->setProcessing(true)==kResultOk,"processing");active=true;}}
 ~Rig(){hook={};if(active){p->setProcessing(false);p->setActive(false);}p->terminate();}
};
struct Block {
 std::array<float,1024> l{},r{};float* chans[2]{l.data(),r.data()};AudioBusBuffers out{};ProcessData data{};ParameterChanges params{64};EventList events{64};
 Block(int n=1024){out.numChannels=2;out.channelBuffers32=chans;data.processMode=kRealtime;data.symbolicSampleSize=kSample32;data.numSamples=n;data.numOutputs=1;data.outputs=&out;data.inputParameterChanges=&params;data.inputEvents=&events;}
 void param(ParamID id,double value,int offset=0){int32 index=0;auto* q=params.addParameterData(id,index);require(q&&q->addPoint(offset,value,index)==kResultOk,"add point");}
 void note(int channel=0,int pitch=60,int offset=0,bool on=true){Event e{};e.type=on?Event::kNoteOnEvent:Event::kNoteOffEvent;e.sampleOffset=offset;if(on){e.noteOn.channel=channel;e.noteOn.pitch=pitch;e.noteOn.velocity=.85;e.noteOn.noteId=channel*128+pitch;}else{e.noteOff.channel=channel;e.noteOff.pitch=pitch;e.noteOff.noteId=channel*128+pitch;}require(events.addEvent(e)==kResultOk,"add event");}
 std::vector<float> run(Processor& p,bool track=false){inRT=track;tresult rc=p.process(data);inRT=false;require(rc==kResultOk,"process");std::vector<float> v;v.insert(v.end(),l.begin(),l.begin()+data.numSamples);v.insert(v.end(),r.begin(),r.begin()+data.numSamples);return v;}
};
void edit(Processor& p,ParamID id,unsigned val){Block b(0);b.param(id,double(val)/(id==kBankID?AssetState::kMaxBank:127));b.run(p);}
std::vector<float> sound(Processor& p,int channel=0){std::vector<float> all;for(int i=0;i<8;++i){Block b;if(!i)b.note(channel);auto v=b.run(p);all.insert(all.end(),v.begin(),v.end());}return all;}
bool audible(const std::vector<float>& v){return std::any_of(v.begin(),v.end(),[](float f){return f!=0;});}
// Independent PCM oracle: drive the production Synth directly with explicit
// expected fields. A Processor routing mutation must never mutate its oracle.
std::vector<float> referenceSound(const State& wanted,int channel) {
    Synth syn(44100);std::string error;
    syn.Core().SetDriver(Awe32::Driver::Win95);
    require(syn.Core().UseBox86Chip(wanted.romPath,error),"reference ROM");
    syn.Core().PowerOnInit();
    syn.Core().ApplyHardwareReverbPreset(wanted.reverbPreset);
    syn.Core().ApplyHardwareChorusPreset(wanted.chorusPreset);
    require(RomGmBank::LoadBanks(syn,wanted.romPath,wanted.sf2Path).sf2,"reference SF2");
    for(int k=0;k<kGuiCount;++k)syn.SetGuiControl(k,float(wanted.controls[k])/AssetState::kControlScale);
    syn.SelectBrowserBank(wanted.bank);
    for(int ch=0;ch<16;++ch)syn.ProgramChange(ch,(wanted.channelProgramMask&(1u<<ch))?wanted.channelPrograms[ch]:wanted.program);
    syn.NoteOn(channel,60,108);
    std::vector<float> result;std::array<int16_t,2048> pcm{};
    for(int block=0;block<8;++block) {
        syn.RenderBlock(pcm.data(),1024);
        for(int side=0;side<2;++side)for(int frame=0;frame<1024;++frame)
            result.push_back(pcm[2*frame+side]/32768.f);
    }
    return result;
}
bool verify(Processor& p,const State& wanted,const std::string& name,int ch=0){auto actual=save(p);auto a=sound(p,ch),b=referenceSound(wanted,ch);bool fields=same(actual,wanted),pcm=a==b&&audible(a);check(fields,name+" V10 bank="+std::to_string(actual.bank)+" program="+std::to_string(actual.program)+" mask="+std::to_string(actual.channelProgramMask));check(pcm,name+" exact PCM incl current/following blocks");return fields&&pcm;}
struct CallbackStream:MemoryStream{std::function<void()> once;tresult PLUGIN_API read(void* b,int32 n,int32* r) override{if(once){auto fn=std::move(once);fn();}return MemoryStream::read(b,n,r);}};
void deterministic(){
 std::vector<std::vector<float>> waves;for(unsigned bank:{0,5})for(unsigned program:{0,7,9}){Rig r(state(bank,program));auto pcm=sound(*r.p);check(pcm==referenceSound(state(bank,program),0),"Processor preset PCM equals independent direct-Synth oracle "+std::to_string(bank)+","+std::to_string(program));waves.push_back(std::move(pcm));}
 bool unique=true;for(size_t i=0;i<waves.size();++i){unique&=audible(waves[i]);for(size_t j=0;j<i;++j)unique&=waves[i]!=waves[j];}check(unique,"fixture six pairwise distinct audible bank/program PCM references");
 {Rig r;CallbackStream old;writeState(old,state());tresult newer=-99;old.once=[&]{newer=recall(*r.p,state(5,9));};auto rc=r.p->setState(&old);check(newer==kResultOk&&rc==kResultFalse,"F01 reentrant newer recall accepted / old rejected");verify(*r.p,state(5,9),"F01 reentrant");}
 {Rig r;CallbackStream old;writeState(old,state());std::atomic<bool> entered=false,release=false;old.once=[&]{entered=true;while(!release.load())std::this_thread::yield();};tresult rc=-99;std::thread t([&]{rc=r.p->setState(&old);});while(!entered.load())std::this_thread::yield();auto nr=recall(*r.p,state(5,9));release=true;t.join();check(rc==kResultFalse&&nr==kResultOk,"F01 two threads reverse completion");verify(*r.p,state(5,9),"F01 two threads");}
 {Rig r;CallbackStream old;writeState(old,state(0,7));std::atomic<bool> entered=false,release=false;old.once=[&]{entered=true;while(!release.load())std::this_thread::yield();};tresult oldrc=-99;std::thread t([&]{oldrc=r.p->setState(&old);});while(!entered.load())std::this_thread::yield();bool fired=false;hook=[&](const char* h){if(!fired&&std::string(h)=="recall_prepared_epoch"){fired=true;release=true;t.join();}};auto newer=recall(*r.p,state(5,9));hook={};check(fired&&oldrc==kResultOk&&newer==kResultOk,"F01 older commits during newer preparation");verify(*r.p,state(5,9),"F01 newer preparation survives older commit");}
 {Rig r;r.p->bankOrder_.PublishBrowser(5);bool fired=false;hook=[&](const char* h){if(!fired&&std::string(h)=="pending_bank_before_writer"){fired=true;require(recall(*r.p,state())==kResultOk,"F02 recall");}};Block b;b.note();auto first=b.run(*r.p);hook={};Rig ref;Block rb;rb.note();auto rf=rb.run(*ref.p);bool pcm=first==rf;for(int i=0;i<7;++i){Block x,y;pcm&=x.run(*r.p)==y.run(*ref.p);}check(fired&&pcm&&same(save(*r.p),state()),"F02 old bank snapshot before RT gate uses newer recall PCM/state");}
 {Rig r;bool fired=false;hook=[&](const char* h){if(!fired&&std::string(h)=="recall_bank_snapshot"){fired=true;edit(*r.p,kBankID,5);edit(*r.p,kProgramID,9);}};auto rc=recall(*r.p,state());hook={};check(rc==kResultOk&&same(save(*r.p),state(5,9)),"F03 denied RT writer: immediate save before next block keeps (5,9)");verify(*r.p,state(5,9),"F03 pending preset after recall");}
 for(int ch=0;ch<16;++ch){Rig r;CallbackStream old;writeState(old,state());old.once=[&]{edit(*r.p,MidiProgramRouting::ParamID(ch),9);};require(r.p->setState(&old)==kResultOk,"channel old recall");auto wanted=state();wanted.channelProgramMask=1u<<ch;wanted.channelPrograms[ch]=9;verify(*r.p,wanted,"F04 channel "+std::to_string(ch+1),ch);require(recall(*r.p,state(5,7))==kResultOk,"newer channel recall");check(same(save(*r.p),state(5,7)),"F04 newer recall clears old channel "+std::to_string(ch+1));}
 {Rig r;bool fired=false;hook=[&](const char* h){if(!fired&&std::string(h)=="recall_bank_snapshot"){fired=true;edit(*r.p,kProgramID,7);for(int ch=0;ch<16;++ch)edit(*r.p,MidiProgramRouting::ParamID(ch),(ch%2)?9:0);}};require(recall(*r.p,state(5,0))==kResultOk,"all channel recall");hook={};auto wanted=state(5,7);wanted.channelProgramMask=65535;for(int ch=0;ch<16;++ch)wanted.channelPrograms[ch]=(ch%2)?9:0;check(same(save(*r.p),wanted),"F04 all 16 denied channel intents + global merge, full mask");}
 {Rig r;bool fired=false;hook=[&](const char* h){if(!fired&&std::string(h)=="parameter_before_writer"){fired=true;require(recall(*r.p,state())==kResultOk,"new recall after accepted program");}};edit(*r.p,kProgramID,9);hook={};verify(*r.p,state(),"NEW-F01 newer recall after global stamp before writer");}
 {Rig r;bool fired=false;hook=[&](const char* h){if(!fired&&std::string(h)=="parameter_before_writer"){fired=true;require(recall(*r.p,state())==kResultOk,"new recall after accepted channel");}};edit(*r.p,MidiProgramRouting::ParamID(3),9);hook={};verify(*r.p,state(),"NEW-F02 newer recall after channel stamp before writer",3);}
 {Rig r;{RealtimeStateVersion::Writer control(r.p->rtStateVersion_,RealtimeStateVersion::Domain::Control);edit(*r.p,kProgramID,9);}bool fired=false;hook=[&](const char* h){if(!fired&&std::string(h)=="pending_program_before_writer"){fired=true;require(recall(*r.p,state())==kResultOk,"pending newer recall");}};Block b(0);b.run(*r.p);hook={};verify(*r.p,state(),"NEW-F03 pending program captured before newer recall");}
 {Rig r;std::atomic<bool> fallback=false;State got;std::thread saver;{RealtimeStateVersion::Writer control(r.p->rtStateVersion_,RealtimeStateVersion::Domain::Control);saver=std::thread([&]{hook=[&](const char* h){if(std::string(h)=="save_fallback")fallback=true;};got=save(*r.p);hook={};});while(!fallback.load())std::this_thread::yield();edit(*r.p,kBankID,5);edit(*r.p,kProgramID,9);for(int ch=0;ch<16;ch+=2)edit(*r.p,MidiProgramRouting::ParamID(ch),7);}saver.join();auto wanted=state(5,9);for(int ch=0;ch<16;ch+=2){wanted.channelProgramMask|=1u<<ch;wanted.channelPrograms[ch]=7;}check(same(got,wanted),"forced getState fallback includes accepted pending global/bank/channel edits");}
 {Rig r;bool fired=false;hook=[&](const char* h){if(!fired&&std::string(h)=="block_pin"){fired=true;require(recall(*r.p,state(5,9))==kResultOk,"engine block recall");}};Block b;b.note();auto v=b.run(*r.p);hook={};Rig ref(state(5,9));Block a;a.note();bool eq=v==a.run(*ref.p);for(int i=0;i<7;++i){Block x,y;eq&=x.run(*r.p)==y.run(*ref.p);}check(eq&&same(save(*r.p),state(5,9)),"engine generation switch after block pin: NoteOn survives next block exact PCM");}
 {Rig r;bool fired=false;hook=[&](const char* h){if(!fired&&std::string(h)=="note_before_dispatch"){fired=true;require(recall(*r.p,state(5,9))==kResultOk,"note dispatch recall");}};auto a=sound(*r.p);hook={};Rig ref(state(5,9));auto b=sound(*ref.p);check(a==b&&audible(a),"NEW-F04 recall published after refresh before NoteOn: current/next PCM");std::cout<<"NOTE_DISPATCH actual_audible="<<audible(a)<<" expected_audible="<<audible(b)<<std::endl;}
 {Rig r;CallbackStream slow;writeState(slow,state(5,9));slow.once=[&]{Block b(0);b.note();b.run(*r.p);};require(r.p->setState(&slow)==kResultOk,"recall after accepted note");Rig ref(state(5,9));bool eq=true,heard=false;for(int i=0;i<8;++i){Block a,b;if(!i)b.note();auto x=a.run(*r.p),y=b.run(*ref.p);eq&=x==y;heard|=audible(x);}check(eq&&heard,"NoteOn after recall start survives publication BETWEEN callbacks");}
 {Rig r;sound(*r.p);require(r.p->setActive(false)==kResultOk,"deactivate");require(r.p->setActive(true)==kResultOk,"reactivate");bool silent=true;for(int i=0;i<8;++i){Block b;silent&=!audible(b.run(*r.p));}check(silent,"deactivate/reactivate clears held-note handoff state");}
 {Rig r;CallbackStream slow;writeState(slow,state(5,9));slow.once=[&]{Block b(0);b.note();b.note(0,60,0,false);b.run(*r.p);};require(r.p->setState(&slow)==kResultOk,"note-off recall");bool silent=true;for(int i=0;i<8;++i){Block b;silent&=!audible(b.run(*r.p));}check(silent,"NoteOff before publication cannot resurrect a released note");}
 {Rig r;Block b;b.param(kBankID,5./AssetState::kMaxBank);b.param(kProgramID,9./127);b.param(MidiProgramRouting::ParamID(1),7./127);b.param(MidiControlMapping::ParamID(0,MidiControlMapping::Index(0)),0);b.param(MidiControlMapping::ParamID(0,MidiControlMapping::Index(32)),0);b.note(0);b.note(1);auto v=b.run(*r.p);auto w=state(5,9);w.channelProgramMask=2;w.channelPrograms[1]=7;check(audible(v)&&same(save(*r.p),w),"same-offset bank/global/channel/CC0/CC32/NoteOn state/audio acceptance");}
 {Rig r;check(r.p->getTailSamples()==kInfiniteTail&&r.p->setProcessing(false)==kResultOk&&r.p->setProcessing(true)==kResultOk,"kInfiniteTail and setProcessing lifecycle");}
}

// Audit-only negative control: accepted persistent automation must survive
// a control-owned state writer gate, without relying on a later host resend.
void persistentControlWriterCollision() {
    Rig r;
    // Positive control first proves that the parameter IDs and state
    // serialization work in the absence of a control writer.
    {
        Block normal(0);
        normal.param(kVolumeID,0.62);
        normal.param(kGuiFirstID,0.22);
        normal.run(*r.p);
    }
    const auto before=save(*r.p);
    check(before.masterVolume==6200&&before.controls[0]==2200,
          "control: positive baseline V10 master/gui values applied without competition");
    {
        RealtimeStateVersion::Writer control(
            r.p->rtStateVersion_,RealtimeStateVersion::Domain::Control);
        require(static_cast<bool>(control),"control writer gate acquired");
        Block concurrent(0);
        concurrent.param(kVolumeID,0.35);
        concurrent.param(kGuiFirstID,0.75);
        concurrent.run(*r.p);
        std::cout<<"CONTROL_AUDIT accepted parameter points with state writer gate held"<<std::endl;
    }
    const auto immediate=save(*r.p);
    std::cout<<"CONTROL_AUDIT immediate_master="<<immediate.masterVolume
             <<" immediate_gui0="<<immediate.controls[0]
             <<" wanted_master=3500 wanted_gui0=7500"<<std::endl;
    check(immediate.masterVolume==3500,
          "control: master Volume must not be discarded on RT writer refusal");
    check(immediate.controls[0]==7500,
          "control: GUI overlay must not be discarded on RT writer refusal");
    // A subsequent process() without repeated automation cannot repair
    // previously discarded events. This rejects a false transient PASS.
    { Block next(0);next.run(*r.p); }
    const auto next=save(*r.p);
    check(next.masterVolume==3500&&next.controls[0]==7500,
          "control: subsequent idle process preserves accepted master/gui changes");
    // One input queue per GUI control: prove there are no lost or aliased
    // 12-control values when the control writer denies every audio update.
    {
        Rig matrix;
        {
            RealtimeStateVersion::Writer gate(
                matrix.p->rtStateVersion_,RealtimeStateVersion::Domain::Control);
            Block all(0);
            for(int i=0;i<kGuiCount;++i)
                all.param(kGuiFirstID+i,double(i+1)/20.);
            all.param(kVolumeID,0.45);
            all.run(*matrix.p);
        }
        const auto saved=save(*matrix.p);
        bool distinct=saved.masterVolume==4500;
        for(int i=0;i<kGuiCount;++i)
            distinct&=saved.controls[i]==uint32_t((i+1)*500);
        check(distinct,
              "control: all 12 independent GUI values and master persist without writer");
        Block following(0);
        following.run(*matrix.p);
        check(same(saved,save(*matrix.p)),
              "control: pending all-controls applied without changing saved snapshot");
    }
    // A recall started AFTER accepted parameters must override them, even
    // though audio could not obtain the realtime state writer on arrival.
    {
        Rig newest;
        {
            RealtimeStateVersion::Writer gate(
                newest.p->rtStateVersion_,RealtimeStateVersion::Domain::Control);
            Block old(0);
            old.param(kVolumeID,0.35);
            old.param(kGuiFirstID,0.75);
            old.run(*newest.p);
        }
        require(recall(*newest.p,state(5,7))==kResultOk,
                "control: newer state recall accepted");
        check(same(save(*newest.p),state(5,7)),
              "control: newer recall overrides older pending volume/gui values");
        {Block following(0);following.run(*newest.p);}
        check(same(save(*newest.p),state(5,7)),
              "control: stale pending volume/gui not resurrected next callback");
    }
    // Conversely, accepted parameter edits AFTER a recall STARTS must
    // survive the older project state committing at the end of its reader.
    {
        Rig older;
        CallbackStream read;
        require(writeState(read,state(5,7)),
                "control: prepare delayed project recall");
        read.once=[&] {
            RealtimeStateVersion::Writer gate(
                older.p->rtStateVersion_,RealtimeStateVersion::Domain::Control);
            Block newer(0);
            newer.param(kVolumeID,0.35);
            newer.param(kGuiFirstID,0.75);
            newer.run(*older.p);
        };
        require(older.p->setState(&read)==kResultOk,
                "control: delayed recall with newer accepted controls");
        auto wanted=state(5,7);
        wanted.masterVolume=3500;
        wanted.controls[0]=7500;
        check(same(save(*older.p),wanted),
              "control: edits newer than recall START survive its commit");
        {Block following(0);following.run(*older.p);}
        check(same(save(*older.p),wanted),
              "control: newer-than-recall controls survive first subsequent process");
    }
}

// Audit-only: accepted program event at sample 32, then NoteOn at sample
// 64 in SAME audio callback, with the realtime persistent writer refused.
// State may report the new program while PCM still uses the old one.
void midblockProgramRace() {
    const auto capture=[](Rig& r,bool denied) {
        std::vector<float> result;
        const auto first=[&] {
            Block block(1024);
            block.param(kProgramID,9./127.,32);
            block.note(0,60,64);
            const auto output=block.run(*r.p);
            result.insert(result.end(),output.begin(),output.end());
        };
        if(denied) {
            RealtimeStateVersion::Writer control(
                r.p->rtStateVersion_,RealtimeStateVersion::Domain::Control);
            require(static_cast<bool>(control),"midblock: control writer acquired");
            first();
        } else first();
        for(int b=1;b<8;++b) {
            Block next;
            const auto output=next.run(*r.p);
            result.insert(result.end(),output.begin(),output.end());
        }
        return result;
    };
    Rig good;
    const auto normal=capture(good,false);
    check(audible(normal)&&save(*good.p).program==9,
          "midblock: ordinary program-9 point before NoteOn yields audible audio/save");
    Rig collided;
    const auto denied=capture(collided,true);
    const auto written=save(*collided.p);
    std::cout<<"MIDBLOCK_PROGRAM_AUDIT written_program="<<written.program
             <<" pcm_equal="<<(normal==denied)
             <<" normal_audible="<<audible(normal)
             <<" denied_audible="<<audible(denied)<<std::endl;
    check(written.program==9,
          "midblock: accepted program point persisted even when RT writer refused");
    check(denied==normal,
          "midblock: NoteOn after refused program point must use newly accepted program PCM");

    // Same contract for a per-channel VST3 ProgramChange parameter. An
    // override is not equivalent to setting the global program: check both
    // PCM and the V10 channel mask/preset.
    const auto channelCapture=[](Rig& r,bool denied) {
        std::vector<float> pcm;
        const auto first=[&] {
            Block b;
            b.param(MidiProgramRouting::ParamID(3),9./127.,32);
            b.note(3,60,64);
            const auto out=b.run(*r.p);
            pcm.insert(pcm.end(),out.begin(),out.end());
        };
        if(denied) {
            RealtimeStateVersion::Writer control(
                r.p->rtStateVersion_,RealtimeStateVersion::Domain::Control);
            require(static_cast<bool>(control),"midblock: channel control gate");
            first();
        } else first();
        for(int i=1;i<8;++i) {
            Block next;
            const auto out=next.run(*r.p);
            pcm.insert(pcm.end(),out.begin(),out.end());
        }
        return pcm;
    };
    Rig channelGood;
    const auto chNormal=channelCapture(channelGood,false);
    Rig channelCollided;
    const auto chDenied=channelCapture(channelCollided,true);
    const auto channelState=save(*channelCollided.p);
    check(audible(chNormal)&&channelState.program==0&&
          channelState.channelProgramMask==(1u<<3)&&
          channelState.channelPrograms[3]==9,
          "midblock: channel 4 accepted program 9 with exact override mask");
    check(chNormal==chDenied,
          "midblock: channel 4 NoteOn PCM identical despite denied writer");
    std::cout<<"MIDBLOCK_CHANNEL_AUDIT saved_mask="
             <<channelState.channelProgramMask
             <<" saved_ch4="<<channelState.channelPrograms[3]
             <<" pcm_equal="<<(chNormal==chDenied)<<std::endl;

    // Distinct program points and NoteOns in the same block: a later
    // channel override must not accidentally change the global program
    // or a different MIDI channel while retrying denied writer updates.
    const auto mixedCapture=[](Rig& r,bool denied) {
        std::vector<float> pcm;
        const auto first=[&] {
            Block b;
            b.param(kProgramID,7./127.,16);
            b.param(MidiProgramRouting::ParamID(3),9./127.,32);
            b.note(2,60,48);
            b.note(3,60,64);
            const auto out=b.run(*r.p);
            pcm.insert(pcm.end(),out.begin(),out.end());
        };
        if(denied) {
            RealtimeStateVersion::Writer control(
                r.p->rtStateVersion_,RealtimeStateVersion::Domain::Control);
            require(static_cast<bool>(control),"midblock: mixed writer gate");
            first();
        } else first();
        for(int i=1;i<8;++i) {
            Block next;
            const auto out=next.run(*r.p);
            pcm.insert(pcm.end(),out.begin(),out.end());
        }
        return pcm;
    };
    Rig mixedGood;
    const auto mixedNormal=mixedCapture(mixedGood,false);
    Rig mixedCollided;
    const auto mixedDenied=mixedCapture(mixedCollided,true);
    const auto mixedState=save(*mixedCollided.p);
    check(audible(mixedNormal)&&mixedState.program==7&&
          mixedState.channelProgramMask==(1u<<3)&&
          mixedState.channelPrograms[3]==9,
          "midblock: global 7 + channel 4 override 9 saved coherently");
    check(mixedNormal==mixedDenied,
          "midblock: mixed global/channel NoteOns retain exact PCM during denied writer");
    std::cout<<"MIDBLOCK_MIXED_AUDIT global="<<mixedState.program
             <<" mask="<<mixedState.channelProgramMask
             <<" pcm_equal="<<(mixedNormal==mixedDenied)<<std::endl;
}

void fxPresetAutomationRecall() {
    Rig rig;
    // All 8x8 native Creative choices must survive the host parameter
    // process path into state and exactly the same live 86Box registers.
    for(unsigned rev=0;rev<8;++rev)for(unsigned cho=0;cho<8;++cho) {
        Block update(0);
        update.param(kReverbPresetID,double(rev)/7.);
        update.param(kChorusPresetID,double(cho)/7.);
        update.run(*rig.p);
        const State saved=save(*rig.p);
        const auto pin=rig.p->engines_.Read();
        require(pin.get()&&pin.get()->synth,"no engine to verify FX");
        const auto& core=pin.get()->synth->Core();
        const auto& config=Emu8000Fx::kChorusPresets[cho];
        bool registers=saved.reverbPreset==rev && saved.chorusPreset==cho &&
            core.Read(Emu8000::Reg::INIT1,3)==Emu8000Fx::kReverbParm[rev][0] &&
            core.Read(Emu8000::Reg::INIT3,9)==config.feedback &&
            core.Read(Emu8000::Reg::INIT3,12)==config.delaySamples &&
            core.Read(Emu8000::Reg::INIT4,3)==config.depth;
        check(registers,"P133 VST3 FX both modes + live INIT registers rev="+
                        std::to_string(rev)+" cho="+std::to_string(cho));
    }
    // A denied audio state writer must not drop successfully accepted
    // automation. getState should immediately reconstruct both FX intents.
    {
        RealtimeStateVersion::Writer blocked(
            rig.p->rtStateVersion_,RealtimeStateVersion::Domain::Control);
        Block update(0);
        update.param(kReverbPresetID,7./7.);
        update.param(kChorusPresetID,5./7.);
        update.run(*rig.p);
    }
    // The Control writer has to release before getState can take its own
    // exclusive fallback writer; the audio edit must still be pending here.
    const auto pending=save(*rig.p);
    check(pending.reverbPreset==7&&pending.chorusPreset==5,
          "P133 denied RT writer: save includes latest accepted FX edits");
    { Block replay(0);replay.run(*rig.p); }
    {
        const auto pin=rig.p->engines_.Read();
        require(pin.get()&&pin.get()->synth,"no FX engine after writer release");
        const auto& core=pin.get()->synth->Core();
        check(core.Read(Emu8000::Reg::INIT3,9)==Emu8000Fx::kChorusPresets[5].feedback &&
              core.Read(Emu8000::Reg::INIT1,3)==Emu8000Fx::kReverbParm[7][0],
              "P133 deferred effects replay targets real chip after control writer release");
    }
    // All saved FX presets restore when a new ROM/SF2 engine is published.
    State desired=state();
    desired.reverbPreset=6;desired.chorusPreset=5;
    desired.controls[10]=10000;desired.controls[11]=10000;
    Rig revived(desired);
    check(same(save(*revived.p),desired),"P133 V11 complete state on fresh engine");
    const auto actual=sound(*revived.p);
    const auto expected=referenceSound(desired,0);
    check(audible(actual)&&actual==expected,
          "P133 restored FX exact PCM matches independently configured hardware Synth");
    // A later, different session must restore both parameters and PCM.
    desired.reverbPreset=3;desired.chorusPreset=0;
    require(recall(*revived.p,desired)==kResultOk,"P133 effect recall");
    check(same(save(*revived.p),desired),"P133 new recall overwrites previous FX modes");
    // Note: the running Synth may retain tails from a previous sound().
    // Reinitialize for an independent deterministic PCM comparison.
    Rig fresh(desired);
    check(audible(sound(*fresh.p))&&same(save(*fresh.p),desired),
          "P133 post-recall new project opens and renders with saved FX choices");
}

// P134: CC120 All Sounds Off must not leave the 86Box voice ringing with
// an envelope engine already off but its output volume target still nonzero.
// Unlike CC123 NoteOff, this is channel-specific immediate stop (apart from
// the existing 980-frame FIFO and the hardware 1/64 volume slide).
void cc120PhysicalStopRegression() {
    const auto cc120=AWE125::MidiControlMapping::ParamID(
        0,AWE125::MidiControlMapping::Index(120));
    require(AWE125::MidiControlMapping::Index(120)>=0,"CC120 mapping");
    Rig rig;
    bool started=false;
    {
        Block on;on.note(0,60);
        started|=audible(on.run(*rig.p));
    }
    for(int i=0;i<8;++i) {
        Block b;started|=audible(b.run(*rig.p));
    }
    check(started,"P134: test soundfont voice really plays before CC120");
    {
        Block kill(0);kill.param(cc120,1.);
        kill.run(*rig.p);
    }
    // Consume substantially more than one hardware FIFO publication and
    // the 1/64 volume slide. This is outside the performance measurement.
    double lateEnergy=0.0;
    for(int i=0;i<16;++i) {
        Block b;const auto pcm=b.run(*rig.p);
        if(i>=12)for(float v:pcm)lateEnergy+=double(v)*double(v);
    }
    check(lateEnergy<=1e-8,
          "P134: CC120 leaves no late stuck waveform or ghost chip voice");
    std::cout<<"P134_CC120_LATE_ENERGY "<<lateEnergy<<std::endl;
    // A new note must still play normally after stop. A stuck old 86Box
    // voice may cause a second nonzero chip voice and wrong overlay.
    bool reattacked=false;
    {Block on;on.note(0,61);reattacked|=audible(on.run(*rig.p));}
    for(int i=0;i<4;++i) {Block b;reattacked|=audible(b.run(*rig.p));}
    check(reattacked,"P134: same channel can sound again after CC120");
    // CC120 for channel 1 must not stop an unrelated channel 2 voice.
    Rig isolated;
    {Block start;start.note(0,60);start.note(1,64);start.run(*isolated.p);}
    for(int i=0;i<4;++i){Block b;b.run(*isolated.p);}
    {Block stop(0);stop.param(cc120,1.);stop.run(*isolated.p);}
    bool otherChannelSounds=false;
    for(int i=0;i<8;++i) {
        Block b;otherChannelSounds|=audible(b.run(*isolated.p));
    }
    check(otherChannelSounds,"P134: channel 1 CC120 does not silence channel 2");
}

void exactMissingPresetProcessorRegression() {
    // This is the exact extracted shipping VST3 Processor, with actual
    // synthetic 86Box ROM and independently generated noncontiguous SF2.
    // No UI/candidate catalog mocks: process(), host parameters, event
    // ordering, V11 getState and setState are all exercised.
    for(unsigned bank:{0u,5u,128u}) {
        for(unsigned missing:{63u,100u}) {
            const State wanted=state(bank,missing);
            Rig rig(wanted);
            const auto actual=sound(*rig.p);
            check(!audible(actual),
                "P166 actual Processor missing SF2 program: no PCM bank "+
                std::to_string(bank)+" program "+std::to_string(missing));
            const State persisted=save(*rig.p);
            check(persisted.bank==bank&&persisted.program==missing,
                "P166 invalid program retains its exact host/V11 number");
            const auto engine=rig.p->engines_.Read();
            bool noHeldVoices=false;
            if(engine.get()&&engine.get()->synth) {
                const auto held=engine.get()->synth->CaptureHeldNotes();
                noHeldVoices=std::none_of(held.begin(),held.end(),
                    [](const Synth::HeldNote& n){return n.sequence!=0;});
            }
            check(noHeldVoices,
                "P166 missing program allocates no actual chip voice");
        }
    }
    // Explicitly listed SF2 bank 5, program 9 is still musical.
    Rig valid(state(5,9));
    check(audible(sound(*valid.p)),"P166 real VST3 Processor bank5 program9 audible");
    // Accepted channel-specific Program Change is NOT allowed to inherit
    // the global program or an unrelated ROM instrument for a missing slot.
    {
        Rig missing(state(0,7));
        Block editOnly(0);
        editOnly.param(MidiProgramRouting::ParamID(3),63./127.);
        editOnly.run(*missing.p);
        const auto st=save(*missing.p);
        check((st.channelProgramMask&(1u<<3))!=0 &&
              st.channelPrograms[3]==63 && st.program==7,
              "P166 V11 host per-channel program 63 preserved exactly");
        auto silence=sound(*missing.p,3);
        check(!audible(silence),
              "P166 MIDI channel4 ProgramChange=63 cannot trigger ROM/GM audio");
    }
    // State save/reload must carry the unavailable 63 rather than remapping
    // to ROM or to the first SF2 preset.
    {
        Rig rig(state(5,9));
        require(recall(*rig.p,state(0,63))==kResultOk,
                "P166 absent program project recall");
        const auto roundtrip=save(*rig.p);
        check(roundtrip.bank==0&&roundtrip.program==63,
              "P166 V11 project recall keeps the exact absent MIDI program number");
        // A new fresh project with that recalled tuple must be silent.
        Rig fresh(roundtrip);
        check(!audible(sound(*fresh.p)),
              "P166 exact absent program survives project close/reopen silently");
    }
}

// P167 AUDIT ONLY. Compiles the exact production Processor from Factory.cpp,
// sends MIDI CC0 through a real Steinberg ParameterChanges queue, and measures
// actual 86Box output after NoteOn on channel 10. Two distinct existing
// soundfonts are essential: a generic 'some sound' check cannot detect
// the drum-bank vs melodic-bank substitution.
void p167ChannelTenZeroBank() {
    Rig base0(state(0,0));
    const auto bank0=sound(*base0.p,9);
    Rig base128(state(128,0));
    const auto drums=sound(*base128.p,9);
    check(audible(bank0)&&audible(drums)&&bank0!=drums,
          "P167 independent control: channel10 distinct SF2 bank0 versus bank128 PCM");
    Rig actual(state(128,0));
    // Explicit CC0=0 MUST select SoundFont melodic bank zero, not the
    // untouched default channel-ten drum bank 128.
    {
        Block bankSelect(0);
        constexpr int index=MidiControlMapping::Index(0);
        bankSelect.param(MidiControlMapping::ParamID(9,index),0.);
        bankSelect.run(*actual.p);
    }
    const auto selected=sound(*actual.p,9);
    check(selected==bank0&&selected!=drums,
          "P167 actual VST3 Processor channel10 explicit CC0=0 selects bank0 PCM");
}

int main(int argc,char** argv) {
    try {
        if(argc!=3)return 2;
        assetsDir=argv[2];
        if(std::string(argv[1])=="p167-channel10-bank-zero") p167ChannelTenZeroBank();
        else if(std::string(argv[1])=="cc120-stop") cc120PhysicalStopRegression();
        else if(std::string(argv[1])=="fx-presets") fxPresetAutomationRecall();
        else if(std::string(argv[1])=="p166-exact-presets")
            exactMissingPresetProcessorRegression();
        else if(std::string(argv[1])=="midblock-program") midblockProgramRace();
        else if(std::string(argv[1])=="persistent-controls") persistentControlWriterCollision();
        else if(std::string(argv[1])=="nullswap") {
            Rig r;bool fired=false;
            hook=[&](const char* h){if(!fired&&std::string(h)=="block_pin") {
                fired=true;require(recall(*r.p,state(0,0,false))==kResultOk,"empty asset recall");
            }};
            Block b;b.note();auto pcm=b.run(*r.p);hook={};
            check(!audible(pcm),"engine removal in running block returns digital silence without crash");
        } else deterministic();
        std::cout<<"RESULT checks="<<checks<<" failed="<<failures<<std::endl;
        return failures?1:0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<std::endl;return 2;}
}
