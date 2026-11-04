#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>

namespace AWE125::MasterOutput {

// Independent of the 12 SF2 enhancement knobs (1100-1111).
// The master volume is post-chip only: 100% is exactly unity, 0% is mute.
inline constexpr uint32_t kParamID=1003;
inline constexpr uint32_t kScale=10000u;
inline constexpr uint32_t kDefault=kScale;

// VST3 continuous parameter points are a piecewise-linear curve. The prior
// block's target is the implicit point at frame -1. Reader is a direct callback
// to IParamValueQueue::getPoint; no allocations in the audio callback.
class Curve {
public:
    using Reader=bool(*)(void*,int32_t,int32_t&,double&);
    void reset(void* context,Reader reader,int32_t count,double initial) noexcept {
        context_=context;reader_=reader;
        count_=std::max<int32_t>(0,count);index_=0;
        previousFrame_=-1;previousValue_=std::clamp(initial,0.,1.);
        hasNext_=false;
        advance();
    }
    double valueAt(int32_t frame) noexcept {
        frame=std::max<int32_t>(0,frame);
        while(hasNext_&&frame>nextFrame_) {
            previousFrame_=nextFrame_;
            previousValue_=nextValue_;
            advance();
        }
        if(!hasNext_)return previousValue_;
        const int32_t span=nextFrame_-previousFrame_;
        if(span<=0)return nextValue_;
        const double portion=std::clamp(
            double(frame-previousFrame_)/double(span),0.,1.);
        return std::clamp(previousValue_+
            (nextValue_-previousValue_)*portion,0.,1.);
    }
private:
    void advance() noexcept {
        hasNext_=false;
        while(reader_&&index_<count_) {
            int32_t offset=0;double value=0.;
            if(reader_(context_,index_++,offset,value)&&
               offset>=0&&std::isfinite(value)) {
                if(offset<previousFrame_)continue;
                if(offset==previousFrame_) {
                    previousValue_=std::clamp(value,0.,1.);
                    continue;
                }
                nextFrame_=offset;
                nextValue_=std::clamp(value,0.,1.);
                hasNext_=true;
                return;
            }
        }
    }
    void* context_=nullptr;
    Reader reader_=nullptr;
    int32_t count_=0,index_=0,previousFrame_=-1,nextFrame_=0;
    double previousValue_=1.,nextValue_=1.;
    bool hasNext_=false;
};

// A fixed 64-output-frame linear ramp avoids zipper jumps. A note keeps
// progressing inside the EMU8000 while muted; changing the master cannot
// affect chip register writes, velocity, envelopes, bank loading or ROM.
class Gain {
public:
    float current() const noexcept {return current_;}
    float target() const noexcept {return target_;}
    void restore(uint32_t stored) noexcept {
        current_=target_=fromStored(stored);
        step_=0.f;
        remaining_=0;
    }
    void setTarget(uint32_t stored) noexcept {
        const float next=fromStored(stored);
        if(next==target_)return;
        target_=next;
        remaining_=64;
        step_=(target_-current_)/64.f;
    }
    float next() noexcept {
        if(remaining_>0) {
            --remaining_;
            current_ = remaining_ ? current_+step_ : target_;
        }
        return current_;
    }
    // Host automation already provides the exact linear trajectory.
    // Do not restart the 64-sample dezipper for every interpolated frame:
    // doing so turns a 64-frame fade into a low-pass decay ending at 62.5%.
    // This resets the manual-change ramp ONLY while an automation queue
    // explicitly owns the parameter.
    float nextAutomated(double normalized) noexcept {
        const float value=static_cast<float>(std::clamp(normalized,0.,1.));
        current_=target_=value;
        step_=0.f;
        remaining_=0;
        return value;
    }
    static float fromStored(uint32_t value) noexcept {
        return static_cast<float>(std::min(value,kScale))/static_cast<float>(kScale);
    }
private:
    float current_=1.f,target_=1.f,step_=0.f;
    int remaining_=0;
};
} // namespace AWE125::MasterOutput
