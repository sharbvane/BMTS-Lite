import json
import tempfile
import threading
import os
import time
import unittest
import urllib.request
from pathlib import Path
import server
from worker import assign,display_ratio,RATIOS

class LiteChecks(unittest.TestCase):
    def test_expired_abandoned_upload_cleanup(self):
        with tempfile.TemporaryDirectory() as folder:
            old=server.DATA;server.DATA=Path(folder);server.JOBS.clear()
            try:
                expired=server.DATA/('a'*32); expired.mkdir(); marker=expired/'created.json'; marker.write_text('{}')
                past=time.time()-90000; os.utime(marker,(past,past))
                active=server.DATA/('b'*32); active.mkdir(); marker=active/'created.json';marker.write_text('{}');os.utime(marker,(past,past))
                server.JOBS[active.name]={'status':'running'}
                foreign=server.DATA/'keep';foreign.mkdir()
                server.cleanup();self.assertFalse(expired.exists());self.assertTrue(active.exists());self.assertTrue(foreign.exists())
            finally:server.DATA=old;server.JOBS.clear()
    def test_ratios_and_full_song(self):
        for ratio in ['auto',*RATIOS]: server.validate({'ratio':ratio,'media':[{'name':'a.mp4','size':10},{'name':'b.mp3','size':10}]})
        with self.assertRaises(ValueError): server.validate({'ratio':'1:1','media':[{'name':'../a.mp4','size':10},{'name':'b.mp3','size':10}]})
        slots=[{'start':i,'end':i+1} for i in range(240)]
        media=[{'path':'a','duration':5},{'path':'b','duration':5}]
        plan=assign(slots,media,240,'test')
        self.assertEqual(plan['duration_seconds'],240);self.assertEqual(len(plan['shots']),240)
        self.assertTrue(all(s['source_end']<=5 for s in plan['shots']))
        self.assertTrue(all(a['local_path']!=b['local_path'] for a,b in zip(plan['shots'],plan['shots'][1:])))
        split=assign([{'start':0,'end':8}],[{'path':'short','duration':1}],8,'test')
        self.assertAlmostEqual(split['shots'][-1]['output_end'],8)
        self.assertAlmostEqual(display_ratio({'width':1920,'height':1080,'side_data_list':[{'rotation':90}]}),9/16)
    def test_local_http_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            old=server.DATA;server.DATA=Path(folder);server.JOBS.clear()
            service=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
            thread=threading.Thread(target=service.serve_forever,daemon=True);thread.start()
            base=f'http://127.0.0.1:{service.server_port}'
            def request(route,data=None,method='POST',key=server.KEY):
                return urllib.request.urlopen(urllib.request.Request(base+route,data=data,method=method,headers={'X-BMTS-Key':key}),timeout=5)
            try:
                with self.assertRaises(urllib.error.HTTPError):request('/api/jobs',b'{}',key='wrong')
                value={'ratio':'4:3','media':[{'name':'x.mp4','size':4},{'name':'x.mp3','size':4}]}
                ident=json.load(request('/api/jobs',json.dumps(value).encode()))['id']
                with self.assertRaises(urllib.error.HTTPError):request(f'/api/jobs/{ident}/start',b'{}')
                request(f'/api/jobs/{ident}/0',b'test','PUT').close()
                with self.assertRaises(urllib.error.HTTPError):request(f'/api/jobs/{ident}/0',b'test','PUT')
                (server.DATA/ident/'result.mp4').write_bytes(b'0123456789');server.JOBS[ident]['status']='done'
                req=urllib.request.Request(base+f'/api/jobs/{ident}/video',headers={'X-BMTS-Key':server.KEY,'Range':'bytes=2-4'})
                with urllib.request.urlopen(req) as response:self.assertEqual(response.status,206);self.assertEqual(response.read(),b'234')
            finally:service.shutdown();service.server_close();server.DATA=old;server.JOBS.clear()

if __name__=='__main__':unittest.main()
