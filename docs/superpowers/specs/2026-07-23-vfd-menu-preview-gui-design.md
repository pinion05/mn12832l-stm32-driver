# VFD 메뉴 미리보기 GUI — 디자인 스펙

- **날짜:** 2026-07-23 (2026-07-24 서브에이전트 검증 후 전면 수정)
- **프로젝트:** Floppybird (`mn12832l-stm32-driver`)
- **상태:** 승인 대기

## 1. 목적

Floppybird(폴아웃 컨셉의 컨셉 전자기기)의 디스플레이는 MN12832L 128×32 VFD이며,
그 위에 **폴아웃 스타일 메뉴 시스템**이 돈다. 이 스펙은 그 메뉴 시스템을 개발하고
컴퓨터에서 시각적으로 미리보기/검증하기 위한 Tkinter 기반 GUI를 정의한다.

핵심 원칙: **치팅 없는 고증 렌더링.** 미리보기에 그려지는 **새로운 프레임**은 기존
CLI 디지털 트윈과 동일한 `파이썬 → C → 파이썬` 라운드트립을 거쳐 검증된다.
`MvlsbRenderer.snapshot()`에서 캔버스로 직행하는 단축경로는 금지한다.

**검증 시점의 정확한 정의 (서브에이전트 검증 반영):** "매 프레임" 검증이 아니다.
기존 `VfdDisplay.present()`는 **직전 프레임과 동일한 프레임은 transport를 부르지
않고 스킵**한다(display.py dedup). 그러므로 검증은 **"화면 내용이 바뀔 때마다"**
일어난다. 정지 화면(같은 프레임 반복)은 재검증하지 않으며, 직전에 검증 통과한
프레임을 그대로 유지한다. 이는 기존 트윈의 동작과 일관되며 합리적이다.

폴아웃 테마는 VFD 자체(진공관의 은은한 청록/녹색 빛, 레트로 감성)가 담당하므로,
GUI 창 자체는 테마 꾸미기를 하지 않고 깔끔한 미리보기 도구로 유지한다.

## 2. 범위

### 2.1 포함 (이 스펙)
- VFD 메뉴 시스템 모델 (순수 Python, VFD 독립)
- **5개 화면**: BOOT, MAIN_MENU, MUSIC(자리), GAME(자리), SETTINGS(자리)
- Tkinter 미리보기 창 (768×192 캔버스 + 상태 표시)
- 하드웨어 입력 시뮬레이션: 버튼 4개 + 로터리 엔코더 1개(회전/클릭)
- **화면이 바뀔 때마다** `DigitalTwinTransport` 라운드트립 검증 (위 참고)
- 폰트: **Pillow 기본 폰트** (`ImageFont.load_default()`) — 기존 `twin._render_demo`가
  쓰는 것과 동일. (펌웨어의 C 자산 `GT20L_Font`는 Python에서 사용 불가하므로 제외)

### 2.2 제외 (이후 스펙)
- 실기 전송 (친구가 디스플레이를 돌려줄 때)
- 미니게임/음악 플레이어의 실제 구현 (지금은 자리만)
- 한글 폰트 (TTF 교체는 나중)
- 폴아웃 테마 창 꾸미기
- 물리 버튼/엔코더의 실제 GPIO 매핑 (이건 시뮬레이션만)

## 3. 아키텍처

