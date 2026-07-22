# 핀 레벨 디지털 트윈

## 한 문장 설명

실제 VFD 대신 가짜 핀을 연결하고, 펌웨어가 핀으로 내보낸 신호만 다시
조립해 터미널 화면에 그리는 테스트입니다.

```text
글자/그림
   ↓
Pillow/Adafruit → 512바이트 화면 버퍼
   ↓
VfdDisplay (중복 제거, sequence, CRC, retry)
   ↓
DigitalTwinTransport (실장 시 SubprocessTransport와 같은 FrameTransport 계약)
   ↓
522바이트 실제 전송 패킷
   ↓
실제 C VfdHostLink (검증, ACK/NACK, back buffer, 43→1 교체)
   ↓
실제 C 스캔 코드 (vfd_scan_pack_step + vfd_scan_emit_frame)
   ↓
가상 STM32 핀 (SIN, CLK, LAT, BLANK, EF, HV)
   ↓
가상 시프트 레지스터와 래치
   ↓
512바이트 역복원
   ↓
원본과 1비트씩 비교 → 터미널 TUI
```

즉, Python이 원본 그림을 그대로 출력하는 눈속임이 아니며 별도 데모 경로도
아닙니다. 실제 라즈베리파이 코드와 같은 `VfdDisplay`가 같은 패킷을 보내고,
실제 펌웨어 수신기와 버퍼 교체 및 스캔 코드가 만든 핀 신호를 해석했을 때만
화면을 표시합니다.

## 실장과 모의 테스트의 경계

| 계층 | 실제 디스플레이 | TUI 디지털 트윈 |
| --- | --- | --- |
| 모델·렌더·512바이트 버퍼 | 동일 | 동일 |
| `VfdDisplay` 상태/CRC/retry | 동일 | 동일 |
| `FrameTransport` 인터페이스 | 동일 | 동일 |
| 하위 어댑터 | serial bridge + UART/USB | `DigitalTwinTransport` + C pipe |
| STM32 패킷 수신/더블버퍼 | 실제 `VfdHostLink` | 같은 C `VfdHostLink` |
| 43단계 스캔/240비트 출력 | 실제 `vfd_scan` | 같은 C `vfd_scan` |
| 최종 출력 | GPIO와 VFD | 가상 핀 역복원과 TUI |

따라서 교체되는 부분은 하드웨어 경계 어댑터뿐입니다.

## 바로 실행하기

```sh
python3 -m venv .venv
.venv/bin/pip install -e .

# 읽기 쉬운 64×8 터미널 표현
make twin PYTHON=.venv/bin/python \
  TWIN_ARGS='--text "HELLO VFD" --compact --no-color'
```

라즈베리파이에 `clang`이 없고 `gcc`만 있다면 `HOST_CC=gcc`를 함께
지정하면 됩니다.

```sh
make twin HOST_CC=gcc PYTHON=.venv/bin/python TWIN_ARGS='--compact'
```

원래 픽셀 비율에 가까운 128×16 반블록 화면은 다음처럼 봅니다.

```sh
make twin PYTHON=.venv/bin/python TWIN_ARGS='--text "MN12832L"'
```

그림 파일도 넣을 수 있습니다. 그림은 비율을 유지한 채 128×32 안에 맞춰집니다.

```sh
make twin PYTHON=.venv/bin/python \
  TWIN_ARGS='--image ./logo.png --compact'
```

외곽선을 따라 점이 도는 로딩 모션도 볼 수 있습니다.

```sh
make twin PYTHON=.venv/bin/python \
  TWIN_ARGS='--border-loader --compact --frames 160 --fps 20'
```

기본 이동량은 프레임마다 4픽셀이며 `--step-pixels`로 바꿀 수 있습니다.
중앙의 `LOADING` 글자는
`src/mn12832l/assets/loading_wordmark.txt`에 있는 41×7 ASCII 아트입니다.
파일의 `#`은 켜진 픽셀, `.`은 꺼진 픽셀이며 2배로 확대해 화면 중앙에
그립니다. 같은 프레임에 외곽 혜성 점과 순환 스캔바를 합성합니다.
애니메이션도 원본 그림만 터미널에 반복 출력하는 방식이 아닙니다. C system
twin 프로세스와 `VfdHostLink` 상태는 실제 연결처럼 계속 유지됩니다. **매 프레임마다**
같은 `VfdDisplay.present()`가 522바이트 패킷을 보내고 ACK를 받은 뒤, 실제 C
더블버퍼에서 보이게 된 프레임으로 가상 핀 31,272개 이벤트를 생성합니다. 그
이벤트를 다시 복원·검증한 경우에만 터미널을 지워 다시 그립니다.

