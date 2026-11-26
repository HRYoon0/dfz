#!/bin/bash
# 맥 Unity 에디터를 화면으로 열어 SessionTest 장면을 Play한다(2026-11-26) — 실물 폰으로 한 판(팀 안내 7-3).
#
#   bash tools/unity_play.sh [스냅샷 폴더]   (기본 ~/Downloads/dfz-unity — unity_check.sh로 가지를 맞춘 것)
#
# 임시 편집기 스크립트 DfzOpenPlay.cs를 넣는다. 저장소에는 올라가지 않고, 다음 unity_check.sh의 rsync --delete가 지운다.
set -u
SNAP="${1:-$HOME/Downloads/dfz-unity}"
HERE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SNAP/unity/ProjectSettings/ProjectVersion.txt" ] || { echo "스냅샷이 아니다: $SNAP" >&2; exit 3; }
pgrep -f "MacOS/Unity -projectPath $SNAP/unity" >/dev/null && { echo "이 스냅샷을 Unity가 이미 열고 있다" >&2; exit 3; }
VER=$(sed -n 's/^m_EditorVersion: //p' "$SNAP/unity/ProjectSettings/ProjectVersion.txt")
UNITY="/Applications/Unity/Hub/Editor/$VER/Unity.app/Contents/MacOS/Unity"
DST="$SNAP/unity/Assets/DfzLocalEditor/Editor"
mkdir -p "$DST"
cp "$HERE/unity_shots/DfzDriver.cs" "$DST/"   # 명령 파일 조종 + 처음 한 번 Play
echo "· $(cat "$SNAP/SNAPSHOT_COMMIT.txt" 2>/dev/null) 스냅샷을 Unity $VER 에디터로 엽니다(빌드 대상 Win64)"
exec "$UNITY" -projectPath "$SNAP/unity" -buildTarget Win64 -logFile "$SNAP/play.log"
