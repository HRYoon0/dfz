/* 두 틀(카메라·컨트롤러)이 함께 쓰는 도구. 색은 앱 dfz.kit 토큰과 같다. */
var PAL = { bg: '#202B3D', surface: '#30435A', card: 'rgba(255,255,255,.09)', ink: '#F4F8FF', muted: '#CCDCE9', face: '#13202F',
  lime: '#D1F58E', mint: '#A4F0D7', sun: '#FFD66B', coral: '#FF8A7A', sky: '#8CC8FF', violet: '#C7A4FF' };
var FONT = "'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif";
var MIN_TEXT = 0.055;   /* 화면 글자는 놀이판 높이의 5% 이상 (앱 검사 규칙) — 여유를 둔 값 */

function font(weight, px) { return weight + ' ' + Math.round(px) + 'px ' + FONT; }
function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

function shuffle(a) {
  a = a.slice();
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); const t = a[i]; a[i] = a[j]; a[j] = t; }
  return a;
}

function rr(ctx, x, y, w, h, r) {
  r = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

/* 글을 maxW 안에 줄바꿈한다. 띄어쓰기 단위로 자르고, 한 낱말이 넘치면 글자 단위로 자른다 */
function wrap(ctx, text, maxW) {
  const out = [];
  String(text).split('\n').forEach(function (para) {
    let line = '';
    para.split(' ').forEach(function (word) {
      const tryLine = line ? line + ' ' + word : word;
      if (ctx.measureText(tryLine).width <= maxW) { line = tryLine; return; }
      if (line) out.push(line);
      line = '';
      Array.from(word).forEach(function (ch) {
        if (ctx.measureText(line + ch).width > maxW && line) { out.push(line); line = ''; }
        line += ch;
      });
    });
    out.push(line);
  });
  return out;
}

/* 상자(x,y,w,h) 가운데에 글을 맞춰 쓴다. 글자 크기는 big에서 시작해 들어갈 때까지 줄이되 small 밑으로는 안 내린다.
   낱말 하나가 폭을 넘으면(낱말 중간에서 잘릴 상황) 줄을 바꾸기 전에 먼저 글자를 줄인다 */
function textBox(ctx, text, x, y, w, h, big, small, color, weight) {
  let px = big, lines;
  const words = String(text).split(/\s+/);
  for (;;) {
    ctx.font = font(weight || 900, px);
    lines = wrap(ctx, text, w);
    const wordFits = words.every(function (wd) { return ctx.measureText(wd).width <= w; });
    if ((wordFits && lines.length * px * 1.22 <= h) || px <= small) break;
    px = Math.max(small, px * 0.9);
  }
  ctx.fillStyle = color;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  const lh = px * 1.22, top = y + h / 2 - (lines.length - 1) * lh / 2;
  lines.forEach(function (ln, i) { ctx.fillText(ln, x + w / 2, top + i * lh, w); });
}

function nightSky(ctx, W, H) {
  const g = ctx.createRadialGradient(W / 2, H * 0.15, 0, W / 2, H * 0.15, Math.max(W, H));
  g.addColorStop(0, '#34507F'); g.addColorStop(0.55, '#1A2944'); g.addColorStop(1, '#111B2E');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);
}

/* O 고리와 X 표 — 이모지 대신 도형으로 그려 윈도·맥이 같게 보인다 */
function drawO(ctx, x, y, r, color) {
  ctx.strokeStyle = color; ctx.lineWidth = r * 0.34;
  ctx.beginPath(); ctx.arc(x, y, r * 0.8, 0, 6.283); ctx.stroke();
}
function drawX(ctx, x, y, r, color) {
  const d = r * 0.72;
  ctx.strokeStyle = color; ctx.lineWidth = r * 0.34; ctx.lineCap = 'round';
  ctx.beginPath(); ctx.moveTo(x - d, y - d); ctx.lineTo(x + d, y + d); ctx.moveTo(x + d, y - d); ctx.lineTo(x - d, y + d); ctx.stroke();
}
/* 판 크기 맞추기 + 매 장면 그리기. dfz.ui.canvas()는 resize 때만 맞추므로 처음 0 크기를 매번 확인한다 */
function runLoop(canvas, step) {
  let last = 0;
  function frame(t) {
    const r = canvas.parentNode.getBoundingClientRect();
    const w = Math.max(1, Math.round(r.width)), h = Math.max(1, Math.round(r.height));
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
    const dt = last ? Math.min(0.1, (t - last) / 1000) : 0;
    last = t;
    step(dt, t, w, h);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

/* 자리 목록 받기 — 들어온 사람은 만들고, 나간 사람은 지운다 */
function syncPeople(people, list, make) {
  const seen = {};
  list.forEach(function (p) {
    seen[p.seat] = true;
    if (!people[p.seat]) people[p.seat] = make(p);
    people[p.seat].index = p.index;
    people[p.seat].color = p.color || people[p.seat].color;
  });
  Object.keys(people).forEach(function (s) { if (!seen[s]) delete people[s]; });
  return Object.values(people).sort(function (a, b) { return a.index - b.index; });
}
