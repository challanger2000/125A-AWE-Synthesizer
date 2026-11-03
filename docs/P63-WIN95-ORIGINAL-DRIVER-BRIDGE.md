# P63 — original Creative driver inside Windows 95: first host->guest MIDI link

## Scope and deliberate constraints

This is an actual **Windows 95 WinMM MIDI guest executable**, not a second SF2
loader and not another filter hypothesis. It forwards MIDI short messages to
the Creative AWE MIDI Synth endpoint selected by name. The original Creative
AWECP32 control panel must load the SF2 first. The existing 86Box EMU8000
hardware, actual Creative Win95 driver and 1 MiB Wave ROM are retained.

P26 and P62 are untouched. Existing FM engines are not referenced by P63.

### Host to guest wiring

1. 86Box: retain the proven Win95 + original Creative driver + emulated
   Sound Blaster AWE32 PnP configuration. Do not replace the hardware core.
2. In 86Box **Ports > COM1**, configure the **Named Pipe** serial device in
   **Server** mode, pipe \\.\pipe\125A-AWE32-MIDI, byte-transparent.
   The Win95 guest uses COM1 at 115200 baud, 8 data bits, no parity, 1 stop bit.
   Avoid claiming the serial guest link is working until exercised.
3. Copy the P63-built `p63_win95_guest_midi.exe` into the guest and start it.
   It lists WinMM MIDI out endpoints, selects one containing `AWE` and
   `SYNTH`, and fails closed if not found. There is **no default synth
   fallback**. It calls original WinMM `midiOutShortMsg` only.
4. Use original Creative AWECP32 to load the user SoundFont, and then from
   the host run:
   ```powershell
   py tools/p63_send_guest_midi.py --bank 1 --program 7 --note 50 --velocity 100
   ```
   This sends CC0=1, program 7, a D3 note-on and note-off. Bank selection
   here is an input to the original driver, not a synthesized tone.
5. Require a guest-console device name check, Creative MIDI activity and
   **captured 86Box wavetable audio** before marking the transport proven.

### Honesty about what is still missing

- The Windows 95 guest helper must be injected into the emulated disk and
  launched, and the 86Box serial device actually configured. The build
  test proves compilation/protocol only, not Win95 runtime operation.
- Real-time bidirectional **PCM output capture/clock synchronisation** and
  VST3 block processing are **not implemented**. Do not call this a
  finished VST3 or claim working Studio One playback.
- COM1 MIDI bytes are subject to guest and serial latency; sample-exact MIDI
  placement is not established. PCM output will need a bounded buffering
  interface and underrun detection.
- For private testing, the user's existing SF2 and Wave ROM can be mounted
  into the disposable guest **without committing them**. Do not upload
  proprietary driver/ROM/Win95 images or private user bank to public artifacts.

### Next implementation gate

Connect the existing automation-driven Win95 guest boot to COM1 and this
WinMM agent, play the user's actual SF2 through the original Creative stack,
and capture the EMU8000 wavetable output. Then add **PCM audio tap +
bounded host PCM queue** and a Windows-x64 VST3 client. Never replace
EMU8000 DSP with FluidSynth, OPL, CQM, or a hand-guessed filter.
