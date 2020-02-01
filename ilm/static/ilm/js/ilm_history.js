function myResetFunction() {
  document.getElementById("frm1").reset();
}

function container_history_andmed() {
  var text = "";
  // Küsime andmed ilmaajaloo parameetrite kohta
  $.ajax({
    url: $("#container_history_andmed").attr("data-url"),
    dataType: 'json',
    success: function (data) {
	  console.log(data)
	  text = data.parameetrid;
    },
    error: function (XMLHttpRequest, textstatus, errorThrown) {
	  alert(textstatus);
    },
	complete: function () {
	  document.getElementById("container_history_andmed").innerHTML = text;
	}
  });
}

function container_history_aasta() {
  // Küsime andmed ja moodustame graafiku
  $.ajax({
    url: $("#container_history_aasta").attr("data-url"),
    dataType: 'json',
    timeout: 300000,
	beforeSend: function() {
      $("#loaderDiv1").show();
    },
    success: function (data) {
	  if (data.tyhi) {
	    document.getElementById("container_history_aasta").innerHTML = data.aasta + " kohta andmeid pole!";

	  } else {
	    var chart = Highcharts.chart("container_history_aasta", data);
	  }
    },
    error: function (XMLHttpRequest, textstatus, errorThrown) {
	  alert(textstatus);
    },
	complete: function () {
	  $("#loaderDiv1").hide();
	}
  });
}

function container_history_kuud() {
  // Küsime andmed ja moodustame graafiku
  $.ajax({
    url: $("#container_history_kuud").attr("data-url"),
    dataType: 'json',
    timeout: 300000,
    beforeSend: function() {
      $("#loaderDiv2").show();
    },
	success: function (data) {
	  if (data.tyhi) {
	    document.getElementById("container_history_kuud").innerHTML = data.aasta + " kohta andmeid pole!";

	  } else {
	    var chart = Highcharts.chart("container_history_kuud", data);
	  }
    },
    error: function (XMLHttpRequest, textstatus, errorThrown) {
	  alert(textstatus);
    },
	complete: function () {
	  $("#loaderDiv2").hide();
	}
  });
}

function container_history_kuu() {
  // Küsime andmed ja moodustame graafiku
  $.ajax({
    url: $("#container_history_kuu").attr("data-url"),
    dataType: 'json',
    timeout: 300000,
	beforeSend: function() {
      $("#loaderDiv3").show();
    },
    success: function (data) {
	  if (data.tyhi) {
	    document.getElementById("container_history_kuu").innerHTML = getMonth(data.kuu) + " " + data.aasta + " kohta andmeid pole!";

	  } else {
	    var chart = Highcharts.chart("container_history_kuu", data);
	  }
    },
    error: function (XMLHttpRequest, textstatus, errorThrown) {
	  alert(textstatus);
    },
	complete: function () {
	  $("#loaderDiv3").hide();
	}
  });
}

function container_history_p2ev() {
  // Küsime andmed ja moodustame graafiku
  $.ajax({
    url: $("#container_history_p2ev").attr("data-url"),
    dataType: 'json',
    timeout: 300000,
	beforeSend: function() {
      $("#loaderDiv4").show();
    },
    success: function (data) {
	  if (data.tyhi) {
	    if (data.p2ev != undefined) {
		  var text = '<p>' + data.p2ev + ". " + getMonth(data.kuu) + " " + data.aasta + " kohta andmeid pole!</p>"
		} else {var text = ""};
	    document.getElementById("container_history_p2ev").innerHTML = text;

	  } else {
	    var chart = Highcharts.chart("container_history_p2ev", data);
	  }
    },
    error: function (XMLHttpRequest, textstatus, errorThrown) {
	  alert(textstatus);
    },
	complete: function () {
	  $("#loaderDiv4").hide();
	}
  });
}

