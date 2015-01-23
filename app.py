import os, sys, json
from functools import wraps

from flask import Flask, request, render_template, g, jsonify, session, redirect, Response
from werkzeug import secure_filename
from peewee import SQL
import soco

from controller import Controller
from db import MUSIC_DIR, User, Song, FTSSong, Playlist, FTSPlaylist

app = Flask("juicebox")
app.secret_key = "swag"
app.controller = Controller()

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
    def __init__(self, data={}):
        Response.__init__(self)
        if not 'success' in data:
            data['success'] = True

        self.data = json.dumps(data)
        self.mimetype = "application/json"

# Auth Decorator
def authed(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not g.user:
            raise AuthException()
        return f(*args, **kwargs)
    return wrapped

@app.before_request
def before_request():
    g.user = None
    try:
        if 'id' in session:
            g.user = User.get(User.id == session['id'])

    except User.DoesNotExist:
        g.user = None

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

@app.route("/")
def route_url_root():
    if not g.user:
      return redirect("login", code=302)
    return render_template('index.html')

@app.route("/api/player/status")
def route_player_status():
    return APIResponse(app.controller.status())

PLAYER_ACTIONS = [ "next", "pause", "play", "stop", "shuffle", "random", "clear", "previous", "seek" ]

@app.route("/api/player/<action>")
@authed
def route_player_actions(action):
    if action not in PLAYER_ACTIONS:
        raise APIError("Invalid Action")

    if action == "random":
        app.controller.switch_mode(Controller.Mode.RANDOM)
        return APIResponse()

    if action == "shuffle":
        app.controller.shuffle()
        return APIResponse()

    if action == "play":
      app.controller.play()
      return APIResponse()

    if action == "pause":
      app.controller.pause()
      return APIResponse()

    if action == "stop":
      app.controller.stop()
      return APIResponse()

    if action == "previous":
      app.controller.previous()
      return APIResponse()

    if action == "next":
      app.controller.next()
      return APIResponse()

    if action == "seek":
      ts = request.values.get("ts")

      if not ts:
        return APIError("Invalid ts")

      app.controller.seek(ts)
      return APIResponse()

    raise APIError("Not Implementted")

@app.route("/api/player/queue/song")
@authed
def route_player_queue_song():
    # If we're in random mode we need to empty the playlist and start over
    if app.controller.mode == Controller.Mode.RANDOM:
        app.controller.switch_mode(Controller.Mode.QUEUE)

    try:
        app.controller.add_song(Song.get(Song.id == request.values.get("song")))
    except Song.DoesNotExist:
        return APIError("Invalid Song ID")

    return APIResponse()

@app.route("/api/player/queue/playlist")
@authed
def route_player_queue_playlist():
    if app.controller.mode == Controller.Mode.RANDOM:
        app.controller.switch_mode(Controller.Mode.QUEUE)

    try:
        app.controller.add_playlist(Playlist.get(Playlist.id == request.values.get("playlist")))
    except Playlist.DoesNotExist:
        return APIError("Invalid Playlist ID")

    return APIResponse()

@app.route("/api/songs")
def route_api_songs():
    page = int(request.values.get("page", 1))

    songs = Song.select(User.username,
            *map(lambda i: getattr(Song, i), Song.DICT_FIELDS)).join(
        User).paginate(page, 100).order_by(Song.added_date)
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
@authed
def route_upload():
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
@authed
def route_api_playlists_create():
    if not request.values.get("name"):
        raise APIError("Must specify name for playlist creation")

    p =Playlist.create(
        owner=g.user,
        title=request.values.get("name"),
        public=request.values.get("public", False))

    return APIResponse({"id": p.id})

@app.route("/api/playlist/<id>/<action>")
@authed
def route_api_playlist_modify(id, action):
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

@app.route("/api/users/settings")
@authed
def route_users_settings():
    if request.values.get("slackid"):
        g.user.slackid = request.values.get("slackid")

    if request.values.get("email"):
        g.user.email = request.values.get("email")

    g.user.save()
    return APIResponse()

@app.route("/api/users/change_password")
@authed
def route_users_change_password():
    pw = requests.values.get("password")
    g.user.password = g.user.hash_passowrd(pw)
    return APIResponse()

@app.route("/login", methods=["GET", "POST"])
def route_login():
    if g.user:
        return redirect("/", code=302)

    if request.method == "GET":
      return render_template("login.html")

    user = request.values.get("user")
    pw = request.values.get("password")

    if not user or not pw:
        raise APIError("Invalid Paramaters")

    try:
        u = User.get(User.username == user)
    except User.DoesNotExist:
        raise APIError("Incorrect Username")

    if not u.check_password(pw):
        raise APIError("Incorrect Password")

    session["id"] = u.id
    return redirect("/", code=302)

@app.route("/api/login", methods=["POST"])
def route_api_login():
    user = request.values.get("user")
    pw = request.values.get("password")

    if not user or not pw:
        raise APIError("Invalid Paramaters")

    try:
        u = User.get(User.username == user)
    except User.DoesNotExist:
        raise APIError("Incorrect Username")

    if not u.check_password(pw):
        raise APIError("Incorrect Password")

    session["id"] = u.id
    return APIResponse()

@app.route("/register", methods=["GET", "POST"])
def route_register():
    if g.user:
        return redirect("/", code=302)

    if request.method == "GET":
        return render_template("register.html")

    params = {k:v for k, v in request.values.items() if k in ["username", "password", "email"]}

    if not all(params.values()):
        return redirect("/", code=302)

    try:
        User.get((User.username == params["username"]) | (User.email == params["email"]))
        return redirect("/", code=302)
    except User.DoesNotExist: pass

    u = User(username=params["username"], email=params["email"])
    u.password = User.hash_password(params["password"])

    session["id"] = u.save()
    g.user = u
    return redirect("/", code=302)

@app.route("/register_api")
def route_register_api():
    if g.user:
        raise APIError("Already logged in!")

    params = {k:v for k, v in request.values.items() if k in ["username", "password", "email"]}

    if not all(params.values()):
        raise APIError("Missing required paramaters!")

    try:
        User.get((User.username == params["username"]) | (User.email == params["email"]))
        raise APIError("User with that username/email already exists!")
    except User.DoesNotExist: pass

    u = User(username=params["username"], email=params["email"])
    u.password = User.hash_password(params["password"])

    session["id"] = u.save()
    return APIResponse()

@app.route("/api/sonos/list")
def route_sonos_list():
    speakers = soco.discover()
    return APIResponse({
        "players": {sp.player_name: sp.ip_address for sp in speakers}
    })

@app.route("/api/sonos/start")
def route_sonos_start():
    sonos = soco.Soco(request.values.get("ip"))
    sonos.play_uri("TODO!")
    return APIResponse()

@app.route("/api/sonos/stop")
def route_sonos_stop():
    sonos = soco.Soco(request.values.get("ip"))
    sonos.stop()
    return APIResponse()

def run():
    if not os.path.exists(MUSIC_DIR):
        print "Invalid MUSIC_DIR path `%s`!" % MUSIC_DIR
        sys.exit(1)

    app.run("0.0.0.0", port=3000, debug=True)

if __name__ == "__main__":
    run()

