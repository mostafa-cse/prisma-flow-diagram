import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "<h1>Flask works with @vercel/python!</h1>"

handler = app