function container_history_p2evad() {
  // Küsime andmed ja moodustame graafiku
  $.ajax({
    url: $("#container_history_p2evad").attr("data-url"),
    dataType: 'json',
    timeout: 300000,
	beforeSend: function() {
      $("#loaderDiv5").show();
    },
    success: function (data) {
	  if (data.tyhi) {
	    if (data.p2ev != undefined) {
		  var text = '<p>' + data.p2ev + ". " + getMonth(data.kuu) + " " + data.aasta + " kohta andmeid pole!</p>"
		} else {var text = ""};
		document.getElementById("container_history_p2evad").innerHTML = text;
	  } else {
	    var chart = Highcharts.chart("container_history_p2evad", data);
		chart.series[0].update({
			dataLabels: {
				enabled: true,
				formatter: function () {
					var color = (this.y<0?'#48AFE8':'#FF3333');
					var temp = (this.y<0?"":"+") + this.y.toFixed(1) + '°C';
					return '<span style="color:' + color + '">' + temp + '</span>';
				}
			}
		});
	  }
    },
    error: function (XMLHttpRequest, textstatus, errorThrown) {
	  alert(textstatus);
    },
	complete: function () {
	  $("#loaderDiv5").hide();
	}
  });
}

function container_history_aastad() {
  // Küsime andmed ja moodustame graafiku
  $.ajax({
    url: $("#container_history_aastad").attr("data-url"),
    dataType: 'json',
    timeout: 300000,
	beforeSend: function() {
      $("#loaderDiv6").show();
    },
    success: function (data) {
	  if (data.tyhi) {
	    if (data.p2ev != undefined) {
		  var text = data.p2ev + ". " + getMonth(data.kuu) + " " + data.aasta + " kohta andmeid pole!"
		} else {var text = ""};
		document.getElementById("container_history_aastad").innerHTML = text;
	  } else {
	    var chart = Highcharts.chart("container_history_aastad", data);
		chart.series[0].update({
			dataLabels: {
				enabled: true,
				formatter: function () {
					var color = (this.y<0?'#48AFE8':'#FF3333');
					var temp = (this.y<0?"":"+") + this.y.toFixed(1) + '°C';
					return '<span style="color:' + color + '">' + temp + '</span>';
				}
			}
		});
	  }
    },
    error: function (XMLHttpRequest, textstatus, errorThrown) {
	  alert(textstatus);
    },
	complete: function () {
	  $("#loaderDiv6").hide();
	}
  });
}

function container_history_kuud_aastatekaupa() {
  // Küsime andmed ja moodustame graafiku
  $.ajax({
    url: $("#container_history_kuud_aastatekaupa").attr("data-url"),
    dataType: 'json',
    timeout: 300000,
    beforeSend: function() {
      $("#loaderDiv7").show();
    },
	success: function (data) {
	  if (data.tyhi) {
	    document.getElementById("container_history_kuud_aastatekaupa").innerHTML = data.aasta + " kohta andmeid pole!";

	  } else {
	    var chart = Highcharts.chart("container_history_kuud_aastatekaupa", data);
	  }
    },
    error: function (XMLHttpRequest, textstatus, errorThrown) {
	  alert(textstatus);
    },
	complete: function () {
	  $("#loaderDiv7").hide();
	}
  });
}

$(document)
.ajaxStart(function(){
  document.getElementById("loader").style.display = "block";
  $("#submit").prop("disabled", true);
  $("#submit").hide();
  $("#submitLoader").show();
})
.ajaxStop(function(){
  $("#submit").removeAttr('disabled');
  $("#submitLoader").hide();
  $("#submit").show();
  document.getElementById("loader").style.display = "none";
});

$(document).ready(function() {
  $("#submitLoader").hide();
  container_history_andmed();
  container_history_aasta();
  container_history_kuud();
  container_history_kuu();
  container_history_p2ev();
  container_history_p2evad();
  container_history_aastad();
  container_history_kuud_aastatekaupa();
});