```
┌─ 입력 부품 (교체 가능) ──────────────────────┐
│  InputSource 약속                            │
│  • 지금: TkinterSource (마우스 버튼/다이얼)   │
│  • 나중: GpioSource (진짜 물리 버튼)          │
│        ↓ 메뉴는 어느 쪽인지 모름              │
│  → InputEvent(BTN1..4, ENCODER_ROTATE±,      │
│               ENCODER_CLICK)                 │
└──────────────────┬───────────────────────────┘
                   │ InputEvent (공통 약속)
                   ▼
┌─ 메뉴 모델 (순수 Python) ─────────────────────┐
│  MenuModel                                   │
│    .handle_input(event) → 상태 전이           │
│    .current_screen() → Screen 데이터          │
└──────────────────┬───────────────────────────┘
                   │ Screen
                   ▼
┌─ 렌더 레이어 ─────────────────────────────────┐
│  draw_screen(screen, framebuffer)            │
│  → MvlsbRenderer.snapshot() = 512바이트       │
└──────────────────┬───────────────────────────┘
                   │ source_frame (512B)
                   ▼
┌─ VfdDisplay.present(frame) ──────────────────┐
│  • 직전 프레임과 같으면 스킵 (dedup)          │
│    → transport 안 부름, 캔버스 유지           │
│  • 다르면 transport.request(packet) 호출      │
└──────────────────┬───────────────────────────┘
                   │ (프레임이 바뀐 경우만)
                   ▼
┌─ DigitalTwinTransport (C 라운드트립) ─────────┐
│  → 522B CRC 패킷                              │
│  → C vfd_host_link (검증+더블버퍼+43상 스캔)  │
│  → 핀 trace → decode_pin_trace                │
│    • 재구성 프레임이 source와 다르면          │
│      DigitalTwinError raise                   │
│    • 같으면 transport.last_result 갱신        │
└──────────────────┬───────────────────────────┘
                   │ 캔버스는 다음 두 가지로 갱신:
                   │ 1) present()가 보냈으면 → last_result 사용
                   │ 2) 스킵됐으면 → 직전 결과 재사용
                   ▼
┌─ Tkinter 캔버스 ──────────────────────────────┐
│  512B → 768×192 픽셀로 확대 그리기            │
│  + PASS/FAIL + 통계(clk/latches/events)       │
└───────────────────────────────────────────────┘
```

**검증 결과 접근 (서브에이전트 검증 반영):** `VfdDisplay.present()`는
`PresentResult(sent, sequence, attempts)`만 반환한다. twin 검증 결과는
`DigitalTwinTransport`의 **`last_result` 프로퍼티로 따로 받아야** 한다
(기존 `twin.py`의 사용 패턴과 동일).

## 4. 컴포넌트 상세

### 4.1 입력 레이어 (`mn12832l.menu.input`)

**설계 원칙: 모듈 교체 가능.** 메뉴는 "누가 입력을 보냈는지" 모른다. Tkinter
마우스 버튼이든, 나중의 라즈베리파이 GPIO 물리 버튼이든, 똑같이 작동해야 한다.
이를 위해 둘 사이의 약속(인터페이스)을 하나만 정해두고, 그 약속을 지키는
"입력 부품(Source)"은 자유롭게 교체한다.

```
┌─ 메뉴 ──────────┐
│  InputEvent 받음│  ← "누가 보냈는지" 관심 없음
└────────┬────────┘
         │ InputEvent (공통 약속)
         ▲
         │ 교체 가능 — 메뉴 수정 없이 갈아끼움
         │
  ┌──────┴──────────────┐
  │  InputSource        │  ← 이것만 바꾸면 됨
  │                     │
  │  • TkinterSource    │  지금: 컴퓨터 마우스 버튼
  │  • GpioSource(나중) │  나중: 진자 물리 버튼
  └─────────────────────┘
```

#### 4.1.1 공통 약속: InputEvent

입력 부품이 메뉴에 보내는 신호의 형태. 기술(Tkinter? GPIO?)에 종속되지 않는
순수 데이터. 누가 어떻게 만들었든 이 형태만 맞으면 된다.

- `BTN1`, `BTN2`, `BTN3`, `BTN4` — 버튼 4개 각각의 "눌림"
- `ENCODER_ROTATE_CW` — 다이얼을 시계 방향으로 한 단계 돌림
- `ENCODER_ROTATE_CCW` — 다이얼을 반시계 방향으로 한 단계 돌림
- `ENCODER_CLICK` — 다이얼 누름 (대부분의 화면에서 SELECT 역할)

