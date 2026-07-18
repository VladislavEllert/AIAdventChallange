"""Day 35.6: PROMPT_V2_STRICT selection — pure, no LLM call."""
from agent_web.services.review.pipeline import (
    PROMPT_VERSION,
    PROMPT_VERSION_V2,
    PROMPT_VERSIONS,
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_V2_STRICT,
    build_prompt,
    run_review,
)


def test_prompt_versions_registry_has_both():
    assert PROMPT_VERSIONS[PROMPT_VERSION] == SYSTEM_PROMPT
    assert PROMPT_VERSIONS[PROMPT_VERSION_V2] == SYSTEM_PROMPT_V2_STRICT
    assert SYSTEM_PROMPT != SYSTEM_PROMPT_V2_STRICT


def test_build_prompt_defaults_to_v1():
    messages = build_prompt("diff", ["a.py"], "")
    assert messages[0]["content"] == SYSTEM_PROMPT


def test_build_prompt_selects_v2_strict():
    messages = build_prompt("diff", ["a.py"], "", prompt_version=PROMPT_VERSION_V2)
    assert messages[0]["content"] == SYSTEM_PROMPT_V2_STRICT


def test_build_prompt_unknown_version_falls_back_to_v1():
    messages = build_prompt("diff", ["a.py"], "", prompt_version="nonexistent")
    assert messages[0]["content"] == SYSTEM_PROMPT


def test_run_review_threads_prompt_version_into_chat_fn_messages():
    seen = {}

    def fake_chat_fn(messages, model):
        seen["system"] = messages[0]["content"]
        return "## Potential bugs\n- none found\n## Architectural issues\n- none found\n## Recommendations\n- none found\n"

    result = run_review(
        "diff --git a/x.py b/x.py\n", ["x.py"], None, "openai/gpt-4o-mini",
        chat_fn=fake_chat_fn, prompt_version=PROMPT_VERSION_V2,
    )
    assert result.ok
    assert seen["system"] == SYSTEM_PROMPT_V2_STRICT
