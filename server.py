"""Loopback-only desktop front door."""
import hmac
import json
import os
import re
import secrets
import shutil
import sys
import subprocess
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from worker import run,RATIOS

ROOT=Path(__file__).resolve().parent
APP=Path(sys.executable).parent if getattr(sys,'frozen',False) else ROOT
DATA=APP/'data'
KEY=secrets.token_urlsafe(24)
URL=None
JOBS={}; LOCK=threading.Lock(); ENGINE=threading.Lock()
LIMIT=4*1024**3
VIDEO={'.mp4','.mov','.m4v','.webm','.mkv'}
AUDIO={'.mp3','.wav','.m4a','.aac','.ogg','.flac'}

def validate(value):
    if not isinstance(value,dict) or value.get('ratio') not in ['auto',*RATIOS]: raise ValueError('请选择支持的画幅。')
    media=value.get('media')
    if not isinstance(media,list) or not 2<=len(media)<=101: raise ValueError('请选择 1–100 段视频和一首音乐。')
    total=0; result=[]
    for i,item in enumerate(media):
        if not isinstance(item,dict): raise ValueError('素材格式错误。')
        name=item.get('name',''); size=item.get('size',0); kind='audio' if i==len(media)-1 else 'video'
        if not isinstance(name,str) or not name or len(name)>240 or re.search(r'[\\/:*?"<>|\x00-\x1f]',name): raise ValueError('文件名不受支持。')
        ext=Path(name).suffix.lower()
        if ext not in (AUDIO if kind=='audio' else VIDEO) or type(size)!=int or size<=0: raise ValueError('文件类型或大小不受支持。')
        total+=size; result.append({'name':name,'size':size,'file':f'input-{i}{ext}'})
    if total>LIMIT: raise ValueError('一次素材总量不能超过 4 GiB。')
    return {'ratio':value['ratio'],'media':result}

def cleanup():
    # Only marked temporary jobs inside this application's data root, never source paths.
    for directory in DATA.iterdir():
        if directory.is_symlink() or not directory.is_dir() or directory.resolve().parent!=DATA.resolve() or not re.fullmatch('[a-f0-9]{32}',directory.name): continue
        active=JOBS.get(directory.name,{})
        if active.get('status')=='running' or active.get('uploading') or active.get('exporting'): continue
        marker=directory/'finished.json' if (directory/'finished.json').is_file() else directory/'created.json'
        if marker.is_file() and time.time()-marker.stat().st_mtime>86400:
            try: shutil.rmtree(directory)
            except OSError: continue # Active downloads can hold Windows file handles; try next time.
            JOBS.pop(directory.name,None)

def create(request):
    with LOCK:
        cleanup()
        if len(JOBS)>=32: raise ValueError('本次启动已创建较多任务，请稍后重启应用。')
        if shutil.disk_usage(DATA).free<sum(m['size'] for m in request['media'])+1024**3: raise ValueError('电脑磁盘空间不足，请先释放空间。')
        ident=secrets.token_hex(16); directory=DATA/ident; directory.mkdir()
        (directory/'created.json').write_text('{"owner":"bmts-lite"}',encoding='utf-8')
        JOBS[ident]={'request':request,'status':'uploading','phase':'等待导入','progress':0,'created':time.time(),'uploaded':set(),'uploading':set()}
        return ident