#### 4.1.2 교체 가능한 부품: InputSource

모든 입력 부품이 지켜야 할 약속. 메뉴는 이것만 보고 입력을 받는다.

> **약속 (poll 기반):** 메뉴가 "입력 생겼는지 물어볼 때마다(poll)" 입력 부품은
> 쌓아둔 InputEvent 들을 순서대로 돌려준다. 없으면 비워둔다.

**Poll vs 이벤트 간극 (서브에이전트 검증 반영):** Tkinter는 본질적으로
이벤트/콜백 기반이다(`command=`, `<Button-1>` 바인딩). 그러므로 `TkinterSource`는
내부적으로 **큐**를 두어야 한다: 콜백에서 큐에 push, `poll()`에서 drain.
빠른 더블클릭이 한 프레임에 몰아 들어올 때 순서가 보존되도록 FIFO 큐를 쓴다.
이 내부 큐 구조는 `TkinterSource` 구현 세부이며, 메뉴나 다른 부품은 모른다.

지금 구현할 부품:
- **TkinterSource** — 창의 마우스 버튼/다이얼 위젯을 InputEvent로 바꿔 줌.
  내부 FIFO 큐 보유.

나중에 추가할 부품 (이 스펙 범위 아님):
- **GpioSource** — 라즈베리파이 GPIO 핀을 읽어 같은 InputEvent로 바꿈.

메뉴 코드를 한 줄도 고치지 않고, TkinterSource 대신 GpioSource를 끼우면 끝이다.

### 4.2 메뉴 모델 (`mn12832l.menu.model`)

VFD/렌더링에 독립적인 순수 상태 기계. 각 화면은 자신의 입력 해석을 소유한다.

#### 4.2.1 화면 전이도

```
                 (자동, 2.0초)
    BOOT ──────────────────────► MAIN_MENU ◄────────────┐
                                   │ ▲                  │
                  ENCODER_CLICK    │ │ BTN4 (뒤로)      │
                 (선택한 항목 진입) │ │                  │
                                   ▼ │                  │
                              ┌──────┴──────┬───────────┴──┐
                              ▼             ▼              ▼
                            MUSIC         GAME          SETTINGS
                          (자리만)      (자리만)        (자리만)
```

- BOOT → MAIN_MENU: 시간 기반 자동 전이 (정확히 2.0초 후).
- MAIN_MENU → {MUSIC, GAME, SETTINGS}: `ENCODER_CLICK`으로 현재 선택 항목 진입.
- {MUSIC, GAME, SETTINGS} → MAIN_MENU: `BTN4`(뒤로)로 복귀.
- MAIN_MENU 내 이동: `ENCODER_ROTATE_CW` = 다음 항목(+1),
  `ENCODER_ROTATE_CCW` = 이전 항목(-1). **랩어라운드** (끝→처음, 처음→끝).
  엔코더 1단계 = 인덱스 1칸 이동 (가속/누적 없음).

#### 4.2.2 화면 정의

- `BOOT` — "FLOPPYBIRD OS v1.0" 부팅 화면. **정확히 2.0초** 후 MAIN_MENU로 자동
  전이. 부팅 중 모든 입력은 무시한다.
- `MAIN_MENU` — `["MUSIC PLAYER", "MINI GAME", "SETTINGS"]` 리스트. 현재 선택
  항목은 `▶` 표시. 3개 항목 모두 한 화면에 표시.
- `MUSIC` — 자리만. 화면 상단에 "NOW PLAYING", 중앙에 가짜 곡명 "TRACK 01",
  하단에 재생바(정적) 표시.
- `GAME` — 자리만. 화면 중앙에 "COMING SOON" 표시.
- `SETTINGS` — 자리만. 가짜 항목 2개: "BRIGHTNESS"와 "CONTRAST" 각각에 현재값
  표시 (예: "BRIGHTNESS 50%"). 2줄로 표시.

