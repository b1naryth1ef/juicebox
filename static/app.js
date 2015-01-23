$(function() {

  var Song = Backbone.Model.extend({
    defaults: {
      title: 'No title',
      artist: 'No artist',
      album: 'No album',
      genre: 'No genre',
      state: 'stop',
      time: 0,
      elapsed: 0,
      id: -1
    },
    urlRoot: '/api/songs',
  });

  var Playlist = Backbone.Model.extend({
    defaults: {
      owner: -1,
      is_public: false,
      id: -1,
      title: 'No title'
    },
    parse: function(response) {
      response.is_public = response['public'];
      delete response['public'];
      return response;
    },
    urlRoot: '/api/playlists'
  });

  var PlaylistCollection = Backbone.Collection.extend({
    model: Playlist,
    url: '/api/playlists',  
    parse: function(response) {
      return response.playlists;
    }
  });

  var Player = Backbone.Model.extend({
    urlRoot: '/api/player',
    mpd_status: {},
    mpd_playlist: [],
    play: function() {
      $.get(this.urlRoot + '/play');
    },
    pause: function() {
      $.get(this.urlRoot + '/pause');
    },
    next: function() {
      $.get(this.urlRoot + '/next');
    },
    previous: function() {
      $.get(this.urlRoot + '/previous');
    },
    stop: function() {
      $.get(this.urlRoot + '/stop');
    },
    shuffle: function() {
      console.log('shuffle');
    },
    random: function() {
      console.log('random');
    },
    clear: function() {
      console.log('clear');
    },
    seek: function(ts) {
      $.get(this.urlRoot + '/seek?ts=' + ts.toString());
    },
    queue: function(id) {
      $.get(this.urlRoot + '/queue/song', { song: id });
    },
    update_status: function() {
      var _this = this;
      $.getJSON(this.urlRoot + '/status').success(function(data) {
        _this.mpd_playlist = data.playlist;
        delete data.playlist
        _this.mpd_status = data;
      });
    },
    update_status_synch: function() {
      var _this = this;
      $.ajax({
        type: "GET",
        url: this.urlRoot + '/status',
        async: false,
        success: function(data) {
          _this.mpd_playlist = data.playlist;
          delete data.playlist
          _this.mpd_status = data;
        }
      });
    }
  });

  var PlayerView = Backbone.View.extend({
    el: $('#mpd'),
    initialize: function() {
      this.player = new Player();
      this.mpd_template = _.template($('#mpd_template').html());
      this.player.update_status_synch();
    },
    render: function() {
      var _this = this;
      var current_state = _this.player.mpd_status.state;
      $(this.el).html(this.mpd_template({
        now_playing: _this.player.mpd_status,
        playlist: _this.player.mpd_playlist
      }));

      $('.playlist_entry').removeClass('playlist_playing');
      if (current_state == 'play') {
        $('.fa-play').css('color', 'green');
        $('#song_' + _this.player.mpd_status.songid).addClass('playlist_playing');
      } else if (current_state == 'stop' || current_state == 'pause') {
        $('.fa-' + current_state).css('color', 'red');
      }
      $('#timeslider').val(_this.player.mpd_status.elapsed);
      $(this.el).find('.control_link').on('click', function(e) {
        var operation = e.target.dataset.operation;
        _this.player[operation]();
        _this.player.update_status();
        _this.render();
      });
      $('#timeslider').on('change', function() {
        _this.player.seek($('#timeslider').val());
        _this.render();
      });
    }
  });

  $('#search_button').on('click', function() {
    $('#search_results').empty();
    $.getJSON('/api/search', { query: $('#search_box').val() }).done(function(data) {
      _.each(data.songs, function(song) {
        $('#search_results').append(_.template($('#song_list_template').html())(song));
        $('#search_result_' + song.id + ' a').on('click', function() {
          PlayerApp.player.queue(song.id);
        });
      });
      $('#search_results').show();
    });
  });
  
  window.PlayerApp = new PlayerView();
  PlayerApp.render();

  setInterval(function() {
    PlayerApp.player.update_status();
    PlayerApp.render();
  }, 1000);

  $('body').on('keyup', function(e) {
    if (e.keyCode == 32) {
      $('.fa-pause').trigger('click');
    }
  });
});
