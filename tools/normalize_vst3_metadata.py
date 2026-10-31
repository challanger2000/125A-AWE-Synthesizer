#!/usr/bin/env python3
"""Normalize Steinberg 3.8.1 moduleinfo.json for strict JSON parsers."""
import json
from pathlib import Path
import sys

def strip_trailing_commas(text: str) -> str:
    out=[]
    quoted=False
    escape=False
    for i,c in enumerate(text):
        if quoted:
            out.append(c)
            if escape:
                escape=False
            elif c=="\\":
                escape=True
            elif c=='"':
                quoted=False
            continue
        if c=='"':
            quoted=True
        if c==",":
            j=i+1
            while j<len(text) and text[j] in "\r\n\t ":
                j+=1
            if j<len(text) and text[j] in "}]":
                continue
        out.append(c)
    if quoted: raise ValueError("Unterminated JSON string")
    return "".join(out)

def normalize(path: Path) -> None:
    obj=json.loads(strip_trailing_commas(path.read_text(encoding="utf-8-sig")))
    if not isinstance(obj,dict) or not obj.get("Classes") or obj.get("Factory Info",{}).get("Vendor")!="125A Systems":
        raise ValueError("Not the expected 125A VST3 module metadata")
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    assert json.loads(path.read_text(encoding="utf-8"))==obj

if __name__=="__main__":
    assert json.loads(strip_trailing_commas('{"a":[1,2,],"b":"string ,] ,}",}'))=={"a":[1,2],"b":"string ,] ,}"}
    assert json.loads(strip_trailing_commas('{"a":"quote \\" ,] still quoted","z":0,}'))["z"]==0
    if len(sys.argv)!=2: raise SystemExit("Expected moduleinfo.json")
    normalize(Path(sys.argv[1]))
    print("PASS: strict moduleinfo.json JSON")