**버튼 매핑 정책:** 버튼 4개(`BTN1`~`BTN4`)의 역할은 모드마다 다르다. 이번
스펙에서는 매핑이 명확한 최소 세트만 정의한다:
- `ENCODER_CLICK` = SELECT (모든 화면에서 진입/확인)
- `BTN4` = BACK (하위 화면에서 MAIN_MENU로 복귀)
- `BTN1`~`BTN3`과 엔코더 회전의 구체적 역할은 각 화면/모드에서 나중에 매핑한다.
이 스펙은 입력 전달 체계와 두 개의 보편적 매핑만 보장하며, 나머지는 자유롭게
변경 가능하다.

#### 4.2.3 인터페이스

```python
class MenuModel:
    def handle_input(self, event: InputEvent) -> None: ...
    def tick(self, dt: float) -> None: ...        # 시간 기반 전이(부팅 타이머)
    def current_screen(self) -> Screen: ...
```

### 4.3 렌더 레이어 (`mn12832l.menu.render`)

`Screen` 데이터를 `MvlsbRenderer`의 framebuffer에 그린다. 폰트는 기존
`twin._render_demo`가 쓰는 **Pillow 기본 폰트**(`ImageFont.load_default()`)를
재사용한다. 펌웨어의 C 자산 `GT20L_Font`는 Python에서 사용할 수 없으므로 제외한다.

```python
def draw_screen(screen: Screen, renderer: MvlsbRenderer) -> bytes:
    renderer.clear()
    # screen.kind에 따라 framebuffer에 텍스트/바/박스 그림 (Pillow 기본 폰트)
    return renderer.snapshot()  # 512바이트 source_frame
```

**자리만 화면의 레이아웃 (deterministic, 테스트 가능):**
- MUSIC: y=0 "NOW PLAYING" / y=12 "TRACK 01" / y=24 재생바(가로선 + 채워진 부분 50%)
- GAME: y=12 (중앙) "COMING SOON"
- SETTINGS: y=0 "BRIGHTNESS 50%" / y=12 "CONTRAST 50%"
좌표 x는 왼쪽 정렬 x=0. 이 고정 레이아웃은 회귀 테스트의 golden frame 기준이 된다.

### 4.4 검증 라운드트립 (`mn12832l.menu.presenter`)

`VfdDisplay` API를 그대로 사용하되 transport로 `DigitalTwinTransport`를 주입한다.
이렇게 하면 나중에 실기에서 `SubprocessTransport`로 교체하기만 하면 끝이다.

```python
transport = DigitalTwinTransport(command=[...])
display = VfdDisplay(transport, renderer=renderer)
display.open()
present_result = display.present(frame)   # PresentResult(sent, sequence, attempts)
twin_result = transport.last_result        # DigitalTwinResult | None (따로 받음)
```

**검증 결과 접근 (서브에이전트 검증 반영):** twin 결과는 `present()` 반환값이
**아니라** `transport.last_result`로 따로 받는다. 두 가지 경우:
1. `present_result.sent == True` (프레임이 바뀌어 transport가 호출됨):
   `twin_result`는 이번 프레임의 검증 결과.
2. `present_result.sent == False` (dedup로 스킵됨): `twin_result`는 직전에
   검증된 결과 그대로 (또는 최초 프레임 전에는 `None`).

### 4.5 Tkinter 창 (`mn12832l.menu.app`)

