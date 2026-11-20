"""Local-only static SPA demo server. No access logs or request body logging."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1] / 'demo-site'


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        path = urlsplit(self.path).path
        if '.' not in path.rsplit('/', 1)[-1]:
            self.path = '/index.html'
        super().do_GET()

    def log_message(self, *_args):
        pass


print('PulseLite demo website listening on http://localhost:4174; access logs disabled.', flush=True)
ThreadingHTTPServer(('127.0.0.1', 4174), Handler).serve_forever()