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

function relocateElementBySelector(elementSelector, destSelector) {
  let element = elementSelector.childNodes[0];
  element.getElementsByClassName('kaart-control-layers')[0].innerText = 'tuvastatud kohad';
  let elementParent = element.parentElement;
  let destElement = destSelector;
  elementParent.removeChild(element);
  const node = document.createTextNode(" ");
  destElement.appendChild(node);
  destElement.appendChild(element);
}

// t6stame kaardikihtide k6rvale kaardiobjektide n2itamise lyliti
function redesignControl() {
  const leafletControlLayersListDiv = document.getElementsByClassName('leaflet-control-layers-list')[0];
  // console.log(leafletControlLayersListDiv);

  const leafletControlLayersBaseDiv = leafletControlLayersListDiv.getElementsByClassName('leaflet-control-layers-base')[0];
  // console.log(leafletControlLayersBaseDiv);

  const leafletControlLayersOverlaysDiv = leafletControlLayersListDiv.getElementsByClassName('leaflet-control-layers-overlays')[0];
  // console.log(leafletControlLayersOverlaysDiv);

  const leafletControlLayersSeparatorDiv = leafletControlLayersListDiv.getElementsByClassName('leaflet-control-layers-separator')[0];
  // console.log(leafletControlLayersSeparatorDiv);

  const allLeafletControlLayersBaseLabels = leafletControlLayersBaseDiv.getElementsByTagName('label');
  for (let i = 0; i < allLeafletControlLayersBaseLabels.length; i++) {
    // console.log(allLeafletControlLayersBaseLabels[i].textContent);
    var allLeafletControlLayersOverlaysLabels = leafletControlLayersOverlaysDiv.getElementsByTagName('label');
    for (let j = 0; j < allLeafletControlLayersOverlaysLabels.length; j++) {
      // console.log(allLeafletControlLayersOverlaysLabels[j].textContent);
      if ( allLeafletControlLayersOverlaysLabels[j].textContent.includes(allLeafletControlLayersBaseLabels[i].textContent) ) {
        // console.log(allLeafletControlLayersOverlaysLabels[j].textContent);
        relocateElementBySelector(allLeafletControlLayersOverlaysLabels[j], allLeafletControlLayersBaseLabels[i]);
      }
    }
  }
}

showKaartAasta(map);
redesignControl()

// map.on('baselayerchange', function (eventLayer) {
  // console.log(eventLayer);
// });
