# P160 — proportional PCB faceplate and real screw-safe VSTGUI

Development base: P156. The working Windows VST3 editor remains **1000 × 640** logical pixels. This is a visual/layout patch, not a DSP, bank, preset, sample, or automation change.

## Changes in the live editor

- The original approved gold wordmark is rendered at 193 × 120 from its original 236 × 147 image, without recreating the typography.
- Control islands have 60% opaque black-gold backing (RGBA alpha 153), with real PCB visible underneath.
- Lower-left FILTER ADSR and lower-right MASTER get deliberate cutouts for the two 22px-radius corner screw heads. The BROWSER overlay reserves those same corners.
- MOD RESET is raised from `(808,535)-(960,571)` to `(808,513)-(960,549)`; its size remains 152 × 36, so its associated atlas/host control still works.
- Main LCD stays at `(264,16)-(776,163)`; dynamic text overlay remains VSTGUI and is **not** baked into the photograph.
- The EMU8000 chip remains inside the dedicated `(788,16)-(984,163)` hardware zone. Four PCB corner screws are visible and must not be repainted by overlays.

## Approved binary assets (not yet committed on this branch)

The following two files have been produced and checked in the associated ChatGPT artifact package:

1. `src/vst3/resource/125A_P160_PCB_1000x640.png` — photograph with original chip, all four PCB screws, and undistorted ISA contacts; exactly 1000 × 640 RGB.
2. `src/vst3/resource/125A_P160_Lcd_Complete_512x147.png` — full four-screw bezel and dark empty amber screen; exactly 512 × 147 RGBA.

Extract `P160_GitHub_Artwork_Import.zip` into the root of a checkout of this branch and commit those two images before calling it a finished, visually approved P160 build. CMake automatically embeds the images as Windows PNG resources when present.

The branch **deliberately falls back** to older P156 PCB / P151 LCD images if either file is missing. Any green CI build on a checkout missing the new binary resources only validates code, existing VST3 behavior and new control geometry. It **does not validate** the selected P160 photograph.

## Release decision

- Do not merge or release without a real Windows EditorHost screenshot using **both P160 binary resources**.
- Confirm four corner screws, complete LCD bezel (all four bezel screws), legible chip, gold logo, 60% dark overlays, bottom ISA contacts, browser popup controls, and MOD RESET hitbox.
- Retain existing passing 45 engine CTests and Steinberg VST3 Validator coverage, plus real GUI acceptance.
