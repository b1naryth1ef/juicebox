import bcrypt
from peewee import *
from gravatar import Gravatar

db = SqliteDatabase("juicebox.db")

class BModel(Model):
    class Meta:
        database = db

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
    class MediaType:
        SONG = 1

    owner = ForeignKeyField(User)
    title = CharField()
    artist = CharField()
    album = CharField(null=True)
    mediatype = IntegerField(default=MediaType.SONG)
    location = CharField()

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
    for table in [User, Song, Playlist, PlaylistEntry]:
        table.drop_table(True)
        table.create_table(True)

    User(username="1", password=User.hash_password("1")).save()
