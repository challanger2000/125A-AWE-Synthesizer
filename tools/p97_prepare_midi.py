"""P97: deterministic MIDI v3.0 events at native EMU8000 44100-Hz sample times."""
import argparse,csv,json
from pathlib import Path
import mido

p=argparse.ArgumentParser()
for f in ("midi","tsv","json"):p.add_argument("--"+f,required=True)
a=p.parse_args()
mid=mido.MidiFile(a.midi)
tempo=500000
elapsed_us=0.
events=[]
counts={}
for m in mido.merge_tracks(mid.tracks):
    elapsed_us+=m.time*tempo/mid.ticks_per_beat
    counts[m.type]=counts.get(m.type,0)+1
    if m.type=="set_tempo":tempo=m.tempo
    if not hasattr(m,"channel"):continue
    if m.type in ("note_on","note_off"):n,v=m.note,m.velocity
    elif m.type=="control_change":n,v=m.control,m.value
    elif m.type=="program_change":n,v=m.program,0
    elif m.type=="pitchwheel":n,v=m.pitch,0
    elif m.type=="aftertouch":n,v=m.value,0
    else:continue
    events.append({"frame":round(elapsed_us*44100/1e6),
                   "time_sec":round(elapsed_us/1e6,6),
                   "type":m.type,"channel":m.channel,"a":n,"b":v})
with open(a.tsv,"w",newline="") as f:
    writer=csv.DictWriter(f,fieldnames=("frame","time_sec","type","channel","a","b"),delimiter="\t")
    writer.writeheader()
    writer.writerows(events)
report={"midi_version":"SoundFont Spec Test v3.0","duration_s":elapsed_us/1e6,
        "ticks_per_beat":mid.ticks_per_beat,"events":len(events),
        "types":counts,"event_start":events[:12]}
Path(a.json).write_text(json.dumps(report,indent=2)+"\n")
assert len(events)==2200 and abs(elapsed_us/1e6-264)<.01,report
print("P97 sample-accurate original v3.0 MIDI:",len(events),"events over",elapsed_us/1e6,"seconds.")
