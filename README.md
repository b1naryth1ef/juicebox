# JuiceBox
A virtual jukebox intended for collaborative enviroments.

## API
The API attempts to be a RESTfull as possible, and thus is segmented based on the highest entity used for a request. All the response examples in this document assume a key in the JSON hash of "success" with a boolean value of `true`.

### Player
The player handles all methods related to the actual playing backend. It's a sort of virtual iPod that allows for pausing, playing, queueing, skipping, shuffling, and more.

#### GET /api/player/status
This route returns the current player status which can be used by all consuming clients to help with displaying information

Example Response:
```
{}
```

#### GET /api/player/[skip, pause, play, stop, shuffle, random, clear]
This route allows for basic controls of the 'iPod' like backend player. Most of these are straightforward, however it should be noted that the random option will switch the player from using a queue to playing a random subset of all songs in the system. Queueing any song or playlist after this mode switch will revert the player back to the queue-based mode. Clear will completely empty the current queue (if in queued mode).

Example Response:
```
{}
```

#### GET /api/player/queue/song
This route will add a song onto the bottom of the queue. If the player is currently in random mode, this will empty the random playlist and immediatly start playing the song.

Params:
  - song - an integer representing the song ID to queue

Example Response:
```
{}
```

#### GET /api/player/queue/playlist
This route will add an entire playlist to the end of the queue. Like the above queue/song route, this will reset the player mode to queued.

Params:
  - playlist - an integer representing the playlist ID to queue

Example Response:
```
{}
```

### Songs
Songs represent an individual song or track that has been previously added to the system. Songs live both in the database, and physically on juiceboxes data volume.

#### GET /api/songs
This route allows for listing and paginating every song added to the database. By default, this route will return the first 100 ordered by the date they where added to the database.

Params:
  - page: the page number (optional)

Example Response:
```
{
  page: 5,
  songs: [{} ...]
}
```

#### GET /api/songs/<id>
Returns information about a song given the song's ID.

Example Response:
```
{
  id: 1,
  owner: 55,
  title: "My Song Title",
  artist: "My Artist Name",
  album: "My Album Name",
  checksum: "My MD5 Hash"
}
```

#### POST /api/songs/upload
Uploads a song to the database.

Params:
  - file: the mp3 file

Example Response:
```
{}
```

### Playlists

