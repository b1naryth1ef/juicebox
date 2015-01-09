$(function() {

  var Song = Backbone.Model.extend({
    defaults: {
      title: 'No title',
      artist: 'No artist',
      album: 'No album',
      genre: 'No genre',
      state: 'stop',
      time: 0,
      elapsed: 0
    }
  })

  var MPD = Backbone.Model.extend({
    play: function() {
      $.get('/api/player/play');
      console.log('play');
    },
    pause: function() {
      $.get('/api/player/pause');
      console.log('pause');
    },
    skip: function() {
      console.log('skip');
    },
    previous: function() {
      $.get('/api/player/previous');
      console.log('previous');
    },
    stop: function() {
      $.get('/api/player/stop');
      console.log('stop');
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
    get_status: function() { // status is a javscript kw :(
      $.getJSON('/api/player/status')
    }
  });

  var MPDView = Backbone.View.extend({
    el: $('#mpd'),
    initialize: function() {
      this.mpd = new MPD({
        now_playing: new Song(Song.defaults)
      })
      this.mpd_template = _.template($('#mpd_template').html());
    },
    render: function() {
      var _this = this;
      window.mpd = this.mpd;
      $(this.el).html(this.mpd_template(_this.mpd.attributes.now_playing.attributes));
      $(this.el).find('.control_link').on('click', function(e) {
        var operation = e.target.dataset.operation;
        _this.mpd[operation]();
        $.getJSON('/api/player/status').success(function(data) {
          _this.mpd.set({ now_playing: new Song($.extend(Song.defaults, data)) });
          _this.render();
        });
        console.log(_this.mpd.attributes.now_playing.attributes);
      });
    }
  });

  var MPDApp = new MPDView;
  MPDApp.render();
});
