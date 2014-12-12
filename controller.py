import logging

from mpd import MPDClient
from db import Song

log = logging.getLogger(__name__)

class Controller(object):
    class Mode:
        NONE = 0
        QUEUE = 1
        RANDOM = 2

    def __init__(self, host="/run/mpd/socket"):
        self.cli = MPDClient()
        self.cli.timeout = 10
        self.cli.connect(host, 0)
        log.info("Controller connected to MPD server version %s" % self.cli.mpd_version)

        self.mode = Controller.Mode.NONE
        self.switch_mode(Controller.Mode.RANDOM)

    def add_song(self, song):
        self.cli.add(song.as_mpd())

    def add_playlist(self, playlist):
        map(self.cli.add, playlist.as_mpd())

    def switch_mode(self, mode):
        self.mode = Controller.Mode.RANDOM

        if mode == Controller.Mode.RANDOM:
            self.cli.consume(0)
            self.cli.random(1)
            self.cli.repeat(1)
            self.cli.single(0)
            self.cli.clear()

            # Load up a ton of random songs
            playlist = Song.as_mpd_playlist(Song.select())
            map(self.cli.add, playlist)

        if mode == Controller.Mode.QUEUE:
            self.cli.consume(1)
            self.cli.random(0)
            self.cli.repeat(0)
            self.cli.single(0)
            self.cli.clear()