def process(ident):
    job=JOBS[ident]; directory=DATA/ident
    def update(phase,progress):
        with LOCK: job.update(phase=phase,progress=round(progress))
    try:
        result=run(directory,job['request'],update)
        with LOCK: job.update(status='done',phase='混剪完成',progress=100,**result)
    except Exception as error:
        with LOCK: job.update(status='error',phase='未能完成混剪',error=str(error).split('\n')[0][:250])
        (directory/'error.log').write_text(str(error),encoding='utf-8')
    finally:
        try: (directory/'finished.json').write_text(json.dumps({'status':job['status']}),encoding='utf-8')
        finally: ENGINE.release()

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass # Do not log access tokens.
    def json(self,status,value):
        data=json.dumps(value,ensure_ascii=False).encode()
        self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def body(self):
        length=int(self.headers.get('Content-Length','0'))
        if not 0<length<=65536: raise ValueError('请求无效。')
        return json.loads(self.rfile.read(length))
    def auth(self):
        key=self.headers.get('X-BMTS-Key') or parse_qs(urlsplit(self.path).query).get('key',[''])[0]
        return hmac.compare_digest(key,KEY) and self.headers.get('Sec-Fetch-Site')!='cross-site' and self.headers.get('Origin',f'http://{self.headers.get("Host")}')==f'http://{self.headers.get("Host")}'
    def file(self,path,mime,download=False):
        size=path.stat().st_size; start=0; end=size-1; partial=False
        if self.headers.get('Range'):
            match=re.fullmatch(r'bytes=(\d*)-(\d*)',self.headers['Range'])
            if not match or not any(match.groups()): return self.json(416,{'error':'无效播放区间'})
            a,b=match.groups()
            if a: start=int(a); end=min(int(b),end) if b else end
            else: start=max(0,size-int(b))
            if start>end or start>=size: return self.json(416,{'error':'播放区间越界'})
            partial=True
        self.send_response(206 if partial else 200); self.send_header('Content-Type',mime)
        self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Length',str(end-start+1)); self.send_header('Accept-Ranges','bytes')
        if partial: self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        if download: self.send_header('Content-Disposition','attachment; filename="BMTS-Lite.mp4"')
        self.end_headers()
        with path.open('rb') as stream:
            stream.seek(start); left=end-start+1
            while left:
                block=stream.read(min(left,1024*1024))
                if not block: break
                self.wfile.write(block); left-=len(block)
    def route(self):
        self.connection.settimeout(120)
        try:
            path=urlsplit(self.path).path
            if self.command=='GET' and path in ['/','/app.js','/style.css','/glass.css']:
                return self.file(ROOT/({'/':'index.html'}.get(path,path[1:])),{'/':'text/html; charset=utf-8','/app.js':'text/javascript; charset=utf-8','/style.css':'text/css; charset=utf-8','/glass.css':'text/css; charset=utf-8'}[path])
            if not self.auth(): return self.json(403,{'error':'请重新打开 BMTS Lite。'})
            if path=='/api/jobs' and self.command=='POST': return self.json(201,{'id':create(validate(self.body()))})
            match=re.fullmatch(r'/api/jobs/([a-f0-9]{32})(?:/(start|video|remix|export|\d+))?',path)
            if not match or match[1] not in JOBS: return self.json(404,{'error':'临时任务已失效，请重新导入。'})
            ident,action=match.groups(); job=JOBS[ident]; directory=DATA/ident
            if action is None and self.command=='GET':
                with LOCK: value={k:v for k,v in job.items() if k not in ['request','uploaded','uploading','exporting']}
                return self.json(200,value)
            if action=='export' and self.command=='POST' and job['status']=='done':
                resolution=self.body().get('resolution')
                if type(resolution)!=int or resolution not in (480,720,1080): raise ValueError('请选择 480p、720p 或 1080p。')
                with LOCK:
                    if job.get('exporting'): return self.json(409,{'error':'正在准备导出，请稍候。'})
                    job['exporting']=True
                try:
                    target=directory/f'export-{resolution}.mp4'
                    if resolution!=1080 and not target.exists():
                        from worker import probe
                        stream=next(s for s in probe(directory/'result.mp4')['streams'] if s['codec_type']=='video')
                        scale=resolution/min(stream['width'],stream['height'])
                        w,h=[max(2,round(stream[k]*scale/2)*2) for k in ('width','height')]
                        partial=directory/f'export-{resolution}.partial.mp4'
                        try:
                            result=subprocess.run(['ffmpeg','-v','error','-nostdin','-y','-i',str(directory/'result.mp4'),'-map','0:v:0','-map','0:a:0','-vf',f'scale={w}:{h}', '-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(partial)],capture_output=True,timeout=1200,creationflags=0x08000000 if sys.platform=='win32' else 0)
                            if result.returncode: raise RuntimeError('导出失败，请重试。')
                            partial.replace(target)
                        finally: partial.unlink(missing_ok=True)
                    (directory/'finished.json').touch()
                    return self.json(200,{'resolution':resolution})
                finally:
                    with LOCK: job['exporting']=False
            if action=='export' and self.command=='GET' and job['status']=='done':
                resolution=parse_qs(urlsplit(self.path).query).get('resolution',[''])[0]
                if resolution not in ('480','720','1080'): raise ValueError('导出规格无效。')
                target=directory/('result.mp4' if resolution=='1080' else f'export-{resolution}.mp4')
                if not target.is_file(): raise ValueError('请先准备导出。')
                return self.file(target,'video/mp4',True)
            if action=='video' and self.command=='GET' and job['status']=='done': return self.file(directory/'result.mp4','video/mp4','download' in parse_qs(urlsplit(self.path).query))
            if action and action.isdigit() and self.command=='PUT':
                index=int(action)
                with LOCK:
                    if job['status']!='uploading' or index>=len(job['request']['media']) or index in job['uploading'] or index in job['uploaded']: raise ValueError('素材已提交或任务已开始。')
                    item=job['request']['media'][index]
                    if int(self.headers.get('Content-Length','0'))!=item['size']: raise ValueError('文件大小不匹配。')
                    job['uploading'].add(index)
                target=directory/item['file']; part=target.with_suffix('.part')
                try:
                    with part.open('xb') as stream:
                        left=item['size']
                        while left:
                            data=self.rfile.read(min(left,1024*1024))
                            if not data: raise ValueError('上传中断，请重试。')
                            stream.write(data); left-=len(data)
                    part.rename(target)
                    with LOCK: job['uploaded'].add(index)
                finally:
                    with LOCK: job['uploading'].discard(index)
                    part.unlink(missing_ok=True)
                return self.json(200,{'ok':True})
            if action=='remix' and self.command=='POST' and job['status']=='done':
                (directory/'finished.json').touch()
                new=create(job['request'])
                for item in job['request']['media']: os.link(directory/item['file'],DATA/new/item['file'])
                JOBS[new]['uploaded']=set(range(len(job['request']['media'])))
                return self.json(201,{'id':new})
            if action=='start' and self.command=='POST':
                with LOCK:
                    if job['status']!='uploading' or len(job['uploaded'])!=len(job['request']['media']): raise ValueError('素材尚未导入完整，或任务已开始。')
                    if not ENGINE.acquire(blocking=False): return self.json(409,{'error':'电脑正在剪辑另一条视频，完成后请重试。'})
                    job.update(status='running',phase='开始处理',started=time.time(),progress=1)
                threading.Thread(target=process,args=(ident,),daemon=True).start()
                return self.json(200,{'ok':True})
            return self.json(405,{'error':'操作不支持。'})
        except (BrokenPipeError,ConnectionResetError): pass
        except Exception as error: self.json(400,{'error':str(error).split('\n')[0][:250]})
    do_GET=route; do_POST=route; do_PUT=route

def main():
    global URL
    DATA.mkdir(exist_ok=True); temp=DATA/'temp'; temp.mkdir(exist_ok=True)
    os.environ['TMP']=os.environ['TEMP']=str(temp)
    os.environ['NUMBA_CACHE_DIR']=str(temp/'numba')
    if (ROOT/'runtime/ffmpeg').is_dir(): os.environ['PATH']=str(ROOT/'runtime/ffmpeg')+os.pathsep+os.environ['PATH']
    if not all(shutil.which(x) for x in ['ffmpeg','ffprobe']): raise RuntimeError('找不到 FFmpeg/ffprobe，请使用完整运行环境。')
    port=int(os.environ.get('BMTS_LITE_PORT',7790))
    for candidate in range(port,port+10):
        try: server=ThreadingHTTPServer(('127.0.0.1',candidate),Handler); port=candidate; break
        except OSError:
            if candidate==port+9: raise
    url=f'http://127.0.0.1:{port}/?key={KEY}'
    URL=url
    print(f'电脑打开：{url}',flush=True)
    print('关闭应用窗口后停止服务。',flush=True)
    if not os.environ.get('BMTS_NO_BROWSER'): webbrowser.open(url)
    server.serve_forever()

if __name__=='__main__': main()
