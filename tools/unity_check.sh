#!/bin/bash
# 맥 Unity로 digitalpe 가지를 컴파일하고, 그 게임 EditMode 검사만 돌린다(2026-11-15).
# 복제하지 않는다 — API로 그 가지의 압축본(tarball)을 받아 ~/Downloads/dfz-unity 에 맞춰 넣는다.
# Unity 캐시(unity/Library)는 남겨 두므로 두 번째부터는 몇 분이면 끝난다.
#
#   bash tools/unity_check.sh <가지> <검사 이름 정규식>
#   예) bash tools/unity_check.sh claude/g015-ring-reveal PairArchery
#
# 끝에 PR 본문 「확인한 결과」에 붙일 줄을 찍는다. 종료 코드: 0 통과 · 2 실패 있음 · 3 컴파일 오류/실행 실패.
# 빌드 대상은 Win64 — 제품이 Windows 하나뿐이라 #if UNITY_STANDALONE_WIN 코드까지 같은 조건으로 컴파일한다.
# 맥에서만 나는 실패(Win32 시리얼 5 · C:/ 경로 1 · CameraChoice 1)는 이 게임 필터에 걸리지 않는다.
set -u
R=EduFit-Tech/digitalpe
BR="${1:?가지 이름}"; FILTER="${2:?검사 이름 정규식(예: PairArchery)}"
SNAP="$HOME/Downloads/dfz-unity"
mkdir -p "$SNAP" /tmp/claude/unitysnap

[ -f "$SNAP/unity/Temp/UnityLockfile" ] && pgrep -f "projectPath $SNAP/unity" >/dev/null && {
  echo "이 스냅샷을 Unity가 열고 있다 — 닫고 다시" >&2; exit 3; }

# 1. 스냅샷: 받은 압축본과 똑같이 맞춘다(지워진 파일도 지운다). Unity 캐시·결과 파일은 남긴다.
SHA=$(gh api "repos/$R/branches/$BR" --jq '.commit.sha[:7]') || exit 3
echo "· $BR @ $SHA 받는 중"
gh api "repos/$R/tarball/$BR" > /tmp/claude/unitysnap.tar.gz || exit 3
tar -xzf /tmp/claude/unitysnap.tar.gz -C /tmp/claude/unitysnap --strip-components=1 || exit 3
rsync -a --delete \
  --exclude '/unity/Library/' --exclude '/unity/Temp/' --exclude '/unity/Logs/' --exclude '/unity/UserSettings/' \
  --exclude '/*.log' --exclude '/*.xml' --exclude '/SNAPSHOT_COMMIT.txt' --exclude '/tools/*.mac.sh' \
  /tmp/claude/unitysnap/ "$SNAP/"
rm -rf /tmp/claude/unitysnap /tmp/claude/unitysnap.tar.gz
echo "$SHA" > "$SNAP/SNAPSHOT_COMMIT.txt"

# 2. 프로젝트가 정한 Unity 버전
VER=$(sed -n 's/^m_EditorVersion: //p' "$SNAP/unity/ProjectSettings/ProjectVersion.txt")
UNITY="/Applications/Unity/Hub/Editor/$VER/Unity.app/Contents/MacOS/Unity"
[ -x "$UNITY" ] || { echo "Unity $VER 이 없다 — Hub에서 그 버전(+Windows Build Support (Mono))을 깔 것" >&2; exit 3; }

# 3. 컴파일 + 고른 EditMode 검사(-runTests가 먼저 컴파일한다)
XML="$SNAP/check-results.xml"; LOG="$SNAP/check.log"
rm -f "$XML"
echo "· Unity $VER · Win64 · EditMode 「${FILTER}」 돌리는 중"
"$UNITY" -batchmode -nographics -projectPath "$SNAP/unity" -buildTarget Win64 \
  -runTests -testPlatform EditMode -testFilter "$FILTER" -testResults "$XML" -logFile "$LOG"
CODE=$?

CS=$(grep -c "error CS" "$LOG")
if [ "$CS" -gt 0 ] || [ ! -f "$XML" ]; then
  echo "✗ 컴파일 오류 $CS건 또는 결과 없음(종료 코드 $CODE) — $LOG"; grep "error CS" "$LOG" | sort -u | head -20; exit 3
fi

# 4. 요약 — PR 본문에 그대로 붙인다
python3 - "$XML" "$VER" "$SHA" "$FILTER" <<'EOF'
import sys, xml.etree.ElementTree as ET
xml, ver, sha, flt = sys.argv[1:]
r = ET.parse(xml).getroot()
g = {k: r.get(k) for k in ('total', 'passed', 'failed', 'skipped')}
print(f"- Unity 확인 — 맥 Unity {ver}, 빌드 대상 Win64, 가지 {sha} 스냅샷.")
print("  - 컴파일: 오류 0.")
print(f"  - EditMode(골라 돌림 — 「{flt}」, 전체 아님): 전체 {g['total']} · 통과 {g['passed']} · 실패 {g['failed']} · 건너뜀 {g['skipped']}.")
for t in r.iter('test-case'):
    if t.get('result') == 'Failed':
        m = t.find('failure/message')
        print(f"    - 실패: {t.get('fullname')} — {(m.text or '').strip().splitlines()[0][:150] if m is not None else ''}")
if g['total'] == '0':
    print("  - ⚠️ 0건 — 필터가 아무 검사도 고르지 않았다. 통과가 아니다.")
    sys.exit(3)
sys.exit(0 if g['failed'] == '0' else 2)
EOF
