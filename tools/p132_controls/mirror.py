"""Mirror an existing numeric artifact without GitHub's 4096-character cut."""
import base64,hashlib,json,sys,zlib
from pathlib import Path
raw=Path(sys.argv[1]).read_bytes()
data=json.loads(raw)
source=data.get('measuredCommit') or data['provenance.json']['commit']
assert source=='418cc6b580a8cb3fd770b33b3804e0626d3c08f8'
encoded=base64.b64encode(zlib.compress(raw,9)).decode()
chunks=[encoded[i:i+3000] for i in range(0,len(encoded),3000)]
sha=hashlib.sha256(raw).hexdigest()
for i,chunk in enumerate(chunks):
 print(f'::notice title=P132_NUMERIC_{i+1}_OF_{len(chunks)}::P132_DATA_{i+1}_OF_{len(chunks)}_SHA_{sha}:{chunk}')
