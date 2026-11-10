/**
 * 디지털 핏 존 변환 기록(https://hryoon0.github.io/dfz/review/)의 「수정 요청」을 구글 시트 탭에 받는다.
 *
 * - POST(본문 JSON, text/plain): { slug, title, page, name, text } → 탭 「수정 요청」에 한 줄. 답 { ok, at }.
 * - GET ?action=list: 게임마다 요청 수·마지막 요청 시각·마지막 처리 상태. 답 { ok, games: { slug: { count, last, status } } }.
 *
 * ★ 익명 웹앱(실행: 나 / 액세스: 모든 사용자)이라 내장 SpreadsheetApp 대신 처음부터 고급 Sheets 서비스(Sheets v4)를 쓴다.
 * ★ 쓰기는 LockService로 줄 세우고, 조회는 CacheService로 20초 묶는다(쓰면 지운다).
 * ★ 정적 페이지라 비밀값을 둘 수 없다 — 대신 길이 제한·게임 ID 모양 검사·10분에 30건 상한으로 막는다.
 * ★ 값은 RAW로 넣는다 — 「=」로 시작하는 글이 수식이 되지 않게.
 */
var SHEET_ID = '1YYFMoVyPWgdroDd1h4kDmHMoguyhsi9WuaZaH_my5xw';
var TAB = '수정 요청';
var HEAD = ['요청 시각', '게임 ID', '게임 제목', '요청한 사람', '수정 요청 내용', '확인 페이지', '처리 상태'];
var LIST_KEY = 'list-v1';
var LIMIT_PER_10MIN = 30;

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
  return { ok: true, row: [at, slug, title, name || '(이름 없음)', text, page, ''] };
}

/** 시트 줄들 → 게임마다 요약. 순수 함수(검사용). 시각은 「yyyy-MM-dd HH:mm」 글이라 글자 비교가 시간 비교다. */
function summarize(rows) {
  var games = {};
  for (var i = 0; i < rows.length; i++) {
    var r = rows[i] || [];
    var slug = String(r[1] || '');
    if (!slug) continue;
    var at = String(r[0] || '');
    var g = games[slug] || (games[slug] = { count: 0, last: '', status: '' });
    g.count++;
    if (at >= g.last) { g.last = at; g.status = String(r[6] || ''); }
  }
  return games;
}

function doGet(e) {
  var action = e && e.parameter && e.parameter.action;
  if (action !== 'list') return json({ ok: false, error: 'unknown-action' });
  try {
    var cached = cacheGet(LIST_KEY);
    if (cached) return json(cached);
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

/** 탭이 없으면 만들고 머리줄을 쓴다. 있으면 6시간 기억해 다시 묻지 않는다. */
function ensureTab() {
  var cache = CacheService.getScriptCache();
  if (cache.get('tab-ok')) return;
  var meta = Sheets.Spreadsheets.get(SHEET_ID, { fields: 'sheets.properties.title' });
  var has = (meta.sheets || []).some(function (s) { return s.properties.title === TAB; });
  if (!has) {
    Sheets.Spreadsheets.batchUpdate({ requests: [{ addSheet: { properties: { title: TAB, gridProperties: { frozenRowCount: 1 } } } }] }, SHEET_ID);
    Sheets.Spreadsheets.Values.update({ values: [HEAD] }, SHEET_ID, "'" + TAB + "'!A1:G1", { valueInputOption: 'RAW' });
  }
  cache.put('tab-ok', '1', 21600);
}

function readRows() {
  try {
    var res = Sheets.Spreadsheets.Values.get(SHEET_ID, "'" + TAB + "'!A2:G");
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
  Logger.log('ok: ' + readRows().length + '줄');
}
