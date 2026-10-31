# AWE-P05 — 44.1/48/96kHz streaming and allocation-free native rendering

**Status: native Windows x64 CI PASS — [Actions #41231977541](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41231977541), 4/4 tests. NOT a VST3/release PASS.**

- Added active `Emu8000.h`, `Emu8000.cpp` and `Emu8000Effects.h` under `src/engine/`. Pristine upstream remains byte-for-byte unchanged.
- `awe32_chip_safety` now compiles and links the active `Emu8000Core`, `Synth`, SoundFont reader and patched 86Box chip implementation together.
- Replaced the native renderer's per-call `std::vector::assign` with fixed 64-frame effect-send buffers.
- Added per-instance two-frame streaming linear sample-rate conversion; no resize, erase, or dynamic memory allocation during `RenderBlock`. Native 44.1 kHz routes 86Box int32 directly to clipped int16, avoiding float conversion.
- Rendering advances the 86Box chip one native frame at a time, synchronized with register bookkeeping instead of bulk RenderNative-then-chip frames. This changes scheduling versus upstream; require reference parity audit.
- The internal chip FIFO latency of 980 native frames is conservatively converted to host sample frames with ceiling, so 48 kHz reports 1067, 96 kHz 2134 and 44.1 kHz 980. Forward linear interpolation may leak the first transient one host frame earlier; VST latency reporting remains future work.
- Chorus factory presets prepare vector capacity on the initialization/control thread so subsequent preset changes cannot allocate in the render path. Reverb preset changes only update scalar parameters.
- New native integration tests cover output PCM equality between a full host block and irregular partitions, native-rate/48/96 kHz audible fallback, and an instrumented global operator new guard during RenderBlock.

## Known limits and release blockers
1. Authentic ROM/SF2 timbral tests, hardware parity, 86Box FIFO onset under 48kHz resampling, and more varied MIDI/voice scenarios still need validation.
2. No VST3 processor/controller yet, therefore no actual host-reported latency or Studio One run.
3. Sample-bank uploads and on-demand DRAM writes remain control-thread operations; `PortOut16` can still grow DRAM if a hypothetical host sends RAM writes in realtime. Hard realtime guard pending.
4. Some upstream voice-allocation and stream-logging functions may allocate if used inside an audio callback; audio-thread API boundaries require a full review.
5. Floating-point per-frame rendering retains mathematical parity only for the selected native model; no claim of accurate audio-chip behavior is made by these tests.

## Additional chip timing regression (P05b)

The `125A_box_rate_fifo` test checks the actual patched 86Box EMU8000 C engine with a synthetic ROM and DRAM sine waveform, native/48kHz rate conversion, 980-frame FIFO initial silence, native-to-host latency arithmetic, block-partition parity, and an operator-new guard. It does not validate authentic ROM timbre.
