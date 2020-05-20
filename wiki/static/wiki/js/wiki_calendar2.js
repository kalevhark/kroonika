// Rippmenüüd aasta ja kuu valimiseks

// Valitud aasta kuud
function filterMonthItemsByYear(element) {
  let ey = document.getElementById("yearinput");
  let selectedYear = ey.options[ey.selectedIndex].value;
  return element[0] == parseInt(selectedYear, 10);
};

// Valitud aasta kuuvalikute lisamine
function addOption(item) {
  // $('#monthinput').append(`<option value=${item[1]}>${getEstonianMonthName(item[1])} (${item[2]})</option>`);
  $("#monthinput").append(
    "<option value="
      .concat(item[1], ">")
      .concat(getEstonianMonthName(item[1]), " (")
      .concat(item[2], ")</option>")
  );
};

// Valitud aasta jaoks kuude valiku seadmine
function getMonthArticles() {
  let valitudAastaKuud = artikleidKuudeKaupa.filter(filterMonthItemsByYear);
  $('#monthinput').empty();
  valitudAastaKuud.forEach(addOption);
  getMonthCalendar();
};

// Valitud kuu jaoks kalendrilaotus
function getMonthCalendar() {
  var elYear = document.getElementById('yearinput');
  var indYSel = elYear.options[elYear.selectedIndex].value;
  var elMonth = document.getElementById('monthinput');
  var indMSel = elMonth.options[elMonth.selectedIndex].value;
  getCalendar('user_calendar_view_last=' + [indYSel, indMSel].join('-'));
};

// Valime eelvalikuna aasta ja kuu 100 aastat tagasi
//function initHundredYearAgo() {
//  let today      = new Date();
//  let thisYear   = today.getFullYear();
//  let thisMonth  = today.getMonth();
//  initYear = thisYear - 100;
//  initMonth = thisMonth + 1
//  $("#yearinput").val(initYear).change();
//  if ( $("#monthinput option[value='" + initMonth + "']").val() !== undefined) {
//    $("#monthinput").val(initMonth);
//  };
//};

function initYearMonthMenu(userCalendarViewLast) {
  if (userCalendarViewLast !== undefined) {
    var [initYear, initMonth] = userCalendarViewLast.split('-')
  } else {
    let today      = new Date();
    let thisYear   = today.getFullYear();
    let thisMonth  = today.getMonth();
    var initYear = thisYear - 100;
    var initMonth = thisMonth + 1;
  };
  if ( $("#yearinput option[value='" + initYear + "']").val() !== undefined) {
    $("#yearinput").val(initYear).change();
  };
  getMonthArticles();
  if ( $("#monthinput option[value='" + initMonth + "']").val() !== undefined) {
    $("#monthinput").val(initMonth).change();
  };
  getCalendar('user_calendar_view_last=' + userCalendarViewLast);
  document.getElementById('yearsubmit').onclick = function(event){
    event.preventDefault();
  };
  document.getElementById("yearsubmit").addEventListener("click", function(event) {
    submitForm(this);
  });
};

function getCalendar(value) {
  if (value !== undefined) {
    qs = '?'.concat(value);
  } else {
    qs = '';
  }
  let divId = '#calendar_widget';
  let url = calendarWidgetUrl.concat(qs);

  $.ajax(
    {
      url: url,
      success: function(data) {
        $(divId).html(data);
      },
      error: function (jqXHR, exception) {
        var msg = '';
        if (jqXHR.status === 0) {
            msg = 'Not connect.\n Verify Network.';
        } else if (jqXHR.status == 404) {
            msg = 'Requested page not found. [404]';
        } else if (jqXHR.status == 500) {
            msg = 'Internal Server Error [500].';
        } else if (exception === 'parsererror') {
            msg = 'Requested JSON parse failed.';
        } else if (exception === 'timeout') {
            msg = 'Time out error.';
        } else if (exception === 'abort') {
            msg = 'Ajax request aborted.';
        } else {
            msg = 'Uncaught Error.\n' + jqXHR.responseText;
        }
        $(divId).html(msg);
        <!-- Proovime 5 s pärast uuesti -->
        {
          window.setTimeout(getCalendar(value), 50000);
        };
      },
    }
  );
};

function submitForm(el) {
  let form=document.getElementById('formYearMonth')
  if (el.id=='yearsubmit') {
    form.action = "{% url 'wiki:mine_krono_aasta' %}";
  };
  form.submit();
};
