"""Fail closed on staged credentials, generated state or oversized files."""
import json
from pathlib import Path
import re
import subprocess

root=Path(__file__).resolve().parents[1]
raw=subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=root)
files=[p for p in raw.decode().split('\0') if p]
issues=[]
patterns=[re.compile(rb'gh[pousr]_[A-Za-z0-9]{30,}'),re.compile(rb'github_pat_[A-Za-z0-9_]{30,}'),re.compile(rb'postgres(?:ql)?(?:\+psycopg)?://[^\s"\x27]+:[^\s"\x27]+@'),re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')]
total=0
for name in files:
    p=Path(name)
    if any(part in ('.venv','node_modules','.cache','.vercel','.browser','.tmp','__pycache__') for part in p.parts) or p.name.startswith('.env') or p.suffix in ('.db','.sqlite','.sqlite3'):
        issues.append({'file':name,'reason':'forbidden generated/credential path'})
    content=subprocess.check_output(['git','show',':'+name],cwd=root)
    total+=len(content)
    if len(content)>5*1024*1024:
        issues.append({'file':name,'reason':'exceeds 5 MiB individual-file threshold'})
    if any(pattern.search(content) for pattern in patterns):
        issues.append({'file':name,'reason':'possible credential pattern; content withheld'})
report={'staged_files':len(files),'total_bytes':total,'max_individual_bytes':5*1024*1024,'issues':issues,'note':'Pattern scan plus ignored-path/size check; not a mathematical guarantee that every possible secret format is detected.'}
(root/'reports/staged-release-audit.json').write_text(json.dumps(report,indent=2))
print(f'Staged files: {len(files)}; bytes: {total}; issues: {len(issues)}')
for issue in issues: print(issue['file']+': '+issue['reason'])
raise SystemExit(bool(issues))