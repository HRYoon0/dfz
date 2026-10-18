"""앱 없이 브라우저에서 바로 여는 게임 HTML 한 장을 만든다.

games/<이름>/web/game.html의 <head> 뒤에 tools/standalone_shim.html(직접 짠 dfz 대역)을
넣어 dist/<이름>.html로 쓴다. 앱의 코드는 들어가지 않는다.
games/<이름>/ruleset.json이 있으면 시간·동작·인원을 읽어 대역에 알려 준다(window.DFZ_SHIM).

사용법:
    python3 -I tools/build_standalone.py games/rocket-jump/web/game.html
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def shim_options(game_path):
    rules = os.path.join(os.path.dirname(os.path.dirname(game_path)), "ruleset.json")
    if not os.path.isfile(rules):
        return {}
    with open(rules, encoding="utf-8") as fh:
        r = json.load(fh)
    return {
        "seconds": r["duration"].get("seconds", 60),
        "countdown": r["duration"].get("countdownSeconds", 3),
        "actions": r["inputs"]["required"] + r["inputs"].get("optional", []),
        "maxPlayers": r["players"]["max"],
    }


def build(game_path):
    game_path = os.path.abspath(game_path)
    with open(game_path, encoding="utf-8") as fh:
        game = fh.read()
    with open(os.path.join(HERE, "standalone_shim.html"), encoding="utf-8") as fh:
        shim = fh.read()
    opts = "<script>window.DFZ_SHIM = " + json.dumps(shim_options(game_path), ensure_ascii=False) + ";</script>\n"

    at = game.lower().find("<head")
    if at < 0:
        raise SystemExit("<head>가 없다: " + game_path)
    close = game.find(">", at)
    page = game[:close + 1] + "\n" + opts + shim + game[close + 1:]

    name = os.path.basename(os.path.dirname(os.path.dirname(game_path)))   # games/<이름>/web/game.html
    out_dir = os.path.join(os.path.dirname(HERE), "dist")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, name + ".html")
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page)
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    print(build(sys.argv[1]))
