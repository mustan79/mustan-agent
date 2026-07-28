import pytest
from unittest.mock import patch, MagicMock
from commands.status_summary import run_status, run_summary

class TestStatusSummary:
    @patch("commands.status_summary.settings")
    @patch("builtins.print")
    def test_run_status(self, mock_print, mock_settings):
        # Settings mock objesine ihtiyaç duyduğu özellikleri (model) ekliyoruz
        mock_settings.config.llm.model = "gemini-1.5-pro"
        mock_settings.config.memory.base_dir = "Aimemory"
        mock_settings.config.memory.stats_file = "stats.json"

        result = run_status()
        assert result is True
        mock_print.assert_any_call(" 📡 MustanAgent v3.3 PRO - Sistem Durumu")

