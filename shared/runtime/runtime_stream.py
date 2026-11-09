import asyncio
import json
import logging
import struct
from collections.abc import AsyncIterator
from typing import Any, Final

import aiohttp

from .runtime_errors import RuntimeClientError, StreamTruncatedError

logger: Final = logging.getLogger("runtime.stream")

_STREAM_DROPS: Final = (
    aiohttp.ClientPayloadError,
    aiohttp.ClientConnectionError,
    ConnectionError,
)


async def demultiplex_stream(
    reader: aiohttp.StreamReader,
    is_tty: bool = False,
) -> AsyncIterator[tuple[int, bytes]]:
    """
    Demultiplex an engine stream (logs or exec output).
    Yields (stream_type, chunk_bytes) where:
      0: stdin
      1: stdout
      2: stderr

    When is_tty is True, streams are un-headered raw bytes and yielded with stream_type=1.
    """
    if is_tty:
        while True:
            try:
                chunk = await reader.read(8192)
            except _STREAM_DROPS as exc:
                raise StreamTruncatedError("Stream dropped before EOF") from exc
            if not chunk:
                break
            yield (1, chunk)
        return

    while True:
        try:
            header = await reader.readexactly(8)
        except asyncio.IncompleteReadError as exc:
            if exc.partial:
                raise StreamTruncatedError("Truncated stream header") from exc
            break
        except _STREAM_DROPS as exc:
            raise StreamTruncatedError("Stream dropped before EOF") from exc

        stream_type = header[0]
        # Validate standard 8-byte multiplex header: stream_type in (0, 1, 2) and 3 zero bytes
        if stream_type in (0, 1, 2) and header[1:4] == b"\x00\x00\x00":
            payload_len = struct.unpack(">I", header[4:8])[0]
            if payload_len == 0:
                continue
            try:
                payload = await reader.readexactly(payload_len)
            except (asyncio.IncompleteReadError, *_STREAM_DROPS) as exc:
                raise StreamTruncatedError(
                    f"Truncated stream payload, expected {payload_len} bytes"
                ) from exc
            yield (stream_type, payload)
        else:
            # Fallback for un-multiplexed raw stream (e.g. proxy or misconfigured TTY)
            yield (1, header)
            while True:
                try:
                    chunk = await reader.read(8192)
                except _STREAM_DROPS as exc:
                    raise StreamTruncatedError("Stream dropped before EOF") from exc
                if not chunk:
                    break
                yield (1, chunk)
            break


async def read_stream_as_text(
    reader: aiohttp.StreamReader,
    is_tty: bool = False,
) -> str:
    """Read a demultiplexed or raw stream into a combined text string."""
    chunks: list[str] = []
    async for _, payload in demultiplex_stream(reader, is_tty=is_tty):
        chunks.append(payload.decode("utf-8", errors="replace"))
    return "".join(chunks)


async def read_exec_stream(
    reader: aiohttp.StreamReader,
    is_tty: bool = False,
) -> tuple[str, str]:
    """Read an exec stream into (stdout, stderr) text buffers."""
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    async for stream_type, payload in demultiplex_stream(reader, is_tty=is_tty):
        text = payload.decode("utf-8", errors="replace")
        if stream_type == 2:
            stderr_chunks.append(text)
        else:
            stdout_chunks.append(text)
    return "".join(stdout_chunks), "".join(stderr_chunks)


async def parse_json_lines_stream(
    reader: aiohttp.StreamReader,
) -> AsyncIterator[dict[str, Any]]:
    """
    Parse an incremental JSON stream (e.g. image pull or build).
    Raises RuntimeClientError if an error object is encountered inside HTTP 200 stream.
    """
    while not reader.at_eof():
        line = await reader.readline()
        if not line:
            break
        stripped = line.strip()
        if not stripped:
            continue
        try:
            data = json.loads(stripped.decode("utf-8", errors="replace"))
        except ValueError:
            continue

        if isinstance(data, dict):
            if "error" in data or "errorDetail" in data:
                err_msg = data.get("error") or "Runtime stream error"
                detail = data.get("errorDetail", {})
                if isinstance(detail, dict) and "message" in detail:
                    err_msg = detail["message"]
                raise RuntimeClientError(message=err_msg, detail=data)
            yield data
