# review/conversions.json → review/index.html(날짜별·게임별 변환 기록)과 게임 페이지마다 「변환 기록」 칸을 만든다.
# 사용: python3 -I tools/build_review.py
#   게임 페이지(review/<slug>.html)에는 <!--@HISTORY@--> … <!--@/HISTORY@--> 사이가 다시 쓰인다.
import html, json, pathlib, re
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
REVIEW = ROOT / "review"
DATA = json.loads((REVIEW / "conversions.json").read_text(encoding="utf-8"))
REPO = DATA["repo"]
GH = f"https://github.com/{REPO}"
WEEK = "월화수목금토일"
E = html.escape


def day_label(d):
    import datetime
    y, m, dd = map(int, d.split("-"))
    return f"{y}년 {m}월 {dd}일 ({WEEK[datetime.date(y, m, dd).weekday()]})"


def commit_link(sha):
    return f'<a class="sha" href="{GH}/commit/{E(sha)}">{E(sha[:7])}</a>' if sha else ""


def history_rows(game):
    # 같은 분이면 나중에 적은 기록이 위 — history는 적은 차례로 쌓는다
    rows = [h for _, h in sorted(enumerate(game["history"]), key=lambda x: (x[1]["date"], x[1].get("time", ""), x[0]), reverse=True)]
    return "\n".join(
        f'<li><span class="when">{E(h["date"])} {E(h.get("time", ""))}</span><span>{E(h["text"])}</span>{commit_link(h.get("commit", ""))}</li>'
        for h in rows)


CSS = """
:root{--bg:#202B3D;--surface:#30435A;--line:#46607E;--ink:#F4F8FF;--muted:#CCDCE9;--lime:#D1F58E;
--font:'Pretendard Variable','Pretendard',-apple-system,BlinkMacSystemFont,'Malgun Gothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--font);font-weight:450;line-height:1.65;font-size:16px}
main{max-width:min(1560px,94vw);margin:0 auto;padding:32px 16px 64px}
h1{font-size:clamp(28px,4vw,40px);line-height:1.2;margin:0 0 8px;font-weight:800}
h2{font-size:22px;margin:40px 0 12px;font-weight:750;padding-top:8px;border-top:1px solid var(--line)}
h3{font-size:17px;margin:20px 0 8px;font-weight:700;color:var(--lime)}
a{color:var(--lime)}
.lead{color:var(--muted);max-width:60em;margin:0}
ul.log{list-style:none;margin:0;padding:0;display:grid;gap:6px}
ul.log li{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:4px 14px;align-items:baseline;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:9px 14px}
ul.log .when{color:var(--muted);font-variant-numeric:tabular-nums;font-weight:600;white-space:nowrap}
ul.log .game{font-weight:700}
.sha{font-family:Consolas,Menlo,monospace;font-size:14px}
ul.log .note{color:var(--muted);font-size:14px;white-space:nowrap}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,300px),1fr));gap:12px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:16px;display:grid;gap:6px;align-content:start}
.card h3{margin:0;font-size:19px}
.card dl{margin:0;display:grid;grid-template-columns:auto minmax(0,1fr);gap:2px 10px;font-size:14px}
.card dt{color:var(--muted);font-weight:600}
.card dd{margin:0;overflow-wrap:anywhere}
.empty{color:var(--muted)}
ul.games{gap:10px}
ul.games li{grid-template-columns:11.5em minmax(0,1fr) auto auto;align-items:center;gap:6px 24px;padding:16px 22px 16px 18px;border-left:6px solid var(--line);border-radius:12px}
ul.games li.st-app{border-left-color:var(--lime)}
ul.games li.st-pr{border-left-color:#FFD66B;background:#36475C}
ul.games li:hover{border-color:#6A86A6}
ul.games .stage{font-size:15px;font-weight:750;border-radius:999px;padding:6px 12px;text-align:center;white-space:nowrap;background:var(--bg);border:1.5px solid var(--line);color:var(--muted)}
ul.games .stage.app{background:var(--lime);border-color:var(--lime);color:#13202F}
ul.games .stage.pr{background:#4A4430;border-color:#FFD66B;color:#FFE29A}
ul.games a.game{font-size:20px;font-weight:750;text-decoration:none}
ul.games a.game:hover{text-decoration:underline}
ul.games .sub{display:block;color:var(--muted);font-size:15px;margin-top:2px}
ul.games .gnote{display:block;margin-top:6px;font-size:15px;line-height:1.5;color:#E8EEF6;background:#2B3A4E;border-left:3px solid #FFD66B;border-radius:6px;padding:6px 10px}
ul.games .gnote b{color:#FFE29A}
ul.games .main .req-mark{display:inline-block;margin-top:6px;font-size:14px;border-radius:10px}
ul.games .main .req-mark[hidden]{display:none}
ul.games .links{font-size:15px;font-weight:600;white-space:nowrap;display:flex;gap:6px 14px;flex-wrap:wrap;justify-content:flex-end}
ul.games .links .sep{display:none}
ul.games .req{margin:0;justify-content:flex-end}
ul.games .req-btn{font-size:15px;padding:8px 18px}
ul.games .req-thread{margin-top:4px}
.search{display:flex;gap:10px;align-items:center;margin:20px 0 4px}
.search input{flex:1;font:inherit;font-weight:500;color:var(--ink);background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:10px 14px}
.search input:focus{outline:2px solid var(--lime);outline-offset:1px}
.search .count{color:var(--muted);font-size:14px;white-space:nowrap}
@media (max-width:1180px){ul.games li{grid-template-columns:11.5em minmax(0,1fr)}ul.games .links,ul.games .req{grid-column:2;justify-content:flex-start}}
@media (max-width:640px){ul.log li{grid-template-columns:minmax(0,1fr)}ul.games li{grid-template-columns:minmax(0,1fr)}ul.games .links,ul.games .req{grid-column:1;justify-content:flex-start}ul.games .stage{justify-self:start}}
"""

