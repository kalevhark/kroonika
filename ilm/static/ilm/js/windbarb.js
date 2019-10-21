$(function() {

  var WindBarbArrowHandler = {

    WindArrow: function(speed, direction, container, arrowWidth) {
      'use strict';
      var index = 0,
        i;

      this.speed = speed;
      this.direction = direction;
      this.trigDirection = direction + 90;
      this.scale = arrowWidth / 8;

      this.ten = 0;
      this.five = 0;
      this.fifty = 0;


      // Create the canvas
      $(container).append(
        $(document.createElementNS('http://www.w3.org/2000/svg', 'svg'))
        .attr({
          height: 2 * arrowWidth,
          width: 2 * arrowWidth
        })
      );
      $("svg", container).append(document.createElementNS('http://www.w3.org/2000/svg', 'defs'));
      $("defs", container).append($(document.createElementNS('http://www.w3.org/2000/svg', 'clipPath')).attr('id', 'clip'));
      $("clipPath", container).append($(document.createElementNS('http://www.w3.org/2000/svg', 'rect'))
        .attr({
          height: 2 * arrowWidth,
          width: 2 * arrowWidth
        }));

      // Draw the widget area    
      $("svg", container).append($(document.createElementNS('http://www.w3.org/2000/svg', 'g')).attr('class', 'wind-arrow'));

      this.widget = $("svg", container);

      if (this.speed > 0) {
        // Prepare the path
        this.path = "";
        if (this.speed <= 7) {
          // Draw a single line
          this.longBar();
          index = 1;
        } else {
          this.shortBar();
        }

        // Find the number of lines in function of the speed
        this.five = Math.floor(this.speed / 5);
        if (this.speed % 5 >= 3) {
          this.five += 1;
        }

        // Add triangles (5 * 10)
        this.fifty = Math.floor(this.five / 10);
        this.five -= this.fifty * 10;
        // Add tenLines (5 * 2)
        this.ten = Math.floor(this.five / 2);
        this.five -= this.ten * 2;

        // Draw first the triangles
        for (i = 0; i < this.fifty; i++) {
          this.addFifty(index + 2 * i);
        }
        if (this.fifty > 0) {
          index += 2 * (this.fifty - 0.5);
        }

        // Draw the long segments
        for (i = 0; i < this.ten; i++) {
          this.addTen(index + i);
        }
        index += this.ten;

        // Draw the short segments
        for (i = 0; i < this.five; i++) {
          this.addFive(index + i);
        }

        this.path += "Z";

        // Add to the widget

        this.widget.append(document.createElementNS('http://www.w3.org/2000/svg', 'g'));

        $("g", this.widget).append($(document.createElementNS('http://www.w3.org/2000/svg', 'path')).attr({
          'd': this.path,
          'vector-effect': 'non-scaling-stroke',
          'transform': 'translate(' + arrowWidth + ', ' + arrowWidth + ') scale(' + this.scale + ') rotate(' + this.trigDirection + ' ' + 0 + ' ' + 0 + ')  translate(-8, -2)',
          'class': 'wind-arrow'
        }));
      }

    },

    shortBar: function() {
      // Draw an horizontal short bar.
      'use strict';
      this.path += "M1 2 L8 2 ";
    },

    longBar: function() {
      // Draw an horizontal long bar.
      'use strict';
      this.path += "M0 2 L8 2 ";
    },
    addTen: function(index) {
      // Draw an oblique long segment corresponding to 10 kn.
      'use strict';
      this.path += "M" + index + " 0 L" + (index + 1) + " 2 ";
    },
    addFive: function(index) {
      // Draw an oblique short segment corresponding to 10 kn.
      'use strict';
      this.path += "M" + (index + 0.5) + " 1 L" + (index + 1) + " 2 ";
    },
    addFifty: function(index) {
      // Draw a triangle corresponding to 50 kn.
      'use strict';
      this.path += "M" + index + " 0 L" + (index + 1) + " 2 L" + index + " 2 L" + index + " 0 ";
    },

  };


  WindBarbArrowHandler.WindArrow(30, 45, $("#windBarbArrow"), 40);
  WindBarbArrowHandler.WindArrow(45, 30, $("#windBarbArrow1"), 30);

});