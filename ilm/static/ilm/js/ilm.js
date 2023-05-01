// Tagastab eestikeelse kuunime
var getMonth = function(idx) {
  var kuud = [
    'jaanuar', 'veebruar', 'märts',
    'aprill', 'mai', 'juuni',
    'juuli', 'august', 'september',
    'oktoober', 'november', 'detsember'
  ];
  return kuud[idx-1];
}

$(document).ready(function() {
  Highcharts.setOptions({
    chart: {
        style: {
            fontFamily: 'Raleway'
        }
    }
   });
});