"""C 헤더와 Python 모듈 간 상수 일치 검증.

코드 리뷰 CODE_REVIEW_20260724_0850 §1.1~1.4 (P0):
프로토콜 매직/버전/커맨드/사이즈, 디스플레이 매직넘버, 핀 트레이스 이벤트 코드가
C 헤더와 Python 모듈에 독립적으로 정의되어 있다. 어느 한쪽만 바꾸면 통신/트윈이
조용히 깨지므로, 이 테스트는 양쪽 값의 일치를 헤더 파싱으로 검증한다.

기존 test_cross_language.py는 "실제 C 바이너리와 왕복 통신"을 검증하지만,
이 테스트는 "상수 정의 자체의 일치"를 검증한다 — 빌드 없이 헤더만 읽으므로
상수 불일치를 가장 빠르게 발견한다.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from mn12832l import protocol, twin

# 리포 루트 (tests/python/ → ../../..)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_FIRMWARE_DIR = _REPO_ROOT / "firmware" / "stm32f0"
_TOOLS_DIR = _REPO_ROOT / "tools"


def _parse_c_define(header_text: str, name: str) -> int:
    """C 헤더에서 `#define NAME value` 또는 `NAME = value,` 형태의 정수를 파싱."""
    # 줄연속(\) 처리
    text = re.sub(r"\\\s*\n\s*", " ", header_text)
    # #define NAME value
    m = re.search(rf"#define\s+{name}\s+(.+?)(?:\n|$)", text)
    if m:
        return _eval_c_int_expr(m.group(1).strip(), text)
    # enum: NAME = value,
    m = re.search(rf"\b{name}\s*=\s*([0-9xXa-fA-F]+)", text)
    if m:
        return int(m.group(1), 0)
    raise AssertionError(f"C 헤더에서 {name}을(를) 찾을 수 없음")


def _eval_c_int_expr(expr: str, header_text: str) -> int:
    """C 정수 산식을 평가. #define 매크로(단일 숫자 또는 다른 매크로 산식) 치환 허용."""
    # 모든 #define NAME <expression> 을 치환 테이블로 구성
    defines = {}
    for m in re.finditer(r"#define\s+(\w+)\s+(.+?)(?=\n[^\s\\]|\Z)", header_text, re.DOTALL):
        name, val = m.group(1), m.group(2).strip()
        val = re.sub(r"\s+\\\s*", " ", val)  # 줄연속 제거
        defines[name] = val
    # 재귀 치환 (최대 5단계 — C 헤더의 매크로 중첩 깊이)
    for _ in range(5):
        new_expr = expr
        for macro_name, macro_val in defines.items():
            if macro_name == expr.strip():
                continue  # 자기 자신 치환 방지
            new_expr = re.sub(rf"\b{macro_name}\b", f"({macro_val})", new_expr)
        if new_expr == expr:
            break
        expr = new_expr
    # u/U 접미어 제거 (16진수/10진수 모두)
    expr = re.sub(r"(0[xX][0-9a-fA-F]+|\d+)[uU]+", r"\1", expr)
    # 안전 검증: 정수와 사칙연산/괄호/공백만
    if not re.fullmatch(r"[\d\s+\-*/()xXa-fA-F]+", expr):
        raise AssertionError(f"복잡한 산식은 지원 안 함: {expr!r}")
    return int(eval(expr))


