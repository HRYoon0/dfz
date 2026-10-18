# Digital Fit Zone 분석 및 게임 추가

바탕화면 바로가기 `Digital Fit Zone.lnk` → `C:\Program Files\Digital Fit Zone\DigitalFitZone.exe`

## 1. 어떤 프로그램인가

| 항목 | 내용 |
|---|---|
| 엔진 | Unity, **Mono 빌드** (`MonoBleedingEdge/`, `DigitalFitZone_Data/Managed/*.dll`) — IL2CPP가 아니라 C# 코드가 IL 그대로 남아 있음 |
| 자체 어셈블리 | `DFZ.Core` 입력·장치 · `DFZ.Game` 세션 진행 · `DFZ.Rules` 룰셋 스키마·검사·해석 · `DFZ.UI` 화면 전부 · `DFZ.Vision` 카메라 자세 인식 · `DFZ.Net` 포털·LAN·게임 캐시 · `DFZ.WebHost` 웹 게임 샌드박스 · `DFZ.Settings` 설정·암호화 저장소 |
| 웹 엔진 | VoltstroStudios **UnityWebBrowser**(CEF) — 웹 게임은 이 안에서 돔 |
| 사용자 데이터 | `%USERPROFILE%\AppData\LocalLow\Digital Fit Zone\Digital Fit Zone\` |

## 2. 분석 방법

요청하신 [morluto/rea](https://github.com/morluto/rea)는 .NET 어셈블리를 **메타데이터 + CIL 명령 정적 분석**으로 살펴보는 MCP 서버입니다.
rea는 Node.js 22 이상이 필요한데 이 PC에는 Node가 없어서, 같은 방식을 Python(`dnfile`)으로 재현했습니다.
실행 파일·DLL은 하나도 고치지 않았습니다.

| 스크립트 (`tools/re/`) | 하는 일 |
|---|---|
| `dump_meta.py` | 타입·필드·메서드 목록과 `#US` 문자열(코드 안 문자열 상수) 추출 |
| `cil_xref.py` | 메서드마다 IL을 훑어 `call`/`callvirt`/`newobj` 대상과 `ldstr` 문자열을 나열 — "누가 무엇을 부르나" 추적 |
| `validate.ps1` | 앱의 **진짜** `GameRuleSetLoader`(DFZ.Rules.dll)를 불러 룰셋 JSON을 검사 |
| `lint.ps1` | 앱의 **진짜** `WebGameLint`(DFZ.WebHost.dll)로 웹 게임 HTML을 검사 |

```bash
python3 -m pip install -r requirements.txt
python3 -I tools/re/dump_meta.py out reference/DigitalFitZone_Data/Managed/DFZ.UI.dll
python3 -I tools/re/cil_xref.py reference/DigitalFitZone_Data/Managed/DFZ.UI.dll out/il_UI.txt
```

뽑아 둔 결과는 `reference/meta/`에 있습니다 (`*.types.txt`, `*.strings.txt`, `il_*.txt`, dfz 통로 원문 `webhost_long_260.txt`, dfz.kit 스타일 `webhost_long_259.txt`).
분석에 쓴 DLL·룰셋 사본은 `reference/DigitalFitZone_Data/`에 있어 앱이 없는 맥에서도 다시 돌릴 수 있습니다.

## 3. 게임은 어떻게 불러오나

`GamePickerScreen.ScanInto`가 세 곳에서 게임을 모읍니다.

| 접두어 | 위치 | 비고 |
|---|---|---|
| `s:` 기본 게임 | `StreamingAssets/games/**/*.json` | 폴더를 통째로 훑어 룰셋이면 모두 목록에 올림 ← **새 게임을 넣는 가장 쉬운 길** |
| `c:` 받은 게임 | `Net.Cache.GameCache` | 포털 서명 키(`portal.signkey`)가 있어야 함 |
| `w:` 만든 웹 게임 | `persistentDataPath/vault` 안 `webgames/` | `EncryptedFileVault`로 암호화 — 「AI로 만들기」·「웹 게임 붙여넣기」 결과 |

게임 하나 = `ruleset.json` 하나. `flow.type`이 진행 방식을 정합니다:
`FreePlay`, `PromptSequence`(화면이 동작을 시킴), `Slice`(풍선), `Race`(스키), `Mugunghwa`, **`Web`**.

### `flow.type: "Web"` — 코드 수정 없이 새 게임을 넣는 공식 통로

- `flow.web.entry`: 룰셋 폴더 안 `web/<이름>.html` 하나만 허용 (URL·절대경로·`..` 불가)
- `flow.web.bridge`
  - `keys` — 참가자 동작을 키보드(←→↑↓·스페이스)로 바꿔 넣음. 점수는 앱이 동작마다 셈. 「웹 게임 붙여넣기」가 이 방식
  - `players` — **참가자별 입력·점수를 다루는 dfz SDK**. 「AI로 만들기」가 이 방식
