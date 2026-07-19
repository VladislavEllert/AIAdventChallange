import pytest


@pytest.fixture(autouse=True)
def isolate_settings_file(tmp_path, monkeypatch):
    """save_settings() writes to a fixed on-disk path — without this, running
    these tests overwrites the developer's real data/settings.json."""
    import agent_web.services.settings_store as store
    monkeypatch.setattr(store, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(store, "_SETTINGS_PATH", tmp_path / "settings.json")


def test_get_settings_has_day29_defaults(client):
    r = client.get("/api/settings")
    assert r.status_code == 200
    body = r.json()
    for key in ("temperature", "max_tokens", "top_p", "num_ctx",
                "image_steps", "image_cfg", "image_seed", "image_width", "image_height"):
        assert key in body


def test_default_model_is_gpt4o_mini(client):
    # Phase 0: default_model switched from ollama/qwen3:4b (unreachable off-LAN/CI)
    # to openai/gpt-4o-mini in both the _DEFAULTS dict and the committed
    # data/settings.json (whichever wins here, this must be the result).
    r = client.get("/api/settings")
    assert r.json()["default_model"] == "openai/gpt-4o-mini"


def test_put_settings_updates_text_params(client):
    r = client.put("/api/settings", json={"temperature": 1.2, "max_tokens": 512, "top_p": 0.8})
    assert r.status_code == 200
    body = r.json()
    assert body["temperature"] == 1.2
    assert body["max_tokens"] == 512
    assert body["top_p"] == 0.8

    r2 = client.get("/api/settings")
    assert r2.json()["temperature"] == 1.2


def test_put_settings_updates_image_params(client):
    r = client.put("/api/settings", json={"image_steps": 30, "image_cfg": 6.5, "image_seed": 42})
    body = r.json()
    assert body["image_steps"] == 30
    assert body["image_cfg"] == 6.5
    assert body["image_seed"] == 42


def test_put_settings_image_seed_random_clears_seed(client):
    client.put("/api/settings", json={"image_seed": 42})
    r = client.put("/api/settings", json={"image_seed_random": True})
    assert r.json()["image_seed"] is None
