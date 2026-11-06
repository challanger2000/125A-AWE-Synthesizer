#pragma once
#include <cstdint>
// Diagnostic DLL only. Plain data across the ABI; reads never flush chip I/O.
struct P135Voices {
    uint32_t allocated=0, nonzero=0, envelopes=0, held=0, pending=0;
    uint32_t frameInBlock=0, chipPosition=0;
    uint64_t generation=0;
};
using P135ReadVoices=int(*)(void*,P135Voices*);
using P135HeapControl=void(*)();
