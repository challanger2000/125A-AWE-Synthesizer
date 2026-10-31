#include "Opl3Midi.h"
#include <algorithm>
#include <cmath>
#include <limits>

namespace AWE125 {
namespace {
constexpr std::array<uint8_t,9> kOperators{0,1,2,8,9,10,16,17,18};
constexpr double kClock=49716.0; // YMF262 nominal frequency constant
uint16_t reg(size_t voice,uint16_t base,uint16_t slot=0) {
    return static_cast<uint16_t>((voice>=9?0x100:0)+base+slot);
}
}

Opl3Midi::Opl3Midi(uint32_t rate,uint32_t latency,bool cqmBackend)
  : chip_(cqmBackend ? nullptr : std::make_unique<opl3_chip>()),
    cqm_(cqmBackend ? std::make_unique<cqm_t>() : nullptr),
    delayed_(size_t{latency}*2,0),latencyFrames_(latency) {
    if(cqm_) {
        // Creative CQM native clock ~49.716 kHz; output is host rate.
        // Genuine independent Nuke.YKT CQM core, not a Yamaha OPL3 variant.
        CQM_Reset(cqm_.get(),49716u,std::clamp(rate,8000u,384000u));
    } else {
        OPL3_Reset(chip_.get(),std::clamp(rate,8000u,384000u));
    }
    Write(0x105,1); // YMF262 mode (18 x two-operator channels)
    Write(0x104,0); // 4-op mode disabled
    Write(0xbd,0); // melodic, no percussion voices
    velocityAtten_[0]=63;
    for(int v=1;v<=127;++v) {
        // TL step is nominal 0.75 dB, carrier attenuation depends on velocity.
        const double db=-20.0*std::log10(double(v)/127.0);
        velocityAtten_[v]=static_cast<uint8_t>(std::clamp(
            int(std::lround(db/0.75)),0,63));
    }
}
Opl3Midi::~Opl3Midi()=default;
bool Opl3Midi::LoadMelodicIbk(const std::string& path,std::string& error) {
    IbkBank candidate;
    if(!candidate.Load(path,error))return false;
    bank_=std::move(candidate);
    return true;
}
bool Opl3Midi::LoadPercussionIbk(const std::string& path,std::string& error) {
    IbkBank candidate;
    if(!candidate.Load(path,error))return false;
    // IBK rhythm voice byte 11: 6=BD,7=SD,8=TT,9=CY,10=HH.
    // Reject non-rhythm banks rather than claiming drum coverage.
    bool hasRhythm=false;
    for(int n=0;n<128;++n) {
        const auto type=candidate.At(static_cast<uint8_t>(n)).registers[11];
        hasRhythm|=type>=6 && type<=10;
    }
    if(!hasRhythm) {error="IBK: no valid YMF262 rhythm percussion entries";return false;}
    AllNotesOff();
    drumBank_=std::move(candidate);
    rhythmRegister_=0x20;
    Write(0xbd,rhythmRegister_); // real YMF262 rhythm mode
    // B6/B7/B8 key-on bits must stay clear throughout rhythm mode.
    for(size_t i=6;i<9;++i) {
        const auto& v=voices_[i];
        Write(reg(i,0xb0),static_cast<uint8_t>((v.fnum>>8)|(v.block<<2)));
    }
    return true;
}
void Opl3Midi::ProgramChange(uint8_t channel,uint8_t program) {
    if(channel<16 && program<128)channels_[channel].program=program;
}
void Opl3Midi::SetDrumPitch(uint8_t channel,uint8_t note) {
    const double hz=440.0*std::pow(2.0,(double(note)-69.0)/12.0);
    uint8_t block=0;
    double fnum=hz*std::ldexp(1.0,20)/kClock;
    while(fnum>1023.0&&block<7){fnum*=0.5;++block;}
    const uint16_t f=static_cast<uint16_t>(std::clamp(int(std::lround(fnum)),0,1023));
    Write(reg(channel,0xa0),static_cast<uint8_t>(f&0xff));
    // These channels are drum voices, NEVER use Bx melodic key-on.
    Write(reg(channel,0xb0),static_cast<uint8_t>((f>>8)|(block<<2)));
}
void Opl3Midi::DrumNoteOn(uint8_t note,uint8_t velocity) {
    if(!drumBank_||note>=128||velocity==0)return;
    const auto& p=drumBank_->At(note).registers;
    const uint8_t type=p[11];
    if(type<6||type>10)return; // no fake GM-to-rhythm substitutions
    const unsigned drum=type-6;
    constexpr std::array<uint8_t,5> keyBits{0x10,0x08,0x04,0x02,0x01};
    constexpr std::array<uint8_t,5> channels{6,7,8,8,7};
    constexpr std::array<uint8_t,5> slots{0x10,0x14,0x12,0x15,0x11};
    constexpr std::array<bool,5> carriers{true,true,false,true,false};
    const uint8_t bit=keyBits[drum];
    // Hardware has only ONE instance of each drum, so retriggers replace it.
    rhythmRegister_&=static_cast<uint8_t>(~bit);
    Write(0xbd,rhythmRegister_); // real drum-envelope KEY OFF
    const uint8_t ch=channels[drum],op=slots[drum];
    const auto writeOp=[&](uint8_t slot,bool carrier) {
        const int delta=carrier?1:0;
        const uint8_t tl=p[2+delta];
        // Scale carrier level while preserving the patch's KSL bits.
        const int db=std::clamp(int(std::lround(
            -20.0*std::log10(double(velocity)/127.0)/0.75)),0,63);
        Write(reg(ch,0x20,slot),p[0+delta]);
        Write(reg(ch,0x40,slot),static_cast<uint8_t>(
            (tl&0xc0)|std::min(63,int(tl&0x3f)+db)));
        Write(reg(ch,0x60,slot),p[4+delta]);
        Write(reg(ch,0x80,slot),p[6+delta]);
        Write(reg(ch,0xe0,slot),p[8+delta]);
    };
    if(drum==0) {
        writeOp(0x10,false);writeOp(0x13,true);
    } else {
        writeOp(op,carriers[drum]);
    }
    Write(reg(ch,0xc0),static_cast<uint8_t>((p[10]&0x0f)|0x30));
    const uint8_t pitch=static_cast<uint8_t>(std::clamp(
        p[13]!=0?int(p[13]):int(note)+int(static_cast<int8_t>(p[12])),0,127));
    SetDrumPitch(ch,pitch);
    drums_[drum]={true,note};
    rhythmRegister_|=bit;
    Write(0xbd,rhythmRegister_); // distinct real BD/SD/TT/CY/HH key
}
void Opl3Midi::DrumNoteOff(uint8_t note) {
    constexpr std::array<uint8_t,5> bits{0x10,0x08,0x04,0x02,0x01};
    for(size_t i=0;i<drums_.size();++i)
        if(drums_[i].pressed&&drums_[i].note==note) {
            drums_[i].pressed=false;
            rhythmRegister_&=static_cast<uint8_t>(~bits[i]);
            Write(0xbd,rhythmRegister_);
        }
}
void Opl3Midi::AllDrumsOff() {
    if(!drumBank_)return;
    for(auto& drum:drums_)drum.pressed=false;
    rhythmRegister_=0x20;
    Write(0xbd,rhythmRegister_);
}
void Opl3Midi::Write(uint16_t address,uint8_t value) {
    if(cqm_)CQM_WriteReg(cqm_.get(),address,value);
    else OPL3_WriteReg(chip_.get(),address,value);
}
void Opl3Midi::KeyOff(size_t i) {
    if(i>=kVoices)return;
    auto& v=voices_[i];
    if(v.allocated)
        Write(reg(i,0xb0),static_cast<uint8_t>((v.fnum>>8)|(v.block<<2)));
    v.pressed=false;v.held=false;
}
void Opl3Midi::UpdatePitch(size_t i) {
    auto& v=voices_[i];
    if(!v.allocated)return;
    const double bend=double(channels_[v.channel].bend)*2.0/8192.0;
    const double hz=440.0*std::pow(2.0,(double(v.pitchNote)-69.0+bend)/12.0);
    uint8_t block=0;
    double fnum=hz*std::ldexp(1.0,20)/kClock;
    while(fnum>1023.0&&block<7){fnum*=0.5;++block;}
    v.fnum=static_cast<uint16_t>(std::clamp(int(std::lround(fnum)),0,1023));
    v.block=block;
    Write(reg(i,0xa0),static_cast<uint8_t>(v.fnum&255));
    Write(reg(i,0xb0),static_cast<uint8_t>(
        (v.fnum>>8)|(block<<2)|((v.pressed||v.held)?0x20:0)));
}
void Opl3Midi::UpdateLevel(size_t i) {
    const auto& v=voices_[i];
    if(!v.allocated)return;
    const auto& ch=channels_[v.channel];
    const int amplitude=std::clamp(
        (int(v.velocity)*int(ch.volume)*int(ch.expression))/(127*127),0,127);
    const uint8_t total=static_cast<uint8_t>(std::min(63,
        int(v.carrierKslTl&0x3f)+int(velocityAtten_[amplitude])));
    // Restore original patch's KSL upper two bits. At full MIDI velocity
    // and neutral channel level this is bit-identical to the IBK carrier TL.
    Write(reg(i,0x40,static_cast<uint16_t>(kOperators[i%9]+3)),
          static_cast<uint8_t>((v.carrierKslTl&0xc0)|total));
}
void Opl3Midi::StartVoice(size_t i,uint8_t channel,uint8_t note,uint8_t velocity) {
    KeyOff(i);
    auto& v=voices_[i];
    v.allocated=true;v.pressed=true;v.held=false;
    v.channel=channel;v.note=note;v.pitchNote=note;v.velocity=velocity;v.age=++age_;
    const uint16_t op=kOperators[i%9];
    // .IBK byte layout: MOD/CAR 20, 40, 60, 80, E0 register pairs,
    // followed by feedback/connection byte. Preserve the real patch bytes.
    // Without a user-supplied bank retain the one documented test patch.
    const std::array<uint8_t,16> fallback{
        0x01,0x01,0x20,0x00,0xf4,0xf4,0x24,0x24,0x00,0x00,0x02,0,0,0,0,0
    };
    const auto& patch=bank_?bank_->At(channels_[channel].program).registers:fallback;
    Write(reg(i,0x20,op),patch[0]); Write(reg(i,0x20,op+3),patch[1]);
    Write(reg(i,0x40,op),patch[2]);
    v.carrierKslTl=patch[3];
    Write(reg(i,0x60,op),patch[4]); Write(reg(i,0x60,op+3),patch[5]);
    Write(reg(i,0x80,op),patch[6]); Write(reg(i,0x80,op+3),patch[7]);
    Write(reg(i,0xe0,op),patch[8]); Write(reg(i,0xe0,op+3),patch[9]);
    Write(reg(i,0xc0),static_cast<uint8_t>((patch[10]&0x0f)|0x30));
    // SBI/IBK melodic transpose is signed 8-bit at index 12.
    // Percussion/rhythm IBK requires a separate physical drum-mode implementation.
    if(bank_)v.pitchNote=static_cast<uint8_t>(std::clamp(
        int(note)+int(static_cast<int8_t>(patch[12])),0,127));
    UpdateLevel(i);UpdatePitch(i); // B0 key-on last
}
void Opl3Midi::NoteOn(uint8_t channel,uint8_t note,uint8_t velocity) {
    if(channel>=16||note>127)return;
    if(velocity==0){NoteOff(channel,note);return;}
    if(channel==9&&drumBank_){DrumNoteOn(note,velocity);return;}
    size_t chosen=kVoices;
    for(size_t i=0;i<kVoices;++i)
        if(!voices_[i].allocated&&(!drumBank_||i<6||i>=9)){chosen=i;break;}
    if(chosen==kVoices) {
        uint64_t oldest=std::numeric_limits<uint64_t>::max();
        for(size_t i=0;i<kVoices;++i) {
            const auto& v=voices_[i];
            if((!drumBank_||i<6||i>=9)&&!v.pressed&&!v.held&&v.age<oldest){oldest=v.age;chosen=i;}
        }
    }
    if(chosen==kVoices) {
        uint64_t oldest=std::numeric_limits<uint64_t>::max();
        for(size_t i=0;i<kVoices;++i)
            if((!drumBank_||i<6||i>=9)&&voices_[i].age<oldest){oldest=voices_[i].age;chosen=i;}
    }
    StartVoice(chosen,channel,note,velocity);
}
void Opl3Midi::NoteOff(uint8_t channel,uint8_t note) {
    if(channel>=16||note>127)return;
    if(channel==9&&drumBank_){DrumNoteOff(note);return;}
    size_t chosen=kVoices;uint64_t oldest=std::numeric_limits<uint64_t>::max();
    for(size_t i=0;i<kVoices;++i) {
        const auto& v=voices_[i];
        if(v.allocated&&v.pressed&&v.channel==channel&&v.note==note
           &&v.age<oldest){oldest=v.age;chosen=i;}
    }
    if(chosen==kVoices)return;
    voices_[chosen].pressed=false;
    if(channels_[channel].sustain)voices_[chosen].held=true;
    else KeyOff(chosen);
}
void Opl3Midi::AllNotesOff() {
    for(size_t i=0;i<kVoices;++i)KeyOff(i);
    for(auto& ch:channels_)ch.sustain=false;
    AllDrumsOff();
}
void Opl3Midi::ControlChange(uint8_t channel,uint8_t cc,uint8_t value) {
    if(channel>=16)return;
    if(channel==9&&drumBank_) {
        if(cc==120||cc==123||cc==121)AllDrumsOff();
        return;
    }
    auto& ch=channels_[channel];
    if(cc==64) {
        const bool on=value>=64;
        if(ch.sustain&&!on)
            for(size_t i=0;i<kVoices;++i)
                if(voices_[i].allocated&&voices_[i].channel==channel&&
                   voices_[i].held)KeyOff(i);
        ch.sustain=on;
    } else if(cc==7||cc==11) {
        if(cc==7)ch.volume=value;else ch.expression=value;
        for(size_t i=0;i<kVoices;++i)
            if(voices_[i].allocated&&voices_[i].channel==channel)UpdateLevel(i);
    } else if(cc==120||cc==123) {
        for(size_t i=0;i<kVoices;++i)
            if(voices_[i].allocated&&voices_[i].channel==channel)KeyOff(i);
        ch.sustain=false;
    } else if(cc==121) {
        ControlChange(channel,64,0);
        ch.volume=100;ch.expression=127;ch.bend=0;
        for(size_t i=0;i<kVoices;++i)
            if(voices_[i].allocated&&voices_[i].channel==channel) {
                UpdatePitch(i);UpdateLevel(i);
            }
    }
}
void Opl3Midi::PitchBend(uint8_t channel,int16_t bend) {
    if(channel>=16)return;
    if(channel==9&&drumBank_)return;
    channels_[channel].bend=static_cast<int16_t>(std::clamp(int(bend),-8192,8191));
    for(size_t i=0;i<kVoices;++i)
        if(voices_[i].allocated&&voices_[i].channel==channel)UpdatePitch(i);
}
void Opl3Midi::RenderBlock(int16_t* out,uint32_t frames) {
    if(!out||frames==0)return;
    if(!latencyFrames_) {
        if(cqm_)CQM_GenerateStream(cqm_.get(),out,frames);
        else OPL3_GenerateStream(chip_.get(),out,frames);
        return;
    }
    for(uint32_t i=0;i<frames;++i) {
        int16_t next[2]{};
        if(cqm_)CQM_GenerateResampled(cqm_.get(),next);
        else OPL3_GenerateResampled(chip_.get(),next);
        const size_t j=size_t{2}*delayIndex_;
        out[i*2]=delayed_[j];out[i*2+1]=delayed_[j+1];
        delayed_[j]=next[0];delayed_[j+1]=next[1];
        if(++delayIndex_==latencyFrames_)delayIndex_=0;
    }
}
uint32_t Opl3Midi::PressedVoices() const {
    return static_cast<uint32_t>(std::count_if(voices_.begin(),voices_.end(),
        [](const Voice& v){return v.pressed;}))
        +static_cast<uint32_t>(std::count_if(drums_.begin(),drums_.end(),
        [](const Drum& d){return d.pressed;}));
}
} // namespace AWE125