**레이아웃:**
```
┌─ Floppybird Menu Preview ─────────────────────┐
│  ┌──────────────────────────────────────┐     │
│  │   (768×192 캔버스, 128×32 × 6배)      │     │
│  │   ▶ MUSIC PLAYER                     │     │
│  │     MINI GAME                        │     │
│  └──────────────────────────────────────┘     │
│  ┌─ TWIN STATUS ────────────────────┐         │
│  │ DIGITAL TWIN: PASS               │         │
│  │ PHASE 43 | CLK↑ 10320 | LAT↑ 43  │         │
│  └───────────────────────────────────┘         │
│  [BTN1] [BTN2] [BTN3] [BTN4]                   │
│  [-] ENCODER: sel=0 [+][CLICK]                 │
│  Screen: MAIN_MENU                             │
└────────────────────────────────────────────────┘
```

**입력:** 키보드 입력을 받지 않는다. 오직 `TkinterSource`(창의 마우스 버튼/엔코더
위젯)가 InputEvent를 만들어 메뉴에 보낸다. 이것은 실제 물리 버튼을 시뮬레이션하는
`InputSource` 약속의 첫 구현체이며, 나중에 `GpioSource`로 교체 가능하다 (4.1 참고).

**갱신 루프:** `root.after()` 기반 단일 루프, 약 20fps(50ms). 한 틱마다:
1. **입력 소비 (서브에이전트 검증 반영):** `for event in source.poll():`
   `model.handle_input(event)` — 이 폴링 단계가 명시적으로 있어야 한다.
2. `model.tick(dt)` — 시간 기반 전이 (BOOT 2.0초 타이머 등)
3. `frame = draw_screen(model.current_screen(), renderer)`
4. `present_result = display.present(frame)`
5. **검증/캔버스 갱신:**
   - `present_result.sent`가 True → `twin_result = transport.last_result`로
     결과 갱신 후 캔버스 그림.
   - `present_result.sent`가 False → 직전 프레임 그대로, 직전 twin 결과 표시 유지.
6. 상태 표시줄 갱신

**BOOT 타이머와 검증 실패의 관계 (서브에이전트 검증 반영):** BOOT 화면의 2.0초
타이머는 `model.tick(dt)`에서 돈다. 만약 BOOT 프레임을 그리는 중 C 라운드트립에서
`DigitalTwinError`가 발생하면, **타이머는 멈추지 않고 계속 흐른다** — 즉 2.0초가
지나면 BOOT 화면이 검증 실패 상태여도 MAIN_MENU로 넘어간다. 단, 실패한 BOOT
프레임은 캔버스에 그려지지 않고 에러 오버레이가 표시된다. "부팅 진행을 막는
무한 대기"는 발생하지 않는다.

**픽셀 그리기:** 512바이트를 순회하며 캔버스 사각형을 생성/이동. 매 프레임
전체 재생성 대신 차분 업데이트로 부드럽게(최적화, 선택적).

**창 닫기/종료 (서브에이전트 검증 반영):** 창 X 버튼 또는 `WM_DELETE_WINDOW`
프로토콜 → `root.after()` 루프 중단 → `display.close()`로 C 서브프로세스
종료 → `root.destroy()`. `Ctrl-C`는 Tkinter 기본 처리에 맡긴다.

**실행:**
```sh
make menu PYTHON=.venv/bin/python
# 또는
PYTHONPATH=src .venv/bin/python -m mn12832l.menu
```

## 5. 에러 처리 (서브에이전트 검증 반영)

**핵심 교정:** 기존 스펙은 "`matches_source=False`면 빨간 오버레이"라고 했으나,
이는 실제 동작과 다르다. `decode_pin_trace`는 재구성 프레임이 source와 다르면
**`DigitalTwinError`를 raise**한다. 즉 "검증 실패"는 조용한 False 상태가 아니라
**예외**다. 그러므로 에러 UX는 예외 처리로 설계한다.

- C 라운드트립 중 `DigitalTwinError`(또는 상위 `TransportError`/`DisplayError`)
  발생 → 캔버스에 빨간 오버레이 + 에러 메시지. 다음 틱에서 재시도(새 프레임이면).
