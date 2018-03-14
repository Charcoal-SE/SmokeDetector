$(document).ready(function() {
  var site_favicons = {};

  var socket = new WebSocket("ws://localhost:9001");

  socket.onmessage = function(msg) {
    var post = JSON.parse(msg.data);
    console.log(post);

    if (post["action"] == "new") {
      with_favicon(post.site, function (favicon_url) {
        var image = $("<img>").attr("src", favicon_url);
        image.attr("id", post.site.replace(/\./g, '') + post.post_id.toString())
        $("body").append(image);
      });
    }
    else if (post["action"] == "moved") {
      icon = $("img#" + post.site.replace(/\./g, '') + post.post_id.toString());
      console.log(icon);

      stage = $("div[data-stage='" + post.stage + "']");
      console.log(stage);
      $(icon).appendTo($(stage));
    }
  };

  function with_favicon(site, closure) {
    if (site in site_favicons) {
      closure(site_favicons[site]);
    }
    else {
      $.get("https://api.stackexchange.com/2.2/info?key=IAkbitmze4B8KpacUfLqkw((&site=" + site + "&filter=!w-(uh37l-y4F5AZ9BH", function(data) {
        site_favicons[site] = data["items"][0]["site"]["favicon_url"];
        closure(site_favicons[site]);
      })
    }
  }
});
