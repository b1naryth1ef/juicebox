import os, sys, json

from flask import Flask, request, g, jsonify, session, Response
from werkzeug import secure_filename
from peewee import SQL

from db import MUSIC_DIR, User, Song, FTSSong, Playlist, FTSPlaylist

app = Flask("juicebox")
app.secret_key = "swag"

MUSIC_EXT = set(['mp3'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in MUSIC_EXT

# A custom App Exception
class AppHandledException(Exception):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

class AuthException(AppHandledException): pass
class APIError(AppHandledException): pass

# A custom app response
class APIResponse(Response):
    def __init__(self, data):
        Response.__init__(self)
        if not 'success' in data:
            data['success'] = True

        self.data = json.dumps(data)
        self.mimetype = "application/json"

@app.before_request
def before_request():
    g.user = None
    if 'id' in session:
        g.user = User.get(User.id == session['id'])

    if "test" in request.headers:
        g.user = User.get(User.id == request.headers.get("test"))

@app.after_request
def app_after_request(response):
    if isinstance(response, dict):
        if not 'success' in response:
            response['success'] = True
        return jsonify(response)
    return response

@app.errorhandler(AuthException)
def app_handle_auth_exception(e):
    return jsonify({
        "success": False,
        "msg": e.kwargs.get("msg", "You must be logged in to complete that action")
    }), 401

@app.errorhandler(APIError)
def app_handle_api_error(e):
    msg = e.args[0] if len(e.args) else e.kwargs.get("msg", "Generic API Error")
    code = e.args[1] if len(e.args) > 1 else e.kwargs.get("code", 400)

    return jsonify({
        "success": False,
        "msg": msg
    }), code

@app.route("/api/songs")
def route_api_songs():
    page = int(request.values.get("page", 1))

    songs = Song.select(User.username,
            *map(lambda i: getattr(Song, i), Song.DICT_FIELDS)).join(User).paginate(page, 100)
    return APIResponse({
        "page": page,
        "songs": map(lambda i: i.to_dict(), list(songs))
    })

@app.route("/api/songs/<id>")
def route_api_songs_single(id):
    try:
        song = Song.get(Song.id == id)
    except Song.DoesNotExist:
        raise APIError("Invalid Song ID")
    return APIResponse(song.to_dict())

@app.route("/api/songs/upload", methods=["POST"])
def route_upload():
    if not g.user:
        raise AuthException()

    f = request.files["file"]
    if f and allowed_file(f.filename):
        return jsonify({"success": Song.new_from_file(g.user, f)})
    raise APIError("No or invalid file specified")

@app.route("/api/playlists")
def route_api_playlists():
    page = int(request.values.get("page", 1))

    playlists = Playlist.select().paginate(page, 100)
    return APIResponse({
        "page": page,
        "playlists": map(lambda i: i.to_dict(), list(playlists))
    })

@app.route("/api/playlists/<id>")
def route_api_playlists_single(id):
    try:
        pl = Playlist.get(Playlist.id == id)
    except Playlist.DoesNotExist:
        raise APIError("Invalid Playlist ID")

    return APIResponse(pl.to_dict(tiny=False))

@app.route("/api/playlists/create")
def route_api_playlists_create():
    if not g.user:
        raise AuthException()

    if not request.values.get("name"):
        raise APIError("Must specify name for playlist creation")

    id =Playlist.create(
        owner=g.user,
        title=request.values.get("name"),
        public=request.values.get("public", False))

    return APIResponse({"id": id})

@app.route("/api/playlist/<id>/<action>")
def route_api_playlist_modify(id, action):
    if not g.user:
        raise AuthException()

    try:
        playlist = Playlist.get(Playlist.id == id)
    except Playlist.DoesNotExist:
        raise APIError("Invalid Playlist ID")

    if not playlist.can_user_modify(g.user):
        raise AuthException(msg="Cannot edit private playlist we do not own")

    try:
        song = Song.get(Song.id == request.values.get("song"))
    except Song.DoesNotExist:
        raise APIError("Invalid Song ID")

    # Try adding to the playlist
    if action == "add":
        playlist.add_song(song)
        return APIResponse({"pos": playlist.get_songs().count()})

    if action == "remove":
        playlist.rmv_song(song)
        return APIResponse({})


@app.route("/api/search")
def route_api_search():
    if not request.values.get("query"):
        raise APIError("Must specify a query to search")

    songs = FTSSong.search(
        request.values.get("query")
    ).order_by(SQL('score')).limit(25)

    playlists = FTSPlaylist.search(
        request.values.get("query")
    ).order_by(SQL('score')).limit(25)

    return APIResponse({
        "songs": map(lambda i: i.song.to_dict(), list(songs)),
        "playlists": map(lambda i: i.playlist.to_dict(), list(playlists))
    })

@app.route("/api/enqueue")
def route_api_enqueue():
    pass

@app.route("/api/control/<action>")
def route_api_control(action):
    pass

@app.route("/api/users/settings")
def route_users_settings():
    if not g.user:
        raise AuthException()

    if request.values.get("slackid"):
        g.user.slackid = request.values.get("slackid")

    g.user.save()
    return APIResponse({})

@app.route("/api/users/change_password")
def route_users_change_password():
    if not g.user:
        raise AuthException()

    pw = requests.values.get("password")
    g.user.password = g.user.hash_passowrd(pw)
    return APIResponse({})

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

def run():
    if not os.path.exists(MUSIC_DIR):
        print "Invalid MUSIC_DIR path `%s`!" % MUSIC_DIR
        sys.exit(1)

    app.run("0.0.0.0", port=3000, debug=True)

if __name__ == "__main__":
    run()