class CrossLangProtocolConstantsTests(unittest.TestCase):
    """§1.1: 프로토콜 매직/버전/커맨드/사이즈 상수."""

    @classmethod
    def setUpClass(cls) -> None:
        # host_link.h의 산식이 vfd_scan.h의 매크로(VFD_WIDTH 등)를 참조하므로
        # 두 헤더를 합쳐서 치환 테이블을 구성한다.
        cls.host_link_h = (_FIRMWARE_DIR / "vfd_host_link.h").read_text()
        cls.scan_h = (_FIRMWARE_DIR / "vfd_scan.h").read_text()
        cls._combined = cls.host_link_h + "\n" + cls.scan_h

    def _c(self, name: str) -> int:
        return _parse_c_define(self._combined, name)

    def test_magic_bytes(self) -> None:
        self.assertEqual(self._c("VFD_HOST_MAGIC_0"), protocol.MAGIC[0], "매직 바이트 0 불일치")
        self.assertEqual(self._c("VFD_HOST_MAGIC_1"), protocol.MAGIC[1], "매직 바이트 1 불일치")

    def test_protocol_version(self) -> None:
        self.assertEqual(self._c("VFD_HOST_PROTOCOL_VERSION"), protocol.PROTOCOL_VERSION, "프로토콜 버전 불일치")

    def test_frame_command(self) -> None:
        self.assertEqual(self._c("VFD_HOST_COMMAND_FRAME"), protocol.FRAME_COMMAND, "FRAME 커맨드 불일치")

    def test_ack_command(self) -> None:
        self.assertEqual(self._c("VFD_HOST_COMMAND_ACK"), protocol.ACK_COMMAND, "ACK 커맨드 불일치")

    def test_header_bytes(self) -> None:
        self.assertEqual(self._c("VFD_HOST_FRAME_HEADER_BYTES"), protocol.FRAME_HEADER_BYTES, "헤더 길이 불일치")

    def test_crc_bytes(self) -> None:
        self.assertEqual(self._c("VFD_HOST_CRC_BYTES"), protocol.CRC_BYTES, "CRC 길이 불일치")

    def test_ack_packet_bytes(self) -> None:
        self.assertEqual(self._c("VFD_HOST_ACK_PACKET_BYTES"), protocol.ACK_PACKET_BYTES, "ACK 패킷 길이 불일치")

    def test_frame_packet_bytes(self) -> None:
        self.assertEqual(self._c("VFD_HOST_FRAME_PACKET_BYTES"), protocol.FRAME_PACKET_BYTES, "FRAME 패킷 길이 불일치")

    def test_frame_bytes(self) -> None:
        self.assertEqual(self._c("VFD_HOST_FRAME_BYTES"), protocol.FRAME_BYTES, "프레임(페이로드) 길이 불일치")


