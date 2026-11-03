"""P97: CT4390 analog capture versus 125A original MIDI/SF2 native chip.
Purpose: quantify differences, not claim physical bit-accuracy.
"""
import argparse,json
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly,correlate

p=argparse.ArgumentParser()
for x in ("reference","native","out"):p.add_argument("--"+x,required=True)
p.add_argument("--seconds",type=int,default=90)
a=p.parse_args()
ref,ref_rate=sf.read(a.reference,frames=(a.seconds+2)*48000,
                     dtype="float32",always_2d=True)
native,native_rate=sf.read(a.native,dtype="float32",always_2d=True)
assert (ref_rate,native_rate)==(48000,44100),(ref_rate,native_rate)
assert ref.shape[1]==native.shape[1]==2
assert len(ref)>=a.seconds*ref_rate and len(native)>=a.seconds*native_rate
assert np.max(np.abs(ref))>.001 and np.max(np.abs(native))>.001,("Silent input",np.max(np.abs(ref)),np.max(np.abs(native)))
# Resample just our emulated digital output, not the analog original.
sample_rate=48000
emulated=resample_poly(native,160,147,axis=0)
step=2400  # 50 ms energy windows
def rms_bins(x):
    n=len(x)//step
    return np.sqrt(np.mean(x[:n*step].reshape(n,step,2)**2,axis=(1,2)))
r0=rms_bins(ref[:a.seconds*sample_rate])
e0=rms_bins(emulated[:a.seconds*sample_rate])
def znorm(x):
    x=np.log10(np.maximum(x,1e-6))
    return (x-x.mean())/max(x.std(),1e-9)
c=correlate(znorm(r0),znorm(e0),mode="full",method="fft")
lags=np.arange(-len(e0)+1,len(r0))
mask=(lags>=-20)&(lags<=20)
lag=int(lags[mask][np.argmax(c[mask])])
# Positive lag means CT4390 recording is delayed compared to native MIDI.
if lag>=0:
    ref=ref[lag*step:]
else:
    emulated=emulated[-lag*step:]
maxlen=min(len(ref),len(emulated),a.seconds*sample_rate-abs(lag)*step)
ref=ref[:maxlen]
emulated=emulated[:maxlen]
re=rms_bins(ref);en=rms_bins(emulated)
active=(re>max(.001,.01*re.max())) & (en>max(.001,.01*en.max()))
assert int(active.sum())>=12,("No aligned active hardware/EMU8000 notes",int(active.sum()))
gain=float(np.median(re[active]/np.maximum(en[active],1e-9)))
gain_db=float(20*np.log10(gain))
env_corr=float(np.corrcoef(np.log10(np.maximum(re,1e-6)),
                          np.log10(np.maximum(en,1e-6)))[0,1])
# The waveform may decorrelate from sample-clock phase and analog ADC.
wave_corr=float(np.corrcoef(ref[::48].mean(axis=1),
                           emulated[::48].mean(axis=1))[0,1])
