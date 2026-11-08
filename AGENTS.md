# P186 current development navigation (9 November 2026)

Repository: challanger2000/125A-AWE-Synthesizer. Windows x64 VST3 only.
Pre-release v0.1.0; NO owner-approved Windows FULL release or Gumroad ZIP.
Current QA branch: qa/p186-etw-diagnostics, adopted P185 source 4d56729788bcf065fbae1c13f5b79b831601d492.
Read START-HERE.md and docs/P186-ETW-DIAGNOSTICS-AND-STATUS.md first.
P186 corrects reporting and reanalyzes existing raw JSON; no new hardware run,
no native Win11 decoder adaptation until actual owner counters are known.
Owner capture.json/asio.json NOT_PROVIDED here. Cause INCONCLUSIVE, release NO_GO.
AWE src/CMake, original ROM/SF2 behavior, GUI, P184 and strict timing unchanged.
Older development milestones below are historical, not current branch authority.

# 125A AWE Synthesizer — development guidance
Status: pre-release engineering baseline v0.1.0, NO approved Windows FULL release, NO Gumroad ZIP.
Repository: challanger2000/125A-AWE-Synthesizer
Current development branch: fix/p170-p171-audio-corrections (P169 baseline; P170/P171 Windows functional checks passed).
Validated product/test source: b02e02d472544eb2122533f9b8d7dc9d0b97f68a.
RT callback matrix FAIL: 1/28800, trace-proven ready preemption in that miss;
physical ASIO/DAW NOT RUN, FULL AUDIT NOT COMPLETE, RELEASE NO-GO.
Read the first P170/P171 section of START-HERE.md and docs/P170-P171-AUDIO-CORRECTIONS.md
for current exact evidence and open gates. Milestones below are historical.
Upstream baseline: turican0/AWE32Emu commit 17b0578fe59909dfaa784b5531d6d1a3a80729ce.
No changes directly to main. No unreviewed GitHub Actions builds.
Read challanger2000/125A-Engineering/START-HERE.md, README, ENGINEERING-GUARDRAILS and relevant STANDARDS/QA/RESEARCH/ROADMAP before modifications.
Keep upstream snapshot verbatim as the compare/reference; implement independent VST3 and realtime adapter in separate 125A directories.
No ROMs, SoundFonts, Creative drivers, private data or original hardware assets in Git history or distributable artifacts.
P0: audio callback allocations; global chip/ROM state; fatal()/exit(1); fixed 44.1 kHz chip clock and 980-frame block latency; state/ROM/host lifecycle and legal redistribution verification.
Evidence labels required: PASS/FAIL/NOT RUN. Never call a build, host test, validator or release PASS without exact run evidence.

Latest verified developer milestone (2026-11-01): **P19 Windows dev GUI**, source
`198a54379dbd95b9cf9090693048201df9e39791` from branch
`develop/v0.1.0-upstream-audit`. VST3 Actions #41271495551 SUCCESS,
16/16 CTests, 47/47 Validator, actual Steinberg EditorHost GUI actions and
unchanged original 125A SVG resource SHA PASS. Full evidence in
`docs/P19-SOUND-BLASTER-FACEPLATE.md`. NOT FINAL, no Gumroad release;
Studio One project recall and owner GUI approval remain NOT RUN. Preserve
original 125A master blob `bd398ffa3b728b1a847bb519fad8168222bccb48`.

Current verified developer checkpoint P20 (2026-11-01): exact tested production source
`3ec81c27eea46dea751516327c959500974bd913` on
`develop/v0.1.0-upstream-audit`; Windows VST3 Action #41272929443 SUCCESS,
16/16 CTests, Steinberg 47/47, real EditorHost Win32 GUI PASS; Engine Safety
#41272929458 SUCCESS 14/14. P20 prevents an explicitly selected SF2 that
fails to load from silently playing a sine fallback under real preset names;
controller receives/GUI shows processor load status via VST3 message.
The reported TX81Z Lately Bass sound is NOT independently verified: actual
user SF2, host-received error status and Studio One acoustic parity NOT RUN.
Do NOT merge P20 sustain-envelope proposal from separate unmerged branch
`fix/p20-sf2-envelope-defaults` as a diagnosis for this symptom without
independent evidence. See `docs/P20-SF2-LOAD-DIAGNOSIS.md`. No FINAL release.

Latest Windows-validated developer checkpoint (2026-11-01): **P22 SF2
semantics**, tested source `361913c5cfde64bc419db168e3c120a6f36bfb71`,
branch `develop/v0.1.0-upstream-audit`. Actions #41274176376 SUCCESS:
16/16 CTests, 47/47 Steinberg Validator and real Win32 EditorHost GUI PASS;
Native Actions #41274176362 SUCCESS 14/14. P21 repairs SF2 additive
preset offsets (fineTune, filter, chorus, attack/decay/release) while
preserving historical SF1/SBK precedence. P22 fixes default absent SF2
volume/modulation sustain to full (EMU8000 127) and SF2 mod-sustain
permille conversion while preserving SF1 missing-sustain hardware zero.
Actual private user SF2 'Synth 512 Bank' was analyzed **offline only**:
program 000 'Grungy Ramp Bass' has +/-5 cents preset offsets and no
explicit sustain generator; program 007 'TX81Z Lately Bass' has 4 preset
layers with significant relative filter/chorus/envelope values. **Do not
commit or re-upload private SF2 or reference WAVs to public GitHub.**
Docs: `docs/P21-SF2-PRESET-COMPOSITION.md` and
`docs/P22-SF2-SUSTAIN-SEMANTICS.md`. Important: Windows CI success
DOES NOT prove actual 125A PCM matches FluidSynth or real EMU8000; final
Studio One A/B reference listening and project recall are NOT RUN.
No FINAL/Gumroad release.