- 앱(`SessionHud.WebGameHtml`)이 룰셋 폴더 + entry로 HTML을 읽어 `<head>` 뒤에 Preact·htm·`dfz.kit` 스타일·dfz 통로 스크립트를 붙인 뒤, `sandbox="allow-scripts"` iframe과 CSP(바깥 연결 전부 차단) 안에서 돌림

### dfz SDK (bridge: players) — DFZ.WebHost.dll에서 꺼낸 실제 규격

```js
dfz.ui.frame({ title, hint });           // 맨 먼저. 위 제목줄·아래 참가자 칸을 앱 모양으로 세움
dfz.on('ready',   cfg  => {});           // { seconds, minPlayers, maxPlayers, mode:'individual'|'teams'|'together', teams, actions, lang }
dfz.on('players', list => {});           // [{ seat, index, color, team }]  (join / leave 도 있음)
dfz.on('start',   ()   => {});
dfz.on('end',     ()   => {});           // 끝나면 앱이 순위 화면을 덮어 그림
dfz.on('input',   e    => {});           // { seat, index, action, x, y, strength }
dfz.score(seat, 점수);                    // 그 사람의 현재 총점(절댓값)을 알림
dfz.finish();                             // 일찍 끝내고 싶을 때
dfz.ui.stage / dfz.ui.canvas() / dfz.ui.toast(글, 색) / dfz.ui.status(seat, 글) / dfz.ui.hint(글)
dfz.kit: html, render, useState… (Preact+htm), fx, burst, confetti, cols
```

동작 이름(`DFZ.Core.Input.InputAction`): `Shake Tilt Jump Touch Raise Squat Move Press Release`
— 카메라는 몸 동작(Jump·Raise·Squat·Move), 폰·컨트롤러는 Shake·Tilt·Press·Touch 등.

**검사 규칙** (`WebGameLint` + `WebGameCheck`, 통과 못 하면 거절):
- `<!doctype html>`로 시작해 `</html>`로 끝나는 파일 하나, 바깥 주소·딸린 파일 금지(그림은 캔버스로)
- `fetch` `XMLHttpRequest` `WebSocket` `localStorage` `alert` `confirm` `prompt` `window.open` `iframe/form/input` 등 금지
- `dfz.ui.frame`, `dfz.on`, `dfz.score`가 꼭 있어야 함 / 키보드·마우스 입력 쓰지 않음
- 주석은 `/* */` (붙여 쓴 `//`는 주소로 읽힘)
- 화면 글자는 놀이판 높이의 5% 이상, 판 밖으로 넘치지 않기, 화면에 영어 동작 이름 금지
- 입력이 들어오면 1초 안에 눈에 보이는 반응, 놀이판이 비어 보이면 안 됨

## 3-1. 참가 기기와 기본 게임 목록

참가 기기는 세 가지입니다 (`inputs.deviceKinds`).

| 기기 | 내는 동작 | 연결 방식 |
|---|---|---|
| **카메라** | 몸 동작 — 점프·만세(Raise)·스쿼트·손 휘두르기(Move) | PC 카메라 + `DFZ.Vision` 자세 인식. 한 화면 최대 6명 |
| **스마트폰** | 흔들기·기울이기·화면 누르기(Touch/Press) | QR로 앱 안 LAN 폰 서버(`StreamingAssets/phone/index.html`)에 접속 |
| **전용 컨트롤러** | 흔들기·기울이기·단추·점프 | 같은 LAN 폰 서버로 들어옴. 관리자 메뉴 「컨트롤러 연결」에서 짝 맺기(`Net.Local.ControllerPairing`) — PC 인증서(`LocalLow\...\tls\lan-server.pfx`)로 확인하고, 인증서가 바뀌면 컨트롤러의 파란 단추로 다시 확인 |

**컨트롤러로 할 수 있는 게임** (설치본 `StreamingAssets/games` 기준)

| 폴더 | 제목 | 기기 | 동작 | 인원 | 진행 방식 |
|---|---|---|---|---|---|
| fire-brigade | 물 잇기 | 폰·컨트롤러 | 흔들기·기울이기 | 2~30 | PromptSequence |
| jump-relay (1min-solo) | 점프 잇기 · 혼자 | 폰·컨트롤러 | 점프·흔들기 | 1~30 | PromptSequence |
| jump-relay (3min-2team) | 점프 잇기 | 폰·컨트롤러 | 점프·흔들기 | 6~30 | PromptSequence (2팀) |
| power-charge | 번개 발전소 | 폰·컨트롤러 | 흔들기·기울이기 | 1~30 | PromptSequence |
| rhythm-wave | 파도 잇기 | 폰·컨트롤러·카메라 | 점프 | 2~30 | PromptSequence |
| tilt-ski | 눈보라 활강 | 폰·컨트롤러 | 기울이기·흔들기 | 1~12 | Race |
| tilt-ski-new | 눈보라 활강(NEW) | 폰·컨트롤러 | 기울이기·흔들기 | 1~12 | Race |

