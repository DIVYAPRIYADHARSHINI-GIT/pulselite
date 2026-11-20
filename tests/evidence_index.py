"""Generate a transparent manifest from actual retained artifacts only."""
import json
import re
from pathlib import Path
root=Path(__file__).resolve().parents[1]
rows=[]
for f in sorted((root/'reports').glob('*.txt')):
    text=f.read_text()
    code=re.search(r'^Exit: (\d+)',text,re.M)
    summary=re.findall(r'(?:\d+ failed, )?\d+ passed[^\n]*|Browser checks: [^\n]+|\d+ passed; \d+ failed|No known vulnerabilities found|found 0 vulnerabilities',text)
    rows.append({'file':str(f.relative_to(root)),'exit':int(code[1]) if code else None,'summary':summary[-1] if summary else 'Command transcript; no test count claimed'})
bugs=[str(p.relative_to(root)) for p in sorted((root/'bugs').iterdir()) if p.is_file()]
screens=[str(p.relative_to(root)) for p in sorted((root/'screenshots').glob('*.png'))]
(root/'reports/evidence-manifest.json').write_text(json.dumps({'commands':rows,'bug_artifacts':bugs,'screenshots':screens},indent=2))
lines=['# Evidence index','', 'Generated from actual retained files. Repeated suite runs are not additional unique tests.','', '## Command and test history','', '| Transcript | Exit | Last recorded summary |','|---|---:|---|']
for r in rows:lines.append(f'| [{Path(r["file"]).name}](../{r["file"]}) | {r["exit"]} | {r["summary"].replace("|","/")} |')
lines+=['','## Permanent bug records','']+[f'- [{Path(p).name}](../{p})' for p in bugs]
lines+=['','## Real screenshots','']+[f'- [{Path(p).name}](../{p})' for p in screens]
(root/'reports/EVIDENCE_INDEX.md').write_text('\n'.join(lines)+'\n')
print(f'Indexed {len(rows)} command transcripts, {len(bugs)} bug artifacts, {len(screens)} real screenshots.')