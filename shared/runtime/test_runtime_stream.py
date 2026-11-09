import struct
from unittest.mock import MagicMock

import aiohttp
import pytest

from shared.runtime.runtime_errors import RuntimeClientError, StreamTruncatedError
from shared.runtime.runtime_stream import (
    parse_json_lines_stream,
    read_exec_stream,
    read_stream_as_text,
)


def _make_frame(stream_type: int, payload: bytes) -> bytes:
    """Build a Docker multiplex frame header (8 bytes) + payload."""
    header = struct.pack(">BxxxI", stream_type, len(payload))
    return header + payload


def _make_reader(data: bytes) -> aiohttp.StreamReader:
    protocol = MagicMock()
    reader = aiohttp.StreamReader(protocol, limit=2**16)
    reader.feed_data(data)
    reader.feed_eof()
    return reader


@pytest.mark.asyncio
async def test_demultiplex_stdout_and_stderr():
    frame1 = _make_frame(1, b"hello stdout\n")
    frame2 = _make_frame(2, b"hello stderr\n")
    frame3 = _make_frame(1, b"more stdout")
    reader = _make_reader(frame1 + frame2 + frame3)

    stdout, stderr = await read_exec_stream(reader, is_tty=False)
    assert stdout == "hello stdout\nmore stdout"
    assert stderr == "hello stderr\n"


@pytest.mark.asyncio
async def test_raw_tty_stream():
    raw_data = b"raw text from container\r\nline 2"
    reader = _make_reader(raw_data)

    text = await read_stream_as_text(reader, is_tty=True)
    assert text == "raw text from container\r\nline 2"


@pytest.mark.asyncio
async def test_raw_fallback_when_not_multiplexed():
    raw_data = b"unmultiplexed raw proxy stream"
    reader = _make_reader(raw_data)

    text = await read_stream_as_text(reader, is_tty=False)
    assert text == "unmultiplexed raw proxy stream"


@pytest.mark.asyncio
async def test_truncated_stream_raises():
    incomplete = struct.pack(">BxxxI", 1, 100) + b"only 10 bytes"
    reader = _make_reader(incomplete)

    with pytest.raises(StreamTruncatedError):
        await read_stream_as_text(reader, is_tty=False)


@pytest.mark.asyncio
async def test_parse_json_lines_stream_success():
    lines = (
        b'{"status": "Pulling fs layer", "id": "layer1"}\r\n'
        b'{"status": "Downloading", "id": "layer1"}\r\n'
        b'{"status": "Download complete", "id": "layer1"}\r\n'
    )
    reader = _make_reader(lines)

    events = [event async for event in parse_json_lines_stream(reader)]
    assert len(events) == 3
    assert events[0]["id"] == "layer1"
    assert events[2]["status"] == "Download complete"


@pytest.mark.asyncio
async def test_parse_json_lines_stream_error_in_200():
    lines = (
        b'{"status": "Pulling fs layer"}\r\n'
        b'{"error": "pull access denied for myrepo/private", "errorDetail": {"message": "unauthorized"}}\r\n'
    )
    reader = _make_reader(lines)

    with pytest.raises(RuntimeClientError) as exc_info:
        async for _ in parse_json_lines_stream(reader):
            pass
    assert "unauthorized" in str(exc_info.value)