## 가상 핀 인터페이스

TUI 통합 테스트에서는 `tools/vfd_system_twin.c`가 패킷 수신부터 핀 출력까지
연결합니다. `tools/vfd_pin_twin.c`는 스캔 계층만 빠르게 검사하는 유닛 테스트용
도구로 남겨 둡니다. 두 도구는 같은 `tools/vfd_pin_trace.c`를 사용해 물리 GPIO
대신 다음 이벤트를 2바이트씩 기록합니다.

| 이벤트 | 실제 의미 | 검사 내용 |
| --- | --- | --- |
| `SIN` | 직렬 데이터 핀 | 클록 상승 순간의 0/1을 저장 |
| `CLK` | 시프트 클록 | 한 단계마다 정확히 한 번 상승하는지 검사 |
| `GAP` | 픽셀/그리드 경계 | 192번째 픽셀 비트 뒤인지 검사 |
| `LAT` | 출력 래치 | 240비트 뒤, 화면이 blank일 때만 허용 |
| `BLANK` | 화면 끄기 | 래치 도중 화면이 꺼져 있는지 검사 |
| `EF` | 컨버터/필라멘트 제어 | 종료 시 안전 레벨인지 검사 |
| `HV` | 고전압 펄스 제어 | 한 프레임 경계 펄스를 검사 |
| `PHASE` | 1~43 스캔 단계 | 순서와 개수를 검사 |

Python의 `decode_pin_trace()`는 가상 시프트 레지스터처럼 동작합니다. 각
단계의 192개 픽셀 비트와 48개 그리드 비트를 래치한 뒤, 홀수/짝수 단계의
배선 순서를 반대로 풀어 128×32 MVLSB 버퍼를 복원합니다.

## 테스트 레벨

- **유닛 테스트:** renderer의 MVLSB 변환, protocol CRC/ACK, C host-link,
  C scan packer, raw `vfd_pin_twin`의 핀 복원을 각각 독립 검증합니다.
- **통합 테스트:** `DigitalTwinTransport`가 지속 실행되는 C system twin과 같은
  522바이트 패킷을 주고받고, CRC 오류에는 NACK하며 stale 화면을 그리지 않는지
  검증합니다.
- **엔드투엔드 테스트:** `VfdDisplay.present()`에서 시작해 C 수신기, 실제
  더블버퍼 교체, 43단계 스캔, 31,272개 핀 이벤트, 역복원 TUI까지 비교합니다.

각 레벨은 따로 실행할 수 있습니다.

```sh
make test-twin-unit PYTHON=.venv/bin/python
make test-pin-twin PYTHON=.venv/bin/python
make test-system-twin PYTHON=.venv/bin/python
```

## PASS가 뜻하는 것

- 화면 버퍼 512바이트가 핀 신호 왕복 후 완전히 같습니다.
- 43단계 × 240비트 = 10,320번의 클록 상승이 있었습니다.
- 각 단계에 픽셀/그리드 경계와 blank 상태의 래치가 한 번씩 있습니다.
- 48개 그리드 선택 비트가 현재 단계와 이웃 단계만 선택합니다.
- 마지막에는 `BLANK=1`, `HV=0`, `EF=0`으로 안전 종료합니다.

## 아직 증명하지 못하는 것

이 테스트는 논리 신호 모델입니다. 다음은 실제 보드가 있어야 확인됩니다.

- GPIO 전압과 전류가 모듈에 안전한지
- 255ns/3us/13us/17us 지연이 실제 MCU와 배선에서 맞는지
- 고전압 및 필라멘트 회로의 극성과 듀티가 맞는지
- UART/USB 수신 인터럽트와 실제 전송 속도가 안정적인지
- 화면의 실제 밝기, 깜빡임, 잔상, 발열

따라서 `DIGITAL TWIN: PASS`는 **소프트웨어의 핀 순서와 화면 복원이
일치한다**는 뜻이며, 실제 하드웨어 연결이 안전하다는 뜻은 아닙니다.