bands=[(50,200),(200,500),(500,2000),(2000,5000),(5000,10000),(10000,20000)]
freq=np.fft.rfftfreq(sample_rate,1/sample_rate)
power_real=np.zeros(len(bands));power_native=np.zeros(len(bands))
active_seconds=0
for i in range(maxlen//sample_rate):
    r=ref[i*sample_rate:(i+1)*sample_rate]
    e=emulated[i*sample_rate:(i+1)*sample_rate]
    if len(r)!=sample_rate or np.sqrt(np.mean(r*r))<.002:continue
    window=np.hanning(sample_rate)
    rfft=np.abs(np.fft.rfft(r.mean(axis=1)*window))**2
    efft=np.abs(np.fft.rfft(e.mean(axis=1)*window))**2
    for j,(lo,hi) in enumerate(bands):
        ix=(freq>=lo)&(freq<hi)
        power_real[j]+=rfft[ix].sum()
        power_native[j]+=efft[ix].sum()
    active_seconds+=1
spectral=[{"band_hz":f"{lo}-{hi}",
           "native_minus_real_db_level_matched":round(float(10*np.log10(
               max(power_native[i],1e-12)/max(power_real[i],1e-12))+gain_db),3)}
          for i,(lo,hi) in enumerate(bands)]
sections=[
 ("01_volume_envelope",0,8),("02_modulation_envelope",8,16),
 ("03_keynum_to_decay",16,30),("04_keynum_to_hold",30,40),
 ("05_modulation_lfo",40,50),("06_vibrato_lfo",50,55),
 ("07_modwheel",55,60),("08_scale_tune",60,64.5),
 ("09_filter_cutoff",64.5,76.5),("10_filter_resonance",76.5,84.5),
 ("11_attenuation",84.5,90),("12_negative_attenuation",90,95.513542),
 ("13_velocity_attenuation",95.513542,126.5),
 ("14_velocity_filter",126.5,157.5),
 ("15_cc1_filter",157.5,164),("16_sample_offset",164,169),
 ("17_reverb",169,198.5),("18_chorus",198.5,228.5),
 ("19_interpolation",228.5,237.5),("20_pitch_bend",237.5,260.5),
 ("21_exclusive_class",260.5,a.seconds)]

def section_spectrum(x,y):
    """Compare only this named test interval, using the SAME global level match."""
    n=min(len(x),len(y))//sample_rate
    ph=np.zeros(len(bands)); pn=np.zeros(len(bands)); active_s=0
    window=np.hanning(sample_rate)
    for i in range(n):
        r=x[i*sample_rate:(i+1)*sample_rate]
        e=y[i*sample_rate:(i+1)*sample_rate]
        if np.sqrt(np.mean(r*r))<.002:continue
        rf=np.abs(np.fft.rfft(r.mean(axis=1)*window))**2
        ef=np.abs(np.fft.rfft(e.mean(axis=1)*window))**2
        for j,(lo,hi) in enumerate(bands):
            ix=(freq>=lo)&(freq<hi)
            ph[j]+=rf[ix].sum()
            pn[j]+=ef[ix].sum()
        active_s+=1
    if not active_s:return 0,[]
    return active_s,[{"band_hz":f"{lo}-{hi}",
            "native_minus_real_db_level_matched":round(float(
                10*np.log10(max(pn[j],1e-12)/max(ph[j],1e-12))+gain_db),3)}
            for j,(lo,hi) in enumerate(bands)]

detailed=[]
for label,start,end in sections:
    lo=int(start*sample_rate);hi=min(int(end*sample_rate),maxlen)
    if hi-lo<sample_rate:continue
    x=ref[lo:hi];y=emulated[lo:hi]
    sr=rms_bins(x);se=rms_bins(y)
    section_env_corr=float(np.corrcoef(np.log10(np.maximum(sr,1e-6)),
                                       np.log10(np.maximum(se,1e-6)))[0,1])
    active_s,section_bands=section_spectrum(x,y)
    detailed.append({"test":label,"time_s":[start,end],
                     "hardware_rms":round(float(np.sqrt(np.mean(x*x))),6),
                     "native_rms":round(float(np.sqrt(np.mean(y*y))),6),
                     "rms_envelope_log_correlation":round(section_env_corr,5),
                     "active_spectral_seconds":active_s,
                     "band_spectrum":section_bands})
report={
  "experiment":"P97 genuine AWE64 Gold CT4390 RCA analog hardware audio comparison",
  "source_recording":"48kHz 16-bit stereo FLAC, RCA line out into RME Babyface Pro FS; Hall 1 / Chorus 1",
  "native":"125A 86Box EMU8000 at 44.1kHz; same public SF2 and MIDI test v3.0",
  "compared_seconds":a.seconds,"aligned_audio_seconds":round(maxlen/sample_rate,3),
  "original_hardware_relative_latency_ms":lag*50,
  "hardware_to_native_global_gain_match_db":round(gain_db,3),
  "rms_envelope_log_correlation":round(env_corr,5),
  "mono_audio_correlation":round(wave_corr,5),
  "active_50ms_envelope_windows":int(active.sum()),
  "number_active_spectral_windows":active_seconds,
  "band_spectrum":spectral,"sections":detailed,
  "limitations":[
    "CT4390 audio is from analog RCA and 48kHz ADC, not S/PDIF",
    "Hardware Hall1 and Chorus1 are enabled; default native DSP mix may differ",
    "Original hardware recording level may have been normalized",
    "Native was resampled 44.1kHz -> 48kHz and envelope-aligned at 50ms resolution",
    "No claimed bitwise equivalence or general 1-to-1 physical AWE64 accuracy"],
  "physical_hardware_1to1_proven":False}
Path(a.out).write_text(json.dumps(report,indent=2)+"\n")
print("P97 ANALOG HARDWARE RESULT:",{"time":report["aligned_audio_seconds"],
      "lag_ms":lag*50,"env_corr":report["rms_envelope_log_correlation"],
      "wave_corr":report["mono_audio_correlation"],
      "level_db":report["hardware_to_native_global_gain_match_db"],
      "spectral":spectral,
      "worst_sections_by_low_band_delta_db":sorted(
          [(s["test"],s["band_spectrum"][0]["native_minus_real_db_level_matched"])
           for s in detailed if s["band_spectrum"]],
          key=lambda pair:abs(pair[1]),reverse=True)[:5]})
