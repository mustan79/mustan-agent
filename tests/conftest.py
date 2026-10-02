"""Keep tests offline and isolate generated project state."""
import pytest


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path, monkeypatch):
    from core.config import settings, MustanConfigSchema
    from core.query_engine import LLMClient
    from core.vault import MustanVault
    from core.cost_tracker import CostTracker
    from buddy.companion import BuddyManager

    monkeypatch.setattr(settings, "config", MustanConfigSchema())
    monkeypatch.setattr(settings.config.memory, "base_dir", str(tmp_path / "memory"))
    monkeypatch.setattr(settings, "config_path", tmp_path / "settings.json")
    monkeypatch.setattr(MustanVault, "get_secret", lambda *args: "")
    monkeypatch.setattr(BuddyManager, "_start_daemon", lambda self: None)
    monkeypatch.setattr(LLMClient, "_instance", None)
    monkeypatch.setattr(CostTracker, "_instance", None)
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY", "OLLAMA_API_KEY"):
        monkeypatch.delenv(name, raising=False)
