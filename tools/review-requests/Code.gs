/**
 * 디지털 핏 존 변환 기록(https://hryoon0.github.io/dfz/review/)의 「수정 요청」을 구글 시트 탭에 받는다.
 *
 * - POST(본문 JSON, text/plain): { slug, title, page, name, text, images? } → 탭 「수정 요청」에 한 줄. 답 { ok, at }.
 *   images = [{ type: 'image/jpeg', data: base64 }] 3장까지(2026-11-22 회원님 「이미지로 업로드할 수 있도록」) — 드라이브 폴더에 올려
 *   링크 있는 사람 보기로 두고, 시트 「그림」 칸(I열)에 주소를 줄마다 적는다.
 * - GET ?action=list: 게임마다 요청 수·마지막 요청 시각·마지막 처리 상태와 요청 글 전부(댓글처럼 보여 준다).
 *   답 { ok, games: { slug: { count, last, status, items: [{ at, name, text, status, reply }] } } }.
 * - GET ?action=prs: 게임마다 변환 PR 단계(app·merged·open·closed)와 수정 PR — GitHub 읽기 전용 토큰(스크립트 속성 GITHUB_TOKEN), 5분 캐시.
 * - 답글은 시트 「답글」 칸(H열)에 적는다 — 페이지에서 그 요청 아래에 붙어 보인다.
 *
 * ★ 익명 웹앱(실행: 나 / 액세스: 모든 사용자)이라 내장 SpreadsheetApp 대신 처음부터 고급 Sheets 서비스(Sheets v4)를 쓴다.
 * ★ 쓰기는 LockService로 줄 세우고, 조회는 CacheService로 20초 묶는다(쓰면 지운다).
 * ★ 정적 페이지라 비밀값을 둘 수 없다 — 대신 길이 제한·게임 ID 모양 검사·10분에 30건 상한으로 막는다.
 * ★ 값은 RAW로 넣는다 — 「=」로 시작하는 글이 수식이 되지 않게.
 */
var SHEET_ID = '1YYFMoVyPWgdroDd1h4kDmHMoguyhsi9WuaZaH_my5xw';
var TAB = '수정 요청';
var HEAD = ['요청 시각', '게임 ID', '게임 제목', '요청한 사람', '수정 요청 내용', '확인 페이지', '처리 상태', '답글', '그림'];
var LIST_KEY = 'list-v3';
var TAB_KEY = 'tab-ok-v3';   // v3 — 「그림」 머리칸
var LIMIT_PER_10MIN = 30;
var MAX_IMAGES = 3;
var MAX_IMAGE_CHARS = 3500000;   // base64 글자 수 — 그림 한 장 약 2.6MB까지(페이지가 긴 변 1600px JPEG로 줄여 보내 보통 0.3MB 안팎)
var IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
var FOLDER_PROP = 'IMAGE_FOLDER_ID';

