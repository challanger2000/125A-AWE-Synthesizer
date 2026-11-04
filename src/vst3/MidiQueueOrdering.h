#pragma once
#include "MidiControlMapping.h"
#include <cstdint>
namespace AWE125::MidiQueueOrdering {
// VST3 queues are per parameter. Their physical array order is not a
// recoverable MIDI stream. At equal sample offset we establish the minimal
// deterministic dependency order needed for RPN 0/0 Data Entry:
// CC101 (RPN MSB), CC100 (RPN LSB), then CC6 (Data Entry).
// Within the same priority group, preserve original queue ordinal even
// though the processor swaps cursor slots for efficient removal.
constexpr int Priority(std::uint32_t id) noexcept {
    const auto d=MidiControlMapping::Decode(id);
    if(!d.valid)return 3;
    switch(d.number) {
        case 101:return 0;
        case 100:return 1;
        case 6:return 2;
        default:return 3;
    }
}
constexpr bool Earlier(int aOffset,std::uint32_t aId,int aOrder,
                       int bOffset,std::uint32_t bId,int bOrder) noexcept {
    if(aOffset!=bOffset)return aOffset<bOffset;
    const int pa=Priority(aId),pb=Priority(bId);
    return pa!=pb?pa<pb:aOrder<bOrder;
}
}
