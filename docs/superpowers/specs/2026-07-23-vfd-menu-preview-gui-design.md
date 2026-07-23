# VFD 메뉴 미리보기 GUI — 디자인 스펙

- **날짜:** 2026-07-23
- **프로젝트:** Floppybird (`mn12832l-stm32-driver`)
- **상태:** 승인 대기

## 1. 목적

Floppybird(폴아웃 컨셉의 컨셉 전자기기)의 디스플레이는 MN12832L 128×32 VFD이며,
그 위에 **폴아웃 스타일 메뉴 시스템**이 돈다. 이 스펙은 그 메뉴 시스템을 개발하고
컴퓨터에서 시각적으로 미리보기/검증하기 위한 Tkinter 기반 GUI를 정의한다.

핵심 원칙: **치팅 없는 고증 렌더링.** 미리보기에 그려지는 모든 프레임은 기존 CLI
디지털 트윈과 동일한 `파이썬 → C → 파이썬` 라운드트립을 거쳐 검증된다.
`MvlsbRenderer.snapshot()`에서 캔버스로 직행하는 단축경로는 금지한다.

폴아웃 테마는 VFD 자체(진공관의 은은한 청록/녹색 빛, 레트로 감성)가 담당하므로,
GUI 창 자체는 테마 꾸미기를 하지 않고 깔끔한 미리보기 도구로 유지한다.

## 2. 범위

### 2.1 포함 (이 스펙)
- VFD 메뉴 시스템 모델 (순수 Python, VFD 독립)
- 4개 화면: BOOT, MAIN_MENU, MUSIC(자리), GAME(자리), SETTINGS(자리)
- Tkinter 미리보기 창 (768×192 캔버스 + 상태 표시)
- 하드웨어 입력 시뮬레이션: 버튼 4개 + 로터리 엔코더 1개(회전/클릭)
- 매 프레임 `DigitalTwinTransport` 라운드트립 검증
- 폰트: 기존 `GT20L_Font`/CLI 폰트 재사용

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
┌─ VfdDisplay + DigitalTwinTransport ──────────┐
│  display.present(frame)                      │
│    → 522B CRC 패킷                           │
│    → C vfd_host_link (검증+더블버퍼+43상 스캔)│
│    → 핀 trace → 재구성 프레임                 │
│    → result.matches_source 검증              │
└──────────────────┬───────────────────────────┘
                   │ reconstructed_frame
                   │ (matches_source=True일 때만)
                   ▼
┌─ Tkinter 캔버스 ──────────────────────────────┐
│  512B → 768×192 픽셀로 확대 그리기            │
│  + PASS/FAIL + 통계(clk/latches/events)       │
└───────────────────────────────────────────────┘
```

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
  │  • GpioSource(나중) │  나중: 진짜 물리 버튼
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

> **약속:** 메뉴가 "입력 생겼는지 물어볼 때마다" 입력 부품은 쌓아둔 InputEvent
> 들을 하나씩(또는 한 번에) 돌려준다. 없으면 비워둔다.

지금 구현할 부품:
- **TkinterSource** — 창의 마우스 버튼/다이얼 위젯을 InputEvent로 바꿔 줌.

나중에 추가할 부품 (이 스펙 범위 아님):
- **GpioSource** — 라즈베리파이 GPIO 핀을 읽어 같은 InputEvent로 바꿈.

메뉴 코드를 한 줄도 고치지 않고, TkinterSource 대신 GpioSource를 끼우면 끝이다.

### 4.2 메뉴 모델 (`mn12832l.menu.model`)

VFD/렌더링에 독립적인 순수 상태 기계. 각 화면은 자신의 입력 해석을 소유한다.

**화면:**
- `BOOT` — "FLOPPYBIRD OS v1.0" 부팅 화면. 약 2초 후 MAIN_MENU로 자동 전이.
  부팅 중 모든 입력은 무시한다.
- `MAIN_MENU` — `["MUSIC PLAYER", "MINI GAME", "SETTINGS"]` 리스트.
  엔코더 회전으로 스크롤, 엔코더 클릭(=SELECT)으로 진입.
- `MUSIC` — 자리만. 가짜 곡명 + 재생바. `BTN4`로 MAIN 복귀.
- `GAME` — 자리만. "COMING SOON" 표시. `BTN4`로 MAIN 복귀.
- `SETTINGS` — 자리만. 가짜 항목(밝기/대비). `BTN4`로 MAIN 복귀.

**인터페이스:**
```python
@dataclass
class Screen:
    kind: ScreenKind
    # 화면별 부가 데이터 (메뉴 인덱스, 곡명, 진행률 등)
    data: dict

class MenuModel:
    def handle_input(self, event: InputEvent) -> None: ...
    def tick(self, dt: float) -> None: ...        # 시간 기반 전이(부팅 타이머 등)
    def current_screen(self) -> Screen: ...
