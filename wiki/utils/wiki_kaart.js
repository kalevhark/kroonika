// wiki.kaart rakenduse jaoks
// kasutatakse utils.shp_util.py poolt open(jsf) kaudu

function showKaartAasta(map) {
  const href = map._container.baseURI;
  const url = new URL(href);
  var r = /\/kaart\/(\d+)\//;
  var kaartAasta = url.pathname.match(r)[1];
  if (kaartAasta) {
    for (let key in basemaps) {
      if (key === kaartAasta) {
        map.addLayer(basemaps[key]);
      } else {
        map.removeLayer(basemaps[key]);
      }
    }
  }
}

showKaartAasta(map);
