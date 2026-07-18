"""Day 32: resilience ladder — failing provider -> retry -> fallback model ->
deterministic failure. Zero network/provider dependency (call_fn is a stub)."""
import pytest

from agent_web.services.review.resilience import (
    DETERMINISTIC_FAILURE_MSG,
    call_with_resilience,
)


def test_succeeds_on_first_try():
    def call_fn(model):
        return f"ok:{model}", {"tokens": 1}

    result = call_with_resilience(call_fn, "primary", fallback_model="fallback")
    assert result.ok
    assert result.payload == "ok:primary"
    assert result.model_used == "primary"
    assert result.retries == 0


def test_retries_primary_before_falling_back():
    calls = []

    def call_fn(model):
        calls.append(model)
        if model == "primary" and calls.count("primary") < 2:
            raise RuntimeError("transient failure")
        if model == "primary":
            return "ok-after-retry", None
        raise AssertionError("should not reach fallback")

    result = call_with_resilience(call_fn, "primary", fallback_model="fallback", max_retries=1)
    assert result.ok
    assert result.model_used == "primary"
    assert result.retries == 1
    assert calls == ["primary", "primary"]


def test_falls_back_to_second_model_after_primary_exhausted():
    calls = []

    def call_fn(model):
        calls.append(model)
        if model == "primary":
            raise RuntimeError("primary is down")
        return "ok-fallback", None

    result = call_with_resilience(call_fn, "primary", fallback_model="fallback", max_retries=1)
    assert result.ok
    assert result.model_used == "fallback"
    assert result.payload == "ok-fallback"
    assert result.retries == 1  # only primary attempts count as retries
    assert calls == ["primary", "primary", "fallback"]


def test_deterministic_failure_when_everything_fails():
    def call_fn(model):
        raise RuntimeError(f"{model} is down")

    on_attempt_calls = []
    result = call_with_resilience(
        call_fn, "primary", fallback_model="fallback", max_retries=1,
        on_attempt=on_attempt_calls.append,
    )
    assert not result.ok
    assert result.payload == DETERMINISTIC_FAILURE_MSG
    assert result.model_used == ""
    # primary x2 + fallback x1 = 3 attempts, all reported
    assert len(on_attempt_calls) == 3
    assert all(a["ok"] is False for a in on_attempt_calls)


def test_deterministic_failure_no_fallback_configured():
    def call_fn(model):
        raise RuntimeError("down")

    result = call_with_resilience(call_fn, "primary", fallback_model=None, max_retries=0)
    assert not result.ok
    assert result.payload == DETERMINISTIC_FAILURE_MSG


def test_timeout_counts_as_a_failed_attempt():
    import time

    def call_fn(model):
        if model == "primary":
            time.sleep(1.0)
            return "should not reach here", None
        return "fallback ok", None

    result = call_with_resilience(
        call_fn, "primary", fallback_model="fallback", max_retries=0, timeout_s=0.05,
    )
    assert result.ok
    assert result.model_used == "fallback"


def test_every_attempt_reported_to_on_attempt():
    attempts = []

    def call_fn(model):
        raise RuntimeError("nope")

    call_with_resilience(
        call_fn, "primary", fallback_model="fallback", max_retries=2,
        on_attempt=attempts.append,
    )
    # primary x3 (1 + 2 retries) + fallback x1 = 4
    assert len(attempts) == 4
    models_tried = [a["model"] for a in attempts]
    assert models_tried == ["primary", "primary", "primary", "fallback"]


def test_pipeline_itself_does_not_crash_on_total_failure():
    """resilience.call_with_resilience never raises — it's a contract, not just
    incidental behavior."""
    def call_fn(model):
        raise ValueError("boom")

    try:
        result = call_with_resilience(call_fn, "primary")
    except Exception as e:  # pragma: no cover - this is exactly what must not happen
        pytest.fail(f"call_with_resilience raised instead of returning a failure result: {e}")
    assert not result.ok
