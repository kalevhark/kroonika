// Thanks to: Lights Plugin by Kit Jenson https://codepen.io/kitjenson/pen/qBKEZGr
// ver=2022.11.05

function showLights(){

  var lights_count = 11,
      wire_color = '#ccc9c2',
      glow_size = 3,
      twinkle = true,
      rotation_max = 35,
      target_elements = document.querySelectorAll('.addLights'),
      colors = ['Blue','red','gold','ForestGreen','DarkViolet','orangered', 'DarkTurquoise'],
      l_width = 100 / lights_count

  target_elements.forEach(function(elm) {
    var elm_loc = elm.getBoundingClientRect(),
        elm_h = Math.floor(elm_loc.height / (elm_loc.width / lights_count));
    // console.log(elm_h)

    // vertical lights
    for(var j=0;j<elm_h;j++) {
      var lj = document.createElement('div');
      lj.className = 'light_box';
      lj.style.width = elm_loc.height / elm_h + 'px';
      lj.style.height = elm_loc.width + 'px';
      lj.style.position = 'absolute';
      lj.style.left = 0;
      lj.style.top = 100 / elm_h * j + '%';
      // l.style.borderTop = '2px solid '+wire_color
      // l.style.borderBottom = '2px solid '+wire_color
      var rott = Math.random() < .5 ? -Math.random()*rotation_max : Math.random()*rotation_max;
      lj.innerHTML = `
        <div class='light' style='--color:${colors[(j+0)%colors.length]}; transform:rotate(${rott}deg);'></div>
        <div class='light' style='--color:${colors[(j+2)%colors.length]}; transform:rotate(${rott}deg);'></div>
      `
      if(twinkle) {
        lj.classList.add('twinkle');
        lj.style.setProperty('--delay', j / 3 - 1 + 's' );
      }
      lj.style.transformOrigin = '0 0';
      var width_px = elm_loc.width/(lights_count);
      lj.style.transform = `translateX(${(lights_count)*(width_px)}px) rotate(90deg)`;
      elm.appendChild(lj);
    }

    // horizontal lights
    for(var i=0;i<lights_count;i++) {
      var li = document.createElement('div');
      li.className = 'light_box';
      li.style.width = l_width + '%';
      li.style.position = 'absolute';
      li.style.left = l_width * i + '%';
      li.style.top = '0';
      li.style.bottom = '0';
      // l.style.borderTop = '2px solid '+wire_color
      // l.style.borderBottom = '2px solid '+wire_color
      var rot = Math.random() < .5 ? -Math.random()*rotation_max : Math.random()*rotation_max;
      li.innerHTML = `
        <div class='light' style='--color:${colors[(i+0)%colors.length]}; transform:rotate(${rot}deg);'></div>
        <div class='light' style='--color:${colors[(i+2)%colors.length]}; transform:rotate(${rot}deg);'></div>
      `;
      if(twinkle) {
        li.classList.add('twinkle');
        li.style.setProperty('--delay', i / 3 - 1 + 's' );
      }
      elm.appendChild(li);
    }
  });

  document.body.innerHTML += `
    <style>
      .twinkle .light::after {
        animation: twinkle 1s linear var(--delay) infinite;
      }
      @keyframes twinkle {
        50% { box-shadow: 0 0 0 transparent; }
      }
      
      .light_box {
        pointer-events: none;
      }
      .light {
        width: 15%;
        max-width: 15px;
        aspect-ratio: 1/1;
        background: ${wire_color};
        position: absolute;
        left: 40%;
        border-radius: 25%;
        --color: gold;
      }
      .light:nth-child(1) {
        top: 99.5%;
        transform-origin: 50% 0%;
      }
      .light:nth-child(2) {
        bottom: 99.5%;
        transform-origin: 50% 100%;
      }
      
      .light::after {
        content: '';
        width: 150%;
        aspect-ratio: 1/2;
        background: 
          radial-gradient(rgba(255,255,255,.5), transparent),
          var(--color);
        font-size: ${glow_size}px;
        box-shadow: 0 0 3em 1em var(--color);
        position: absolute;
        left: -25%;  
      }
      .light:nth-child(1)::after {
        top: 80%;
        border-radius: 100% / 60% 60% 125% 125%;
      }
      .light:nth-child(2)::after {
        bottom: 80%;
        border-radius: 100% / 125% 125% 60% 60%;
      }
      
      .addLights {
        position: relative;
        border: 2px solid ${wire_color};
      }
    </style>
  `;
}