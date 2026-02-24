import sys
import os

# Set Vercel environment flag BEFORE importing app
os.environ['VERCEL'] = '1'
os.makedirs('/tmp/matplotlib', exist_ok=True)
os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib'

# Add parent directory to path to import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, init_db

# Initialize database on cold start
init_db()

# Vercel serverless function handler
handler = app
