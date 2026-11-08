"""Expose actionable public test/build diagnostics without private log data."""
from pathlib import Path
import re
import sys
text=Path(sys.argv[1]).read_text(encoding='utf-8-sig',errors='replace')
lines=[s for s in text.splitlines() if re.search(r'error (?:C\d|LNK|MSB)|fatal error|^FAIL |^EXCEPTION|error:|\*\*\*Failed',s)]
if not lines:lines=text.splitlines()[-15:]
for i in range(0,len(lines),8):
    body='\n'.join(lines[i:i+8])[:2800].replace('%','%25').replace('\r','%0D').replace('\n','%0A')
    print('::error title=P170 diagnostic::'+body)
