// Aluseks https://codepen.io/geekwen/pen/JYYrob
// Oluliselt täiendanud Kalev Härk 2020
const monthNames = ['', 'jaanuar', 'veebruar', 'märts', 'aprill', 'mai', 'juuni', 'juuli', 'august', 'september', 'oktoober', 'november', 'detsember'];
const KUUL = ['jaanuaril', 'veebruaril', 'märtsil', 'aprillil', 'mail', 'juunil', 'juulil', 'augustil', 'septembril', 'oktoobril', 'novembril', 'detsembril'];

// var monthDays = new Array;

function getCalendar(theYear, theMonth) {
  $.ajax(
    {
      url: calendar_days_with_events_in_month_url,
      data: {
        year: theYear,
        month: theMonth
      },
      success: function(events) {
        // console.log(data);
        events.days_with_events.forEach(function(day) {
          let dayThisMonthId = '#gw--day-this-month-id_' + day;
          $(dayThisMonthId).addClass("day-with-events");
        });
        events.months_with_events.forEach(function(month) {
          let monthChoiceId = '#gw--month-choice-id_' + month;
          $(monthChoiceId).addClass("month-with-events");
        });
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
        console.log(msg);
        <!-- Proovime 5 s pärast uuesti -->
        {
          window.setTimeout(getCalendar(year, month), 50000);
        };
      },
    }
  );
};

