$(function() {

  var Song = Backbone.Model.extend({});

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
      var data = {};
      $.getJSON('/api/player/status').success(function(d) { data = d; });
      return d;
    }
  });

  var MPDView = Backbone.View.extend({
    el: $('#mpd'),
    initialize: function() {
      this.mpd = new MPD({
        now_playing: new Song({
          title: 'No title',
          artist: 'No artist',
          album: 'No album',
          genre: 'No genre',
          state: 'stop',
          time: 0,
          elapsed: 0
        })
      })
      this.mpd_template = _.template($('#mpd_template').html());
    },
    render: function() {
      var mpd = this.mpd;
      var _this = this;
      window.mpd = this.mpd;
      $(this.el).html(this.mpd_template(mpd.attributes.now_playing.attributes));
      $(this.el).find('.control_link').on('click', function(e) {
        var operation = e.target.dataset.operation;
        mpd[operation]();
        mpd.attributes.now_playing = new Song(mpd.get_status);
        console.log(mpd.attributes.now_playing.attributes);
        _this.render();
      });
    }
  });

  var MPDApp = new MPDView;
  MPDApp.render();
});