REQUEST_CSS = """
.req{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-top:6px}
.req-btn{font:inherit;font-weight:700;font-size:14px;background:var(--bg);color:var(--ink);border:1px solid var(--lime);border-radius:999px;padding:5px 14px;cursor:pointer}
.req-btn:hover{background:var(--lime);color:#13202F}
.req-mark{font-size:14px;font-weight:650;color:#13202F;background:#FFD66B;border-radius:999px;padding:3px 12px}
.req-mark.done{background:var(--lime)}
dialog.req-dlg{background:var(--surface);color:var(--ink);border:1px solid var(--line);border-radius:14px;padding:20px;width:min(520px,92vw)}
dialog.req-dlg::backdrop{background:rgba(10,16,26,.6)}
.req-dlg h3{margin:0 0 4px}
.req-dlg label{display:grid;gap:4px;margin-top:12px;font-weight:650;font-size:14px;color:var(--muted)}
.req-dlg input,.req-dlg textarea{font:inherit;font-weight:450;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:8px 10px}
.req-dlg textarea{min-height:130px;resize:vertical}
.req-dlg .row{display:flex;gap:8px;justify-content:flex-end;margin-top:14px;align-items:center}
.req-dlg .row button{font:inherit;font-weight:700;border-radius:10px;padding:8px 16px;cursor:pointer;border:1px solid var(--line);background:var(--bg);color:var(--ink)}
.req-dlg .row button.send{background:var(--lime);color:#13202F;border-color:var(--lime)}
.req-dlg .msg{margin-right:auto;font-size:14px;color:#FFB4A8}
.req-dlg .open-note{margin:10px 0 0;font-size:14px;color:var(--muted)}
.req-thread{grid-column:1/-1;margin:8px 0 0;font-size:14px;font-weight:500}
.req-thread summary{cursor:pointer;color:var(--muted);font-weight:650}
.req-item{margin:8px 0 0;padding:10px 12px;background:var(--bg);border:1px solid var(--line);border-radius:10px}
.req-item .who{font-weight:700}
.req-item .at{color:var(--muted);margin-left:8px}
.req-item .st{margin-left:8px;font-weight:650;color:#13202F;background:var(--lime);border-radius:999px;padding:1px 10px}
.req-item p{margin:4px 0 0;white-space:pre-wrap;overflow-wrap:anywhere}
.req-item .ed{color:var(--muted);margin-left:6px;font-size:13px}
.req-item .own{float:right;display:flex;gap:6px}
.req-item .own button,.req-item .edit-row button{font:inherit;font-size:13px;font-weight:650;border-radius:8px;padding:2px 10px;cursor:pointer;border:1px solid var(--line);background:var(--surface);color:var(--ink)}
.req-item .own button:hover,.req-item .edit-row button:hover{border-color:var(--lime)}
.req-item textarea{display:block;width:100%;box-sizing:border-box;min-height:90px;margin-top:6px;font:inherit;font-weight:450;color:var(--ink);background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:8px 10px}
.req-item .edit-row{display:flex;gap:6px;justify-content:flex-end;align-items:center;margin-top:6px}
.req-item .edit-row .msg{margin-right:auto;color:#FFB4A8;font-size:13px}
.req-pics{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
.req-pics a,.req-pics .pic{position:relative;display:block}
.req-pics img{display:block;max-height:160px;max-width:100%;border-radius:8px;border:1px solid var(--line);background:var(--bg)}
.req-dlg .req-pics img{max-height:90px}
.req-pics .del{position:absolute;top:4px;right:4px;font:inherit;font-weight:700;font-size:13px;line-height:1;border:0;border-radius:999px;padding:5px 8px;background:rgba(10,16,26,.8);color:#fff;cursor:pointer}
.req-dlg .pick{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:12px;font-size:14px;color:var(--muted)}
.req-dlg .pick button{font:inherit;font-weight:700;font-size:14px;border-radius:10px;padding:7px 14px;cursor:pointer;border:1px solid var(--line);background:var(--bg);color:var(--ink)}
.req-reply{margin:8px 0 0 14px;padding:2px 0 2px 12px;border-left:3px solid var(--lime)}
"""

