"""웹 게임 미리보기 페이지를 만든다.

앱(DFZ.WebHost.dll)이 게임 앞에 넣는 dfz 통로 스크립트와 dfz.kit 스타일,
StreamingAssets/app/web의 Preact·htm을 그대로 꺼내 게임 HTML에 붙이고,
가짜 참가자를 키보드·단추로 움직일 수 있는 미리보기 페이지(tools/out/<게임>-preview.html)를 쓴다.
앱의 코드가 담기므로 out/ 폴더는 바깥에 올리지 않는다.

사용법:
    python3 -I tools/build_preview.py games/rocket-jump/web/game.html

앱 파일은 DFZ_DATA → 윈도 설치 폴더 → 프로젝트의 reference/DigitalFitZone_Data 순으로 찾는다
(맥에서는 reference/를 씀).

필요: pip install dnfile
"""
import json
import os
import sys

import dnfile

def find_data_dir():
    """앱의 DigitalFitZone_Data 폴더 — 환경 변수 DFZ_DATA, 윈도 설치본, 프로젝트의 reference/ 순으로 찾는다."""
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (os.environ.get("DFZ_DATA"),
                 r"C:\Program Files\Digital Fit Zone\DigitalFitZone_Data",
                 os.path.join(here, "..", "reference", "DigitalFitZone_Data")):
        if cand and os.path.isfile(os.path.join(cand, "Managed", "DFZ.WebHost.dll")):
            return os.path.normpath(cand)
    raise SystemExit("DigitalFitZone_Data를 찾지 못했다. DFZ_DATA 환경 변수로 알려 주세요.")


INSTALL = find_data_dir()
WEBHOST = os.path.join(INSTALL, "Managed", "DFZ.WebHost.dll")
LIBS = ["preact.umd.js", "hooks.umd.js", "htm.umd.js"]   # WebPlayerKit.LibraryFiles 순서


def user_strings(path):
    """#US 힙의 문자열을 모두 꺼낸다."""
    pe = dnfile.dnPE(path)
    data = pe.net.user_strings.__data__
    out, i = [], 1
    while i < len(data):
        n, hdr = data[i], 1
        if n & 0x80 == 0:
            ln = n
        elif n & 0xC0 == 0x80:
            ln, hdr = ((n & 0x3F) << 8) | data[i + 1], 2
        else:
            ln, hdr = ((n & 0x1F) << 24) | (data[i + 1] << 16) | (data[i + 2] << 8) | data[i + 3], 4
        raw = data[i + hdr:i + hdr + ln]
        if ln > 1:
            try:
                out.append(raw[:-1].decode("utf-16-le"))
            except UnicodeDecodeError:
                pass
        i += hdr + ln
    return out


def pick(strings, prefix):
    for s in strings:
        if s.startswith(prefix):
            return s
    raise SystemExit("DFZ.WebHost.dll에서 찾지 못했다: " + prefix)


def library_tags():
    """WebPlayerKit.LibraryTags와 같은 모양으로 라이브러리를 <script>에 담는다."""
    tags = []
    for name in LIBS:
        with open(os.path.join(INSTALL, "StreamingAssets", "app", "web", name), encoding="utf-8") as fh:
            js = fh.read().replace("</script", "<\\/script").replace("</SCRIPT", "<\\/SCRIPT")
        tags.append("<script>" + js + "\n</script>\n")
    return "".join(tags)


def inject(game_html, head):
    """앱처럼 <head ...> 바로 뒤에 도구와 통로를 넣는다."""
    low = game_html.lower()
    at = low.find("<head")
    if at < 0:
        return head + game_html
    close = game_html.find(">", at)
    return game_html[:close + 1] + head + game_html[close + 1:]


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    game_path = os.path.abspath(sys.argv[1])
    with open(game_path, encoding="utf-8") as fh:
        game_html = fh.read()

    strings = user_strings(WEBHOST)
    kit_style = pick(strings, '<style id="dfz-kit">')
    bridge = pick(strings, '<script>(function(){"use strict";var H={ready:[]')
    page = inject(game_html, library_tags() + kit_style + bridge)

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "preview_shell.html"), encoding="utf-8") as fh:
        shell = fh.read()
    out_html = shell.replace("/*__GAME_SRCDOC__*/null", json.dumps(page).replace("</", "<\\/"))
    sys.path.insert(0, here)   # python3 -I 는 스크립트 폴더를 경로에 넣지 않는다
    from build_standalone import shim_options
    out_html = out_html.replace("/*__OPTS__*/{}", json.dumps(shim_options(game_path), ensure_ascii=False))
    game_name = os.path.basename(os.path.dirname(os.path.dirname(game_path)))   # games/<이름>/web/game.html
    os.makedirs(os.path.join(here, "out"), exist_ok=True)
    out_path = os.path.join(here, "out", game_name + "-preview.html")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(out_html)
    print("미리보기:", out_path)


if __name__ == "__main__":
    main()
