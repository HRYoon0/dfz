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
main{max-width:1040px;margin:0 auto;padding:32px 16px 64px}
h1{font-size:clamp(28px,4vw,40px);line-height:1.2;margin:0 0 8px;font-weight:800}
h2{font-size:22px;margin:40px 0 12px;font-weight:750;padding-top:8px;border-top:1px solid var(--line)}
h3{font-size:17px;margin:20px 0 8px;font-weight:700;color:var(--lime)}
a{color:var(--lime)}
.lead{color:var(--muted);max-width:46em;margin:0}
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
@media (max-width:640px){ul.log li{grid-template-columns:minmax(0,1fr)}}
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
            f'<li><span class="when">{"새 변환" if x["new"] else "업데이트"}</span>'
            f'<span><a class="game" href="{E(x["game"]["page"])}">{E(x["game"]["title"])}</a></span>'
            f'<span class="note">{x["count"]}건 · 마지막 {E(x["last"])}</span></li>'
            for x in items)
        days.append(f'<h3>{day_label(d)}</h3>\n<ul class="log">\n{lis}\n</ul>')

    cards = []
    for g in sorted(DATA["games"], key=lambda g: max(h["date"] + h.get("time", "") for h in g["history"]), reverse=True):
        first = min(h["date"] for h in g["history"])
        last = max(h["date"] for h in g["history"])
        cards.append(f"""<article class="card">
<h3><a href="{E(g['page'])}">{E(g['title'])}</a></h3>
<dl>
<dt>만든 사람</dt><dd>{E(g['author']) or '미기재'}</dd>
<dt>원본</dt><dd>{E(g['source'])}</dd>
<dt>변환 결과</dt><dd>{E(g['result'])}</dd>
<dt>상태</dt><dd>{E(g['status'])}</dd>
<dt>처음 · 마지막</dt><dd>{first} · {last} (고친 횟수 {len(g['history'])})</dd>
<dt>브랜치</dt><dd><a href="{GH}/tree/{E(g['branch'])}">{E(g['branch'])}</a> · <a href="{GH}/compare/{E(DATA['base'])}...{E(g['branch'])}">기준과 비교</a></dd>
</dl>
</article>""")

    page = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>디지털 핏 존 변환 기록</title>
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<style>{CSS}</style>
</head>
<body>
<main>
<h1>디지털 핏 존 변환 기록</h1>
<p class="lead">여러 사람이 만든 게임을 <a href="{GH}">{E(REPO)}</a>의 C# 형식(판정 → 감독 → 무대)으로 옮긴 기록입니다. 게임마다 작업 브랜치(<code>claude/…</code>)가 있고, 기준 브랜치 <code>{E(DATA['base'])}</code>에는 아직 합치지 않았습니다. 날짜별에는 그날 변환하거나 고친 게임만 나옵니다. 게임 이름을 누르면 그 게임의 확인 페이지(고친 기록, 달라진 것, 파일, 검증, 앱에 붙이는 길, 체험판)가 열립니다. 저장소 링크는 권한이 있는 사람에게만 열립니다.</p>
<h2>날짜별</h2>
{chr(10).join(days) if days else '<p class="empty">아직 기록이 없습니다.</p>'}
<h2>게임별 ({len(DATA['games'])}개)</h2>
<div class="cards">
{chr(10).join(cards)}
</div>
</main>
</body>
</html>
"""
    (REVIEW / "index.html").write_text(page, encoding="utf-8", newline="\n")


def build_game_pages():
    pat = re.compile(r"<!--@HISTORY@-->.*?<!--@/HISTORY@-->", re.S)
    for g in DATA["games"]:
        p = REVIEW / g["page"]
        s = p.read_text(encoding="utf-8")
        block = f'<!--@HISTORY@-->\n<ul class="log">\n{history_rows(g)}\n</ul>\n<!--@/HISTORY@-->'
        if not pat.search(s):
            raise SystemExit(f"{p.name}에 <!--@HISTORY@--> 칸이 없다")
        p.write_text(pat.sub(lambda _: block, s), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    build_game_pages()
    build_index()
    print("review/index.html 과 게임 페이지", len(DATA["games"]), "개를 다시 썼다")
