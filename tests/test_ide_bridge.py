import pytest
from unittest.mock import patch, MagicMock

from bridge.ide_server import MustanBridge
from commands.ide import run_ide

class TestMustanBridge:
    """
    MustanAgent IDE Entegrasyon (WebSocket) Köprüsü Test Senaryoları.
    """

    def setup_method(self):
        """Her testten önce Singleton örneğini sıfırla ki testler çakışmasın."""
        MustanBridge._instance = None

    def test_bridge_singleton_pattern(self):
        """
        Soru: Bridge sınıfı gerçekten Singleton mı çalışıyor?
        Test: İki kez get_instance() çağrıldığında bellekteki aynı nesne dönmeli.
        """
        bridge1 = MustanBridge.get_instance()
        bridge2 = MustanBridge.get_instance()
        
        assert bridge1 is bridge2
        assert bridge1.port == 8765 # Varsayılan port kontrolü

    @patch("bridge.ide_server.threading.Thread")
    @patch("bridge.ide_server.websockets")
    def test_bridge_start_prevents_multiple_threads(self, mock_websockets, mock_thread):
        """
        Soru: Sunucu zaten çalışıyorken tekrar başlatılırsa yeni thread açmayı reddediyor mu?
        """
        bridge = MustanBridge.get_instance()
        
        # İlk başlatma başarılı olmalı
        result1 = bridge.start()
        assert result1 is True
        assert bridge.is_running is True
        mock_thread.assert_called_once()
        
        # İkinci başlatma reddedilmeli ve yeni thread açılmamalı
        result2 = bridge.start()
        assert result2 is False
        mock_thread.assert_called_once() # Call count artmamalı!

    def test_ide_context_generation_empty(self):
        """
        Soru: IDE bağlı değilken LLM'e boş bağlam mı gidiyor?
        """
        bridge = MustanBridge.get_instance()
        
        # Bağlantı yokken
        assert bridge.get_ide_context() == ""
        
        # Bağlı ama aktif dosya yokken
        bridge.connected_ide = True
        assert bridge.get_ide_context() == ""

    def test_ide_context_generation_populated(self):
        """
        Soru: IDE'den gelen aktif dosya ve seçili kod LLM bağlamına doğru formatta (Markdown) yansıyor mu?
        """
        bridge = MustanBridge.get_instance()
        bridge.connected_ide = True
        bridge.active_file = "src/auth/login.py"
        bridge.selection = "def authenticate(user):\n    pass"
        
        context = bridge.get_ide_context()
        
        # Başlık ve dosya adı kontrolü
        assert "[CANLI IDE BAĞLAMI]" in context
        assert "`src/auth/login.py`" in context
        
        # Seçili kod bloğu kontrolü
        assert "```\ndef authenticate(user):\n    pass\n```" in context

    @patch("commands.ide.MustanBridge")
    def test_ide_command_routing(self, mock_bridge_class):
        """
        Soru: /ide komutu doğru argümanları işleyip sunucuyu tetikliyor mu?
        """
        # Singleton mock ayarı
        mock_instance = MagicMock()
        mock_instance.port = 8765
        mock_instance.is_running = False
        mock_instance.start.return_value = True
        mock_bridge_class.get_instance.return_value = mock_instance
        
        # /ide start komutu testi
        result = run_ide("start")
        assert result is True
        mock_instance.start.assert_called_once()
        
        # /ide status komutu testi (Mevcut durumu yazdırmalı)
        result_status = run_ide("status")
        assert result_status is True
        
        # Geçersiz komut testi
        result_invalid = run_ide("invalid_command")
        assert result_invalid is False


