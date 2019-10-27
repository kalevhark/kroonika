// Järgnev käivitub kui leht laetud ja kutsub välja graafiku
var chart,
	obj,
	chartTitle;

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

// Kombineeritud ilmagraafiku joonistamine
function mixed_ilmateade() {
	// Automaatse värskenduse teated
	var msg = '<span style="color:red"> Andmete värskendamine...</span>'
	var errormsg = 'ebaõnnestus.'

	var obj=$('#container_mixed_ilmateade').highcharts();

	if (obj) {
		chartTitle = obj.options.title.text;
		obj.setTitle({ text: chartTitle.replace(msg, '').replace(errormsg, '') + msg });
		};

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
                'http://yr.github.io/weather-symbols/png/100/' +
                data.yrno_symbols[i] + '.png',
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
                'http://yr.github.io/weather-symbols/png/100/' +
                data.yrno_symbols[i] + '.png',
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
        chart.series[3].update({
          dataLabels: {
            formatter: function () {
              if (this.y > 0) {
                return this.y;
              }
            }
          }
        });

        // Näitame prognoositavate sademete hulka ainult kui suurem nullist
        chart.series[4].update({
          dataLabels: {
            formatter: function () {
              if (this.y > 0) {
                return this.y;
              }
            }
          }
        });

        // Automaatne uuendamine akna suuruse muutumisel
        //		$(window).resize(function() {
        //			mixed_ilmateade();
        //		});
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
