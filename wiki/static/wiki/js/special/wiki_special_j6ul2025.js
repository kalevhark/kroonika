// Thanks to: Christmas Lights by Jason Knott https://codepen.io/jgknott/pen/XNwPby
// ver=2022.11.05

var on = false;

function toggleLights(){
  if(on){
    on = false;
    TweenMax.to('.light',.2, {filter:'', opacity: 0.55})
  }else{
    TweenMax.staggerTo('.light', .5, {filter:'url(\'#glow\')', opacity: 1}, .04)
    on = true;
  }
}
