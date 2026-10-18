# digital_fit

Digital Fit Zone(설치형 Unity 앱)을 분석한 기록과, 그 앱의 웹 게임 규격으로 만든 게임 **로켓 점프**.
분석 내용은 [ANALYSIS.md](ANALYSIS.md)에 있습니다.

## 폴더

```
dist/rocket-jump.html          완성본 — 브라우저로 바로 여는 게임 한 장 (앱 코드 없음, 공유 가능)
games/rocket-jump/
  web/game.html                게임 본체 (앱 규격 dfz SDK) — 여기를 고친다
  ruleset.json                 앱에 넣을 때 쓰는 룰셋
tools/
  build_standalone.py          game.html → dist/<이름>.html
  standalone_shim.html         앱 없이 돌게 하는 dfz 대역 (직접 짠 코드)
  build_preview.py             앱의 진짜 통로를 붙인 검증용 미리보기 → tools/out/
  preview_shell.html           미리보기 화면 틀
  re/                          분석 스크립트 (dump_meta.py, cil_xref.py, validate.ps1, lint.ps1)
reference/                     윈도 PC의 앱에서 복사해 둔 참고 자료 (공유 금지)
  DigitalFitZone_Data/Managed/   DFZ.*.dll, netstandard.dll
  DigitalFitZone_Data/StreamingAssets/  기본 게임 룰셋 17개, Preact·htm, ko/en 언어 파일
  meta/                          DLL에서 뽑은 타입·문자열·IL 호출 목록
```

`reference/`가 있으면 앱이 설치되지 않은 맥에서도 모든 도구가 돕니다.
도구는 앱 파일을 `DFZ_DATA` 환경 변수 → 윈도 설치 폴더 → `reference/DigitalFitZone_Data` 순서로 찾습니다.

## 학년별 게임 18개 (틀 + 캐릭터 + 내용)

우리반 플레이랩 885 기획안을 엔진 계열별로 묶어 세 틀로 만들었다. 모두 DFZ 웹 게임 규격(bridge: players)이다.

| 틀 | 묶은 기획안 | 입력 | 인원 |
|---|---|---|---|
| `templates/camera.html` 몸으로 OX | 판별·선택형(근거 선택·특징 판별·예측 선택·듣기 뜻 매칭 …) | 만세 = O, 앉기 = X (카메라) | 1~6 |
| `templates/controller.html` 기울여 맞추기 | 기울기센서형(수치 조절·비교, 값 조절과 비교, 변환 조절) | 기울이기 한 칸씩, 누르기 확정 (폰·컨트롤러) | 1~30 |
| `templates/pointer.html` 콕콕 분류 | 멀티 마우스형(공동 분류·공동 끌어놓기·특징 선택) | 자리마다 자기 커서 — 누르고 있으면 집고 떼면 놓기 (폰·컨트롤러) | 1~30 |

- 캐릭터 「콩콩이」: `templates/buddy.js` (캔버스 그리기, Codex 제작) · 콘셉트 `design/buddy-concept.png`
  `Buddy.draw(ctx, { x, y, size, color, pose: 'idle|raise|squat|jump|lean|cheer|oops', lean, t, label })`
- 공용 도구 `templates/common.js` (dfz.kit 색 · 글자 5% 이상 · 줄바꿈)
- 내용 `content/g<학년>-ox-camera.json`, `-tilt-controller.json`, `-sort-pointer.json` — 문항만 고치면 된다.
  컨트롤러 답은 눈금 글자(`"3/4"`), 분류 답은 바구니 이름으로 쓰고, 빌드가 있는지 검사한다.

```bash
python3 -I tools/build_games.py                 # content/ 전부 → games/<id>/ + dist/<id>.html
python3 -I tools/build_games.py g3-ox-camera    # 하나만
```

### 콕콕 분류의 커서 입력

| 동작 | 커서 | 지금 설치본에서 |
|---|---|---|
| `Move` (x, y 0~1) | 가리키는 곳으로 간다 | 내는 장치 없음 — 포인터 장치가 붙으면 그대로 쓴다 (룰셋 선택 동작) |
| `Tilt` (x, y) | 기울인 쪽으로 흘러간다 | 폰·컨트롤러 |
| `Press` / `Release` | 집기 / 놓기 | 컨트롤러 단추는 둘을 따로 보낸다 |
| `Touch` | 집기·놓기 번갈아 | 폰 |

- 앱 근거: 장치별 동작 표 `DFZ.Core` `DeviceCapability`(카메라만 Move), 웹 미리보기 `WebPreviewKeys.StepMove`(손 좌표 0~1을 Move로),
  `UguiWebStage.FlushInputs`(장치 벡터 x·y를 그대로 웹 게임에 넘김).
- 룰셋 필수는 `Tilt`·`Press`(폰·컨트롤러가 모두 냄), 선택은 `Release`·`Touch`·`Move`.
- 실기기에서 기울기 위아래가 반대면 `pointer.html`의 `TILT_FLIP_Y`를 -1로, 속도는 `TILT_SPEED`.
- 단독 실행(`dist/*-sort-pointer.html`)에서는 마우스가 1번 자리의 `Move`, 누르기 키를 떼면 `Release`.

단독 실행(`dist/*.html`) 키: 동작마다 한 줄 — 1~6 / Q~Y / A~H (자리 순), 스페이스 = 시작. 화면 아래 단추로도 된다.
앱 검사기 크기 한도는 300 KB(307200바이트, `WebGameLint.Check` 상수) — 지금 게임은 18~23 KB.

## 맥에서 시작하기

```bash
python3 -m pip install -r requirements.txt
```

게임을 고친 뒤 완성본 다시 만들기:

```bash
python3 -I tools/build_standalone.py games/rocket-jump/web/game.html
```

```bash
open dist/rocket-jump.html
```

앱과 같은 통로로 검증하는 미리보기 (가짜 참가자·자동 참가자 지원):

```bash
python3 -I tools/build_preview.py games/rocket-jump/web/game.html
```

```bash
open tools/out/rocket-jump-preview.html
```

앱의 검사기로 룰셋·HTML 확인 — PowerShell 7(`brew install powershell`)이 필요합니다. 맥에서는 아직 돌려 보지 않았습니다(윈도에서는 통과).

```bash
pwsh tools/re/validate.ps1 games/rocket-jump/ruleset.json
```

```bash
pwsh tools/re/lint.ps1 games/rocket-jump/web/game.html
```

## 조작 (dist/rocket-jump.html)

- 인원 고르고 **스페이스** 또는 「시작」
- 점프: `1`~`6` · 앉기: `Q W E R T Y` · 화면 아래 단추로도 가능

## 주의

- `reference/`와 `tools/out/`에는 앱의 코드·DLL이 들어 있습니다. 바깥 저장소나 공개된 곳에 올리지 마세요(`.gitignore`에 넣어 두었음).
- 맥에는 Malgun Gothic이 없어서 Apple SD Gothic Neo로 보입니다. 실제 앱(윈도)에서는 Malgun Gothic으로 보입니다.
