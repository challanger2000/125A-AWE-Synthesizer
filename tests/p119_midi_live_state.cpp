#include "MidiLiveState.h"
#include <array>
#include <iostream>
#include <vector>
struct Recorder {
    struct Event {int channel,number,value;};
    std::vector<Event> events;
    void ControlChange(uint8_t ch,uint8_t cc,uint8_t v){events.push_back({ch,cc,v});}
    void PitchBend(uint8_t ch,int16_t value){events.push_back({ch,129,value});}
    void ChannelPressure(uint8_t ch,uint8_t value){events.push_back({ch,128,value});}
    bool has(int channel,int number,int value) const {
        for(const auto& e:events)
            if(e.channel==channel&&e.number==number&&e.value==value)return true;
        return false;
    }
    bool hasNumber(int number) const {
        for(const auto& e:events)if(e.number==number)return true;
        return false;
    }
};
static bool check(bool yes,const char* label) {
    std::cout<<(yes?"PASS: ":"FAIL: ")<<label<<"\n";return yes;
}
int main(){
    bool ok=true;
    AWE125::MidiLiveState saved;
    Recorder blank;saved.Replay(blank);
    ok&=check(blank.events.empty(),"default state does not override browser bank or hardware defaults");
    saved.Accept(0,64,1.);
    saved.Accept(0,129,.8);
    saved.Accept(1,11,32./127.);
    saved.Accept(2,0,5./127.);
    saved.Accept(3,101,0.);
    saved.Accept(3,100,0.);
    saved.Accept(3,6,12./127.);
    saved.Accept(4,120,1.);
    saved.Accept(4,123,1.);
    Recorder first;saved.Replay(first);
    ok&=check(first.has(0,64,127)&&first.has(0,129,4914),
              "sustain and pitch bend survive engine replacement");
    ok&=check(first.has(1,11,32)&&first.has(2,0,5),
              "expression and intentionally selected MIDI bank are per-channel");
    ok&=check(first.has(3,101,0)&&first.has(3,100,0)&&first.has(3,6,12),
              "RPN0/0 pitch bend range survived engine replacement");
    ok&=check(!first.hasNumber(120)&&!first.hasNumber(123),
              "one-shot all-sounds-off and all-notes-off never replayed");
    const auto count=first.events.size();
    Recorder second;saved.Replay(second);
    ok&=check(second.events.size()==count,
              "repeated engine replacements receive equivalent MIDI snapshot");
    saved.Accept(0,121,1.);
    Recorder reset;saved.Replay(reset);
    ok&=check(reset.has(0,64,0)&&reset.has(0,129,0)&&
              reset.has(0,11,127)&&reset.has(0,1,0),
              "reset controllers resets pedal pitch expression and modulation");
    ok&=check(!reset.has(1,64,0),
              "one-channel reset does not alter unrelated MIDI channels");
    std::cout<<(ok?"P119_MIDI_PERSISTENCE_PASS":"P119_MIDI_PERSISTENCE_FAIL")<<"\n";
    return ok?0:1;
}
