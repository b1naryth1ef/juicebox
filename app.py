from flask import Flask, request, g, jsonify, session
from werkzeug import secure_filename

from db import User, Song

app = Flask("juicebox")
app.secret_key = "swag"

MUSIC_DIR = "/data/music"
MUSIC_EXT = set(['mp3'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in MUSIC_EXT

@app.before_request
def before_request():
    g.user = None
    if 'id' in session:
        g.user = User.get(User.id == session['id'])

@app.route("/upload", methods=["POST"])
def route_upload():
    if not g.user:
        return 401

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

@app.route("/api/search")
def route_api_search():
    songs = Song.select(Song.title, Song.artist, Song.album).where(
        (Song.title ** request.values.get("query")) |
        (Song.album ** request.values.get("query")) |
        (Song.artist ** request.values.get("query"))
    ).limit(25)

    return jsonify({
        "success": True,
        "songs": map(lambda i: i.to_dict(), list(songs))
    })

@app.route("/api/enqueue")
def route_api_enqueue():
    pass

@app.route("/api/control/<action>")
def route_api_control(action):
    pass

@app.route("/login", methods=["POST"])
def route_login():
    user = request.values.get("user")
    pw = request.values.get("password")

    if not user or not pw:
        return jsonify({"success": False})

    try:
        u = User.get(User.username == user)
    except User.DoesNotExist:
        return jsonify({"success": False})

    if not u.check_password(pw):
        return jsonify({"success": False})
    
    session["id"] = u.id
    return jsonify({"success": True})

@app.route("/register")
def route_register(x):
    params = {k:v for k, v in request.values.items() if k in ["username", "password", "email"]}
    
    if not all(params.values()):
        return jsonify({"success": False, "msg": "Missing params"})
    
    try:
        User.get((User.username == params["username"]) | (User.email == params["email"]))
        return jsonify({"success": False, "msg": "Username or Email already exists"})
    except User.DoesNotExist: pass

    u = User(username=params["username"], email=params["email"])
    u.password = User.hash_password(params["password"])
    
    session["id"] = u.save()
    return jsonify({"success": True})

@app.route("/stream")
def route_stream():
    pass

if __name__ == "__main__":
    app.run("0.0.0.0", port=3000, debug=True)
