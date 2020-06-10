// ver 2020.5
// Tagastab eestikeelse kuunime
function getEstonianMonthName(idx) {
  var kuud = [
    'jaanuar', 'veebruar', 'märts',
    'aprill', 'mai', 'juuni',
    'juuli', 'august', 'september',
    'oktoober', 'november', 'detsember'
  ];
  return kuud[idx-1];
}

// Abifunktsioon viivituse tekitamiseks
function throttle(fn, delay) {
  var last;
  var timer;
  return function () {
    var now = +new Date();

    if (last && now < last + delay) {
      clearTimeout(timer);
      timer = setTimeout(function () {
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
  if ($(window).scrollTop() >= 43) {
    $('nav').addClass('fixed-header');
  }
  else {
    $('nav').removeClass('fixed-header');
  }
}

// Väikese ekraani menüü (Opening and Collapsing the Navigation Bar)
function toggleRightMenu() {
  let x = document.getElementById("rightMenu");
  const closeIcon = "&#10060;";
  const openIcon  = "&#9776;";
  if (x.className.indexOf("w3-show") == -1) {
    x.className += " w3-show";
    document.getElementById("rightMenuLink").innerHTML = closeIcon;
  } else {
    x.className = x.className.replace(" w3-show", "");
    document.getElementById("rightMenuLink").innerHTML = openIcon;
  }
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
  // Sulgeme navigatsioonimenüü, kui see on avatud
  let rightMenu = document.getElementById("rightMenu");
  if (rightMenu.className.indexOf("w3-show") != -1) {
    toggleRightMenu();
  };
  // Avame tagasisidevormi
  var x = document.getElementById("panelFeedBack");
  if (x.className.indexOf("w3-show-block") == -1) {
    x.className += " w3-show-block";
//    kirjeldusField = document.getElementById("id_kirjeldus");
    kirjeldusField = $("#id_kirjeldus");
    if (kirjeldusField.is(":visible")) {
      kirjeldusField.focus();
    };
  } else {
    x.className = x.className.replace(" w3-show-block", "");
  };
};

function hoverDate(x) {
  const newClassName = 'date-highlighted';
  let selectedId = x.parentElement.id;
  let selectedDateClass = x.className;
  let selectedDateField = document.getElementById(selectedId);
  $(selectedDateField.getElementsByClassName('year')).addClass(newClassName);
  if (selectedDateClass.includes('month')) {
    $(selectedDateField.getElementsByClassName('month')).addClass(newClassName);
  }
  if (selectedDateClass.includes('day')) {
    $(selectedDateField.getElementsByClassName('month')).addClass(newClassName);
    $(selectedDateField.getElementsByClassName('day')).addClass(newClassName);
  }
}

function normalDate(x) {
  const oldClassName = 'date-highlighted';
  let selectedId = x.parentElement.id;
  let selectedDateField = document.getElementById(selectedId);
  let selectedDateFieldElements = Array.from(selectedDateField.querySelectorAll("a"));

  selectedDateFieldElements.forEach(function (element) {
    $(element).removeClass(oldClassName);
  });
}

function changeIconColor(data) {
  elementIlmStartIcon = document.getElementById("ilm_start_icon");
  if (elementIlmStartIcon !== undefined) {
    temperatureNow = data.airtemperatures[data.airtemperatures.length - 1][1];
        if (temperatureNow < 0) {
          elementIlmStartIcon.style.color = '#48AFE8';
        } else {
          elementIlmStartIcon.style.color = '#FF3333';
        };
  };
};

// Ikoonide värvi muutmine, kui on vihje või kommentaar
function showFeedBackInfo() {
  // Küsime andmed
	$.ajax({
	  url: $("#wiki_base_info").attr("data-url"),
	  dataType: 'json',
	  timeout: 300000,
	  success: function (data)
      {
        // Värvime tagasiside ikooni, kui on perioodil tagasisidet
        elementFeedbackIcon = document.getElementById("wiki_base_feedback");
        if (elementFeedbackIcon !== undefined) {
          if (data.feedbacks > 0) {
            elementFeedbackIcon.style.color = '#48AFE8';
            elementFeedbackIcon.title = data.feedbacks + ' tagasiside' + (data.feedbacks > 1 ? 't' : '') + ' viimase 24h jooksul';
          };
        };
        // Värvime blogi ikooni, kui on perioodil kommentaare
        elementBlogIcon = document.getElementById("wiki_base_blog");
        if (elementBlogIcon !== undefined) {
          if (data.comments > 0) {
            elementBlogIcon.style.color = '#48AFE8';
            elementBlogIcon.title = data.comments + ' kommentaar' + (data.comments > 1 ? 'i' : '') + ' viimase 24h jooksul';
          };
        };
      },
	  error: function (XMLHttpRequest, textstatus, errorThrown)
      {
        window.setTimeout(wiki_base_info, 600000);
      }
	});
};

// Avab perioodivaadete alamvalikud
function openLinks(evt, linkName) {
  let modelName = 'artikkel';
  if (linkName.indexOf("isik") >= 0) {
    modelName = 'isik';
  };
  if (linkName.indexOf("organisatsioon") >= 0) {
    modelName = 'organisatsioon';
  };
  if (linkName.indexOf("objekt") >= 0) {
    modelName = 'objekt';
  };
  let newClassName = 'background-' + modelName;
  var i, x, tablinks;
  x = document.getElementsByClassName("seotud");
  for (i = 0; i < x.length; i++) {
    x[i].style.display = "none";
  }
  tablinks = document.getElementsByClassName("tablink");
  for (i = 0; i < x.length; i++) {
    tablinks[i].className = tablinks[i].className.replace(/\bbackground-artikkel\b/g, "");
    tablinks[i].className = tablinks[i].className.replace(/\bbackground-isik\b/g, "");
    tablinks[i].className = tablinks[i].className.replace(/\bbackground-organisatsioon\b/g, "");
    tablinks[i].className = tablinks[i].className.replace(/\bbackground-objekt\b/g, "");
  }
  document.getElementById(linkName).style.display = "block";
  evt.currentTarget.className += " " + newClassName;
}
