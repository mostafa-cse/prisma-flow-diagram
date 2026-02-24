import sys
import os

# Minimal test - no external imports except flask
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "<h1>Flask works on Vercel!</h1><p>Now testing matplotlib...</p>"

handler = app