# 수정 요청 — Apps Script 웹앱(tools/review-requests/Code.gs)이 구글 시트 「게임 템플릿 100」의 탭 「수정 요청」에 받는다.
REQUEST_URL = "https://script.google.com/macros/s/AKfycbwRpKn6QXcB_kITjF_YPSyPDp8Dx9tiD84oj90SO8u2FfV6lLIcHy5StBsAhaPeLg-S/exec"
PAGES = "https://hryoon0.github.io/dfz/review/"

REQUEST_JS = """
(function(){
  var URL_ = %s, PAGES = %s;
  // 응답이 없을 때 「보내는 중」이 영원히 돌지 않게 15초에 끊는다
  function fetchJSON(url, opts, ms){ var c = new AbortController(), t = setTimeout(function(){ c.abort(); }, ms || 15000);
    return fetch(url, Object.assign({}, opts, { signal: c.signal })).then(function(r){ return r.json(); }).finally(function(){ clearTimeout(t); }); }
  function mark(slug, g){
    var el = document.querySelector('[data-slug="' + slug + '"] .req-mark'); if (!el || !g || !g.count) return;
    var day = String(g.last || '').slice(0, 10);
    el.textContent = (g.status ? g.status + ' · ' : '수정 요청함 · ') + day + (g.count > 1 ? ' (' + g.count + '건)' : '');
    el.title = '마지막 요청 ' + g.last;
    el.classList.toggle('done', !!g.status); el.hidden = false;
  }
  // 받은 글은 남이 쓴 것이라 textContent로만 넣는다(태그를 적어 보내도 글자로 보인다)
  function el(tag, cls, text){ var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  // 내가 보낸 요청의 고치기 열쇠 — 이 브라우저에만 있다(2026-11-26 「수정하거나 삭제하고 싶은데」)
  function keys(){ try { return JSON.parse(localStorage.getItem('dfz-req-keys') || '{}'); } catch (e) { return {}; } }
  function keep(id, key){ var k = keys(); k[id] = key; localStorage.setItem('dfz-req-keys', JSON.stringify(k)); }
  function post(body, ms){ return fetchJSON(URL_, { method: 'POST', headers: { 'Content-Type': 'text/plain;charset=utf-8' }, body: JSON.stringify(body) }, ms)
    .then(function(r){ if (!r || !r.ok) throw new Error(r && r.error || 'fail'); return r; }); }
  function why(err){ var w = String(err.message);
    return w === 'rate-limit' ? '요청이 몰렸어요. 10분 뒤 다시 해 주세요.' : w === 'bad-key' || w === 'gone' ? '이 요청은 여기서 고칠 수 없어요(이미 지웠거나 다른 브라우저에서 보낸 것).' : '저장하지 못했어요. 다시 해 주세요.'; }
  function own(d, it, p){
    var key = it.id && keys()[it.id]; if (!key) return;
    var bar = el('span', 'own'), eb = el('button', '', '고치기'), db = el('button', '', '지우기'); eb.type = db.type = 'button';
    bar.appendChild(eb); bar.appendChild(db); d.firstChild.prepend(bar);
    eb.addEventListener('click', function(){
      if (d.querySelector('textarea')) return;
      var ta = el('textarea'), row = el('div', 'edit-row'), m = el('span', 'msg'), ok = el('button', '', '저장'), no = el('button', '', '취소');
      ta.value = it.text; ta.maxLength = 1000; ok.type = no.type = 'button'; row.appendChild(m); row.appendChild(no); row.appendChild(ok);
      p.hidden = true; p.after(ta); ta.after(row); ta.focus();
      no.addEventListener('click', function(){ ta.remove(); row.remove(); p.hidden = false; });
      ok.addEventListener('click', function(){ var t = ta.value.trim(); if (t.length < 2) { m.textContent = '고칠 점을 적어 주세요.'; return; }
        ok.disabled = true; ok.textContent = '저장 중…';
        post({ action: 'edit', id: it.id, key: key, text: t }).then(load).catch(function(err){ ok.disabled = false; ok.textContent = '저장'; m.textContent = why(err); }); });
    });
    db.addEventListener('click', function(){
      if (!confirm('이 수정 요청을 지울까요? 페이지에서 사라집니다.')) return;
      db.disabled = true; db.textContent = '지우는 중…';
      post({ action: 'delete', id: it.id, key: key }).then(load).catch(function(err){ db.disabled = false; db.textContent = '지우기'; alert(why(err)); });
    });
  }
  // 요청 글과 답글을 댓글처럼 — 목록에서는 접어 두고, 게임 페이지에서는 펴 둔다
  function thread(slug, g){
    var req = document.querySelector('.req[data-slug="' + slug + '"]'); if (!req || !g || !g.items || !g.items.length) return;
    var box = req.nextElementSibling;
    if (!box || !box.classList.contains('req-thread')) { box = el('details', 'req-thread'); box.open = !req.closest('ul.games'); req.after(box); }
    box.textContent = '';
    box.appendChild(el('summary', '', '수정 요청 ' + g.items.length + '건'));
    g.items.forEach(function(it){
      var d = el('div', 'req-item'), h = el('div');
      h.appendChild(el('span', 'who', it.name)); h.appendChild(el('span', 'at', it.at)); if (it.edited) h.appendChild(el('span', 'ed', '(' + it.edited.slice(5) + ' 고침)'));
      if (it.status) h.appendChild(el('span', 'st', it.status));
      var p = el('p', '', it.text); d.appendChild(h); d.appendChild(p); own(d, it, p);
      if (it.images && it.images.length) { var ps = el('div', 'req-pics');
        it.images.forEach(function(id, i){ if (!/^[A-Za-z0-9_-]+$/.test(id)) return;
          var a = el('a'), im = el('img'); a.href = 'https://drive.google.com/file/d/' + id + '/view'; a.target = '_blank'; a.rel = 'noopener';
          im.src = 'https://drive.google.com/thumbnail?id=' + id + '&sz=w800'; im.alt = it.name + '이 올린 그림 ' + (i + 1); im.loading = 'lazy';
          a.appendChild(im); ps.appendChild(a); });
        d.appendChild(ps); }
      if (it.reply) { var r = el('div', 'req-reply'); r.appendChild(el('span', 'who', '답글')); r.appendChild(el('p', '', it.reply)); d.appendChild(r); }
      box.appendChild(d);
    });
  }
  // 게임별 목록 — 고친 기록과 수정 요청 중 더 늦은 시각이 위로(2026-11-17 회원님 「수정요청 받으면 또 그게 최신」)
  function resort(games){
    var ul = document.querySelector('ul.games'); if (!ul) return;
    var rows = [].slice.call(ul.children);
    rows.forEach(function(li){ var g = games[li.dataset.slug], at = g && String(g.last || '').slice(0, 16);
      if (at && at > (li.dataset.last || '')) li.dataset.last = at; });
    rows.sort(function(a, b){ return (b.dataset.last || '').localeCompare(a.dataset.last || ''); }).forEach(function(li){ ul.appendChild(li); });
  }
  function load(){ fetchJSON(URL_ + '?action=list').then(function(r){ if (r && r.ok) { Object.keys(r.games).forEach(function(k){ mark(k, r.games[k]); thread(k, r.games[k]); }); resort(r.games); } }).catch(function(){}); }
  var dlg = document.getElementById('req-dlg'), form = dlg.querySelector('form'), msg = dlg.querySelector('.msg'), send = dlg.querySelector('.send'), W = form.elements, cur = null;
  // 그림(2026-11-22) — 3장까지, 긴 변 1600px JPEG로 줄여 보낸다(휴대폰 사진 그대로면 수 MB라 느리고 잘 끊긴다)
  var MAX = 3, pics = [], strip = dlg.querySelector('.req-pics'), file = dlg.querySelector('input[type=file]');
  function shrink(f){ return new Promise(function(ok, bad){
    var u = URL.createObjectURL(f), im = new Image();
    im.onload = function(){ var k = Math.min(1, 1600 / Math.max(im.naturalWidth, im.naturalHeight)), c = document.createElement('canvas');
      c.width = Math.round(im.naturalWidth * k); c.height = Math.round(im.naturalHeight * k);
      var x = c.getContext('2d'); x.fillStyle = '#fff'; x.fillRect(0, 0, c.width, c.height); x.drawImage(im, 0, 0, c.width, c.height);
      URL.revokeObjectURL(u); ok(c.toDataURL('image/jpeg', 0.85)); };
    im.onerror = function(){ URL.revokeObjectURL(u); bad(new Error('not-image')); }; im.src = u; }); }
  function drawPics(){ strip.textContent = '';
    pics.forEach(function(d, i){ var w = el('div', 'pic'), im = el('img'), x = el('button', 'del', '×');
      im.src = d; im.alt = '올릴 그림 ' + (i + 1); x.type = 'button'; x.setAttribute('aria-label', '그림 ' + (i + 1) + ' 빼기');
      x.addEventListener('click', function(){ pics.splice(i, 1); drawPics(); }); w.appendChild(im); w.appendChild(x); strip.appendChild(w); });
    dlg.querySelector('.pick-count').textContent = pics.length ? pics.length + ' / ' + MAX + '장' : ''; }
  var pending = 0;
  function addFiles(list){ [].slice.call(list || []).forEach(function(f){
    if (String(f.type).indexOf('image/') !== 0) return;
    if (pics.length + pending >= MAX) { msg.textContent = '그림은 ' + MAX + '장까지예요.'; return; }
    pending++;
    shrink(f).then(function(d){ pics.push(d); }).catch(function(){ msg.textContent = '그림을 읽지 못했어요.'; })
      .finally(function(){ pending--; drawPics(); }); }); }
  dlg.querySelector('.pick button').addEventListener('click', function(){ file.click(); });
  file.addEventListener('change', function(){ addFiles(file.files); file.value = ''; });
  // 화면 캡처를 글 칸에 바로 붙여 넣어도(Ctrl+V) 그림으로 받는다
  W.note.addEventListener('paste', function(e){ var fs = [].slice.call((e.clipboardData || {}).files || []);
    if (fs.length) { e.preventDefault(); addFiles(fs); } });
  document.querySelectorAll('.req-btn').forEach(function(b){ b.addEventListener('click', function(){
    cur = b.closest('.req').dataset; dlg.querySelector('.game').textContent = cur.title; msg.textContent = ''; send.disabled = false; send.textContent = '보내기';
    form.reset(); pics = []; drawPics(); var n = localStorage.getItem('dfz-req-name'); if (n) W.who.value = n; dlg.showModal(); W.note.focus(); }); });
  dlg.querySelector('.cancel').addEventListener('click', function(){ dlg.close(); });
  form.addEventListener('submit', function(e){
    e.preventDefault(); if (!cur) return;
    var text = W.note.value.trim(); if (text.length < 2) { msg.textContent = '고칠 점을 적어 주세요.'; return; }
    if (pending) { msg.textContent = '그림을 준비하는 중이에요. 잠시 뒤 보내 주세요.'; return; }
    send.disabled = true; send.textContent = '보내는 중…'; msg.textContent = '';
    localStorage.setItem('dfz-req-name', W.who.value.trim());
    // text/plain — 브라우저가 사전 요청(OPTIONS)을 보내지 않게(Apps Script는 그것을 받지 못한다)
    if (pics.length) send.textContent = '그림 올리는 중…';
    var images = pics.map(function(d){ return { type: 'image/jpeg', data: d.split(',')[1] }; });
    post({ slug: cur.slug, title: cur.title, page: PAGES + cur.page, name: W.who.value.trim(), text: text, images: images },
      images.length ? 60000 : 15000)
      .then(function(r){
        if (r.id && r.key) keep(r.id, r.key);
        dlg.close(); load();
        mark(cur.slug, { count: 1, last: r.at, status: '' });
      })
      .catch(function(err){ send.disabled = false; send.textContent = '다시 보내기';
        var why = String(err.message);
        msg.textContent = why === 'rate-limit' ? '요청이 몰렸어요. 10분 뒤 다시 보내 주세요.'
          : /image/.test(why) ? '그림을 올리지 못했어요. 그림을 빼고 보내 보세요.' : '보내지 못했어요. 다시 보내 주세요.'; });
  });
  load();
})();
""" % (json.dumps(REQUEST_URL), json.dumps(PAGES))

