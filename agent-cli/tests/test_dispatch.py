from unittest.mock import MagicMock, patch


def test_resolve_ollama_strips_prefix():
    from agent_cli.llm.dispatch import DispatchProvider

    proxyapi = MagicMock()
    ollama = MagicMock()
    d = DispatchProvider(proxyapi=proxyapi, ollama=ollama)

    provider, model = d.resolve("ollama/qwen3:4b")
    assert provider is ollama
    assert model == "qwen3:4b"


def test_resolve_openai_unchanged():
    from agent_cli.llm.dispatch import DispatchProvider

    proxyapi = MagicMock()
    d = DispatchProvider(proxyapi=proxyapi, ollama=MagicMock())

    provider, model = d.resolve("openai/gpt-4o-mini")
    assert provider is proxyapi
    assert model == "openai/gpt-4o-mini"


def test_resolve_gemini_goes_to_proxyapi():
    from agent_cli.llm.dispatch import DispatchProvider

    proxyapi = MagicMock()
    d = DispatchProvider(proxyapi=proxyapi, ollama=MagicMock())

    provider, model = d.resolve("gemini/gemini-2.5-flash-lite")
    assert provider is proxyapi
    assert model == "gemini/gemini-2.5-flash-lite"


def test_client_for_returns_bare_model():
    from agent_cli.llm.dispatch import DispatchProvider

    ollama = MagicMock()
    ollama.client = "ollama-openai-client"
    d = DispatchProvider(proxyapi=MagicMock(), ollama=ollama)

    client, model = d.client_for("ollama/qwen3:4b")
    assert client == "ollama-openai-client"
    assert model == "qwen3:4b"


def test_ollama_lazy_construction_only_when_needed():
    """Constructing DispatchProvider must not eagerly build an Ollama client
    (would require the Ollama box to be reachable just to import)."""
    from agent_cli.llm.dispatch import DispatchProvider

    with patch("agent_cli.llm.dispatch.OllamaProvider") as MockOllama:
        d = DispatchProvider(proxyapi=MagicMock())
        MockOllama.assert_not_called()
        _ = d.ollama
        MockOllama.assert_called_once()


def test_chat_stream_with_stats_dispatches_to_ollama():
    from agent_cli.llm.dispatch import DispatchProvider

    ollama = MagicMock()
    ollama.chat_stream_with_stats.return_value = (iter(["hi"]), "ref")
    d = DispatchProvider(proxyapi=MagicMock(), ollama=ollama)

    gen, ref = d.chat_stream_with_stats([{"role": "user", "content": "x"}], "ollama/qwen3:4b")
    assert ref == "ref"
    ollama.chat_stream_with_stats.assert_called_once_with(
        [{"role": "user", "content": "x"}], "qwen3:4b"
    )


def test_ollama_provider_cost_always_zero():
    with patch("agent_cli.llm.ollama.OpenAI"):
        from agent_cli.llm.ollama import OllamaProvider
        provider = OllamaProvider()
        assert provider._cost_rub(1000, 1000, "qwen3:4b") == 0.0


def test_ollama_provider_chat_stream_with_stats():
    from agent_cli.llm.ollama import OllamaProvider

    chunk_content = MagicMock()
    chunk_content.choices = [MagicMock()]
    chunk_content.choices[0].delta.content = "hello"
    chunk_content.usage = None

    chunk_usage = MagicMock()
    chunk_usage.choices = []
    chunk_usage.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = iter([chunk_content, chunk_usage])

    with patch("agent_cli.llm.ollama.OpenAI", return_value=mock_client):
        provider = OllamaProvider()
        gen, ref = provider.chat_stream_with_stats([{"role": "user", "content": "hi"}], "qwen3:4b")
        chunks = list(gen)

    assert chunks == ["hello"]
    usage = ref.usage
    assert usage.prompt_tokens == 10
    assert usage.cost_rub == 0.0  # always free
