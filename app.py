from gevent import monkey; monkey.patch_all()

from flask import Flask, request, g, jsonify, session
from werkzeug import secure_filename

from db import User, Song

app = Flask("juicebox")

MUSIC_DIR = "/data/music"
MUSIC_EXT = set(['mp3'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in MUSIC_EXT

@app.before_request
def before_request():
    g.user = User.get(User.id == 1)

@app.route("/upload", methods=["POST"])
def route_upload():
    f = request.files["file"]
    if f and allowed_file(f.filename):
        return jsonify({"success": Song.new_from_file(g.user, f)})
    return jsonify({}), 400

@app.route("/api/songs")
def route_api_songs():
    page = int(request.values.get("page", 1))

    q = Song.select(Song.id, Song.title, Song.artist, User.username).join(User).paginate(page, 100)
    return jsonify({
        "success": True,
        "page": page,
        "songs": map(lambda i: i.to_dict(), list(q))
    })

@app.route("/stream")
def route_stream():
    pass

if __name__ == "__main__":
    app.run(debug=True)
