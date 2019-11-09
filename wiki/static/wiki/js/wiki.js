// Abifunktsioon viivituse tekitamiseks
function throttle(fn, delay) {
  let last;
  let timer;

  return () => {
    const now = +new Date;

    if (last && now < last + delay) {
      clearTimeout(timer);

      timer = setTimeout(() => {
        last = now;
        fn();
      }, delay);
    } else {
      last = now;
      fn();
    }

  };
}

// Fikseeritud navigatsiooniriba tekitamiseks
function onScroll() {
  if ($(window).scrollTop() >= 60) {
    $('nav').addClass('fixed-header');
  }
  else {
    $('nav').removeClass('fixed-header');
  }
}

window.addEventListener('scroll', throttle(onScroll, 25));

// Töötleb kõik reCAPTCHAga varustatud vormid
function grecaptcha_onload() {
  $('.g-recaptcha-response').each(function( k, v ) {
    var submit = $(v).closest("form").find('[type="submit"]');
    grecaptcha.render( submit[0], {
      'sitekey' : '{% recaptcha_public_key %}',
      'callback' : function( token ) {
        $(v).closest("form").find('.g-recaptcha-response').val( token );
        $(v).closest("form").submit();
      },
      'size' : 'invisible',
    });
  });
}

// Väikese ekraani menüü (Opening and Collapsing the Navigation Bar)
function openRightMenu() {
  document.getElementById("rightMenu").style.display = "block";
}
function closeRightMenu() {
  document.getElementById("rightMenu").style.display = "none";
}

// Load Facebook SDK for JavaScript
(function(d, s, id) {
  var js, fjs = d.getElementsByTagName(s)[0];
  if (d.getElementById(id)) return;
  js = d.createElement(s); js.id = id;
  js.src = "https://connect.facebook.net/et_EE/sdk.js#xfbml=1&version=v3.0";
  fjs.parentNode.insertBefore(js, fjs);
}(document, 'script', 'facebook-jssdk'));

// Tagasisidevormi kuvamiseks
function showFeedback() {
  var x = document.getElementById("panelFeedBack");
  if (x.className.indexOf("w3-show-block") == -1) {
    x.className += " w3-show-block";
    document.getElementById("id_kirjeldus").focus();
  } else {
    x.className = x.className.replace(" w3-show-block", "");
  }
}