REQUEST_DIALOG = """<dialog class="req-dlg" id="req-dlg" aria-labelledby="req-h">
<form method="dialog">
<h3 id="req-h">수정 요청</h3>
<div class="game" style="font-weight:700"></div>
<label>요청한 사람(선택)<input name="who" maxlength="40" autocomplete="name"></label>
<label>고칠 점<textarea name="note" maxlength="1000" required placeholder="무엇을 어떻게 고치면 좋을지 적어 주세요 (화면 캡처는 여기에 붙여 넣어도 돼요)"></textarea></label>
<div class="pick"><button type="button">그림 넣기</button><span>3장까지 · 글 칸에 Ctrl+V로 붙여 넣기</span><span class="pick-count"></span><input type="file" accept="image/*" multiple hidden></div>
<div class="req-pics"></div>
<p class="open-note">보낸 글·이름·그림은 이 페이지에 그대로 보입니다. 학생 얼굴이 나온 사진은 올리지 마세요. 보낸 뒤에는 같은 브라우저에서 「고치기」·「지우기」를 할 수 있습니다.</p>
<div class="row"><span class="msg" role="status"></span><button type="button" class="cancel">취소</button><button type="submit" class="send">보내기</button></div>
</form>
</dialog>"""


def stage_of(g):
    """상태 글을 한 낱말로 — 목록 줄 앞 표시. 자세한 글은 마우스를 올리면 보인다."""
    # 앱에 들어간 게임이라도 수정 PR이 검토 중이면 그쪽을 앞에 — 고친 판은 아직 앱에 없다(2026-11-15 G015)
    for n in g.get("fixes", []):
        if re.search(rf"#{n}\b[^·]*검토 중", g["status"]):
            return f"수정 PR #{n} 검토 중", "pr"
    if "앱에 들어" in g["status"]:
        return "앱 포함", "app"
    if g.get("pr"):
        return f"PR #{g['pr']} 검토 중", "pr"
    return "브랜치", ""


