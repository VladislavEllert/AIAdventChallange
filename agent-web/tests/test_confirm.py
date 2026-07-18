"""Day 34: tools/confirm.py — unit tests with real threads, no ASGI.

Full end-to-end confirm-over-SSE belongs in Playwright (34.12) only — see
plan's Tests table note on TestClient's blocking portal causing interleaved
hangs with a second thread mid-stream. These tests exercise the registry +
threading.Event handshake directly.
"""
import threading
import time

import pytest

from agent_web.services.tools import confirm


@pytest.fixture(autouse=True)
def _clean_registry():
    confirm._reset_for_tests()
    yield
    confirm._reset_for_tests()


def test_approve_unblocks_wait_with_true(tmp_path):
    stream_id = "stream-approve"
    confirm.start_session(stream_id)
    req = confirm.request_confirmation(stream_id, "write_file", {"path": "x.txt"}, "test")

    def approver():
        time.sleep(0.05)
        ok = confirm.resolve(req.call_id, True)
        assert ok

    t = threading.Thread(target=approver)
    t.start()
    approved = confirm.await_confirmation(req.call_id, timeout=5.0, poll_interval=0.02)
    t.join()

    assert approved is True


def test_deny_unblocks_wait_with_false_disk_untouched(tmp_path):
    stream_id = "stream-deny"
    confirm.start_session(stream_id)
    target = tmp_path / "should_not_exist.txt"
    req = confirm.request_confirmation(stream_id, "write_file", {"path": str(target)}, "test")

    def denier():
        time.sleep(0.05)
        ok = confirm.resolve(req.call_id, False)
        assert ok
        # Simulate: caller only writes to disk after an approved confirm.
        if req.approved:
            target.write_text("should never happen")

    t = threading.Thread(target=denier)
    t.start()
    approved = confirm.await_confirmation(req.call_id, timeout=5.0, poll_interval=0.02)
    t.join()

    assert approved is False
    assert not target.exists()


def test_timeout_auto_denies_with_small_timeout():
    stream_id = "stream-timeout"
    confirm.start_session(stream_id)
    req = confirm.request_confirmation(stream_id, "delete_file", {"path": "x.txt"}, "test")

    start = time.monotonic()
    approved = confirm.await_confirmation(req.call_id, timeout=0.2, poll_interval=0.05)
    elapsed = time.monotonic() - start

    assert approved is False
    assert elapsed < 2.0  # proves the test didn't actually sleep the real 60s default


def test_wait_for_confirmation_yields_keepalive_then_result():
    stream_id = "stream-keepalive"
    confirm.start_session(stream_id)
    req = confirm.request_confirmation(stream_id, "write_file", {"path": "x.txt"}, "test")

    def approver():
        time.sleep(0.12)
        confirm.resolve(req.call_id, True)

    t = threading.Thread(target=approver)
    t.start()

    kinds = []
    for kind, payload in confirm.wait_for_confirmation(req.call_id, timeout=5.0, poll_interval=0.05):
        kinds.append(kind)
    t.join()

    assert kinds[-1] == "result"
    assert kinds.count("keepalive") >= 1  # generator doesn't just block silently


def test_unknown_call_id_auto_denies():
    approved = confirm.await_confirmation("does-not-exist", timeout=1.0, poll_interval=0.05)
    assert approved is False


def test_stale_ended_session_cannot_approve():
    stream_id = "stream-stale"
    confirm.start_session(stream_id)
    req = confirm.request_confirmation(stream_id, "write_file", {"path": "x.txt"}, "test")

    confirm.end_session(stream_id)  # tab "closed"

    ok = confirm.resolve(req.call_id, True)
    assert ok is False  # resolve() itself refuses a stale session


def test_stale_session_auto_denies_mid_wait():
    stream_id = "stream-stale-midwait"
    confirm.start_session(stream_id)
    req = confirm.request_confirmation(stream_id, "write_file", {"path": "x.txt"}, "test")

    def close_tab():
        time.sleep(0.08)
        confirm.end_session(stream_id)

    t = threading.Thread(target=close_tab)
    t.start()
    approved = confirm.await_confirmation(req.call_id, timeout=5.0, poll_interval=0.03)
    t.join()

    assert approved is False
