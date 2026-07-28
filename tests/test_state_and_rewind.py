import os
import tempfile
import json
import pytest
from unittest.mock import patch
from memory.session_state import save_session_state, load_session_state
from commands.rewind import run_rewind

class TestSessionAndMemory:

    @patch("memory.session_state.settings")
    def test_session_state_persistence(self, mock_settings):
        """
        Soru: Oturum hafızası (Session State) diske güvenle yazılıp okunuyor mu?
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock settings ile hafıza dizinini temp_dir'e yönlendir
            mock_settings.config.memory.base_dir = temp_dir
            
            # State kaydet
            save_session_state(active_task="WP-005", status="in_progress")
            
            # State'i oku
            loaded_state = load_session_state()
            
            assert loaded_state is not None
            assert loaded_state["last_active_task"] == "WP-005"
            assert loaded_state["status"] == "in_progress"
            assert "timestamp" in loaded_state

    @patch("commands.rewind.restore_checkpoint")
    def test_rewind_command(self, mock_restore):
        """
        Soru: /rewind komutu argüman eksikse reddedip, doğruysa aracı çağırıyor mu?
        """
        # Argüman yoksa False dönmeli
        assert run_rewind("") is False
        
        # Doğru argümanla çalışmalı ve restore aracı çağrılmalı
        mock_restore.return_value = "[+] Geri yükleme başarılı!"
        result = run_rewind("cp_2026_test_backup")
        
        assert result is True
        mock_restore.assert_called_once_with("cp_2026_test_backup")


