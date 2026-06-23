"""Smoke test: config loads and defaults are sane. Real tests land with modules."""
from agent_core.config import settings


def test_settings_load():
    assert settings.model_name  # non-empty Ollama tag
    assert settings.agent_port == 8000
    assert settings.seed == 42
