# MN12832L 라이브러리 분석·개선 결과

## 결론

제공된 STM32 코드는 GU128x32D/MN12832L 변환 보드의 2x5 헤더
(`SIN/CLK/LAT/BLK/SO1/SO2/HV/EF/GND/5V`)에 맞는 경로다. 반면 ZIP 안의
Arduino 라이브러리는 GCP를 사용하는 raw-panel 계열 참고 구현이라 현재
보드에 그대로 적용할 수 없다.

이번 개선은 원본을 건드리지 않고 STM32 경로를 **호스트에서 검증 가능한
드라이버 코어**로 정리했다. 다만 정확한 MCU 프로젝트와 실기 계측 자료가
없으므로 바로 플래시 가능한 완성 펌웨어나 전기적 안전성을 의미하지 않는다.

## 복원된 동작

1. 프레임버퍼는 `data[4][128]`이며 한 바이트가 세로 8픽셀을 나타낸다.
2. 한 스캔 상은 32행 × 6lane = 192 pixel bit를 먼저 보낸다.
3. 이어서 이웃한 두 grid를 선택하는 48bit를 보내 총 240bit가 된다.
4. 총 43상이며 마지막 상은 물리적으로 존재하는 126·127열만 사용하고
   가상의 128열(0-based)을 0으로 억제한다.
5. 홀수 상 lane 순서는 `b1,0,b2,0,b3,0`, 짝수 상은
   `0,b3,0,b2,0,b1`이다.
6. TIM14 이벤트마다 이전 shift-register 내용을 latch한 뒤 다음 상을
   bit-bang한다. 43번째 데이터 전송 뒤 기존과 같은 한 타이머 구간의 HV
   펄스를 유지한다.

## 원본에서 확인한 주요 결함과 처리

| 등급 | 원본 결함 | 처리 |
| --- | --- | --- |
| P0 | 최적화 시 빈 delay loop 네 개가 `ret`로 제거됨 | `vfd_delay.c`로 분리하고 Cortex-M0 `-O2` 어셈블리의 `nop`/back-edge를 검사 |
| P0 | ISR 공유 `ResetSCAN`이 non-volatile이고 check/clear race 존재 | volatile event와 PRIMASK 임계구역 take로 교체 |
| P0 | Error/HardFault 시 BLK·HV·EF 안전 상태가 보장되지 않음 | BLK high → HV low → EF low 순서의 공통 shutdown을 Error/NMI/HardFault에 연결 |
| P0 | GPIO 초기값에서 BLK도 low이고 PF0/PF1 preload가 없음 | 출력 전환 전에 BLK high, EF/HV low를 preload |
| P1 | 폰트 blit의 `y=32`가 `data[4]`를 접근 | 모든 API에 NULL/x/y 검사와 right/bottom clipping 적용, UBSan 회귀 테스트 추가 |
| P1 | 테스트한 scan packer와 실제 `main.c` 경로가 분리됨 | 실제 경로가 packer와 240bit emitter를 직접 사용하도록 연결 |
| P1 | 외부 font-ROM SPI 함수가 인자를 무시하고 non-void return도 없음 | 현재 보드 경로에서 제거; 불완전 중복 소스는 `legacy/unsupported`로 격리 |
| P1 | `font15x16` 선언은 4행, 정의는 5행 | `demo_fonts.h`의 단일 5행 선언으로 통합 |
| P1 | 테스트 바이너리의 헤더 의존성이 없어 stale 결과 가능 | Make prerequisite와 자동 dependency gate 추가 |

## 검증 범위

- 폰트: 정렬/비정렬/3-page/right-edge/bottom-edge/NULL, UBSan.
- 스캔: 43상 × 32행 × 모든 유효 source column lane property.
- 프레임: 240bit MSB-first 및 192bit 뒤 단일 gap callback.
- 상태: phase wrap, 마지막 두 열, HV 펄스 lifecycle.
- 보드 글루: fake HAL 기반 `-Werror` syntax build와 source contract.
- 지연: ARM Cortex-M0 `-O2` assembly gate.
- 정적분석: Clang analyzer, Semgrep, TruffleHog, diff whitespace.
- 보존: 원본 디렉터리의 SHA-256 11개 전부 재검증.

## 남은 차단 조건

다음 정보 없이는 실기 완료 판정을 내릴 수 없다.

- 정확한 STM32F0 부품명과 device define.
- 해당 버전의 HAL/CMSIS, startup assembly, linker script, programmer 설정.
- 보드 revision과 입력 로직 레벨/극성 자료.
- BLK/LAT/EF/HV 실제 파형과 네 empirical delay의 계측값.
- 장시간 구동 시 HV duty, refresh, 전원 전류, 발열 확인.

따라서 현재 완료 판정은 **소스 하드닝과 호스트 검증**에 한정한다.
