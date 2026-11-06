# P132 numeric evidence

Only numeric benchmark/control data; no ROM/SF2, PCM or ETL in Git.

The original complete numeric artifact was recovered via size-bounded CI
annotations after GitHub truncated the first 4,500-character chunks. Each
complete payload was SHA256-verified before JSON parsing. Pretty-printed JSON
here retains its numeric values; the original byte hashes below refer to the
compact original payload, not to the reformatted files.

| Payload | Source Windows run | Original JSON SHA256 |
| --- | --- | --- |
| Windows A | 42208362856 | `9442aca8df6a9c5873df0cb8d3ced4ada28b960bdd9bb366badfec1f2b4f3e7f` |
| Windows B | 42208362915 | `b23e4d5bdb573c227600f04a46dfd2069929679df17ec6b0f2f1a6ffcb931f4b` |
| Natural Recall | 42211942566 | `e3c945ccab4025491e30bbae2ed1ce4aec885fc86fb096f565b8fdb6ae619c61` |

Before source: `418cc6b580a8cb3fd770b33b3804e0626d3c08f8`, unchanged production
`c7d803c1b328166f6f5edcb770aa9c9f8b49ecda`. Recovery/control host source:
`5ac6f4407f97d08c826d4b0cc1c1b2e10b3c42e1`.

`before/all-cases.csv` contains both complete and matched-load populations for
all 240 before cells. Full per-callback QPC, raw cycles, PCM digests, voice
census, context switches, heap events and ETLs are in the named Actions
artifacts (14-day retention), not in this aggregate table. See the main
[P132 report](../../P132-REALTIME-AUDIT.md) for methodology and limitations.

## Post-fix evidence

Source `45df2931e75e54b53e32352ffa45573943dca85d`, adapter correction
`e1d2b64a06228496d53716e34b250902c4afd115`. Windows runs:
A `42213516747`, B `42213516842`, both SUCCESS. Both have 44 CTests,
47 Validator checks and 3 GUI smokes. Original numeric payload byte hashes:

- A: `c18fb77b994511ba57a3eaf770b0f05f173633ff1f35232fb42f0f4f0ef1c04b`
- B: `9e9dfebdc0d3fd9c81c320544f5e849a406ebaccaf26df26d416c387eed23295`

`after/all-cases.csv` retains all 240 full post-fix cells and 24 crossover
cells, each with complete and physically matched-load populations. Crossover
`paired-before-*` still loads the original 418cc6b diagnostic DLL, while
`paired-after-*` loads the corrected DLL, on the same runner and host binary.
The artifacts contain the original per-callback rows, control counts, cycles,
PCM digests and ETW files. Full post-fix traces have 796/172800 deadline misses;
functional CI SUCCESS must not be read as real-time PASS.