# PR 상태 — 페이지를 열 때마다 웹앱(?action=prs)이 GitHub에서 읽은 단계로 줄 앞 표시를 바꾼다(2026-11-15 회원님
# 「페이지가 새로고침 될 때 확인되도록」). 웹앱은 5분 캐시. 답이 없으면(토큰 없음·오류) conversions.json 상태 글 그대로.
PRS_JS = """
(function(){
  var URL_ = %s, GH = %s, c = new AbortController(), t = setTimeout(function(){ c.abort(); }, 15000);
  fetch(URL_ + '?action=prs', { signal: c.signal }).then(function(r){ return r.json(); }).then(function(r){
    if (!r || !r.ok) return;
    Object.keys(r.games).forEach(function(slug){
      var g = r.games[slug], li = document.querySelector('ul.games li[data-slug="' + slug + '"]'); if (!li) return;
      var st = li.querySelector('.stage'), L = { app: ['앱 포함', 'app'], merged: ['병합 · 앱 연결 전', 'pr'],
        open: ['PR #' + g.pr + ' 검토 중', 'pr'], closed: ['PR #' + g.pr + ' 닫힘', ''] }[g.stage];
      var fo = (g.fixes || []).filter(function(f){ return f.state === 'open'; })[0];
      if (fo) L = ['수정 PR #' + fo.n + ' 검토 중', 'pr'];
      if (L) { st.textContent = L[0]; st.className = 'stage ' + L[1]; li.className = 'st-' + L[1]; st.title += ' — GitHub에서 ' + r.at + ' 확인'; }
      (g.fixes || []).forEach(function(f){
        var a = li.querySelector('a[data-fix="' + f.n + '"]');
        if (a) a.textContent = '수정 PR #' + f.n + ({ open: ' 검토 중', merged: ' 병합', closed: ' 닫힘' }[f.state] || '');
      });
    });
  }).catch(function(){}).finally(function(){ clearTimeout(t); });
})();
""" % (json.dumps(REQUEST_URL), json.dumps(GH))


