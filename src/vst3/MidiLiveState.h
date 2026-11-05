#pragma once
#include "MidiControlMapping.h"
#include <array>
#include <cstddef>
#include <cstdint>
namespace AWE125 {
class MidiLiveState {
public:
    struct Channel {
        std::array<double,MidiControlMapping::kControls.size()> values{};
        std::array<bool,MidiControlMapping::kControls.size()> touched{};
        bool rangeTouched=false;
        uint8_t pitchRange=2;
        uint64_t bankMsbSequence=0,bankLsbSequence=0;
        Channel() noexcept {
            for(std::size_t i=0;i<values.size();++i)
                values[i]=MidiControlMapping::InitialNormalized(MidiControlMapping::kControls[i]);
        }
    };
    void Accept(unsigned channel,int number,double normalized) noexcept {
        if(channel>=channels_.size())return;
        const auto idx=MidiControlMapping::Index(number);
        if(idx<0)return;
        Channel& ch=channels_[channel];
        const double x=normalized<0?0:normalized>1?1:normalized;
        const uint8_t b=MidiControlMapping::Byte(x);
        if(number==120||number==123)return; // event-only; NEVER replay
        if(number==121) {
            ResetControllers(ch);
            return;
        }
        ch.values[static_cast<std::size_t>(idx)]=x;
        ch.touched[static_cast<std::size_t>(idx)]=true;
        if(number==6 && MidiControlMapping::Byte(ch.values[MidiControlMapping::Index(101)])==0 &&
            MidiControlMapping::Byte(ch.values[MidiControlMapping::Index(100)])==0) {
            ch.pitchRange=b;
            ch.rangeTouched=true;
        }
    }
    // MIDI CC0/CC32 are CHANNEL-local, not global browser selections.
    // All three kinds of bank events share the BankOrder chronological stamp.
    void AcceptBank(unsigned channel,int number,double normalized,
                    uint64_t sequence) noexcept {
        if(channel>=channels_.size()||(number!=0&&number!=32))return;
        Accept(channel,number,normalized);
        if(number==0)channels_[channel].bankMsbSequence=sequence;
        else channels_[channel].bankLsbSequence=sequence;
    }
    // P120 bank precedence: a later explicit GUI or project-recall bank
    // supersedes older CC0/CC32 values. Do not replay the older CC0,
    // because Synth::ControlChange(0) disables browserBankActive.
    // A subsequent MIDI CC0 will mark its own channel touched again and win.
    void BrowserBankSelected(uint64_t selectionSequence=~uint64_t{0}) noexcept {
        constexpr auto msb=static_cast<std::size_t>(MidiControlMapping::Index(0));
        constexpr auto lsb=static_cast<std::size_t>(MidiControlMapping::Index(32));
        for(auto& ch:channels_) {
            if(ch.bankMsbSequence<=selectionSequence)ch.touched[msb]=false;
            if(ch.bankLsbSequence<=selectionSequence)ch.touched[lsb]=false;
        }
    }
    // A global bank select sets browserBankActive on ALL melodic channels.
    // Re-apply ONLY newer channel-specific CC0/CC32, never a sibling channel.
    template<class Receiver>
    void ReplayNewerBankControls(Receiver& receiver,
                                 uint64_t globalSequence) const noexcept {
        const auto msb=static_cast<std::size_t>(MidiControlMapping::Index(0));
        const auto lsb=static_cast<std::size_t>(MidiControlMapping::Index(32));
        for(unsigned channel=0;channel<channels_.size();++channel) {
            const auto& ch=channels_[channel];
            if(ch.touched[msb]&&ch.bankMsbSequence>globalSequence)
                receiver.ControlChange(static_cast<uint8_t>(channel),0,
                    MidiControlMapping::Byte(ch.values[msb]));
            if(ch.touched[lsb]&&ch.bankLsbSequence>globalSequence)
                receiver.ControlChange(static_cast<uint8_t>(channel),32,
                    MidiControlMapping::Byte(ch.values[lsb]));
        }
    }
    const Channel& Get(unsigned channel) const noexcept {return channels_[channel];}
    // Replaying only changed controls preserves the Synth's hardware defaults
    // and, crucially, doesn't accidentally override SelectBrowserBank via CC0=0.
    template<class Receiver>
    void Replay(Receiver& receiver) const noexcept {
        for(unsigned ch=0;ch<16;++ch) {
            const Channel& state=channels_[ch];
            const auto send=[&](int number,uint8_t value) {
                receiver.ControlChange(static_cast<uint8_t>(ch),
                    static_cast<uint8_t>(number),value);
            };
            for(const int n:{0,32,1,7,10,11,91,93}) {
                const int idx=MidiControlMapping::Index(n);
                if(state.touched[static_cast<std::size_t>(idx)])
                    send(n,MidiControlMapping::Byte(state.values[static_cast<std::size_t>(idx)]));
            }
            if(state.rangeTouched) {
                send(101,0);send(100,0);send(6,state.pitchRange);
            }
            for(const int n:{101,100}) {
                const int idx=MidiControlMapping::Index(n);
                if(state.touched[static_cast<std::size_t>(idx)])
                    send(n,MidiControlMapping::Byte(state.values[static_cast<std::size_t>(idx)]));
                else if(state.rangeTouched)send(n,127);
            }
            {
                const int idx=MidiControlMapping::Index(64);
                if(state.touched[static_cast<std::size_t>(idx)])
                    send(64,MidiControlMapping::Byte(state.values[static_cast<std::size_t>(idx)]));
            }
            {
                const int idx=MidiControlMapping::Index(128);
                if(state.touched[static_cast<std::size_t>(idx)])
                    receiver.ChannelPressure(static_cast<uint8_t>(ch),
                        MidiControlMapping::Byte(state.values[static_cast<std::size_t>(idx)]));
            }
            {
                const int idx=MidiControlMapping::Index(129);
                if(state.touched[static_cast<std::size_t>(idx)])
                    receiver.PitchBend(static_cast<uint8_t>(ch),
                        MidiControlMapping::PitchBend(state.values[static_cast<std::size_t>(idx)]));
            }
        }
    }
private:
    static void ResetControllers(Channel& ch) noexcept {
        for(const int n:{1,11,64,128,129}) {
            const auto idx=static_cast<std::size_t>(MidiControlMapping::Index(n));
            ch.values[idx]=MidiControlMapping::InitialNormalized(MidiControlMapping::kControls[idx]);
            ch.touched[idx]=true;
        }
    }
    std::array<Channel,16> channels_{};
};
} // namespace AWE125
