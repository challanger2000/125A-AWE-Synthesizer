# P42 — Original Windows 95 AWE32 class-navigation investigation

**Scope:** Experimental QEMU/Windows 95 guest UI only. No P26 audio engine changes, no driver or Windows binary redistribution.

## Evidence already verified (2026-11-01)

- P41b run [41297570570](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41297570570), screenshot `p40_090_sound_category.png`: after pressing **s** while the genuine hardware-class list has focus, **SCSI controllers** is selected (not Sound).
- P41c run [41297958300](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41297958300), `p40_088_add_hardware_wizard.png`: the **hardware-class list** is already visible; `Shift+Tab` then focuses **Cancel**, preventing the `s` keys from selecting any category.
- P41d run [41338357447](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41338357447), `p41d_099_hardware_class_list.png`: the wizard arrives at the **Mitsumi CD-ROM** model page, *not* the intended AWE32 MEDIA class. Workflow success here only means screenshots and test script completed.

## P42 targeted correction

1. From the previously captured hardware-class page, do **not** press Shift+Tab; press `s` to choose **SCSI controllers**.
2. Press `Down` once, which is expected to select the next alphabetical entry, **Sound, video and game controllers**. Record screenshot.
3. Advance, allow original Windows 95 driver database selection, invoke **Have Disk**, enter `C:\\AWE32` (original staged Creative INF directory), and record the proposed models.
4. **Stop before model confirmation/installation.** A screenshot showing the intended Creative device must be visually confirmed first.

## Proof boundary

- The original INF's `Class=MEDIA` and `CTL0021` section support model selection but do **not** prove driver/device binding.
- A generic QEMU PC currently has **no EMU8000/AWE32 physical device emulated**, so even a successful Have Disk selection is **not** real EMU8000 hardware register evidence.
- Future proof must establish the original `SBAWE.VXD` device binding against a real or accurately emulated AWE32 and capture genuine MIDI note-on register writes for the user's two bass patches, with patch-specific SF2 behavior and settings recorded.
- No assertion of 1:1 AWE32 audio is justified by the current screen-navigation checks.


## P42 run result — verified

- GitHub Actions run [41338899532](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41338899532) completed successfully.
- Screenshot `p42_092_sound_video_game_controllers.png` visibly selects the **Sound, video and game controllers** class. This conclusively fixes the P41 keyboard-focus/class-selection problem.
- Screenshot `p42_150_creative_awe32_model_candidates.png` visibly shows original Creative manufacturer driver candidates, including **Creative Advanced Wave Effects Synthesis for AWE 32**, with the first **Creative 3D Stereo Enhancement Technology** entry initially highlighted.
- **No driver model was yet selected or installed in P42.** Original `SBAWE.VXD` binding, emulated AWE32 device presence, note-on registers, and 1:1 audio remain unproven.

## Next controlled step

Select the second Creative model in the verified `Select Device` list (one `Down` key), verify the highlighted name, and confirm that model once. Screenshot the resulting original Windows 95 dialog; do not blindly skip further installation prompts.
