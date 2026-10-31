# 125A AWE Synthesizer — development guidance
Status: pre-release engineering baseline v0.1.0, NO approved Windows FULL release, NO Gumroad ZIP.
Repository: challanger2000/125A-AWE-Synthesizer
Development branch: develop/v0.1.0-upstream-audit
Upstream baseline: turican0/AWE32Emu commit 17b0578fe59909dfaa784b5531d6d1a3a80729ce.
No changes directly to main. No unreviewed GitHub Actions builds.
Read challanger2000/125A-Engineering/START-HERE.md, README, ENGINEERING-GUARDRAILS and relevant STANDARDS/QA/RESEARCH/ROADMAP before modifications.
Keep upstream snapshot verbatim as the compare/reference; implement independent VST3 and realtime adapter in separate 125A directories.
No ROMs, SoundFonts, Creative drivers, private data or original hardware assets in Git history or distributable artifacts.
P0: audio callback allocations; global chip/ROM state; fatal()/exit(1); fixed 44.1 kHz chip clock and 980-frame block latency; state/ROM/host lifecycle and legal redistribution verification.
Evidence labels required: PASS/FAIL/NOT RUN. Never call a build, host test, validator or release PASS without exact run evidence.
