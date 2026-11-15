#!/bin/bash
# HTML 판을 앱의 웹 게임 검사기로 검사한다(2026-11-15) — 맥 Unity, 스냅샷에 임시 EditMode 검사를 넣어 돌리고 뺀다.
#
#   bash tools/web_lint.sh <스냅샷 폴더> <HTML 파일>
#   예) bash tools/web_lint.sh ~/Downloads/dfz-unity port/g015-pair-archery/docs/progress/g015-pair-archery-web/game.html
#
# 종료 코드 0 통과 · 2 문제 있음(목록을 찍는다) · 3 실행 실패.
# ★ 격리 브라우저(CEF) 실행은 하지 않는다 — 엔진 패키지가 Windows 전용(engine.cef.win.x64)이라 맥에서는 못 돈다.
set -u
SNAP="${1:?스냅샷 폴더}"; HTML="${2:?HTML 파일}"
case "$HTML" in /*) ;; *) HTML="$PWD/$HTML" ;; esac
[ -f "$HTML" ] || { echo "HTML이 없다: $HTML" >&2; exit 3; }
HERE="$(cd "$(dirname "$0")" && pwd)"
DST="$SNAP/unity/Assets/DigitalFitZone/Tests/EditMode"
VER=$(sed -n 's/^m_EditorVersion: //p' "$SNAP/unity/ProjectSettings/ProjectVersion.txt")
UNITY="/Applications/Unity/Hub/Editor/$VER/Unity.app/Contents/MacOS/Unity"
cp "$HERE/unity_shots/DfzPortWebLint.cs" "$DST/"
XML="$SNAP/weblint-results.xml"; rm -f "$XML"
DFZ_WEB_HTML="$HTML" "$UNITY" -batchmode -nographics -projectPath "$SNAP/unity" -buildTarget Win64 \
  -runTests -testPlatform EditMode -testFilter DfzPortWebLint -testResults "$XML" -logFile "$SNAP/weblint.log"
rm -f "$DST/DfzPortWebLint.cs" "$DST/DfzPortWebLint.cs.meta"
grep -h "\[dfz-port 웹 검사\]" "$SNAP/weblint.log" | head -1
python3 - "$XML" <<'EOF'
import sys, xml.etree.ElementTree as ET
try: r = ET.parse(sys.argv[1]).getroot()
except Exception as e: print("✗ 결과 없음 — weblint.log를 볼 것:", e); sys.exit(3)
for t in r.iter('test-case'):
    m = t.find('failure/message')
    print(t.get('result'), '' if m is None else (m.text or '').strip()[:1500])
    sys.exit(0 if t.get('result') == 'Passed' else 2)
print("✗ 검사가 돌지 않았다"); sys.exit(3)
EOF
