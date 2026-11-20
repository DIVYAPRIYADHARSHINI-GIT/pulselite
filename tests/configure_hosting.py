"""Apply only non-secret PulseLite config through approved Vercel API, no env pull."""
import json
import subprocess
import sys
from pathlib import Path

items=json.loads(Path(sys.argv[1]).read_text())
project=sys.argv[2]
for item in items:
    result=subprocess.run(['vercel','api',f'/v10/projects/{project}/env?upsert=true','--method','POST','--input','-','--silent','--scope','divya-6411'],input=json.dumps(item),text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
    print(f'{item["key"]}: exit {result.returncode}',flush=True)
    if result.returncode:
        print(result.stdout)
        sys.exit(result.returncode)