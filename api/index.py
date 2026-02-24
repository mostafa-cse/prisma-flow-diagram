import sys
import os

# Set Vercel environment flag BEFORE importing app
os.environ['VERCEL'] = '1'
os.makedirs('/tmp/matplotlib', exist_ok=True)
os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib'

# Add parent directory to path to import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app import app, init_db
    init_db()
    handler = app
except Exception as _e:
    import traceback
    _tb = traceback.format_exc()

    from flask import Flask as _Flask
    _err_app = _Flask(__name__)

    @_err_app.route("/", defaults={"path": ""})
    @_err_app.route("/<path:path>")
    def _error_page(path):
        return f"<pre><b>Import/init error:</b>\n{_tb}</pre>", 500

    handler = _err_app
