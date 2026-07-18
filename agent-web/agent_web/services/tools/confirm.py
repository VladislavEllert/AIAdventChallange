"""Day 34: human-in-the-loop confirmation registry for DANGEROUS tool calls.

One process-wide dict keyed by call_id. Requires a single uvicorn worker —
a second worker process would have its own empty dict and could never see a
confirmation POSTed to a different worker (see week-07/day-34/README.md).

Design notes (plan step 34.6):
- Instead of one blocking `event.wait(120)`, `wait_for_confirmation` polls in
  a loop (`while not ev.wait(poll_interval): yield keepalive`) capped at
  `timeout` seconds total, so the SSE generator in chat.py can emit
  `: keepalive\n\n` lines to keep the HTTP connection alive during a long wait.
  The keepalive line has no `event: `/`data: ` prefix, so it is inert to the
  existing SSE parser in frontend/src/api/chat.ts (verified: that parser only
  reacts to lines starting with those two prefixes).
- `timeout`/`poll_interval` are parameters, not hardcoded sleeps, so tests
  don't actually wait 60s.
- Each SSE request registers its own short-lived "stream session" (NOT the
  chat session_id, which persists across many messages) via `start_session`/
  `end_session`. A confirm POST for a call_id whose stream session has already
  ended (closed/stale tab) is auto-denied by `resolve()` — a late approval
  from a dead tab must never execute a write.
"""
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterator

DEFAULT_TIMEOUT = 60.0
DEFAULT_POLL_INTERVAL = 5.0


@dataclass
class ConfirmRequest:
    call_id: str
    session_id: str
    tool_name: str
    arguments: dict[str, Any]
    reason: str
    event: threading.Event = field(default_factory=threading.Event)
    approved: bool = False


_LOCK = threading.Lock()
_PENDING: dict[str, ConfirmRequest] = {}
_ACTIVE_STREAMS: set[str] = set()


def new_call_id() -> str:
    return uuid.uuid4().hex


def start_session(stream_id: str) -> None:
    with _LOCK:
        _ACTIVE_STREAMS.add(stream_id)


def end_session(stream_id: str) -> None:
    with _LOCK:
        _ACTIVE_STREAMS.discard(stream_id)


def is_session_active(stream_id: str) -> bool:
    with _LOCK:
        return stream_id in _ACTIVE_STREAMS


def request_confirmation(
    stream_id: str, tool_name: str, arguments: dict[str, Any], reason: str, call_id: str | None = None,
) -> ConfirmRequest:
    req = ConfirmRequest(
        call_id=call_id or new_call_id(),
        session_id=stream_id,
        tool_name=tool_name,
        arguments=arguments,
        reason=reason,
    )
    with _LOCK:
        _PENDING[req.call_id] = req
    return req


def resolve(call_id: str, approved: bool) -> bool:
    """Called by POST /api/tools/confirm. Returns False if call_id is unknown
    OR the requesting stream has already ended — a stale tab cannot approve."""
    with _LOCK:
        req = _PENDING.get(call_id)
    if req is None:
        return False
    if not is_session_active(req.session_id):
        return False
    req.approved = approved
    req.event.set()
    return True


def peek(call_id: str) -> ConfirmRequest | None:
    with _LOCK:
        return _PENDING.get(call_id)


def list_pending() -> list[ConfirmRequest]:
    with _LOCK:
        return list(_PENDING.values())


def wait_for_confirmation(
    call_id: str, timeout: float = DEFAULT_TIMEOUT, poll_interval: float = DEFAULT_POLL_INTERVAL,
) -> Iterator[tuple[str, Any]]:
    """Generator: yields ("keepalive", None) on every poll tick while waiting,
    then a final ("result", approved: bool). Auto-denies on timeout, and
    auto-denies immediately (without waiting further) if the request's stream
    session ends while we're still polling."""
    req = peek(call_id)
    if req is None:
        yield ("result", False)
        return

    elapsed = 0.0
    while elapsed < timeout:
        if not is_session_active(req.session_id):
            break  # stale stream — fall through to auto-deny below
        if req.event.wait(poll_interval):
            break  # resolved (approve or deny)
        elapsed += poll_interval
        yield ("keepalive", None)

    if not req.event.is_set():
        req.approved = False
        req.event.set()

    with _LOCK:
        _PENDING.pop(call_id, None)

    yield ("result", req.approved)


def await_confirmation(
    call_id: str, timeout: float = DEFAULT_TIMEOUT, poll_interval: float = DEFAULT_POLL_INTERVAL,
) -> bool:
    """Blocking convenience wrapper (drains wait_for_confirmation) for non-SSE
    callers — headless use, unit tests."""
    approved = False
    for kind, payload in wait_for_confirmation(call_id, timeout, poll_interval):
        if kind == "result":
            approved = bool(payload)
    return approved


def _reset_for_tests() -> None:
    """Test-only escape hatch — production code never calls this."""
    with _LOCK:
        _PENDING.clear()
        _ACTIVE_STREAMS.clear()
