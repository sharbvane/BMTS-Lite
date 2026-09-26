"""Explicit real render and HTTP export check, also callable inside the EXE."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import traceback
import urllib.request

def verify(folder):
    import server
    from worker import run,probe
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=True)
    report={'ok':False};service=None
    try:
        os.environ['PATH']=str(server.ROOT/'runtime/ffmpeg')+os.pathsep+os.environ['PATH']
        os.environ['TEMP']=os.environ['TMP']=str(folder)
        os.environ['NUMBA_CACHE_DIR']=str(folder/'numba')
        ident='e'*32;directory=folder/ident;directory.mkdir(exist_ok=True)
        def command(args):subprocess.run(['ffmpeg','-v','error','-nostdin','-y',*args],capture_output=True,check=True,timeout=120)
        command(['-f','lavfi','-i','testsrc2=size=640x360:rate=30','-t','5','-c:v','libx264',str(directory/'input-0.mp4')])
        command(['-f','lavfi','-i',r'aevalsrc=0.4*sin(2*PI*220*t)*exp(-12*mod(t\,0.5)):s=22050:d=4','-c:a','pcm_s16le',str(directory/'input-1.wav')])
        request={'ratio':'16:9','media':[{'file':'input-0.mp4'},{'file':'input-1.wav'}]}
        def update(phase,progress):(folder/'progress.json').write_text(json.dumps({'phase':phase,'progress':progress},ensure_ascii=False),encoding='utf-8')
        result=run(directory,request,update)
        original=hashlib.sha256((directory/'result.mp4').read_bytes()).hexdigest()
        server.DATA=folder;server.JOBS[ident]={'status':'done',**result}
        service=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        threading.Thread(target=service.serve_forever,daemon=True).start()
        url=f'http://127.0.0.1:{service.server_port}/api/jobs/{ident}/export'
        report['exports']={}
        for resolution in (480,720,1080):
            req=urllib.request.Request(url,json.dumps({'resolution':resolution}).encode(),headers={'X-BMTS-Key':server.KEY})
            with urllib.request.urlopen(req,timeout=180) as response: assert json.load(response)['resolution']==resolution
            req=urllib.request.Request(url+f'?resolution={resolution}',headers={'X-BMTS-Key':server.KEY})
            with urllib.request.urlopen(req,timeout=60) as response:
                assert 'attachment' in response.headers['Content-Disposition']
                output=folder/f'saved-{resolution}.mp4';output.write_bytes(response.read())
            info=probe(output);stream=next(s for s in info['streams'] if s['codec_type']=='video')
            assert stream['height']==resolution and abs(float(info['format']['duration'])-4)<.15
            command(['-i',str(output),'-f','null','-'])
            report['exports'][resolution]=[stream['width'],stream['height']]
        assert hashlib.sha256((directory/'result.mp4').read_bytes()).hexdigest()==original
        report.update(ok=True,render=result,source_result_unchanged=True)
    except Exception:
        report['error']=traceback.format_exc()
    finally:
        if service:service.shutdown();service.server_close()
        (folder/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':
    import sys
    verify(sys.argv[1])
