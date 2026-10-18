"""틀(templates/) + 캐릭터(buddy.js) + 내용(content/<id>.json) → 앱용 게임 폴더와 단독 실행 HTML.

content/<id>.json 하나가 게임 하나다. kind가 틀을 정한다:
    camera      → templates/camera.html      몸으로 OX (만세 = O, 앉기 = X), 1~6명
    controller  → templates/controller.html  기울여 맞추기 (기울이기 + 누르기), 1~30명
    pointer     → templates/pointer.html     콕콕 분류 (멀티 포인터: Move·Tilt + Press·Release), 1~30명

만드는 것:
    games/<id>/web/game.html   앱에 넣는 본체 (dfz 통로는 앱이 붙인다)
    games/<id>/ruleset.json    앱 룰셋 — ruleSetId는 id에서 뽑아 늘 같다
    dist/<id>.html             브라우저로 바로 여는 완성본

사용법:
    python3 -I tools/build_games.py            # content/ 전부
    python3 -I tools/build_games.py g1-ox-camera
"""
import json
import os
import re
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # python3 -I 는 스크립트 폴더를 경로에 넣지 않는다
from build_standalone import build as build_standalone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "templates")

KINDS = {
    "camera": {
        "template": "camera.html", "category": "Reaction", "players": (1, 6), "devices": ["Camera"],
        "required": ["Raise", "Squat"], "optional": [], "magnitude": 0.3,
        "moves": [("Raise", "맞다고 생각하면 두 팔을 번쩍 든다(O)"), ("Squat", "틀리다고 생각하면 앉는다(X)")],
        "scoring": "맞힌 문제 하나에 1점",
        "cautions": ["옆 사람과 팔 하나 이상 떨어져 선다", "무릎이 아프면 얕게 앉아도 된다"],
    },
    "controller": {
        "template": "controller.html", "category": "Accuracy", "players": (1, 30), "devices": ["Phone", "Controller"],
        "required": ["Tilt", "Press"], "optional": ["Shake"], "magnitude": 0.35,
        "moves": [("Tilt", "기울이면 내 눈금이 한 칸씩 움직인다"), ("Press", "누르면 답을 확정한다(흔들어도 된다)")],
        "scoring": "정답 칸에 맞추면 1점 — 확정하지 않아도 시간이 끝날 때 위치로 채점",
        "cautions": ["컨트롤러 끈을 손목에 건다", "흔들 때 옆 친구와 부딪히지 않게 간격을 둔다"],
    },
    "pointer": {
        "template": "pointer.html", "category": "Cooperation", "players": (1, 30), "devices": ["Phone", "Controller"],
        # 필수는 폰·컨트롤러가 모두 내는 것만 (앱 DeviceCapability 표) — Move는 포인터 장치가 붙으면 쓰는 선택 동작
        "required": ["Tilt", "Press"], "optional": ["Release", "Touch", "Move"], "magnitude": 0.2,
        "moves": [("Tilt", "기울이면 내 커서가 그쪽으로 움직인다"), ("Press", "누르고 있으면 카드를 집는다"),
                  ("Release", "떼면 그 자리에 놓는다 — 알맞은 바구니면 점수")],
        "scoring": "알맞은 바구니에 넣은 카드 한 장에 1점",
        "cautions": ["컨트롤러 끈을 손목에 건다", "카드는 먼저 집은 친구 것 — 기다렸다가 다른 카드를 집는다"],
    },
}

# 앱 검사기가 거절하는 낱말 (WebGameLint) — 빌드 단계에서 미리 막는다
FORBIDDEN = [r"fetch\s*\(", r"XMLHttpRequest", r"WebSocket", r"localStorage", r"sessionStorage", r"indexedDB",
             r"alert\s*\(", r"confirm\s*\(", r"prompt\s*\(", r"window\s*\.\s*open\s*\(", r"<\s*(?:iframe|form|input|textarea|select)\b",
             r"(?<![:/*])//(?! )", r"EventSource", r"addEventListener\(\s*['\"](?:mouse|key|pointer|touch|click)"]


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def check_content(gid, c):
    """내용 파일 실수를 빌드 때 잡는다 — 컨트롤러 답은 눈금 글자로 적고 여기서 번호로 바꾼다"""
    if c["kind"] == "camera":
        for it in c["items"]:
            if not isinstance(it.get("a"), bool) or not it.get("q"):
                raise SystemExit(f"{gid}: 문항에 q(문장)와 a(true/false)가 있어야 한다 — {it}")
        return c
    if c["kind"] == "pointer":
        cards = []
        for it in c["cards"]:
            if it["bin"] not in c["bins"]:
                raise SystemExit(f"{gid}: 카드 '{it['t']}'의 바구니 '{it['bin']}'이 {c['bins']}에 없다")
            cards.append(dict(it, bin=c["bins"].index(it["bin"])))
        return dict(c, cards=cards)
    items = []
    for it in c["items"]:
        sc = c["scales"].get(it["scale"])
        if not sc:
            raise SystemExit(f"{gid}: 없는 눈금 '{it['scale']}'")
        if it["answer"] not in sc["stops"]:
            raise SystemExit(f"{gid}: '{it['ask']}'의 답 '{it['answer']}'이 눈금 {sc['stops']}에 없다")
        if it["answer"] == sc["stops"][0]:
            print(f"  주의 {gid}: '{it['ask']}'의 답이 시작 칸이라 안 움직여도 맞는다")
        items.append(dict(it, answer=sc["stops"].index(it["answer"])))
    return dict(c, items=items)


