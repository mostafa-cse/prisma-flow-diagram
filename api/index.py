from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "<h2>Flask works on Vercel!</h2>"

handler = app
