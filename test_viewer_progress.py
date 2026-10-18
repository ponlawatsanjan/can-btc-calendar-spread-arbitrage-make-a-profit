import json
from pathlib import Path
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen, Request

from plot_raw_ticks import make_handler, ThreadingHTTPServer


class ProgressTests(unittest.TestCase):
    def setUp(self):
        def builder(contracts,start,end,budget,cache,progress):
            for i in range(6):
                progress({'completed':i,'total':5,'unit':'pair-days','pair':'NEAR / FAR','day':'2021-03-16'})
                time.sleep(.04)
            return {'contracts':[],'total_raw_rows':0,'total_shown':0}
        self.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler({},0,1,Path('.'),builder))
        self.server.daemon_threads=True
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.base='http://127.0.0.1:'+str(self.server.server_port)

    def get(self,path):
        with urlopen(self.base+path,timeout=5) as response:
            return json.load(response)

    def test_progress_is_observable_while_request_runs(self):
        done=threading.Event();errors=[]
        def request():
            try:self.get('/api/ticks?start=0&end=1&limit=100&job=progress-test')
            except Exception as error:errors.append(error)
            finally:done.set()
        threading.Thread(target=request,daemon=True).start()
        percentages=[]
        while not done.wait(.02):
            status=self.get('/api/progress?job=progress-test')
            if status['status']=='running':percentages.append(status['percent'])
        self.assertFalse(errors)
        self.assertTrue(any(0<p<100 for p in percentages))
        self.assertEqual(percentages,sorted(percentages))
        final=self.get('/api/progress?job=progress-test')
        self.assertEqual(final['percent'],100)
        self.assertEqual(final['status'],'complete')

    def test_cancel_is_reported_and_releases_worker(self):
        done=threading.Event()
        def request():
            try:self.get('/api/ticks?start=0&end=1&limit=100&job=cancel-test')
            except HTTPError:pass
            finally:done.set()
        threading.Thread(target=request,daemon=True).start()
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            if self.get('/api/progress?job=cancel-test')['status']=='running':break
            time.sleep(.01)
        with urlopen(Request(self.base+'/api/cancel?job=cancel-test',method='POST'),timeout=5) as response:
            self.assertTrue(json.load(response)['cancel_requested'])
        self.assertTrue(done.wait(5))
        self.assertEqual(self.get('/api/progress?job=cancel-test')['status'],'cancelled')
        self.get('/api/ticks?start=0&end=1&limit=100&job=next-test')
        self.assertEqual(self.get('/api/progress?job=next-test')['percent'],100)


if __name__=='__main__':unittest.main()