def ruleset(gid, c, k):
    return {
        "schemaVersion": "1.0",
        "ruleSetId": str(uuid.uuid5(uuid.NAMESPACE_URL, "digital_fit/" + gid)),
        "title": c["title"],
        "description": c["description"],
        "category": k["category"],
        "players": {"min": k["players"][0], "max": k["players"][1], "teams": {"enabled": False}},
        "duration": {"mode": "Timed", "seconds": c["seconds"], "countdownSeconds": 3},
        "inputs": {"required": k["required"], "optional": k["optional"], "deviceKinds": k["devices"], "minMagnitude": k["magnitude"]},
        "flow": {"type": "Web", "web": {"entry": "web/game.html", "people": k["players"][1], "bridge": "players"}},
        "scoring": {
            "rules": [{"id": "reported", "trigger": "OnAction",
                       "when": {"action": k["required"][0], "minMagnitude": 0.0, "cooldownMs": 0},
                       "award": {"points": 1, "target": "Player"}}],
            "aggregation": "Sum", "teamAggregation": "Average", "allowNegative": False,
        },
        "victory": {"condition": "HighestScore", "scope": "Individual", "tieBreak": ["Draw"], "showRanking": 5},
        "difficulty": {"default": "Normal"},
        "guide": {"ko": {
            "moves": [{"action": a, "effect": e} for a, e in k["moves"]],
            "scoring": [{"rule": "reported", "text": k["scoring"]}],
            "cautions": k["cautions"],
        }},
    }


def build(gid):
    c = json.load(open(os.path.join(ROOT, "content", gid + ".json"), encoding="utf-8"))
    k = KINDS[c["kind"]]
    c = check_content(gid, c)
    game = {key: c[key] for key in ("title", "seconds", "answerSec", "items", "scales", "bins", "cards") if key in c}

    html = read(os.path.join(TPL, k["template"]))
    html = html.replace("__TITLE__", c["title"])
    html = html.replace("/*@GAME@*/null", json.dumps(game, ensure_ascii=False))
    html = html.replace("/*@BUDDY@*/", read(os.path.join(TPL, "buddy.js")).strip())
    html = html.replace("/*@COMMON@*/", read(os.path.join(TPL, "common.js")).strip())
    for pat in FORBIDDEN:
        m = re.search(pat, html)
        if m:
            line = html.count("\n", 0, m.start()) + 1
            raise SystemExit(f"{gid}: 앱 검사기가 거절할 글 '{m.group(0)}' ({line}줄)")

    out = os.path.join(ROOT, "games", gid)
    os.makedirs(os.path.join(out, "web"), exist_ok=True)
    game_path = os.path.join(out, "web", "game.html")
    with open(game_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)
    with open(os.path.join(out, "ruleset.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(ruleset(gid, c, k), fh, ensure_ascii=False, indent=2)
    dist = build_standalone(game_path)
    print(f"{gid}: {len(html.encode()) // 1024} KB → {os.path.relpath(dist, ROOT)}")


DEVICE_KO = {"Camera": "카메라", "Phone": "폰", "Controller": "컨트롤러"}


def write_index():
    """dist/index.html — dist/에 있는 게임 모음. 내용 파일이 있으면 그 정보, 없으면(로켓 점프 등) 룰셋 정보로 카드를 만든다."""
    games = []
    for gid in sorted(os.listdir(os.path.join(ROOT, "games"))):
        rules = os.path.join(ROOT, "games", gid, "ruleset.json")
        if not os.path.isfile(os.path.join(ROOT, "dist", gid + ".html")) or not os.path.isfile(rules):
            continue
        r = json.load(open(rules, encoding="utf-8"))
        cpath = os.path.join(ROOT, "content", gid + ".json")
        c = json.load(open(cpath, encoding="utf-8")) if os.path.isfile(cpath) else {}
        games.append({
            "file": gid + ".html", "kind": c.get("kind", "other"), "grade": c.get("grade", 0),
            "title": r["title"], "description": c.get("description", r.get("description", "")),
            "devices": "·".join(DEVICE_KO.get(d, d) for d in r["inputs"]["deviceKinds"]),
            "players": f"{r['players']['min']}~{r['players']['max']}명",
            "seconds": r["duration"].get("seconds", 60),
            "items": len(c.get("items") or c.get("cards") or []),
        })
    order = ["camera", "controller", "pointer", "other"]   # 한 학년 안에서 틀 순서
    games.sort(key=lambda g: (g["grade"] == 0, g["grade"], order.index(g["kind"]) if g["kind"] in order else 9))
    html = read(os.path.join(TPL, "index.html"))
    html = html.replace("/*@GAMES@*/[]", json.dumps(games, ensure_ascii=False))
    html = html.replace("/*@BUDDY@*/", read(os.path.join(TPL, "buddy.js")).strip())
    with open(os.path.join(ROOT, "dist", "index.html"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)
    print(f"모음 페이지: dist/index.html (게임 {len(games)}개)")


if __name__ == "__main__":
    ids = sys.argv[1:] or sorted(f[:-5] for f in os.listdir(os.path.join(ROOT, "content")) if f.endswith(".json"))
    for gid in ids:
        build(gid)
    write_index()
