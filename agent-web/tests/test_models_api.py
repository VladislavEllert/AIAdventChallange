from agent_cli.config import _MODEL_PRICING


def test_list_models(client):
    r = client.get("/api/models")
    assert r.status_code == 200
    models = r.json()
    assert len(models) == len(_MODEL_PRICING)
    model_ids = [m["model_id"] for m in models]
    assert "openai/gpt-4o-mini" in model_ids
    assert "gemini/gemini-2.5-flash-lite" in model_ids


def test_models_have_prices(client):
    r = client.get("/api/models")
    for m in r.json():
        assert m["input_price"] > 0
        assert m["output_price"] > 0


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
