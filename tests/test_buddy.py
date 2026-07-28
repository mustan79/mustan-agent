import pytest
from unittest.mock import patch, MagicMock
from buddy.companion import BuddyManager
from buddy.types import Species

class TestMemocanBuddy:
    
    @patch("buddy.companion.VoiceService")
    @patch("buddy.companion.LLMClient")
    def test_easter_egg_trigger(self, mock_llm_class, mock_voice_class):
        """
        Soru: Kullanıcı 3 kere memo yazdığında Easter Egg tetikleniyor mu?
        Test: 'memo memo memo' girdisi process_input'tan True dönmeli ve LLM çağrılmalı.
        """
        # Mock LLM Client ayarı
        mock_llm = MagicMock()
        mock_llm.generate_content.return_value = "İşte sana bir şiir!"
        mock_llm_class.return_value = mock_llm
        
        # Sesi kapalı başlatarak testin hızlı ve sessiz bitmesini sağla
        buddy = BuddyManager(species=Species.ROBOT, voice_enabled=False)
        
        # Normal girdi tetiklemez
        assert buddy.process_input("merhaba nasılsın") is False
        mock_llm.generate_content.assert_not_called()
        
        # Easter Egg girdisi tetikler
        result = buddy.process_input("memo naber memo hadi memo")
        
        assert result is True
        mock_llm.generate_content.assert_called_once()
        
    @patch("buddy.companion.VoiceService")
    def test_sleep_wakeup_cycle(self, mock_voice_class):
        """
        Soru: Ajan uyku modundayken uyandırılabiliyor mu?
        """
        buddy = BuddyManager(species=Species.DUCK, voice_enabled=False)
        
        # Zorla uyku moduna sok
        buddy.is_sleeping = True
        
        # Yeni girdi gelince uyanmalı ve False (normal işleme devam et) dönmeli
        result = buddy.process_input("uyan bakalım")
        
        assert buddy.is_sleeping is False
        assert result is False