/** 받은 값을 검사해 시트 한 줄로. 틀리면 { ok:false, error }. 순수 함수(검사용). */
function buildRow(p, at) {
  if (!p || typeof p !== 'object') return { ok: false, error: 'bad-body' };
  var slug = String(p.slug || '').trim();
  var text = String(p.text || '').trim();
  var name = String(p.name || '').trim();
  var title = String(p.title || '').trim();
  var page = String(p.page || '').trim();
  if (!/^[a-z0-9][a-z0-9-]{1,59}$/.test(slug)) return { ok: false, error: 'bad-slug' };
  if (text.length < 2) return { ok: false, error: 'empty-text' };
  if (text.length > 1000) return { ok: false, error: 'too-long' };
  if (name.length > 40 || title.length > 80) return { ok: false, error: 'too-long' };
  if (page && !/^https:\/\/hryoon0\.github\.io\/dfz\/review\//.test(page)) page = '';
  var images = Array.isArray(p.images) ? p.images : [];
  if (images.length > MAX_IMAGES) return { ok: false, error: 'too-many-images' };
  for (var i = 0; i < images.length; i++) {
    var im = images[i] || {};
    if (IMAGE_TYPES.indexOf(String(im.type)) < 0) return { ok: false, error: 'bad-image' };
    if (typeof im.data !== 'string' || !/^[A-Za-z0-9+\/=]+$/.test(im.data)) return { ok: false, error: 'bad-image' };
    if (im.data.length > MAX_IMAGE_CHARS) return { ok: false, error: 'image-too-big' };
  }
  return { ok: true, row: [at, slug, title, name || '(이름 없음)', text, page, '', '', ''], images: images };
}

/** 시트 줄들 → 게임마다 요약. 순수 함수(검사용). 시각은 「yyyy-MM-dd HH:mm」 글이라 글자 비교가 시간 비교다. */
function summarize(rows) {
  var games = {};
  for (var i = 0; i < rows.length; i++) {
    var r = rows[i] || [];
    var slug = String(r[1] || '');
    if (!slug) continue;
    var at = String(r[0] || '');
    var g = games[slug] || (games[slug] = { count: 0, last: '', status: '', items: [] });
    g.count++;
    g.items.push({ at: at, name: String(r[3] || ''), text: String(r[4] || ''), status: String(r[6] || ''), reply: String(r[7] || ''),
                   images: imageIds(r[8]) });
    if (at >= g.last) { g.last = at; g.status = String(r[6] || ''); }
  }
  return games;
}

/** 「그림」 칸의 드라이브 주소들 → 파일 ID 목록. 순수 함수(검사용). */
function imageIds(cell) {
  var ids = [], re = /\/d\/([A-Za-z0-9_-]{10,})/g, m;
  while ((m = re.exec(String(cell || ''))) !== null) ids.push(m[1]);
  return ids;
}

/** 그림을 드라이브 폴더에 올리고 링크 있는 사람 보기로 — 주소 목록. 익명 웹앱이라 내장 DriveApp 대신 고급 Drive 서비스(v2). */
function saveImages(images, at, slug) {
  if (!images.length) return [];
  var props = PropertiesService.getScriptProperties();
  var folder = props.getProperty(FOLDER_PROP);
  if (!folder) {
    folder = Drive.Files.insert({ title: 'dfz 수정 요청 그림', mimeType: 'application/vnd.google-apps.folder' }).id;
    props.setProperty(FOLDER_PROP, folder);
  }
  return images.map(function (im, i) {
    var ext = im.type === 'image/png' ? 'png' : im.type === 'image/webp' ? 'webp' : 'jpg';
    var name = at.replace(/[^0-9]/g, '') + '-' + slug + '-' + (i + 1) + '.' + ext;
    var blob = Utilities.newBlob(Utilities.base64Decode(im.data), im.type, name);
    var file = Drive.Files.insert({ title: name, mimeType: im.type, parents: [{ id: folder }] }, blob);
    Drive.Permissions.insert({ role: 'reader', type: 'anyone' }, file.id);
    return 'https://drive.google.com/file/d/' + file.id + '/view';
  });
}

// ── PR 상태(2026-11-15 회원님 「페이지가 새로고침 될 때 확인되도록」) ──
// digitalpe는 비공개라 페이지가 직접 못 묻는다 — 웹앱이 읽기 전용 토큰(스크립트 속성 GITHUB_TOKEN)으로 묻고 결과만 넘긴다.
// 게임 목록·PR 번호는 공개된 conversions.json에서 읽는다(페이지가 보낸 값을 받지 않아 아무 PR이나 캐물을 수 없다).
var REPO = 'EduFit-Tech/digitalpe';
var CONVERSIONS = 'https://hryoon0.github.io/dfz/review/conversions.json';
var PRS_KEY = 'prs-v1';

/** PR 하나의 상태 — GitHub pulls 응답에서. 순수 함수(검사용). */
function prState(p) {
  if (!p || !p.number) return null;
  return { n: p.number, state: p.merged_at ? 'merged' : (p.state === 'open' ? 'open' : 'closed') };
}

/**
 * 게임 하나의 단계. 순수 함수(검사용).
 * app = 변환 PR이 병합되고 main에 게임 폴더(StreamingAssets/games/<slug>)가 있다 · merged = 병합됐지만 폴더가 없다 · open · closed · none.
 */
function stageOf(slug, pr, folders) {
  if (!pr) return 'none';
  if (pr.state !== 'merged') return pr.state;
  return folders.indexOf(slug) >= 0 ? 'app' : 'merged';
}

function gh(path, token) {
  return { url: 'https://api.github.com/repos/' + REPO + path, muteHttpExceptions: true,
           headers: { Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json' } };
}

function readPrs() {
  var token = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');
  if (!token) return { ok: false, error: 'no-token' };
  var games = JSON.parse(UrlFetchApp.fetch(CONVERSIONS, { muteHttpExceptions: true }).getContentText()).games || [];
  var nums = [];
  games.forEach(function (g) { [g.pr].concat(g.fixes || []).forEach(function (n) { if (n && nums.indexOf(n) < 0) nums.push(n); }); });
  var reqs = [gh('/contents/unity/Assets/StreamingAssets/games?ref=main', token)]
    .concat(nums.map(function (n) { return gh('/pulls/' + n, token); }));
  var res = UrlFetchApp.fetchAll(reqs);
  if (res[0].getResponseCode() !== 200) return { ok: false, error: 'github-' + res[0].getResponseCode() };
  var folders = JSON.parse(res[0].getContentText()).filter(function (f) { return f.type === 'dir'; }).map(function (f) { return f.name; });
  var byNum = {};
  for (var i = 0; i < nums.length; i++) {
    if (res[i + 1].getResponseCode() === 200) byNum[nums[i]] = prState(JSON.parse(res[i + 1].getContentText()));
  }
  var out = {};
  games.forEach(function (g) {
    var pr = byNum[g.pr] || null;
    out[g.slug] = { stage: stageOf(g.slug, pr, folders), pr: g.pr || null,
                    fixes: (g.fixes || []).map(function (n) { return byNum[n]; }).filter(Boolean) };
  });
  return { ok: true, games: out, at: Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm') };
}

function doGet(e) {
  var action = e && e.parameter && e.parameter.action;
  if (action === 'prs') {
    try {
      var hit = cacheGet(PRS_KEY);
      if (hit) return json(hit);
      var r = readPrs();
      if (r.ok) cachePut(PRS_KEY, r, 300);   // 5분 — 새로고침이 몰려도 GitHub에는 5분에 한 번
      return json(r);
    } catch (err) {
      return json({ ok: false, error: 'prs-failed' });
    }
  }
  if (action !== 'list') return json({ ok: false, error: 'unknown-action' });
  try {
    var cached = cacheGet(LIST_KEY);
    if (cached) return json(cached);
    ensureTab();   // 「답글」 머리칸이 없던 옛 탭에 채워 넣는다(6시간에 한 번)
    // ponytail: 조회마다(20초 묶음) 탭 전체를 읽고, 95KB를 넘으면 묶음도 건너뛴다 — 요청이 수백 건을 넘으면 게임별 조회로 나눈다
    var res = { ok: true, games: summarize(readRows()) };
    cachePut(LIST_KEY, res, 20);
    return json(res);
  } catch (err) {
    return json({ ok: false, error: 'read-failed' });
  }
}

function doPost(e) {
  var p;
  try { p = JSON.parse(e.postData.contents); } catch (err) { return json({ ok: false, error: 'bad-body' }); }
  var at = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm');
  var built = buildRow(p, at);
  if (!built.ok) return json(built);
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(15000);
  } catch (err) {
    return json({ ok: false, error: 'busy' });
  }
  try {
    if (!allowOne()) return json({ ok: false, error: 'rate-limit' });
    ensureTab();
    try {
      built.row[8] = saveImages(built.images, at, String(p.slug).trim()).join('\n');
    } catch (err) {
      return json({ ok: false, error: 'image-failed' });
    }
    Sheets.Spreadsheets.Values.append({ values: [built.row] }, SHEET_ID, "'" + TAB + "'!A1",
      { valueInputOption: 'RAW', insertDataOption: 'INSERT_ROWS' });
    CacheService.getScriptCache().remove(LIST_KEY);
    return json({ ok: true, at: at });
  } catch (err) {
    return json({ ok: false, error: 'write-failed' });
  } finally {
    lock.releaseLock();
  }
}

/** 탭이 없으면 만들고, 머리줄을 쓴다(있어도 다시 쓴다 — 새로 생긴 칸 이름이 들어가게). 6시간 기억해 다시 묻지 않는다. */
function ensureTab() {
  var cache = CacheService.getScriptCache();
  if (cache.get(TAB_KEY)) return;
  var meta = Sheets.Spreadsheets.get(SHEET_ID, { fields: 'sheets.properties.title' });
  var has = (meta.sheets || []).some(function (s) { return s.properties.title === TAB; });
  if (!has) {
    Sheets.Spreadsheets.batchUpdate({ requests: [{ addSheet: { properties: { title: TAB, gridProperties: { frozenRowCount: 1 } } } }] }, SHEET_ID);
  }
  Sheets.Spreadsheets.Values.update({ values: [HEAD] }, SHEET_ID, "'" + TAB + "'!A1:I1", { valueInputOption: 'RAW' });
  cache.put(TAB_KEY, '1', 21600);
}

function readRows() {
  try {
    var res = Sheets.Spreadsheets.Values.get(SHEET_ID, "'" + TAB + "'!A2:I");
    return res.values || [];
  } catch (err) {
    if (String(err).indexOf('Unable to parse range') >= 0) return [];   // 탭이 아직 없다 — 요청 0건
    throw err;
  }
}

/** 10분에 30건까지 — 넘으면 거절(익명 웹앱 도배 막기). */
function allowOne() {
  var cache = CacheService.getScriptCache();
  var key = 'rate-' + Math.floor(Date.now() / 600000);
  var n = Number(cache.get(key) || 0);
  if (n >= LIMIT_PER_10MIN) return false;
  cache.put(key, String(n + 1), 700);
  return true;
}

function cacheGet(k) { try { var v = CacheService.getScriptCache().get(k); return v ? JSON.parse(v) : null; } catch (e) { return null; } }
function cachePut(k, o, ttl) { try { var s = JSON.stringify(o); if (s.length < 95000) CacheService.getScriptCache().put(k, s, ttl); } catch (e) {} }
function json(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }

/** 처음 한 번 편집기에서 실행해 권한을 승인한다(익명 웹앱은 소유자 권한으로 돈다). 탭도 만든다. */
function authorize() {
  ensureTab();
  // 드라이브 권한(그림 올리기)도 이때 승인한다 — 폴더가 없으면 만든다
  Logger.log('그림 폴더: ' + (PropertiesService.getScriptProperties().getProperty(FOLDER_PROP) || '(첫 그림 때 만듦)'));
  Drive.Files.list({ maxResults: 1 });
  Logger.log('ok: ' + readRows().length + '줄');
  CacheService.getScriptCache().remove(PRS_KEY);
  Logger.log('PR 상태: ' + JSON.stringify(readPrs()));   // 토큰을 넣은 뒤 한 번 — 외부 요청 권한도 이때 승인한다
}