**카메라 전용 게임**: 물풍선 팡팡(동물·워터파크), 색깔 신호등, 번개 지령, 거울 나라, 무궁화 꽃이 피었습니다, 쉼 없이 1분, 천천히 오르기 — 모두 1~6명.
**스마트폰 전용**: 두더지 소동(누르기, 1~30명).

카메라 게임은 한 화면 6명이 한계인데, 폰·컨트롤러 게임은 최대 30명까지 받습니다. 그래서 반 전체가 함께하는 수업에는 컨트롤러 게임이 맞습니다.

## 4. 만든 게임 — 로켓 점프 (HTML로만 제공, 앱에는 설치하지 않음)

### 규칙
- **점프** → 내 로켓이 한 칸 오르고 불꽃·`+1`
- 8초 뒤부터 9~13초마다 **운석 경보**(2.4초) → 그 안에 **앉으면** 방패가 켜지고 2칸 더, 못 막으면 3칸 내려감
- 점수 = 로켓 높이. 60초가 지나면 꽃가루와 순위 화면
- 1~6명, 개인전. 지금 룰셋은 **카메라 전용**
- 게임 코드는 이미 `Jump`·`Shake`=점프, `Squat`·`Press`=앉기로 받도록 짜 두었으므로, 앱에 넣을 때 `ruleset.json`의 `deviceKinds`에 `Controller`(·`Phone`)를 더하고 `inputs`에 `Shake`·`Press`를 선언하면 컨트롤러 판으로도 쓸 수 있음 (컨트롤러 실기 테스트는 안 함)

### 파일

| 파일 | 용도 |
|---|---|
| **`dist/rocket-jump.html`** | **완성본 — 브라우저로 바로 여는 HTML 한 장** (약 28 KB, 인터넷·설치 불필요) |
| `games/rocket-jump/web/game.html` | 게임 본체. 앱의 웹 게임 규격(dfz SDK) 그대로 작성 |
| `games/rocket-jump/ruleset.json` | 나중에 앱에 넣을 때 쓸 룰셋 (지금은 쓰지 않음) |
| `tools/standalone_shim.html` | 앱 없이 돌게 하는 dfz 대역 — 앱 코드를 복사하지 않고 같은 이름의 기능을 새로 짬 |
| `tools/build_standalone.py` | `game.html` + 대역 → `dist/<이름>.html` |
| `tools/build_preview.py`, `tools/preview_shell.html` | 앱의 실제 통로·도구를 DLL에서 꺼내 붙인 검증용 미리보기 (`tools/out/`, 앱 코드 포함 — 바깥 공유 금지) |

### `dist/rocket-jump.html` 조작
- 시작 화면에서 인원(1~6명) 고르고 **스페이스** 또는 「시작」 → 3·2·1 뒤 출발
- **점프**: 숫자 `1`~`6` (그 자리) · **앉기**: `Q W E R T Y` · 화면 아래 칸의 단추로도 가능
- 끝나면 「다시 하기」

```
python3 -I tools/build_standalone.py games/rocket-jump/web/game.html   # game.html을 고친 뒤 다시 만들기
```

### 검증한 것
- 앱의 `GameRuleSetLoader`(DFZ.Rules.dll)로 룰셋 검사 → `IsValid=True`, `bridge=players`, `entry=web/game.html`
- 앱의 `WebGameLint`(DFZ.WebHost.dll)로 `game.html` 검사 → `Ok=True`, 문제 없음
- 앱의 통로를 붙인 미리보기에서 4인 한 판 → 점수 보고, 경보·방패·운석, 순위 화면, 오류 0건
- `dist/rocket-jump.html`을 브라우저에서 키 입력으로 60초 한 판 끝까지 → 시작 화면·카운트다운·점수·결과 화면 정상, 오류 0건

### 확인하지 못한 것
- 실제 앱 안에서 카메라로 돌려 보기 (앱에 넣지 않았으므로)

## 5. 나중에 앱에 넣으려면

`games/rocket-jump/` 폴더(룰셋 + `web/game.html`)를 그대로 Unity 프로젝트의 `Assets/StreamingAssets/games/rocket-jump/`에 넣고 빌드하면 「게임 선택」 목록에 기본 게임으로 올라옵니다. `dist/` 파일이 아니라 `game.html`을 넣어야 합니다 — 앱이 진짜 통로를 붙여 주기 때문입니다.

## 6. 주의

- `ruleSetId`(UUID)는 게임마다 달라야 합니다. 새 게임을 만들 때 새로 뽑으세요.
- `tools/out/`의 미리보기 파일에는 앱의 스크립트가 들어 있으니 바깥에 올리지 마세요. `dist/` 파일에는 앱 코드가 없습니다.
- 분석은 읽기만 했고 설치된 프로그램의 파일은 하나도 바꾸지 않았습니다.