SEARCH_JS = """
(function(){
  var q = document.getElementById('q'), count = document.getElementById('q-count'), empty = document.getElementById('q-empty');
  var games = [].slice.call(document.querySelectorAll('ul.games li'));
  function run(){
    var words = q.value.toLowerCase().split(/\\s+/).filter(Boolean), shown = {}, n = 0;
    games.forEach(function(li){ var ok = words.every(function(w){ return li.dataset.q.indexOf(w) >= 0; }); li.hidden = !ok; if (ok) { shown[li.dataset.slug] = 1; n++; } });
    document.querySelectorAll('section.day').forEach(function(sec){
      var any = false; sec.querySelectorAll('li').forEach(function(li){ var ok = !!shown[li.dataset.slug]; li.hidden = !ok; any = any || ok; }); sec.hidden = !any; });
    count.textContent = words.length ? n + '개' : ''; empty.hidden = n > 0;
  }
  q.addEventListener('input', run);
})();
"""


def build_index():
    # 날짜별에는 그날 손댄 게임만 한 줄씩 — 세세한 고친 기록은 게임 페이지의 「변환 기록」에 있다
    by_day = defaultdict(dict)
    for g in DATA["games"]:
        first = min(h["date"] for h in g["history"])
        for h in g["history"]:
            day = by_day[h["date"]].setdefault(g["slug"], {"game": g, "count": 0, "last": "", "new": h["date"] == first})
            day["count"] += 1
            day["last"] = max(day["last"], h.get("time", ""))

    days = []
    for d in sorted(by_day, reverse=True):
        items = sorted(by_day[d].values(), key=lambda x: x["last"], reverse=True)
        lis = "\n".join(
            f'<li data-slug="{E(x["game"]["slug"])}"><span class="when">{"새 변환" if x["new"] else "업데이트"}</span>'
            f'<span><a class="game" href="{E(x["game"]["page"])}">{E(x["game"]["title"])}</a></span>'
            f'<span class="note">{x["count"]}건 · 마지막 {E(x["last"])}</span></li>'
            for x in items)
        days.append(f'<section class="day"><h3>{day_label(d)}</h3>\n<ul class="log">\n{lis}\n</ul></section>')

    rows = []
    def latest(g):
        return max(h["date"] + " " + h.get("time", "00:00") for h in g["history"])

    for g in sorted(DATA["games"], key=latest, reverse=True):
        last = max(h["date"] for h in g["history"])
        label, cls = stage_of(g)
        pr = f'<a href="{GH}/pull/{g["pr"]}">PR #{g["pr"]}</a><span class="sep"> · </span>' if g.get("pr") else ""
        pr = "".join(f'<a data-fix="{n}" href="{GH}/pull/{n}">수정 PR #{n}</a><span class="sep"> · </span>' for n in g.get("fixes", [])) + pr
        q = " ".join([g["title"], g["slug"], g.get("author", ""), g["source"], g["result"], g.get("note", ""), label]).lower()
        rows.append(
            f'<li class="st-{cls}" data-slug="{E(g["slug"])}" data-last="{E(latest(g))}" data-q="{E(q)}"><span class="stage {cls}" title="{E(g["status"])}">{E(label)}</span>'
            f'<span class="main"><a class="game" href="{E(g["page"])}">{E(g["title"])}</a>'
            f'<span class="sub">만든 사람 {E(g["author"]) or "미기재"} · 마지막 {last} · 고친 {len(g["history"])}건</span>'
            + (f'<span class="gnote">{E(g["note"])}</span>' if g.get("note") else "")
            + f'<span class="req-mark" hidden></span></span>'
            f'<span class="links">{pr}<a href="{GH}/tree/{E(g["branch"])}">브랜치</a></span>'
            f'<div class="req" data-slug="{E(g["slug"])}" data-title="{E(g["title"])}" data-page="{E(g["page"])}"><button type="button" class="req-btn">수정 요청</button></div></li>')

    page = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>디지털 핏 존 변환 기록</title>
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<style>{CSS}{REQUEST_CSS}</style>
</head>
<body>
<main>
<h1>디지털 핏 존 변환 기록</h1>
<p class="lead">여러 사람이 만든 게임을 <a href="{GH}">{E(REPO)}</a>의 C# 형식(판정 → 감독 → 무대)으로 옮긴 기록입니다. 게임마다 작업 브랜치(<code>claude/…</code>)를 기준 브랜치 <code>{E(DATA['base'])}</code>에서 만들고, <code>{E(DATA['base'])}</code> 대상 PR로 올려 주개발자가 검토·병합합니다(2026-11-06부터 — 그전 기준은 <code>feature/stage-1-4a</code>). 날짜별에는 그날 변환하거나 고친 게임만 나옵니다. 게임 이름을 누르면 그 게임의 확인 페이지(고친 기록, 달라진 것, 파일, 검증, 앱에 붙이는 길, 체험판)가 열립니다. 고칠 점이 있으면 게임 줄의 「수정 요청」을 눌러 보내 주세요 — 요청과 답글은 그 게임 줄 아래 「수정 요청 ○건」을 누르면 댓글처럼 보입니다. 저장소 링크는 권한이 있는 사람에게만 열립니다.</p>
<div class="search"><input type="search" id="q" placeholder="게임 찾기 — 이름, 번호(G021), 만든 사람, 원본" aria-label="게임 찾기"><span class="count" id="q-count"></span></div>
<h2>게임별 ({len(DATA['games'])}개)</h2>
<ul class="log games">
{chr(10).join(rows)}
</ul>
<p class="empty" id="q-empty" hidden>찾는 게임이 없습니다.</p>
<h2>날짜별</h2>
{chr(10).join(days) if days else '<p class="empty">아직 기록이 없습니다.</p>'}
</main>
{REQUEST_DIALOG}
<script>{REQUEST_JS}</script>
<script>{SEARCH_JS}</script>
<script>{PRS_JS}</script>
</body>
</html>
"""
    (REVIEW / "index.html").write_text(page, encoding="utf-8", newline="\n")


def request_block(g):
    """게임 페이지 머리의 「수정 요청」 — 목록과 같은 웹앱·같은 창."""
    return (f'<!--@REQUEST@-->\n<style>{REQUEST_CSS}</style>\n'
            f'<div class="req" data-slug="{E(g["slug"])}" data-title="{E(g["title"])}" data-page="{E(g["page"])}" style="margin:14px 0 0">'
            f'<button type="button" class="req-btn">이 게임 수정 요청</button><span class="req-mark" hidden></span></div>\n'
            f'{REQUEST_DIALOG}\n<script>{REQUEST_JS}</script>\n<!--@/REQUEST@-->')


def build_game_pages():
    pat = re.compile(r"<!--@HISTORY@-->.*?<!--@/HISTORY@-->", re.S)
    req = re.compile(r"<!--@REQUEST@-->.*?<!--@/REQUEST@-->", re.S)
    for g in DATA["games"]:
        p = REVIEW / g["page"]
        s = p.read_text(encoding="utf-8")
        block = f'<!--@HISTORY@-->\n<ul class="log">\n{history_rows(g)}\n</ul>\n<!--@/HISTORY@-->'
        if not pat.search(s):
            raise SystemExit(f"{p.name}에 <!--@HISTORY@--> 칸이 없다")
        s = pat.sub(lambda _: block, s)
        # 수정 요청 칸 — 처음이면 「변환 기록」 제목 앞에 넣고, 다음부터는 그 자리를 다시 쓴다
        if req.search(s):
            s = req.sub(lambda _: request_block(g), s)
        else:
            assert s.count("<h2>변환 기록</h2>") == 1, p.name
            s = s.replace("<h2>변환 기록</h2>", request_block(g) + "\n\n  <h2>변환 기록</h2>", 1)
        p.write_text(s, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    build_game_pages()
    build_index()
    print("review/index.html 과 게임 페이지", len(DATA["games"]), "개를 다시 썼다")
