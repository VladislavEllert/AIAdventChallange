"""Day 32.2: resilience wrapper around a single provider call.

Ladder: primary model (with `max_retries` retries) -> fallback model (once,
if given and different) -> deterministic failure. This module never raises
past its own boundary — pipeline.py stays pure, and the CLI (__main__.py)
never crashes on a bad/absent API key or a slow provider; it gets a typed
`ResilientCallResult` back and decides the exit code itself.

Every attempt (success or failure, primary or fallback) is reported via
`on_attempt` so the caller can log it to metrics.py (plan 32.2: "every step
recorded to metrics").
"""
import concurrent.futures as cf
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

DETERMINISTIC_FAILURE_MSG = "review failed, needs human"


@dataclass
class ResilientCallResult:
    ok: bool
    payload: Any
    model_used: str
    retries: int
    usage: Any = None


def call_with_resilience(
    call_fn: Callable[[str], tuple[Any, Any]],
    primary_model: str,
    fallback_model: Optional[str] = None,
    max_retries: int = 1,
    timeout_s: float = 60.0,
    on_attempt: Optional[Callable[[dict], None]] = None,
) -> ResilientCallResult:
    """`call_fn(model) -> (payload, usage)`.

    Tries `primary_model` up to `1 + max_retries` times (each attempt capped
    at `timeout_s`, run on a worker thread so a hung call can't hang the
    caller past the timeout), then `fallback_model` once if it's set and
    differs from the primary. Any exception (timeout, auth, network, or a
    `call_fn` that raises because the pipeline reported ok=False) counts as
    a failed attempt and moves to the next rung of the ladder. Exhausting
    the ladder returns `ok=False` with `payload=DETERMINISTIC_FAILURE_MSG` —
    this function itself never raises.
    """
    schedule = [primary_model] * (max_retries + 1)
    if fallback_model and fallback_model != primary_model:
        schedule.append(fallback_model)

    retries = 0
    for i, model in enumerate(schedule):
        if i > 0 and model == primary_model:
            retries += 1
        t0 = time.time()
        try:
            with cf.ThreadPoolExecutor(max_workers=1) as ex:
                payload, usage = ex.submit(call_fn, model).result(timeout=timeout_s)
            elapsed_ms = (time.time() - t0) * 1000
            if on_attempt:
                on_attempt({"model": model, "ok": True, "elapsed_ms": elapsed_ms, "attempt": i})
            return ResilientCallResult(ok=True, payload=payload, model_used=model, retries=retries, usage=usage)
        except Exception as e:
            elapsed_ms = (time.time() - t0) * 1000
            if on_attempt:
                on_attempt({"model": model, "ok": False, "elapsed_ms": elapsed_ms, "attempt": i, "error": str(e)})
            continue

    return ResilientCallResult(
        ok=False, payload=DETERMINISTIC_FAILURE_MSG, model_used="", retries=retries, usage=None
    )
