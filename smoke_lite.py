"""Explicit integration check against a running Lite server; creates a new test job."""
import json
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit,parse_qs

url,parent=sys.argv[1:3]; parts=urlsplit(url); base=f'{parts.scheme}://{parts.netloc}'; key=parse_qs(parts.query)['key'][0]
parent=Path(parent); old=json.loads((parent/'request.json').read_text(encoding='utf-8'))
files=[parent/m['relative'] for m in old['media'] if m['kind']=='video'][:4]+[parent/next(m['relative'] for m in old['media'] if m['kind']=='audio')]
def api(route,value=None,method=None):
    data=value if isinstance(value,bytes) else json.dumps(value).encode() if value is not None else None
    req=urllib.request.Request(base+route,data=data,method=method or ('POST' if data is not None else 'GET'),headers={'X-BMTS-Key':key})
    with urllib.request.urlopen(req,timeout=120) as response:return json.load(response)
job=api('/api/jobs',{'ratio':sys.argv[3] if len(sys.argv)>3 else '4:3','media':[{'name':f.name,'size':f.stat().st_size} for f in files]})['id']
print('job',job,flush=True)
for i,f in enumerate(files): api(f'/api/jobs/{job}/{i}',f.read_bytes(),'PUT')
api(f'/api/jobs/{job}/start',{})
phase=''
for _ in range(600):
    state=api(f'/api/jobs/{job}')
    if phase!=state['phase']:phase=state['phase']; print(phase,flush=True)
    if state['status']=='done':
        result={'job':job,**state}
        Path(__file__).with_name('smoke-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print('PASS',state['duration'],state['ratio'],state['shots'],flush=True);break
    if state['status']=='error':raise RuntimeError(state.get('error'))
    time.sleep(2)
else:raise TimeoutError('Render still running; inspect the job before retrying.')
