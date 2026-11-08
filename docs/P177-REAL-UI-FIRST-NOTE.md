# P177 — Real Windows VST3 SF2 dialog → Controller → browser → first-note PCM

Candidate baseline: P176 commit `65bba76976115d8b3634a4a1316bc59d79ebab80`.
Development branch: `qa/p177-controller-gui-first-note`. No production DSP,
UI, ROM, preset, VST3 parameter ID, or state-format changes.

## Previously untested

P171/P176 send a SF2 load message directly to the Processor. This cannot
establish that the actual Windows SF2 file picker, Controller RequestSf2Load,
ACK and PresetCatalog refresh, native VSTGUI program navigation, and host
begin/perform/endEdit truly reach the first playable MIDI NoteOn.

## New falsifiable integration

1. Load the **exported shipping-candidate Windows VST3 DLL** in a native host,
   instantiate and connect its actual Processor and Controller, and attach
   the real VSTGUI editor to a Win32 window.
2. An independent Python Win32 driver physically clicks the plug-in's
   SF2 button, enters a generated SoundFont path through the genuine native
   Windows `GetOpenFileNameW` dialog, and clicks NEXT on the actual GUI.
3. A real VST3 `IComponentHandler` records begin/perform/endEdit for
   sparse bank 0's next existing program, program 7. It rejects a mere
   visual highlight or a controller update with no host gesture.
4. Inspect the Processor's **persisted SF2 path** after the GUI load.
5. Submit that host program point at sampleOffset 0 together with the
   **first** MIDI NoteOn, using the very same actual loaded DLL instance.
6. Require nonzero PCM and byte-for-byte equality to an independent
   fresh instance initialized with the identical generated SF2,
   synthetic zero ROM and program 7.

Sources: `tests/p177_ui_first_note_host.cpp`,
`tests/p177_win32_first_note_driver.py`, CMake test
`125A_p177_real_gui_load_first_note`, and scoped Windows workflow
`.github/workflows/p177-real-gui-first-note.yml`.

## Evidence discipline

At authoring, the new P177 code was **NOT YET COMPILED OR EXECUTED**.
No P177 PASS is claimed before verifying exact-commit Windows native logs.
P176's 63/63 CTests, 537/537 Steinberg Validator, 99/99 GUI checks and
independent Test Lab TECHNICAL_PASS were observed in Windows run
https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42488547080
for P176 exact SHA, including passed `125A_p176_exported_dll_sf2_loops`.
These checks are not portable proof of the private original SF2/Creative ROM.

Remaining regardless of P177 outcome: original-user-SF2 first-note test,
hardware parity, DAW/ASIO/MMCSS real-system test, independent FULL AUDIT,
and release sign-off. No merge to `main` or P175 without owner approval.
