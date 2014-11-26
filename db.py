import os, sys
import bcrypt, eyed3, uuid

from peewee import *
from playhouse.sqlite_ext import SqliteExtDatabase, FTSModel

from gravatar import Gravatar

db = SqliteExtDatabase("juicebox.db", threadlocals=True)

MUSIC_DIR = "data/music"
MD5SUM = "md5" if sys.platform == "darwin" else "md5sum"

class BModel(Model):
    SEARCHABLE = False

    class Meta:
        database = db

    def get_search_model(self):
        return None

    def save(self, *args, **kwargs):
        id = Model.save(self, *args, **kwargs)

        if self.SEARCHABLE:
            search_model = self.get_search_model()
            if bool(self._get_pk_value()):
                search_model.update_from(self)
            else:
                search_model.create_from(self)
        return id

class SModel(FTSModel):
    class Meta:
        database = db

    @classmethod
    def update_fields(cls, instA, instB):
        relation_name = instA.__class__.__name__.lower()
        setattr(instB, relation_name, instA.id)

        for field in cls._meta.fields.keys():
            if field == "id" or field == relation_name: continue
            setattr(instB, field, getattr(instA, field))

    @classmethod
    def create_from(cls, inst):
        self = cls()
        cls.update_fields(inst, self)
        self.save()
        return self

    @classmethod
    def update_from(cls, inst):
        parent_name = inst.__class__.__name__.lower()
        try:
            self = cls.get(getattr(cls, parent_name) == inst)
        except cls.DoesNotExist:
            return cls.create_from(inst)
        cls.update_fields(inst, self)
        self.save()
        return self

class User(BModel):
    username = CharField()
    email = CharField(null=True)
    password = CharField()
    slackid = CharField(null=True)
    active = BooleanField(default=True)

    def get_avatar(self, size=200):
        g = Gravatar(self.email or username+"@getbraintree.com")
        return "http://unicornify.appspot.com/avatar/%s?s=%s" % size

    @staticmethod
    def hash_password(pw):
        return bcrypt.hashpw(pw, bcrypt.gensalt())

    def check_password(self, pw):
        return bcrypt.hashpw(pw, self.password) == self.password

class Song(BModel):
    SEARCHABLE = True
    DICT_FIELDS = ["id", "owner", "title", "artist", "album", "checksum"]

    class MediaType:
        SONG = 1

    owner = ForeignKeyField(User)
    title = CharField()
    artist = CharField()
    album = CharField(null=True)
    mediatype = IntegerField(default=MediaType.SONG)
    checksum = CharField(null=False)
    location = CharField()

    def get_search_model(self):
        return FTSSong

    def create_song_path(self):
        DIR = os.path.join(MUSIC_DIR, self.owner.username)
        if not os.path.exists(DIR):
            os.mkdir(DIR)

        DIR = os.path.join(MUSIC_DIR, self.artist)
        if not os.path.exists(DIR):
            os.mkdir(DIR)

        if self.album:
            DIR = os.path.join(DIR, self.album)
            if not os.path.exists(DIR):
                os.mkdir(DIR)

        DIR = os.path.join(DIR, self.title+".mp3")
        return DIR

    @classmethod
    def new_from_file(cls, user, fobj):
        temp_name_base = str(uuid.uuid4())
        temp_name = os.path.join(MUSIC_DIR, temp_name_base + ".mp3")
        fobj.save(temp_name)

        # First lets grab the metadata
        cur = os.getcwd()
        os.chdir(MUSIC_DIR)
        meta = eyed3.load(os.path.basename(temp_name))
        os.chdir(cur)

        # Grab checksum
        checksum = os.popen("%s %s" % (MD5SUM, temp_name)).read().split(" ", 1)[0]

        # Normalize Audio
        new_temp_name = os.path.join(MUSIC_DIR, temp_name_base + "_normal.mp3")
        os.popen("sox --norm %s %s" % (temp_name, new_temp_name))
        temp_name = new_temp_name

        # We need some basic stuff
        if not meta.tag.artist or not meta.tag.title:
            raise Exception("Not enough metadata")

        count = cls.select(cls.id).where(
            ((cls.artist == meta.tag.artist) & (cls.title == meta.tag.title)) |
            (cls.checksum == checksum)
        ).count()

        # Already exists
        if count:
            return -1

        song = cls()
        song.owner = user
        song.title = meta.tag.title
        song.artist = meta.tag.artist
        song.album = meta.tag.album
        song.location = song.create_song_path()
        song.checksum = checksum
        os.rename(temp_name, song.location)
        return song.save()

    def to_dict(self):
        return {
            "id": self.id,
            "owner": self.owner.id,
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "checksum": self.checksum
        }

    def open_meta(self):
        return eyed3.load(self.location)

class FTSSong(SModel):
    class Meta:
        database = db

    song = ForeignKeyField(Song)
    title = TextField()
    artist = TextField()
    album = TextField()

class Playlist(BModel):
    owner = ForeignKeyField(User)
    title = CharField()

    def get_songs(self):
        return PlaylistEntry.join(Song).select(PlaylistEntry.playlist == self).order_by(PlaylistEntry.id)

class PlaylistEntry(BModel):
    playlist = ForeignKeyField(Playlist)
    song = ForeignKeyField(Song)

# TODO: stats, likes

if __name__ == "__main__":
    for table in [User, Song, Playlist, PlaylistEntry, FTSSong]:
        table.drop_table(True)
        table.create_table(True)

    User(username="1", password=User.hash_password("1")).save()
