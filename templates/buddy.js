var Buddy = (function () {
  'use strict';
  var POSES = ['idle', 'raise', 'squat', 'jump', 'lean', 'cheer', 'oops'];
  var ink = '#13202F';
  var rim = 'rgba(255,255,255,.55)';
  function oval(c, x, y, rx, ry, fill, edge) {
    c.beginPath();
    c.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2);
    c.fillStyle = fill;
    c.fill();
    if (edge) { c.strokeStyle = edge; c.stroke(); }
  }
  function line(c, points, color, width) {
    c.beginPath();
    c.moveTo(points[0], points[1]);
    for (var i = 2; i < points.length; i += 2) c.lineTo(points[i], points[i + 1]);
    c.strokeStyle = color;
    c.lineWidth = width;
    c.stroke();
  }
  function body(c) {
    c.beginPath();
    c.moveTo(-29, -48);
    c.bezierCurveTo(-29, -73, -15, -87, 1, -87);
    c.bezierCurveTo(21, -87, 30, -69, 29, -51);
    c.bezierCurveTo(39, -24, 23, -9, 1, -10);
    c.bezierCurveTo(-24, -8, -39, -23, -29, -48);
    c.closePath();
  }
  /* 발바닥 중앙이 원점인 높이 100의 설계 좌표. 모든 변형은 호출 안에서 복원한다. */
  function draw(ctx, o) {
    o = o || {};
    var size = Number(o.size);
    if (!(size > 0) || !isFinite(size)) return;
    var pose = POSES.indexOf(o.pose) >= 0 ? o.pose : 'idle';
    var t = typeof o.t === 'number' && isFinite(o.t) ? o.t : 0;
    var color = o.color || '#D1F58E';
    var mood = o.mood || (pose === 'oops' ? 'sad' : pose === 'idle' || pose === 'lean' || pose === 'squat' ? 'calm' : 'happy');
    var breath = Math.sin(t / 650) * .012;
    var blink = t > 0 && t % 3900 > 3750;
    var crouch = pose === 'squat';
    var airborne = pose === 'jump';
    var angle = pose === 'lean' ? Math.max(-1, Math.min(1, Number(o.lean) || 0)) * .32 : pose === 'oops' ? Math.sin(t / 180) * .045 : 0;
    ctx.save();
    try {
      ctx.translate(Number(o.x) || 0, Number(o.y) || 0);
      ctx.scale(size / 100, size / 100);
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.translate(0, airborne ? -10 - (1 + Math.sin(t / 240)) * 2 : 0);
      ctx.rotate(angle);
      ctx.scale(crouch ? 1.12 : 1 - breath / 2, crouch ? .73 : 1 + breath);
      ctx.lineWidth = 2.2;
      oval(ctx, -15, -6, 9, 5, color, rim);
      oval(ctx, 15, -6, 9, 5, color, rim);
      /* 팔은 몸 뒤에서 연결하고 둥근 끝을 사용한다. */
      var lifted = pose === 'raise' || pose === 'cheer' || airborne;
      [-1, 1].forEach(function (side) {
        var endY = lifted ? (pose === 'raise' ? -80 : -68) : crouch ? -22 : -30;
        line(ctx, [side * 25, -48, side * 39, endY], rim, 13);
        line(ctx, [side * 25, -48, side * 39, endY], color, 9);
      });
      body(ctx);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.save();
      try {
        ctx.clip();
        oval(ctx, 0, -10, 38, 12, 'rgba(0,0,0,.18)');
      } finally { ctx.restore(); }
      body(ctx);
      ctx.strokeStyle = rim;
      ctx.lineWidth = 2.2;
      ctx.stroke();
      /* 짧은 새싹 한 개와 잎 한 장. */
      line(ctx, [0, -87, 0, -95], '#D1F58E', 2.8);
      ctx.beginPath();
      ctx.moveTo(0, -94);
      ctx.bezierCurveTo(2, -100, 10, -99, 11, -97);
      ctx.bezierCurveTo(9, -91, 3, -91, 0, -94);
      ctx.fillStyle = '#D1F58E';
      ctx.fill();
      oval(ctx, -19, -49, 5, 3, '#FF8A7A');
      oval(ctx, 19, -49, 5, 3, '#FF8A7A');
      [-1, 1].forEach(function (side) {
        var x = side * 11;
        if (pose === 'oops') {
          line(ctx, [x - 3, -63, x + 3, -57], ink, 2.8);
          line(ctx, [x + 3, -63, x - 3, -57], ink, 2.8);
        } else if (blink || pose === 'cheer') {
          ctx.beginPath();
          ctx.moveTo(x - 4, -58);
          ctx.quadraticCurveTo(x, blink ? -58 : -65, x + 4, -58);
          ctx.strokeStyle = ink;
          ctx.lineWidth = 2.8;
          ctx.stroke();
        } else oval(ctx, x, -60, 3.8, 5, ink);
      });
      ctx.beginPath();
      ctx.moveTo(-4, -48);
      ctx.quadraticCurveTo(0, mood === 'sad' ? -53 : -42, 4, -48);
      if (mood === 'happy') {
        ctx.quadraticCurveTo(0, -36, -4, -48);
        ctx.fillStyle = ink;
        ctx.fill();
        oval(ctx, 0, -43, 2.3, 1.4, '#FF8A7A');
      } else {
        ctx.strokeStyle = ink;
        ctx.lineWidth = 2.3;
        ctx.stroke();
      }
      if (o.label !== undefined && o.label !== null && String(o.label)) {
        oval(ctx, 0, -27, 11, 10, 'rgba(255,255,255,.75)');
        ctx.fillStyle = ink;
        ctx.font = "bold 11px 'Malgun Gothic','Apple SD Gothic Neo',sans-serif";
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(Array.from(String(o.label)).slice(0, 3).join(''), 0, -26, 19);
      }
      if (crouch || airborne) {
        ctx.lineWidth = 2.2;
        oval(ctx, -17, -12, 8, 7, color, rim);
        oval(ctx, 17, -12, 8, 7, color, rim);
      }
      if (pose === 'cheer') {
        [-1, 1].forEach(function (s) {
          line(ctx, [s * 35, -87, s * 40, -92], '#FFD66B', 3);
          line(ctx, [s * 43, -77, s * 48, -79], '#FFD66B', 3);
        });
      }
      if (pose === 'oops') {
        ctx.beginPath();
        for (var j = 0; j <= 24; j++) {
          var a = j * .39;
          var r = 1 + j * .17;
          var px = 38 + Math.cos(a) * r;
          var py = -83 + Math.sin(a) * r;
          if (!j) ctx.moveTo(px, py); else ctx.lineTo(px, py);
        }
        ctx.strokeStyle = '#F4F8FF';
        ctx.lineWidth = 1.8;
        ctx.stroke();
      }
    } finally { ctx.restore(); }
  }
  return { draw: draw, POSES: POSES.slice() };
})();
