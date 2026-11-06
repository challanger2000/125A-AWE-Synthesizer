"""P132: one-expression audit-only patch, same arithmetic as P129 draft PR #67.

Must be invoked only in disposable CI checkout.  Never silently change or
commit the production DSP implementation or copy creative ROM/audio assets.
"""
from pathlib import Path
import argparse
import hashlib

p = argparse.ArgumentParser()
p.add_argument("--source", required=True)
args = p.parse_args()
path = Path(args.source)
source = path.read_text(encoding="utf-8")
original = "engine->chorus_left_buffer[engine->write] = *inbuf + ((dat_l * engine->feedback) >> 8);"
replacement = ("const int32_t fed_back = (int32_t)\n"
               "            (((int64_t) dat_l * engine->feedback) / INT64_C(256));\n"
               "        engine->chorus_left_buffer[engine->write] = *inbuf + fed_back;")
if source.count(original) != 1:
    raise SystemExit("FAIL CLOSED: unexpected original Chorus arithmetic")
if "const int32_t fed_back" in source:
    raise SystemExit("FAIL CLOSED: candidate already present")
print("P132_BASE_SOURCE_SHA256", hashlib.sha256(source.encode("utf-8")).hexdigest())
candidate = source.replace(original, replacement)
if candidate.replace(replacement, original) != source:
    raise SystemExit("FAIL CLOSED: candidate changed more than one expression")
path.write_text(candidate, encoding="utf-8")
print("P132_CANDIDATE_SOURCE_SHA256", hashlib.sha256(candidate.encode("utf-8")).hexdigest())
print("P132_TEMPORARY_CANDIDATE_APPLIED=1; DO_NOT_MERGE=1")
