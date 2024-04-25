// Vasakule või paremale libistamisel vahetame ennustuse andmeid
$(function(){
  // Bind the swipeleftHandler callback function to the swipe event on document
  document.addEventListener('swiped-left', swipeHandler);
  document.addEventListener('swiped-right', swipeHandler);

  // Callback function references the event target and adds the 'swipeleft' class to it
  function swipeHandler( event ){
    if(event.handled !== true) // This will prevent event triggering more then once
    {
        $( "#forecast-ilmateenistus" ).toggleClass( "w3-hide" );
        $( "#forecast-yrno" ).toggleClass( "w3-hide" );
        event.handled = true;
    }
    return false;
  }
});