"""
Vercel serverless function — bridges Vercel's BaseHTTPRequestHandler interface
to the Flask WSGI application in the parent directory.
"""
import sys
import os
import io
from http.server import BaseHTTPRequestHandler

# Env setup BEFORE importing app
os.environ['VERCEL'] = '1'
os.makedirs('/tmp/matplotlib', exist_ok=True)
os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib'

# Add project root to path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    from app import app as flask_app, init_db
    init_db()
    _init_error = None
except Exception:
    import traceback
    _init_error = traceback.format_exc()
    flask_app = None


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._handle('GET', b'')

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length) if length else b''
        self._handle('POST', body)

    def do_DELETE(self):
        self._handle('DELETE', b'')

    def _handle(self, method, body):
        if _init_error or flask_app is None:
            self.send_response(500)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            msg = (_init_error or "app not loaded").encode()
            self.wfile.write(b'<pre>' + msg + b'</pre>')
            return

        # Build WSGI environ
        parsed = self.path.split('?', 1)
        path_info = parsed[0] or '/'
        query_str = parsed[1] if len(parsed) > 1 else ''

        environ = {
            'REQUEST_METHOD': method,
            'PATH_INFO': path_info,
            'QUERY_STRING': query_str,
            'SERVER_NAME': self.headers.get('Host', 'localhost').split(':')[0],
            'SERVER_PORT': '443',
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'https',
            'wsgi.input': io.BytesIO(body),
            'wsgi.errors': sys.stderr,
            'wsgi.multithread': False,
            'wsgi.multiprocess': False,
            'wsgi.run_once': True,
            'CONTENT_LENGTH': str(len(body)),
            'CONTENT_TYPE': self.headers.get('Content-Type', ''),
        }
        # Forward all HTTP headers
        for key, val in self.headers.items():
            key_upper = key.upper().replace('-', '_')
            if key_upper in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
                continue
            environ['HTTP_' + key_upper] = val

        # Call Flask WSGI app
        status_holder = []
        headers_holder = []

        def start_response(status, response_headers, exc_info=None):
            status_holder.append(status)
            headers_holder.extend(response_headers)

        try:
            result = flask_app(environ, start_response)
            body_bytes = b''.join(result)
        except Exception:
            import traceback
            self.send_response(500)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(traceback.format_exc().encode())
            return

        status_code = int(status_holder[0].split(' ', 1)[0])
        self.send_response(status_code)
        for h_name, h_val in headers_holder:
            self.send_header(h_name, h_val)
        self.end_headers()
        self.wfile.write(body_bytes)

    def log_message(self, *args):
        pass  # suppress default logging
