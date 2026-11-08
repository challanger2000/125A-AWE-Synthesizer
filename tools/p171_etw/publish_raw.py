"""Publish unchanged synthetic callback rows in bounded public notices.

GitHub's unauthenticated annotation view truncates each message at 4096 chars.
Partitions keep each job below 50 notices; no dataset rows are filtered.
"""
import base64
import hashlib
from pathlib import Path
import sys
import zlib

source,partition,label,batch=sys.argv[1:5];partition=int(partition);batch=int(batch)
raw=Path(source).read_bytes();digest=hashlib.sha256(raw).hexdigest()
expected={'A':'3e00913b25ab17eb7c0310140fcb3e7823b37712201d7fb7261470fe5f8852fe',
          'B':'0c93af66a70e9043144ea58f616c2c51987f5ced5eb108e77fd7e3a511cba543'}
if digest!=expected[label] or partition not in range(4) or batch not in range(4):raise RuntimeError('wrong original data or partition')
encoded=base64.b64encode(zlib.compress(raw,9)).decode()
parts=[encoded[i:i+2800] for i in range(0,len(encoded),2800)]
selected=[(i,s) for i,s in enumerate(parts) if i%4==partition]
if len(selected)>40:raise RuntimeError('job notice limit exceeded')
for i,part in selected[batch*10:(batch+1)*10]:
    print(f'::notice title=P171 original numeric rows::P171_ORIGINAL_CSV_{i+1}_OF_{len(parts)}_SHA_{digest}:{part}')
print('P171_RAW_PARTITION',label,partition,'batch',batch,'of total',len(parts),'sha256',digest)
