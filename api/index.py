import sys
import os

os.environ['VERCEL'] = '1'
os.makedirs('/tmp/matplotlib', exist_ok=True)
os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib'

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app import app as _app, init_db
    init_db()
    handler = _app
except Exception:
    import traceback
    _tb = traceback.format_exc()
    from flask import Flask as _F, Response as _R
    _e = _F(__name__)
    @_e.route("/", defaults={"path": ""})
    @_e.route("/<path:path>")
    def _err(path):
        return _R(f"<pre>{_tb}</pre>", 200, mimetype="text/html")
    handler = _e
