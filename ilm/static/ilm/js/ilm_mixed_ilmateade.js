// Järgnev käivitub kui leht laetud ja kutsub välja graafiku
// version 2023.05
var chart,
	obj,
	chartTitle;

function changeIlmStartIconColor(data) {
  elementIlmStartIcon = document.getElementById("ilm_start_icon");
  if (elementIlmStartIcon !== undefined) {
    temperatureNow = data.airtemperatures[data.airtemperatures.length - 1][1];
      if (temperatureNow > 0) {
        elementIlmStartIcon.style.color = '#FF3333';
      } else {
        elementIlmStartIcon.style.color = '#48AFE8';
      }
  }
}

// Kombineeritud ilmagraafiku joonistamine
function mixed_ilmateade() {
	// Automaatse värskenduse teated
	var msg = '<span style="color:red"> Andmete värskendamine...</span>';
	var errormsg = 'ebaõnnestus.';
  var temperatureNow;

	var obj=$('#container_mixed_ilmateade').highcharts();

	if (obj) {
		chartTitle = obj.options.title.text;
		obj.setTitle({ text: chartTitle.replace(msg, '').replace(errormsg, '') + msg });
		}

	// Küsime andmed ja moodustame graafiku
	$.ajax({
	  url: $("#container_mixed_ilmateade").attr("data-url"),
	  dataType: 'json',
	  timeout: 300000,
	  success: function (data)
      {
        document.getElementById("loader").style.display = "none";
        document.getElementById("container_mixed_ilmateade").style.display = "block";
        var chart = Highcharts.chart("container_mixed_ilmateade", data);

        // Täiendame eelneva 24h andmed ilmasümbolitega
        $.each(chart.series[1].data, function (i, point) {
          if (i < 24 && i % 2 === 0 && data.yrno_symbols[i] != null) {
            chart.renderer
              .image(
                'https://cdn.jsdelivr.net/gh/YR/weather-symbols@6.0.2/dist/svg/' +
                data.yrno_symbols[i] + '.svg',
                point.plotX + chart.plotLeft - 8,
                point.plotY + chart.plotTop - 30,
                30,
                30
              )
              .attr({
                zIndex: 5
              })
              .add();
            }
          });

        // Täiendame järgneva 48h andmed ilmasümbolitega
        $.each(chart.series[2].data, function (i, point) {
          if (i > 23 && i % 2 === 0 && data.yrno_symbols[i] != null) {
            chart.renderer
              .image(
                '/static/ilm/img/weathericon/svg/' +
                data.yrno_symbols[i] + '.svg',
                point.plotX + chart.plotLeft - 8,
                point.plotY + chart.plotTop - 30,
                30,
                30
              )
              .attr({
                zIndex: 5
              })
              .add();
            }
        });

        // Näitame mõõdetud sademete hulka ainult kui suurem nullist
        chart.get('andmed_eelnevad24h_precipitations').update({
          dataLabels: {
            formatter: function () {
              if (this.y > 0) {
                return this.y;
              }
            }
          }
        });

        // Näitame prognoositavate sademete hulka ainult kui suurem nullist
        // Liidetakse min ja max näitajad
        chart.get('andmed_j2rgnevad48h_precipitations_max').update({
          dataLabels: {
            formatter: function () {
              if (this.y > 0) {
                if (chart.get('andmed_j2rgnevad48h_precipitations').data[this.x]) {
                  return this.y + chart.get('andmed_j2rgnevad48h_precipitations').data[this.x];
                } else {
                  return this.y;
                }
              }
            }
          }
        });
        // Näitame prognoositavate sademete hulka ainult kui suurem nullist
        chart.get('andmed_j2rgnevad48h_precipitations').update({
          dataLabels: {
            formatter: function () {
              if (this.y > 0) {
                return this.y;
              }
            }
          }
        });

        changeIlmStartIconColor(data);
        // Automaatne uuendamine 5 minuti pärast
        window.setTimeout(mixed_ilmateade, 300000);
      },
	  error: function (XMLHttpRequest, textstatus, errorThrown)
      {
        var obj=$('#container_mixed_ilmateade').highcharts();
        if (obj) {
          chartTitle = obj.options.title.text;
          obj.setTitle({ text: chartTitle.replace(msg, '') + msg + errormsg });
          };
        window.setTimeout(mixed_ilmateade, 600000);
      }
	});
}

$(document).ready(function() {
  mixed_ilmateade();
});

$(window).bind('resize', function(e)
  {
    if (window.RT) clearTimeout(window.RT);
    window.RT = setTimeout(function()
      {
        mixed_ilmateade();
      }, 100);
  }
);
