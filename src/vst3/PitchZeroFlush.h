#pragma once
#include "MidiLiveState.h"
#include <array>
#include <algorithm>
#include <cmath>
#include <cstdint>

namespace AWE125::PitchZeroFlush {
// Applies legal zero-frame pitchbend points with *last point wins*
// semantics. This exact helper is used by the real VST3 process() callback.
// A later NoteOn inherits the committed bend even though no PCM was rendered.
template<class Queue,class Reader,class Receiver>
void Commit(const std::array<Queue*,16>& queues,Reader read,
            MidiLiveState& live,Receiver&& receive) noexcept {
    for(unsigned channel=0;channel<queues.size();++channel) {
        auto* const queue=queues[channel];
        if(!queue)continue;
        bool hasValue=false;
        double normalized=0.;
        for(int32_t i=0;i<queue->getPointCount();++i) {
            int32_t offset=-1;
            double value=0.;
            if(read(queue,i,offset,value)&&offset==0&&std::isfinite(value)) {
                normalized=std::clamp(value,0.,1.);
                hasValue=true;
            }
        }
        if(!hasValue)continue;
        live.Accept(channel,129,normalized);
        receive(static_cast<uint8_t>(channel),
                MidiControlMapping::PitchBend(normalized));
    }
}
} // namespace AWE125::PitchZeroFlush