- `FrameRejectedError`(MCU가 BUSY/CRC 외 상태로 거부) → 같은 빨간 오버레이.
- 잘못된 프레임 크기 → `present()`가 `ValueError` 발생 → 프로그래밍 버그로 간주,
  루프 중단.
- C 엔진 실행 자체 실패(파일 없음 등) → 예외 메시지 표시 + 루프 중단(재시도 안 함).

`matches_source` 프로퍼티 자체는 informational(상태 표시줄 통계용)으로만 쓰고,
제어 흐름의 분기 조건으로는 쓰지 않는다.

## 6. 테스팅

메뉴 모델과 렌더 레이어는 Tkinter 없이 단위 테스트 가능해야 한다.
- `MenuModel` 상태 전이: 입력 시퀀스 → 예상 화면 (BOOT→MAIN→MUSIC 등).
  엔코더 회전 ↔ 인덱스 매핑, 랩어라운드도 검증.
- `draw_screen`: 각 화면 종류 → 512바이트 프레임. 자리만 화면은 4.3의 고정
  레이아웃과 일치하는지 golden frame 비교.
- presenter: 각 화면 프레임이 `run_digital_twin`(또는 transport)을 통과.
- **모듈 교체 검증 (성공 기준 6):** 가짜 `InputSource`(이벤트 리스트를 순서대로
  내뱉는)를 끼워 메뉴를 Tkinter 없이 구동, 예상 화면 전이가 일어나는지 확인.

GUI 자체(VfdDisplay + Tkinter)는 기존 `tests/python/test_twin.py` 패턴을
확장한 통합 테스트로, 각 화면을 렌더하고 twin이 PASS하는지 확인한다.

## 7. 파일 구조 (예정)

```
src/mn12832l/
├── menu/
│   ├── __init__.py
│   ├── input.py       # InputEvent + InputSource 약속 (교체 가능 베이스)
│   ├── model.py       # MenuModel, Screen (입력 부품 모름)
│   ├── render.py      # draw_screen() — Pillow 기본 폰트
│   ├── presenter.py   # VfdDisplay + DigitalTwinTransport 연결
│   ├── tk_source.py   # TkinterSource (오늘의 입력 부품, 내부 FIFO 큐)
│   ├── app.py         # Tkinter 창 + 입력 루프
│   └── __main__.py    # python -m mn12832l.menu 진입점
│   # (나중) gpio_source.py  # GpioSource — 메뉴 수정 없이 끼워넣기
tests/python/
├── test_menu_model.py     # 상태 전이, 엔코더 매핑, 랩어라운드
├── test_menu_render.py    # 각 화면 golden frame
├── test_menu_input.py     # 가짜 InputSource로 메뉴 구동 (Tkinter 없이)
└── test_menu_presenter.py # 각 화면 twin PASS
Makefile
└── menu 타깃 추가
```

## 8. 성공 기준

1. `python -m mn12832l.menu` 실행 시 Tkinter 창이 뜬다.
2. 버튼/엔코더로 BOOT(2.0초) → MAIN_MENU → MUSIC/GAME/SETTINGS(각각 BTN4로 복귀)
   전이가 일어난다. 엔코더 회전 1단계 = 인덱스 1칸(랩어라운드).
3. 화면이 바뀔 때마다 `DIGITAL TWIN: PASS`가 뜬다 (치팅 없는 고증 경로).
   정지 화면은 직전 결과 유지 (매 프레임 재검증 아님 — 1절 참고).
4. 메뉴 모델 단위 테스트가 통과한다 (전이, 엔코더 매핑, 랩어라운드, 자리 화면
   golden frame).
5. `make all`에 새 테스트가 포함되어 기존 게이트와 함께 통과한다.
6. **모듈 교체 가능성 검증:** 가짜 `InputSource`를 끼워 넣어 메뉴를 Tkinter
   없이 구동하는 테스트가 통과한다. 이는 나중에 `GpioSource` 교체가 메뉴
   수정 없이 됨을 보장한다.
