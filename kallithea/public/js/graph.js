// branch_renderer.js - Rendering of branch DAGs on the client side
//
// Copyright 2010 Marcin Kuzminski <marcin AT python-works DOT com>
// Copyright 2008 Jesper Noehr <jesper AT noehr DOT org>
// Copyright 2008 Dirkjan Ochtman <dirkjan AT ochtman DOT nl>
// Copyright 2006 Alexander Schremmer <alex AT alexanderweb DOT de>
//
// derived from code written by Scott James Remnant <scott@ubuntu.com>
// Copyright 2005 Canonical Ltd.
//
// This software may be used and distributed according to the terms
// of the GNU General Public License, incorporated herein by reference.

var colors = [
	[ 1.0, 0.0, 0.0 ],
	[ 1.0, 1.0, 0.0 ],
	[ 0.0, 1.0, 0.0 ],
	[ 0.0, 1.0, 1.0 ],
	[ 0.0, 0.0, 1.0 ],
	[ 1.0, 0.0, 1.0 ],
	[ 1.0, 1.0, 0.0 ],
	[ 0.0, 0.0, 0.0 ]
];

function BranchRenderer(canvas_id, content_id) {

	this.canvas = document.getElementById(canvas_id);
	var t = document.getElementById(content_id);
	
	if (!document.createElement("canvas").getContext)
		this.canvas = window.G_vmlCanvasManager.initElement(this.canvas);
	if (!this.canvas) { // canvas creation did for some reason fail - fail silently
		this.render = function(data,canvasWidth) {};
		return;
	}
	this.ctx = this.canvas.getContext('2d');
	this.ctx.strokeStyle = 'rgb(0, 0, 0)';
	this.ctx.fillStyle = 'rgb(0, 0, 0)';
	this.cur = [0, 0];
	this.line_width = 2.0;
	this.dot_radius = 3.5;
	this.close_x = 1.5 * this.dot_radius;
	this.close_y = 0.5 * this.dot_radius;

	this.calcColor = function(color, bg, fg) {
		color %= colors.length;
		var red = (colors[color][0] * fg) || bg;
		var green = (colors[color][1] * fg) || bg;
		var blue = (colors[color][2] * fg) || bg;
		red = Math.round(red * 255);
		green = Math.round(green * 255);
		blue = Math.round(blue * 255);
		var s = 'rgb(' + red + ', ' + green + ', ' + blue + ')';
		return s;
	}

	this.setColor = function(color, bg, fg) {
		var s = this.calcColor(color, bg, fg);
		this.ctx.strokeStyle = s;
		this.ctx.fillStyle = s;
	}

	this.render = function(data,canvasWidth) {
		var idx = 1;
		var rela = this.canvas;

		this.canvas.setAttribute('width',canvasWidth);
		this.canvas.setAttribute('height',t.clientHeight);

		var lineCount = 1;
		for (var i=0;i<data.length;i++) {
			var in_l = data[i][1];
			for (var j in in_l) {
				var m = in_l[j][0];
				if (m > lineCount)
					lineCount = m;
			}
		}

		var edge_pad = this.dot_radius + 2;
		var box_size = Math.min(18, Math.floor((canvasWidth - edge_pad*2)/(lineCount)));
		var base_x = canvasWidth - edge_pad;

		for (var i=0; i < data.length; ++i) {

			var row = document.getElementById("chg_"+idx);
			if (row == null)
				continue;
			var	next = document.getElementById("chg_"+(idx+1));
			var extra = 0;
			
			cur = data[i];
			node = cur[0];
			in_l = cur[1];
			closing = cur[2];

			var rowY = row.offsetTop + row.offsetHeight/2 - rela.offsetTop;
			var nextY = (next == null) ? rowY + row.offsetHeight/2 : next.offsetTop + next.offsetHeight/2 - rela.offsetTop;

			for (var j in in_l) {
				line = in_l[j];
				start = line[0];
				end = line[1];
				color = line[2];
				
				x = base_x - box_size * start;

				// figure out if this is a dead-end;
				// we want to fade away this line
				var dead_end = true;
				if (next != null) {
					nextdata = data[i+1];
					next_l = nextdata[1];
					found = false;
					for (var k=0; k < next_l.length; ++k) {
						if (next_l[k][0] == end) {
							dead_end = false;
							break;
						}
					}
					if (nextdata[0][0] == end) // this is a root - not a dead end
						dead_end = false;
				}

				if (dead_end) {
					var gradient = this.ctx.createLinearGradient(x,rowY,x,nextY);
					gradient.addColorStop(0,this.calcColor(color, 0.0, 0.65));
					gradient.addColorStop(1,this.calcColor(color, 1.0, 0.0));
					this.ctx.strokeStyle = gradient;
					this.ctx.fillStyle = gradient;
				}
				// if this is a merge of differently
				// colored line, make it a gradient towards
				// the merged color
				else if (color != node[1] && start == node[0])
				{
					var gradient = this.ctx.createLinearGradient(x,rowY,x,nextY);
					gradient.addColorStop(0,this.calcColor(node[1], 0.0, 0.65));
					gradient.addColorStop(1,this.calcColor(color, 0.0, 0.65));
					this.ctx.strokeStyle = gradient;
					this.ctx.fillStyle = gradient;
				}
				else
				{
					this.setColor(color, 0.0, 0.65);
				}
				
				this.ctx.lineWidth=this.line_width;
				this.ctx.beginPath();
				this.ctx.moveTo(x, rowY);

				if (start == end)
				{
					this.ctx.lineTo(x,nextY+extra,3);
				}
				else
				{
					var x2 = base_x - box_size * end;
					var ymid = (rowY+nextY) / 2;
					this.ctx.bezierCurveTo (x,ymid,x2,ymid,x2,nextY);
				}
				this.ctx.stroke();
			}
			
			column = node[0];
			color = node[1];
			
			x = base_x - box_size * column;
		
			this.setColor(color, 0.25, 0.75);
			if (closing)
			{
				this.ctx.fillRect(x - this.close_x, rowY - this.close_y, 2*this.close_x, 2*this.close_y);
			}
			else
			{
				this.ctx.beginPath();
				this.ctx.arc(x, rowY, this.dot_radius, 0, Math.PI * 2, true);
				this.ctx.fill();
			}

			idx++;
		}
				
	}

}
