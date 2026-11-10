#!/usr/bin/env python3
"""P67 strict end-to-end Win95 guest Creative MIDI evidence gate.

Reads only P63LOG.TXT from the disposable Win95 FAT image AFTER 86Box exits.
Never exports Win95, Creative binaries, ROMs, private user SF2 or MIDI traces.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from pyfatfs.PyFatFS import PyFatFS
from p38_stage_creative_awe32_win95 import partition_offset


def inspect(log: bytes, *, max_bytes: int = 8192) -> dict:
    if max_bytes not in (8192, 65536) or len(log)>max_bytes:
        raise ValueError("Unexpected Win95 agent diagnostic size")
    txt=log.decode("ascii","replace")
    return {
        "phase":"P67",
        "agent_launched_in_actual_win95":"P66 CRT-free original Creative Win95 bridge startup" in txt,
        "original_creative_winmm_endpoint_selected":"SELECTED original Creative AWE Synth" in txt,
        "original_creative_com1_ready":"READY COM1 115200 8N1" in txt,
        "creatives_midi_short_messages_delivered":txt.count("MIDI DELIVERED"),
        "win95_agent_error":any(line.startswith("ERROR ") for line in txt.splitlines()),
        "private_driver_executable_logged":False,
        "raw_user_sf2_published":False,
    }


def p220_expected_winmm_delivery(full_report):
    """Recognize the 154 private 77-SF2 trials without trusting status flags.

    The guest has no per-message payload in the historical P63 log, so this
    proves only aggregate WinMM delivery count, NOT that 154 individually
    requested program/CC values were echoed by Windows or selected by ROM.
    """
    trial=full_report.get("p220_original_win95_private_capture")
    if trial is None:return None
    from p220_77_preset_capture_plan import BANK_SHA
    if (not isinstance(trial,dict) or
            trial.get("private_sf2_sha256")!=BANK_SHA or
            trial.get("all_154_original_pcm_captured") is not True or
            full_report.get("full_77_preset_soundfont_validated") is not True):
        raise ValueError("P220 cannot enlarge Win95 log capacity without exact full-bank capture proof")
    records=trial.get("trials")
    if not isinstance(records,list) or len(records)!=154:
        raise ValueError("P220 original Win95 trial count incomplete")
    programs=[p for p in range(78) if p!=63]
    expected=[(f"P{p:03d}-{mode}",p) for p in programs for mode in ("DRY","MODFX")]
    if [(x.get("id"),x.get("program")) for x in records if isinstance(x,dict)]!=expected:
        raise ValueError("P220 MIDI trial program identity/order incomplete")
    if not all(x.get("source_audio_pcm_from")=="86box_wavetable_during_real_original_Win95"
               and x.get("original_emu8000_voice_write_delta",0)>0
               and x.get("note_off_sent_to_guest") is True
               for x in records):
        raise ValueError("P220 missing live Creative 86Box capture/driver register evidence")
    # Existing P64 mandatory two baselines program0/7 are 4 commands each.
    # Each P220 scenario: CC0+CC7+CC11+CC1+CC91+CC93+PC+ON+OFF = 9.
    return 8+154*9


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--disk",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--audio-report",type=Path,required=True)
    a=p.parse_args()
    full_report=json.loads(a.audio_report.read_text(encoding="utf8"))
    p220_delivery=p220_expected_winmm_delivery(full_report)
    with PyFatFS(str(a.disk),offset=partition_offset(a.disk),read_only=True,preserve_case=False) as fs:
        startup=fs.readbytes("AWE32/P68BOOT.LOG").decode("ascii","replace") if fs.exists("AWE32/P68BOOT.LOG") else ""
        root_marker=fs.readbytes("P71ROOT.TXT").decode("ascii","replace") if fs.exists("P71ROOT.TXT") else ""
        midi_marker=fs.readbytes("P73MIDI.TXT").decode("ascii","replace") if fs.exists("P73MIDI.TXT") else ""
        batch=fs.readbytes("AWE32/P68BAT.LOG").decode("ascii","replace") if fs.exists("AWE32/P68BAT.LOG") else ""
        if fs.exists("AWE32/P63LOG.TXT"):
            result=inspect(fs.readbytes("AWE32/P63LOG.TXT"),
                           max_bytes=65536 if p220_delivery is not None else 8192)
        else:
            result={"phase":"P67","agent_launched_in_actual_win95":False,
                    "original_creative_winmm_endpoint_selected":False,
                    "original_creative_com1_ready":False,
                    "creatives_midi_short_messages_delivered":0,
                    "win95_agent_error":True,
                    "raw_user_sf2_published":False,
                    "error":"Win95 guest agent never created P63LOG.TXT"}
    result["p68_startup_batch_launched"] = "P70 STARTUP BATCH" in batch or "P68 STARTUP BATCH" in batch
    result["p73_midi_entrypoint_executed"] = "P73 WIN95 MIDI ENTRYPOINT EXECUTED" in midi_marker
    result["p73_midi_started_and_running_after_1sec"] = "P63 STILL RUNNING AFTER 1 SEC" in startup
    result["p73_midi_early_exit_diagnostic"] = next((line.strip() for line in startup.splitlines() if line.startswith("P63 EXITED BEFORE") or line.startswith("P63 WAIT ERROR")), "")
    result["p71_entrypoint_executed_root_marker"] = "P71 ENTRYPOINT EXECUTED" in root_marker
    result["p71_entrypoint_executed_exitcode"] = "P71 ENTRY EXITCODE OBSERVED" in batch
    result["p71_entrypoint_no_exitcode"] = "P71 ENTRY EXITCODE MISSING" in batch
    result["p70_guest_exe_exists"] = "P68BOOT.EXE EXISTS" in batch
    result["p70_direct_execution_began"] = "DIRECT EXEC BEGIN" in batch
    result["p70_direct_execution_returned"] = "DIRECT EXEC RETURNED" in batch
    result["p70_direct_execution_nonzero"] = "DIRECT EXEC NONZERO" in batch
    result["p70_guest_exe_missing"] = "P68BOOT.EXE MISSING" in batch
    result["p68_win95_autostart_launched"]="P68 WIN95 AUTOSTART LOADED" in startup
    result["p68_win95_createprocess_ok"]="P63 CREATEPROCESS SUCCESS" in startup
    result["p68_launch_diagnostic"]=next((line.strip() for line in startup.splitlines() if line.startswith("P63 CREATEPROCESS")), "P68BOOT.LOG not created")
    result["p220_original_77_expected_midi_deliveries"] = p220_delivery
    result["p220_original_77_guest_delivery_count_match"] = (
        p220_delivery is not None and
        result["creatives_midi_short_messages_delivered"]==p220_delivery)
    result["p220_winmm_message_values_individually_attested"] = False
    audio=full_report.get("p64_original_win95_midi",{})
    pcm=audio.get("direct_86box_pcm_fifo") or {}
    result["emu8000_pcm_stream_frames"]=pcm.get("frames",0)
    result["emu8000_nonzero_pcm_frames"]=pcm.get("nonzero_frames",0)
    result["emu8000_note_register_delta"]=audio.get("original_creative_midi_activity_register_write_delta",0)
    result["audio_observed"]=bool(result["emu8000_nonzero_pcm_frames"]>0 and result["emu8000_note_register_delta"]>0)
    trial=audio.get("p75_program_results",[])
    result["p75_private_sf2_test"]=bool(audio.get("p75_original_private_sf2_test",False))
    result["p75_sf2_sample_upload_plausible"]=(not result["p75_private_sf2_test"]) or bool(
        full_report.get("p75_private_sample_upload_plausible",False))
    result["p75_programs_tested"]=[x.get("program") for x in trial]
    result["p84_universal_sf2_test"]=bool(full_report.get("p84_universal_sf2_test"))
    expected=( [x["program"] for x in full_report.get("p84_selected_presets",[])]
              if result["p84_universal_sf2_test"] else [0,7])
    result["p75_both_basses_nonzero"]=(not result["p75_private_sf2_test"]) or (
        result["p75_programs_tested"]==expected and
        all(x.get("nonzero_audio",False) for x in trial) and
        trial[1].get("register_write_delta",0)>0)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print(json.dumps(result,indent=2))
    ok=(result["p68_win95_createprocess_ok"]
        and result["agent_launched_in_actual_win95"]
        and result["original_creative_winmm_endpoint_selected"]
        and result["original_creative_com1_ready"]
        and result["creatives_midi_short_messages_delivered"] >= (8 if result["p75_private_sf2_test"] else 4)
        and result["p75_both_basses_nonzero"]
        and result["p75_sf2_sample_upload_plausible"]
        and not result["win95_agent_error"]
        and result["audio_observed"]
        and (p220_delivery is None or result["p220_original_77_guest_delivery_count_match"]))
    if not ok:
        raise SystemExit("P67 FAIL: original Win95 Creative WinMM MIDI path is not proven")


if __name__=="__main__":
    main()