class CrossLangAckStatusTests(unittest.TestCase):
    """§1.1: AckStatus enum 값 일치."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.host_link_h = (_FIRMWARE_DIR / "vfd_host_link.h").read_text()

    def _c_ack(self, name: str) -> int:
        m = re.search(rf"VFD_HOST_ACK_{name}\s*=\s*([0-9]+)", self.host_link_h)
        assert m is not None, f"C 헤더에 VFD_HOST_ACK_{name} 없음"
        return int(m.group(1))

    def test_ack_status_values(self) -> None:
        cases = [
            ("OK", protocol.AckStatus.OK),
            ("CRC_ERROR", protocol.AckStatus.CRC_ERROR),
            ("VERSION_ERROR", protocol.AckStatus.VERSION_ERROR),
            ("COMMAND_ERROR", protocol.AckStatus.COMMAND_ERROR),
            ("LENGTH_ERROR", protocol.AckStatus.LENGTH_ERROR),
            ("BUSY", protocol.AckStatus.BUSY),
        ]
        for c_name, py_status in cases:
            with self.subTest(status=c_name):
                self.assertEqual(
                    self._c_ack(c_name), int(py_status),
                    f"AckStatus.{c_name} 불일치 (C={self._c_ack(c_name)}, Py={int(py_status)})",
                )


class CrossLangDisplayGeometryTests(unittest.TestCase):
    """§1.2: 디스플레이 매직넘버 (128/32/4/43/192/48)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.scan_h = (_FIRMWARE_DIR / "vfd_scan.h").read_text()

    def test_width(self) -> None:
        self.assertEqual(_parse_c_define(self.scan_h, "VFD_WIDTH"), protocol.FRAME_WIDTH)

    def test_height(self) -> None:
        self.assertEqual(_parse_c_define(self.scan_h, "VFD_HEIGHT"), protocol.FRAME_HEIGHT)

    def test_page_count(self) -> None:
        # FRAME_BYTES = FRAME_WIDTH * FRAME_HEIGHT // 8 = WIDTH * PAGE_COUNT
        # → PAGE_COUNT = HEIGHT / 8
        self.assertEqual(_parse_c_define(self.scan_h, "VFD_PAGE_COUNT"), protocol.FRAME_HEIGHT // 8)

    def test_scan_phases(self) -> None:
        self.assertEqual(_parse_c_define(self.scan_h, "VFD_SCAN_PHASES"), twin.SCAN_PHASES)

    def test_pixel_bits_per_phase(self) -> None:
        self.assertEqual(
            _parse_c_define(self.scan_h, "VFD_PIXEL_BITS_PER_PHASE"), twin.PIXEL_BITS_PER_PHASE
        )

    def test_grid_bits_per_phase(self) -> None:
        self.assertEqual(
            _parse_c_define(self.scan_h, "VFD_GRID_BITS_PER_PHASE"), twin.GRID_BITS_PER_PHASE
        )


class CrossLangPinEventCodesTests(unittest.TestCase):
    """§1.4: 핀 트레이스 이벤트 코드 1~9 (C enum ↔ Python 상수)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.pin_trace_c = (_TOOLS_DIR / "vfd_pin_trace.c").read_text()

    def _c_event(self, name: str) -> int:
        m = re.search(rf"TWIN_EVENT_{name}\s*=\s*([0-9]+)", self.pin_trace_c)
        assert m is not None, f"C 헤더에 TWIN_EVENT_{name} 없음"
        return int(m.group(1))

    def test_pin_event_codes(self) -> None:
        cases = [
            ("PHASE", twin.EVENT_PHASE),
            ("SIN", twin.EVENT_SIN),
            ("CLK", twin.EVENT_CLK),
            ("GAP", twin.EVENT_GAP),
            ("BLANK", twin.EVENT_BLANK),
            ("LAT", twin.EVENT_LAT),
            ("EF", twin.EVENT_EF),
            ("HV", twin.EVENT_HV),
            ("END", twin.EVENT_END),
        ]
        for c_name, py_value in cases:
            with self.subTest(event=c_name):
                self.assertEqual(
                    self._c_event(c_name), py_value,
                    f"EVENT_{c_name} 불일치 (C={self._c_event(c_name)}, Py={py_value})",
                )


def _extract_c_trace_header(c_source: str) -> bytes | None:
    """C 소스에서 핀 트레이스 헤더(VFDTPIN1)를 추출.

    C 구현에 따라 헤더는 두 형태로 정의될 수 있다:
      1. 문자열 리터럴: ``"VFDTPIN1"``
      2. uint8_t 문자 배열: ``static const uint8_t header[8] = {
        'V', 'F', 'D', 'T', 'P', 'I', 'N', '1', };``

    어느 형태든 잡아내야 guard가 유효하다. 매칭 실패 시 None 반환.
    """
    # 1) 문자열 리터럴: "VFDTPIN1"
    m = re.search(r'"(VFDTPIN\d)"', c_source)
    if m:
        return m.group(1).encode("ascii")

    # 2) uint8_t 문자 배열: 식별자 'header'를 가진 배열 이니셜라이저에서
    #    연속된 문자 리터럴들을 추출. 임의의 다른 문자 리터럴에 오염되지
    #    않도록 배열 선언(header[N] = { ... }) 영역만 검사한다.
    m = re.search(
        r"\bheader\s*\[\s*\d*\s*\]\s*=\s*\{([^}]*)\}",
        c_source,
    )
    if m:
        body = m.group(1)
        chars = re.findall(r"'([ -~])'", body)  # ASCII 출력 문자 1개
        if chars:
            return "".join(chars).encode("ascii")

    return None


class CrossLangTraceHeaderTests(unittest.TestCase):
    """§1.4: 핀 트레이스 헤더 문자열 'VFDTPIN1'."""

    def test_trace_header(self) -> None:
        """C 헤더 정의가 반드시 발견·검증되어야 함 (거짓 통과 방지).

        이전에는 ``re.search(r'"(VFDTPIN\\d)"', ...)`` 가 문자열 리터럴만
        매칭했는데, C 헤더가 ``uint8_t header[8] = {'V','F',...}`` 문자 배열로
        정의된 경우 매칭이 안 되어 ``if m:`` 블록을 건너뛰고 조용히 통과했다.
        이제 헤더 추출이 None이면 명시적으로 실패하여 guard가 실제로
        동작함을 보장한다.
        """
        pin_trace_c = (_TOOLS_DIR / "vfd_pin_trace.c").read_text()
        # C 헤더는 문자열 리터럴("VFDTPIN1") 또는 uint8_t 문자 배열
        # ('V','F',...) 어느 형태든 추출해야 함. 매칭 실패 시 거짓 통과가
        # 되므로 명시적으로 실패한다.
        c_header = _extract_c_trace_header(pin_trace_c)
        self.assertIsNotNone(
            c_header,
            "C 핀 트레이스 헤더 정의를 찾을 수 없음 — guard가 아무것도 검증하지 않음",
        )
        assert c_header is not None  # 타입 좁히기 (mypy)
        self.assertEqual(
            c_header, twin.TRACE_HEADER,
            f"핀 트레이스 헤더 불일치 (C={c_header!r}, Py={twin.TRACE_HEADER!r})",
        )


if __name__ == "__main__":
    unittest.main()
