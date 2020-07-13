//// Chrome veateadete vaigistamiseks https://developer.mozilla.org/en-US/docs/Web/API/EventTarget/addEventListener
//const eventListenerOptionsSupported = () => {
//  let supported = false;
//
//  try {
//    const opts = Object.defineProperty({}, 'passive', {
//      get() {
//        supported = true;
//      }
//    });
//
//    window.addEventListener('test', null, opts);
//    window.removeEventListener('test', null, opts);
//  } catch (e) {}
//
//  return supported;
//}
//
//const defaultOptions = {
//  passive: false,
//  capture: false
//};
//const supportedPassiveTypes = [
//  'scroll', 'wheel',
//  'touchstart', 'touchmove', 'touchenter', 'touchend', 'touchleave',
//  'mouseout', 'mouseleave', 'mouseup', 'mousedown', 'mousemove', 'mouseenter', 'mousewheel', 'mouseover'
//];
//const getDefaultPassiveOption = (passive, eventName) => {
//  if (passive !== undefined) return passive;
//
//  return supportedPassiveTypes.indexOf(eventName) === -1 ? false : defaultOptions.passive;
//};
//
//const getWritableOptions = (options) => {
//  const passiveDescriptor = Object.getOwnPropertyDescriptor(options, 'passive');
//
//  return passiveDescriptor && passiveDescriptor.writable !== true && passiveDescriptor.set === undefined
//    ? Object.assign({}, options)
//    : options;
//};
//
//const overwriteAddEvent = (superMethod) => {
//  EventTarget.prototype.addEventListener = function (type, listener, options) {
//    const usesListenerOptions = typeof options === 'object' && options !== null;
//    const useCapture          = usesListenerOptions ? options.capture : options;
//
//    options         = usesListenerOptions ? getWritableOptions(options) : {};
//    options.passive = getDefaultPassiveOption(options.passive, type);
//    options.capture = useCapture === undefined ? defaultOptions.capture : useCapture;
//
//    superMethod.call(this, type, listener, options);
//  };
//
//  EventTarget.prototype.addEventListener._original = superMethod;
//};
//
//const supportsPassive = eventListenerOptionsSupported();
//
//if (supportsPassive) {
//  const addEvent = EventTarget.prototype.addEventListener;
//  overwriteAddEvent(addEvent);
//}


// Vasakule või paremale libistamisel vahetame ennustuse andmeid
$(function(){
  // Bind the swipeleftHandler callback function to the swipe event on document
  document.addEventListener('swiped-left', swipeHandler);
  document.addEventListener('swiped-right', swipeHandler);

  // Callback function references the event target and adds the 'swipeleft' class to it
  function swipeHandler( event ){
    if(event.handled !== true) // This will prevent event triggering more then once
    {
        $( "#forecast-hours" ).toggleClass( "w3-hide" );
        $( "#forecast-days" ).toggleClass( "w3-hide" );
        event.handled = true;
    }
    return false;
  };

//  // Bind the swipeleftHandler callback function to the swipe event on div.box
//  // $( document ).on( "swiperight", swiperightHandler );
//  document.addEventListener('swiped-right', swiperightHandler);
//
//  // Callback function references the event target and adds the 'swipeleft' class to it
//  function swiperightHandler( event ){
//    if(event.handled !== true) // This will prevent event triggering more then once
//    {
//        // $.mobile.changePage("#article1");
//        $( "#forecast-hours" ).toggleClass( "w3-hide" );
//        $( "#forecast-days" ).toggleClass( "w3-hide" );
//        event.handled = true;
//    }
//    // console.log(event);
//    return false;
//  }
});