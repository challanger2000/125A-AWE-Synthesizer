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

