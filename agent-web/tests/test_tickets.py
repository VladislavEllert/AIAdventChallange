"""Day 33: agent-web/data/support/tickets.json schema check. Pure file/data test,
no server, no live calls."""
import json
from pathlib import Path

TICKETS_PATH = Path(__file__).parent.parent / "data" / "support" / "tickets.json"

_REQUIRED_FIELDS = {
    "id", "title", "product_area", "version", "environment", "symptom",
    "steps", "status", "user", "history",
}


def _load():
    return json.loads(TICKETS_PATH.read_text(encoding="utf-8"))


def test_tickets_file_exists_and_parses():
    tickets = _load()
    assert isinstance(tickets, list)


def test_ticket_count_in_range():
    tickets = _load()
    assert 8 <= len(tickets) <= 10


def test_ticket_ids_unique():
    tickets = _load()
    ids = [t["id"] for t in tickets]
    assert len(ids) == len(set(ids))


def test_required_fields_present():
    tickets = _load()
    for t in tickets:
        missing = _REQUIRED_FIELDS - t.keys()
        assert not missing, f"ticket {t.get('id')} missing fields: {missing}"


def test_history_is_nonempty_list_of_dicts():
    tickets = _load()
    for t in tickets:
        assert isinstance(t["history"], list)
        assert len(t["history"]) > 0
        for h in t["history"]:
            assert "author" in h and "text" in h


def test_steps_is_nonempty_list():
    tickets = _load()
    for t in tickets:
        assert isinstance(t["steps"], list)
        assert len(t["steps"]) > 0


def test_environment_and_version_are_specific_not_placeholder():
    """Sanity: these fields must carry real content — /support's whole point is
    grounding answers in them, an empty/placeholder value would defeat that."""
    tickets = _load()
    for t in tickets:
        assert t["environment"].strip()
        assert t["version"].strip()
