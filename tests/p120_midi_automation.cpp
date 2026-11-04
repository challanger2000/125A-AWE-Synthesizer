#include "MidiQueueOrdering.h"
#include "MidiProgramRouting.h"
#include "MidiLiveState.h"
#include "MasterOutput.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <utility>
#include <vector>
using namespace AWE125;
struct Event {std::uint32_t id;int ordinal;int offset;int value;};
static bool test(bool condition,const char* message) {
    std::cout<<(condition?"PASS: ":"FAIL: ")<<message<<"\n";
    return condition;
}
struct Recorder {
    std::vector<std::pair<int,int>> cc;
    void ControlChange(uint8_t, uint8_t number,uint8_t value) {
        cc.emplace_back(number,value);
    }
    void PitchBend(uint8_t,int16_t){}
    void ChannelPressure(uint8_t,uint8_t){}
    bool has(int ccNumber,int value) const {
        for(const auto& c:cc)
            if(c.first==ccNumber&&c.second==value)return true;
        return false;
    }
};
int main() {
    bool ok=true;
    constexpr auto id=[](int cc) {
        return MidiControlMapping::ParamID(
            0,static_cast<uint32_t>(MidiControlMapping::Index(cc)));
    };
    std::vector<Event> queues{{id(101),0,0,0},
                              {id(100),1,0,0},
                              {id(6),2,0,12}};
    std::vector<int> ordered;
    while(!queues.empty()) {
        auto it=std::min_element(queues.begin(),queues.end(),
            [](const Event& a,const Event& b) {
                return MidiQueueOrdering::Earlier(a.offset,a.id,a.ordinal,
                                                  b.offset,b.id,b.ordinal);
            });
        ordered.push_back(it->value);
        *it=queues.back();queues.pop_back(); // same removal as production
    }
    ok&=test(ordered==std::vector<int>{0,0,12},
        "RPN 101, RPN 100, Data Entry keep dependency order under cursor swaps");
    for(unsigned ch=0;ch<16;++ch)
        ok&=test(MidiProgramRouting::Channel(MidiProgramRouting::ParamID(ch))
                     ==static_cast<int>(ch),
                 "16 MIDI program parameter IDs map independently");
    ok&=test(MidiProgramRouting::Channel(1000)==-1 &&
             MidiProgramRouting::Channel(2000)==-1,
             "existing global Program and MIDI CC IDs are never reinterpreted");
    MidiLiveState live;
    live.Accept(0,0,5./127.);
    Recorder old;live.Replay(old);
    ok&=test(old.has(0,5),"MIDI CC0 initially selects bank 5");
    live.BrowserBankSelected(); // later UI or project Recall bank 3
    Recorder after;live.Replay(after);
    ok&=test(!after.has(0,5),
        "later browser/Recall bank overrides older CC0 after engine swap");
    live.Accept(0,0,7./127.);
    Recorder again;live.Replay(again);
    ok&=test(again.has(0,7),
        "MIDI CC0 sent after browser selection becomes effective again");
    struct Points{std::vector<std::pair<int32_t,double>> p;};
    const auto read=+[](void* ctx,int32_t index,int32_t& sample,double& value){
        const auto& v=static_cast<Points*>(ctx)->p;
        if(index<0||static_cast<std::size_t>(index)>=v.size())return false;
        sample=v[index].first;value=v[index].second;return true;
    };
    Points sparse{{{127,1.}}},dense;
    for(int i=0;i<128;++i)
        dense.p.emplace_back(i,0.5+(i+1)/256.);
    MasterOutput::Curve curveSparse,curveDense;
    curveSparse.reset(&sparse,read,1,.5);
    curveDense.reset(&dense,read,128,.5);
    bool equal=true;
    for(int n=0;n<128;++n) {
        const auto pa=MidiControlMapping::PitchBend(curveSparse.valueAt(n));
        const auto pb=MidiControlMapping::PitchBend(curveDense.valueAt(n));
        if(pa!=pb)equal=false;
    }
    ok&=test(equal,
        "128-frame sparse vs dense continuous VST3 pitchbend yields identical per-sample MIDI bends");
    std::cout<<(ok?"P120_MIDI_AUTOMATION_PASS":"P120_MIDI_AUTOMATION_FAIL")<<"\n";
    return ok?0:1;
}
