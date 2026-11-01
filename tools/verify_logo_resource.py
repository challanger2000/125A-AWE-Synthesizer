#!/usr/bin/env python3
"""Verify exact owner-authored vector master is unchanged in source and VST3."""
import hashlib
import sys
from pathlib import Path
MASTER_BLOB="bd398ffa3b728b1a847bb519fad8168222bccb48"
def verify(path):
    p=Path(path)
    data=p.read_bytes()
    sha=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\\0"+data).hexdigest()
    if sha!=MASTER_BLOB:
        raise SystemExit(f"FAIL: 125A branding resource was altered: {p} ({sha})")
    if data.count(b"<path ")!=30:
        raise SystemExit(f"FAIL: expected 30 vector components in {p}")
    print(f"PASS: exact 125A master SVG (git blob {sha}) in {p}")
if __name__=="__main__":
    for item in sys.argv[1:]:
        verify(item)
