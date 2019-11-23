// Rippmenüüd aasta ja kuu valimiseks

// Valitud aasta kuud
function filterMonthItemsByYear(element) {
  let ey = document.getElementById("yearinput");
  let selectedYear = ey.options[ey.selectedIndex].value;
  return element[0] == parseInt(selectedYear, 10);
};

// Valitud aasta kuuvalikute lisamine
function addOption(item) {
  $('#monthinput').append(`<option value=${item[1]}>${getEstonianMonthName(item[1])} (${item[2]})</option>`);
};

// Valitud aasta jaoks kuude valiku seadmine
function getMonthArticles() {
  let valitudAastaKuud = artikleidKuudeKaupa.filter(filterMonthItemsByYear);
  $('#monthinput').empty();
  valitudAastaKuud.forEach(addOption);
};

// Valime eelvalikuna aasta ja kuu 100 aastat tagasi
function initHundredYearAgo() {
  let today      = new Date();
  let thisYear   = today.getFullYear();
  let thisMonth  = today.getMonth();
  initYear = thisYear - 100;
  initMonth = thisMonth + 1
  $("#yearinput").val(initYear).change();
  if ( $("#monthinput option[value='" + initMonth + "']").val() !== undefined) {
    $("#monthinput").val(initMonth);
  };
};

// let artikleidKuudeKaupa = {{ artikleid_kuus }};
$( document ).ready(function() {
  // let valitudAastaKuud = [];
  getMonthArticles();
  initHundredYearAgo();
});