var GWDateTimePicker = {
  init: function(param) {
    var [CYEAR, CMONTH] = userCalendarViewLast.split('-');
    CYEAR = parseInt(CYEAR);
    CMONTH = parseInt(CMONTH);
    var now = new Date,
      // CYEAR = now.getFullYear() - 100,
      // CMONTH = now.getMonth() + 1,
      CDAY = now.getDate(),
      $elements = {
        target: document.getElementById(param.targetId),
        wrapper: document.getElementById("gw--datetimepicker"),
        body: document.getElementById("gw--datetimepicker-body"),
        selectedYear: document.getElementById("gw--datetimepicker-selected-year"),
        selectedMonth: document.getElementById("gw--datetimepicker-selected-month"),
        year: document.getElementById("gw--datetimepicker-year"),
        month: document.getElementById("gw--datetimepicker-month"),
        day: document.getElementById("gw--datetimepicker-day")
      };

    $elements.selectedYear.innerHTML = CYEAR;
    $elements.selectedMonth.innerHTML = monthNames[CMONTH];

    // 初始化当月的列表
    this.setDays(CYEAR, CMONTH);

    // 初始化事件
    $elements.wrapper.onclick = function(e) {
      var target = e.target,
        selectedYear, selectedMonth;

      switch (target.id) {
        case "gw--datetimepicker-selected-year":
          $elements.selectedYear.removeAttribute("data-value");
          GWDateTimePicker.setYears(parseInt($elements.selectedYear.innerHTML));
          GWDateTimePicker.showYears($elements);
          break;
        case "gw--datetimepicker-selected-month":
          $elements.selectedYear.removeAttribute("data-value");
          GWDateTimePicker.showMonths($elements);
          break;
        case "gw--datetimepicker-prev":
          GWDateTimePicker.setNav($elements, true);
          break;
        case "gw--datetimepicker-next":
          GWDateTimePicker.setNav($elements);
          break;
        case "gw--now":
          GWDateTimePicker.setDays(CYEAR, CMONTH);
          $elements.selectedYear.innerHTML = CYEAR;
          $elements.selectedMonth.innerHTML = monthNames[CMONTH];
          GWDateTimePicker.showDays($elements);
          GWDateTimePicker.setOutput($elements.target, CYEAR, CMONTH, CDAY);
          break;
      }

      switch (target.className) {
        case "gw--year":
          $elements.selectedYear.innerHTML = target.innerHTML;
          getCalendar(target.innerHTML, 1);
          GWDateTimePicker.showMonths($elements);
          break;
        case "gw--year year-with-events":
          $elements.selectedYear.innerHTML = target.innerHTML;
          getCalendar(target.innerHTML, 1);
          GWDateTimePicker.showMonths($elements);
          break;
        case "gw--month":
          $elements.selectedMonth.innerHTML = target.innerHTML;
          GWDateTimePicker.setDays($elements.selectedYear.innerHTML, monthNames.indexOf($elements.selectedMonth.innerHTML));

          GWDateTimePicker.showDays($elements);
          break;
        case "gw--month month-with-events":
          $elements.selectedMonth.innerHTML = target.innerHTML;
          GWDateTimePicker.setDays($elements.selectedYear.innerHTML, monthNames.indexOf($elements.selectedMonth.innerHTML));

          GWDateTimePicker.showDays($elements);
          break;
        case "gw--day":
          GWDateTimePicker.setOutput($elements.target, $elements.selectedYear.innerHTML, monthNames.indexOf($elements.selectedMonth.innerHTML), target.innerHTML);
          break;
        case "prev gw--day":
          selectedYear = $elements.selectedYear.innerHTML;
          selectedMonth = parseInt(monthNames.indexOf($elements.selectedMonth.innerHTML));
          selectedMonth--;

          if (selectedMonth < 1) {
            selectedYear--;
            selectedMonth = 12;
          }

          GWDateTimePicker.setOutput($elements.target, selectedYear, selectedMonth, target.innerHTML);
          break;
        case "next gw--day":
          selectedYear = $elements.selectedYear.innerHTML;
          selectedMonth = parseInt(monthNames.indexOf($elements.selectedMonth.innerHTML));
          selectedMonth++;

          if (selectedMonth > 12) {
            selectedYear++;
            selectedMonth = 1;
          }

          GWDateTimePicker.setOutput($elements.target, selectedYear, selectedMonth, target.innerHTML);
          break;
      }
    };
  },
  setYears: function(year) {
    var i = year + 8,
      html = "",
      col = 0;
    year -= 8;
    while (year < i) {
      if (col === 0) {
        html += "<tr>";
      }

      let yearWithEventsClass = ''
      if (yearsWithEvents.includes(year)) {
        yearWithEventsClass = ' year-with-events'
      }
      html += '<td class="gw--year' + yearWithEventsClass + '">' + year + '</td>';

      if (col === 3) {
        html += "</tr>";
        col = -1;
      }

      year++;
      col++;
    }

    document.getElementById("gw--datetimepicker-year-body").innerHTML = html;
  },
  setDays: function(year, month) {
    /**
     * @param year Int
     * @param month Int 必须是 1-12
     * */
    year = parseInt(year);
    month = parseInt(month);

    var DAYARR = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31],
        totalDays = DAYARR[--month], // month 需要减1
        day = 1,
        week = 0,
        line = 0,
        innerHTML = "",
        $wrap = document.getElementById("gw--datetimepicker-day-body"),
        firstDateWeek = new Date(Date.UTC(year, month)).getDay()-1;

    if (firstDateWeek < 0) {
      firstDateWeek = 6;
    }

    // Liigaasta parandused
    if (month === 1 && ((year % 4 == 0 && year % 100 != 0) || year % 400 == 0)) {
      totalDays++;
    }

    // Kalendrisysteemide erinevused
    if (calendarSystem != 'on') {
      // Kalendrimuudatuse parandused
      if (year < 1918 || (year === 1918 && month === 0)) {
        --firstDateWeek;
        if (firstDateWeek < 0) {
          firstDateWeek = 6;
        }
      }
      if (month === 1 && year === 1918) {
        day = 14;
        firstDateWeek = 3;
      }
      // Parandus, sest 1900 ebareeglipäraselt liigaasta
      if (month === 1 && year === 1900) {
        totalDays++;
      }
      if (year < 1900 || (year === 1900 && month < 2)) {
        --firstDateWeek;
        if (firstDateWeek < 0) {
          firstDateWeek = 6;
        }
      }
    }

    var daysNotThisMonth = DAYARR[(month + 11) % 12] - firstDateWeek;

    // Nädalad
    while (week < 7) {
      if (week == 0) {
        innerHTML += '<tr>';
      }

      if (line == 0) {
        //
        while (week++ < firstDateWeek) {
          innerHTML += '<td class="prev gw--day">' + (daysNotThisMonth + week) + '</td>';
        }

        week = firstDateWeek;

        while (week++ < 7) {
          dayThisMonthId = 'gw--day-this-month-id_' + day;
          dayTitle = 'title="' + 'Mis juhtus ' + day + '. ' + KUUL[month] + '?' + '"';
          dayHref = '<a href="' + kroonikaUrl  + year + '/' + (month+1) + '/' + day + '/"'+ dayTitle + '>' + day++ + '</a>';
          innerHTML += '<td class="selected gw--day" id="' +  dayThisMonthId + '">' + dayHref + '</td>';
        }

        daysNotThisMonth = 1;
        if (calendarSystem != 'on') { // Juhul kui vana kalendri järgi, siis üleminek 31.01 -> 14.02
          if (month === 0 && year === 1918) {
            daysNotThisMonth = 14;
          };
        };

        week = 0;
        line++;
        continue;
      } else {
        if (day <= totalDays) {
          if (calendarSystem == 'on' && (new Date(year, month, day ) < new Date(1918, 1, 14))) {
            calendarSystemClass = ' text-ukj';
          } else {
            calendarSystemClass = '';
          }
          dayThisMonthId = 'gw--day-this-month-id_' + day;
          dayTitle = 'title="' + 'Mis juhtus ' + day + '. ' + KUUL[month] + '?' + '"';
          dayHref = '<a href="' + kroonikaUrl  + year + '/' + (month+1) + '/' + day + '/"'+ dayTitle + '>' + day++ + '</a>';
          innerHTML += '<td class="selected gw--day' + calendarSystemClass + '" id="' +  dayThisMonthId + '">' + dayHref + '</td>';
        } else {
          innerHTML += '<td class="next gw--day">' + daysNotThisMonth++ + '</td>';
        }
      }

      if (week == 6) {
        innerHTML += '</tr>';
        line++;
      }

      line < 6 && week == 6 ? week = 0 : week++;
    }

    $wrap.innerHTML = innerHTML;
    getCalendar(year, month+1);

  },
  setNav: function($con, isPrev) {
    var year = parseInt($con.selectedYear.innerHTML),
      month = parseInt(monthNames.indexOf($con.selectedMonth.innerHTML));

    switch ($con.body.getAttribute("data-selected")) {
      case "year":
        var yearView = parseInt($con.selectedYear.getAttribute("data-value"));

        if (isPrev === true) {
          yearView ? yearView -= 12 : yearView = year - 12;
        } else {
          yearView ? yearView += 12 : yearView = year + 12;
        }

        $con.selectedYear.setAttribute("data-value", yearView.toString());
        GWDateTimePicker.setYears(yearView);
        break;
      case "day":
        isPrev ? month-- : month++;

        if (isPrev === true && month < 1) {
          $con.selectedYear.innerHTML = --year;
          month = 12;
          $con.selectedMonth.innerHTML = monthNames[12];
        } else if (isPrev !== true && month > 12) {
          $con.selectedYear.innerHTML = ++year;
          month = 1;
          $con.selectedMonth.innerHTML = monthNames[1];
        } else {
          $con.selectedMonth.innerHTML = monthNames[month];
        }

        GWDateTimePicker.setDays(year, month);
        break;
    }
  },
  setOutput: function($target, year, month, day) {
    // $target.value = year + "年 " + month + "月 " + day + "日";
  },
  showYears: function($con) {
    $con.year.style.display = "block";
    $con.month.style.display = "none";
    $con.day.style.display = "none";
    $con.body.setAttribute("data-selected", "year");
  },
  showMonths: function($con) {
    $con.year.style.display = "none";
    $con.month.style.display = "block";
    $con.day.style.display = "none";
    $con.body.setAttribute("data-selected", "month");
  },
  showDays: function($con) {
    $con.year.style.display = "none";
    $con.month.style.display = "none";
    $con.day.style.display = "block";
    $con.body.setAttribute("data-selected", "day");
  }
};

