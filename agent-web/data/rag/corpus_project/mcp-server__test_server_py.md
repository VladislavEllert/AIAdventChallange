<!-- source: mcp-server/test_server.py | title: test_server.py -->

"""Tests for MCP server tools (unit, no network)."""
import pytest
from unittest.mock import patch, MagicMock

import importlib, sys


def _load_server():
    # Reload to reset module-level state
    if "server" in sys.modules:
        del sys.modules["server"]
    import server
    return server


def test_web_search_no_results():
    server = _load_server()
    with patch("server.DDGS") as mock_ddgs:
        mock_ddgs.return_value.__enter__.return_value.text.return_value = []
        result = server.web_search("test query")
    assert "No results" in result


def test_web_search_returns_results():
    server = _load_server()
    fake_results = [{"title": "Test", "body": "Body text", "href": "https://example.com"}]
    with patch("server.DDGS") as mock_ddgs:
        mock_ddgs.return_value.__enter__.return_value.text.return_value = fake_results
        result = server.web_search("test")
    assert "Test" in result
    assert "example.com" in result


def test_get_moex_quote_from_cache():
    server = _load_server()
    server._moex_cache["SBER"] = {"ticker": "SBER", "last": 300.0, "open": 295.0, "volume": 1000000}
    result = server.get_moex_quote("sber")
    assert "300.0" in result
    assert "SBER" in result


def test_get_moex_quote_no_data():
    server = _load_server()
    server._moex_cache.clear()
    with patch("server._fetch_moex", return_value=None):
        result = server.get_moex_quote("XXXX")
    assert "No data" in result


def test_get_moex_summary_empty():
    server = _load_server()
    server._moex_cache.clear()
    result = server.get_moex_summary()
    assert "empty" in result.lower() or "30" in result


def test_get_moex_summary_with_data():
    server = _load_server()
    server._moex_cache["GAZP"] = {"ticker": "GAZP", "last": 150.5, "open": 148.0, "volume": 5000000}
    result = server.get_moex_summary()
    assert "GAZP" in result
    assert "150.5" in result
