#!/bin/bash
# 맥 Unity로 앱 경기 화면을 찍는다(2026-11-15) — PR 「화면·보안·배포 영향」의 전/후 그림.
#
#   bash tools/unity_shots.sh <스냅샷 폴더> <게임 폴더> <저장 폴더> [찍을 초 "1,4,8"]
#   예) 후: bash tools/unity_shots.sh ~/Downloads/dfz-unity      g015-pair-archery reference/shots/g015/after
#       전: bash tools/unity_shots.sh ~/Downloads/dfz-unity-main g015-pair-archery reference/shots/g015/before
#
# 스냅샷은 tools/unity_check.sh가 만든 것(첫 임포트가 끝난 것). 임시 검사 DfzPortShotCapture.cs를 넣어 PlayMode로 돌리고
# 끝나면 뺀다 — 저장소에는 올라가지 않는다. 사람 얼굴·카메라 영상이 없는 화면만 찍는다(가짜 장치·봇).
set -u
SNAP="${1:?스냅샷 폴더}"; GAME="${2:?게임 폴더}"; OUT="${3:?저장 폴더}"; TIMES="${4:-1,4,8,12,16,20}"
HERE="$(cd "$(dirname "$0")" && pwd)"
case "$OUT" in /*) ;; *) OUT="$PWD/$OUT" ;; esac
DST="$SNAP/unity/Assets/DigitalFitZone/Tests/PlayMode"
[ -d "$DST" ] || { echo "스냅샷이 아니다: $SNAP" >&2; exit 3; }
VER=$(sed -n 's/^m_EditorVersion: //p' "$SNAP/unity/ProjectSettings/ProjectVersion.txt")
UNITY="/Applications/Unity/Hub/Editor/$VER/Unity.app/Contents/MacOS/Unity"
mkdir -p "$OUT"
cp "$HERE/unity_shots/DfzPortShotCapture.cs" "$DST/"
XML="$SNAP/shots-results.xml"; rm -f "$XML"

echo "· $GAME 화면 찍는 중 → $OUT"
# PlayMode는 그리기가 필요해 -nographics를 붙이지 않는다(팀 run-tests.sh와 같다)
DFZ_SHOT_GAME="$GAME" DFZ_SHOT_TIMES="$TIMES" DIGITALPE_SHOT_OUT="$OUT" \
  "$UNITY" -batchmode -projectPath "$SNAP/unity" -buildTarget Win64 -runTests -testPlatform PlayMode \
  -testFilter DfzPortShotCapture -testResults "$XML" -logFile "$SNAP/shots.log" &
U=$!
# 결과 파일을 쓰고도 안 꺼지면(팀 기록) 2분 뒤 이 Unity 하나만 끈다
while kill -0 $U 2>/dev/null; do
  if [ -f "$XML" ] && [ $(( $(date +%s) - $(stat -f %m "$XML") )) -gt 120 ]; then kill -TERM $U; break; fi
  sleep 3
done
wait $U 2>/dev/null

rm -f "$DST/DfzPortShotCapture.cs" "$DST/DfzPortShotCapture.cs.meta"
python3 - "$XML" <<'EOF'
import sys, xml.etree.ElementTree as ET
try: r = ET.parse(sys.argv[1]).getroot()
except Exception as e: print("✗ 결과 없음 — shots.log를 볼 것:", e); sys.exit(3)
for t in r.iter('test-case'):
    m = t.find('failure/message') if t.find('failure/message') is not None else t.find('reason/message')
    print(t.get('result'), '' if m is None else (m.text or '').strip()[:300])
    sys.exit(0 if t.get('result') == 'Passed' else 2)
print("✗ 검사가 돌지 않았다"); sys.exit(3)
EOF
CODE=$?
ls "$OUT"
exit $CODE
