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

// Väikese ekraani menüü (Opening and Collapsing the Navigation Bar)
function openRightMenu() {
  let openRightMenuDisplayStatus = document.getElementById("rightMenu").style.getPropertyValue('display');
  if (openRightMenuDisplayStatus == "block") {
    document.getElementById("rightMenu").style.display = "none";
  } else {
    document.getElementById("rightMenu").style.display = "block";
  };
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
  // Sulgeme navigatsioonimenüü, kui see on avatud
  let openRightMenuDisplayStatus = document.getElementById("rightMenu").style.getPropertyValue('display');
  if (openRightMenuDisplayStatus == "block") {
    document.getElementById("rightMenu").style.display = "none";
  };
  // Avame tagasisidevormi
  var x = document.getElementById("panelFeedBack");
  if (x.className.indexOf("w3-show-block") == -1) {
    x.className += " w3-show-block";
    document.getElementById("id_kirjeldus").focus();
  } else {
    x.className = x.className.replace(" w3-show-block", "");
  }
}

function hoverDate(x) {
  const newClassName = 'date-highlighted'
  let selectedId = x.parentElement.id;
  let selectedDateClass = x.className;
  let selectedDateField = document.getElementById(selectedId)
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
  const oldClassName = 'date-highlighted'
  let selectedId = x.parentElement.id;
  let selectedDateField = document.getElementById(selectedId);
  let selectedDateFieldElements = selectedDateField.querySelectorAll("a");

  selectedDateFieldElements.forEach(element => {
    $(element).removeClass(oldClassName);
  });
}

$( document ).ready(function() {
  // console.log( "ready!" );
  // Navigatsiooniriba asukoha kontrollimiseks
  window.addEventListener('scroll', throttle(onScroll, 25));
  // Kuupäevaväljade unikaalsete id-de lisamine
  let dates = document.body.getElementsByClassName('date');
  // console.dir(dates);
  let counter = 0;
  for (let i = 0; i < dates.length; i++) {
    if (!dates[i].id) {
      dates[i].id = "_date_" + counter++;
    }
  }
});