```

**버튼 매핑 정책:** 버튼 4개(`BTN1`~`BTN4`)의 역할은 모드마다 다르다. 이번
스펙에서는 매핑이 명확한 최소 세트만 정의한다:
- `ENCODER_CLICK` = SELECT (모든 화면에서 진입/확인)
- `BTN4` = BACK (하위 화면에서 MAIN_MENU로 복귀)
- `BTN1`~`BTN3`과 엔코더 회전의 구체적 역할은 각 화면/모드에서 나중에 매핑한다.
이 스펙은 입력 전달 체계와 두 개의 보편적 매핑만 보장하며, 나머지는 자유롭게
변경 가능하다.

### 4.3 렌더 레이어 (`mn12832l.menu.render`)

`Screen` 데이터를 `MvlsbRenderer`의 framebuffer에 그린다. 폰트는 기존
`GT20L_Font`(펌웨어) 또는 CLI 테스트가 쓰는 폰트를 재사용한다.

```python
def draw_screen(screen: Screen, renderer: MvlsbRenderer) -> bytes:
    renderer.clear()
    # screen.kind에 따라 framebuffer에 텍스트/바/박스 그림
    return renderer.snapshot()  # 512바이트 source_frame
```

### 4.4 검증 라운드트립 (`mn12832l.menu.presenter`)

`VfdDisplay` API를 그대로 사용하되 transport로 `DigitalTwinTransport`를 주입한다.
이렇게 하면 나중에 실기에서 `SubprocessTransport`로 교체하기만 하면 끝이다.

```python
display = VfdDisplay(DigitalTwinTransport(engine=...), renderer=renderer)
result = display.present(frame)
# result를 통해 twin 검증 결과(reconstructed_frame, matches_source, 통계)에 접근
```

`matches_source=False`이면 캔버스를 그리지 않고 에러 오버레이를 표시한다.
거짓 성공 화면은 금지.

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

**갱신 루프:** `root.after()` 기반 단일 루프, 약 20fps(50ms).
1. `model.tick(dt)` — 시간 기반 전이
2. `frame = draw_screen(model.current_screen(), renderer)`
3. `result = display.present(frame)` — C 라운드트립 검증
4. `matches_source=True`면 캔버스 갱신, 아니면 에러 표시
5. 상태 표시줄 갱신

**픽셀 그리기:** 512바이트를 순회하며 캔버스 사각형을 생성/이동. 매 프레임
전체 재생성 대신 차분 업데이트로 부드럽게(최적화, 선택적).

**실행:**
```sh
make menu PYTHON=.venv/bin/python
# 또는
PYTHONPATH=src .venv/bin/python -m mn12832l.menu
```

## 5. 에러 처리

- `matches_source=False` → 캔버스 빨간 오버레이 + 에러 메시지. 부팅 진행 안 함.
- C 엔진 실행 실패 → 예외 메시지 표시 + 루프 중단(계속 시도하지 않음).
- 잘못된 프레임 크기 → `present()`가 예외 발생.

## 6. 테스팅

메뉴 모델과 렌더 레이어는 Tkinter 없이 단위 테스트 가능해야 한다.
- `MenuModel` 상태 전이: 입력 시퀀스 → 예상 화면 (BOOT→MAIN→MUSIC 등)
- `draw_screen`: 각 화면 종류 → 512바이트 프레임이 `run_digital_twin`을 통과
- `matches_source` 검증이 모든 화면에서 참

GUI 자체(VfdDisplay + Tkinter)는 기존 `tests/python/test_twin.py` 패턴을
확장한 통합 테스트로, 각 화면을 렌더하고 twin이 PASS하는지 확인한다.

## 7. 파일 구조 (예정)

```
src/mn12832l/
├── menu/
│   ├── __init__.py
│   ├── input.py       # InputEvent + InputSource 약속 (교체 가능 베이스)
│   ├── model.py       # MenuModel, Screen (입력 부품 모름)
│   ├── render.py      # draw_screen()
│   ├── presenter.py   # VfdDisplay + DigitalTwinTransport 연결
│   ├── tk_source.py   # TkinterSource (오늘의 입력 부품)
│   └── app.py         # Tkinter 창 + 입력 루프
│   # (나중) gpio_source.py  # GpioSource — 메뉴 수정 없이 끼워넣기
├── __main__ 형태로 `python -m mn12832l.menu` 진입점
tests/python/
├── test_menu_model.py
├── test_menu_render.py
└── test_menu_input.py  # 가짜 InputSource로 메뉴 구동 (Tkinter 없이)
Makefile
└── menu 타깃 추가
```

## 8. 성공 기준

1. `python -m mn12832l.menu` 실행 시 Tkinter 창이 뜬다.
2. 버튼/엔코더로 BOOT → MAIN_MENU → 각 하위 화면을 탐색할 수 있다.
3. 매 프레임 `DIGITAL TWIN: PASS`가 뜬다 (치팅 없는 고증 경로).
4. 메뉴 모델 단위 테스트가 통과한다.
5. `make all`에 새 테스트가 포함되어 기존 게이트와 함께 통과한다.
6. **모듈 교체 가능성 검증:** 가짜 `InputSource`를 끼워 넣어 메뉴를 Tkinter
   없이 구동하는 테스트가 통과한다. 이는 나중에 `GpioSource` 교체가 메뉴
   수정 없이 됨을 보장한다.
