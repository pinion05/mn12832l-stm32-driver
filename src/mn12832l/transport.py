"""Persistent process transport for a serial/USB bridge CLI."""

from __future__ import annotations

import os
import select
import subprocess
import threading
import time
from typing import Optional, Sequence, Union

from .protocol import ACK_PACKET_BYTES


CommandPart = Union[str, os.PathLike]


class TransportError(RuntimeError):
    """Base error for transport lifecycle or I/O failures."""


class TransportClosedError(TransportError):
    """Raised when an operation requires an open child process."""


class TransportTimeoutError(TransportError):
    """Raised when the bridge does not return an ACK in time."""


class SubprocessTransport:
    """Exchange packets with one persistent child process using binary pipes."""

    def __init__(
        self, command: Sequence[CommandPart], timeout: float = 1.0
    ) -> None:
        if not command:
            raise ValueError("command must not be empty")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        self._command = tuple(os.fspath(part) for part in command)
        self._timeout = float(timeout)
        self._process: Optional[subprocess.Popen[bytes]] = None
        self._lock = threading.Lock()

    @property
    def pid(self) -> int:
        process = self._require_open()
        return process.pid

    def open(self) -> None:
        """Start the bridge once; repeated calls are idempotent."""

        with self._lock:
            if self._process is not None and self._process.poll() is None:
                return
            self._process = subprocess.Popen(
                self._command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=None,
                bufsize=0,
                shell=False,
            )

    def request(self, packet: bytes) -> bytes:
        """Write one frame packet and read exactly one fixed-size ACK."""

        with self._lock:
            process = self._require_open()
            if process.stdin is None or process.stdout is None:
                raise TransportError("bridge pipes are unavailable")
            try:
                self._write_all(process.stdin.fileno(), packet)
            except (BrokenPipeError, OSError) as error:
                raise TransportError("failed to write to bridge") from error
            return self._read_response(process, packet)

    def close(self) -> None:
        """Close stdin and stop the persistent bridge process."""

        with self._lock:
            process = self._process
            self._process = None
            if process is None:
                return
            if process.stdin is not None:
                try:
                    process.stdin.close()
                except OSError:
                    pass
            try:
                process.wait(timeout=self._timeout)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=self._timeout)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            if process.stdout is not None:
                process.stdout.close()

    def _require_open(self) -> subprocess.Popen[bytes]:
        process = self._process
        if process is None or process.poll() is not None:
            raise TransportClosedError("transport is not open")
        return process

    def _read_response(
        self, process: subprocess.Popen[bytes], packet: bytes
    ) -> bytes:
        """Read the standard ACK response for one transmitted packet."""

        del packet
        return self._read_exact(process, ACK_PACKET_BYTES)

    def _read_exact(
        self, process: subprocess.Popen[bytes], size: int
    ) -> bytes:
        if process.stdout is None:
            raise TransportError("bridge stdout is unavailable")

        output = bytearray()
        deadline = time.monotonic() + self._timeout
        descriptor = process.stdout.fileno()
        while len(output) < size:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TransportTimeoutError("timed out waiting for bridge ACK")
            readable, _, _ = select.select([descriptor], [], [], remaining)
            if not readable:
                raise TransportTimeoutError("timed out waiting for bridge ACK")
            chunk = os.read(descriptor, size - len(output))
            if not chunk:
                raise TransportError("bridge exited before returning a full ACK")
            output.extend(chunk)
        return bytes(output)

    @staticmethod
    def _write_all(descriptor: int, packet: bytes) -> None:
        remaining = memoryview(packet)
        while remaining:
            written = os.write(descriptor, remaining)
            if written == 0:
                raise BrokenPipeError("bridge accepted zero bytes")
            remaining = remaining[written:]
