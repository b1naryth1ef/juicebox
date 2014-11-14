from gevent import monkey; monkey.patch_all()

from flask import Flask

app = Flask("juicebox")

@app.route("/")
def route_index():
    return "Hello World!"

@app.route("/stream")
def route_stream():
    pass
