"""Create only named PulseLite apps. Print non-secret IDs, never link/pull env."""
import json
import subprocess

for name,framework in [('pulselite-web','vite'),('pulselite-demo',None)]:
    payload={'name':name,'framework':framework}
    result=subprocess.run(['vercel','api','/v10/projects','--method','POST','--input','-','--scope','divya-6411'],input=json.dumps(payload),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=30)
    if result.returncode:
        print(result.stderr)
        raise SystemExit(result.returncode)
    data=json.loads(result.stdout)
    print(json.dumps({key:data.get(key) for key in ('id','name','accountId')}))