"""Day 34: tools/danger.py — pure deterministic function, no LLM, no I/O."""
from agent_web.services.tools import danger


def test_read_search_list_are_safe():
    assert danger.danger_level("read_file") == danger.SAFE
    assert danger.danger_level("search_files") == danger.SAFE
    assert danger.danger_level("list_dir") == danger.SAFE
    assert not danger.is_dangerous("read_file")
    assert not danger.is_dangerous("search_files")
    assert not danger.is_dangerous("list_dir")


def test_write_delete_are_dangerous():
    assert danger.danger_level("write_file") == danger.DANGEROUS
    assert danger.danger_level("delete_file") == danger.DANGEROUS
    assert danger.is_dangerous("write_file")
    assert danger.is_dangerous("delete_file")


def test_commit_shaped_name_is_dangerous():
    # Not registered (day 35's git_tools.py owns this), but the plan requires
    # commit-shaped calls to read as DANGEROUS — verified here via the
    # fail-closed default: unknown tool names are DANGEROUS, never SAFE.
    assert danger.danger_level("git_commit") == danger.DANGEROUS


def test_unknown_tool_defaults_dangerous_fail_closed():
    assert danger.danger_level("some_never_registered_tool") == danger.DANGEROUS


def test_path_argument_does_not_change_verdict():
    # Pure function of tool name (+ path, which currently never flips the verdict —
    # see danger.py docstring). Same tool, different paths -> same level.
    assert danger.danger_level("write_file", "a.txt") == danger.danger_level("write_file", "b/c.txt")
    assert danger.danger_level("read_file", "a.txt") == danger.danger_level("read_file", "b/c.txt")


def test_module_exposes_no_provider_or_client_symbol():
    # Regression guard: this module must stay a pure lookup table — no LLM
    # client/provider object should ever appear on it.
    assert not hasattr(danger, "client")
    assert not hasattr(danger, "provider")
