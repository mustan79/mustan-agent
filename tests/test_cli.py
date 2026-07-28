import os
import pytest
from unittest.mock import patch
from commands.scan import run_scan
from commands.doctor import run_doctor

class TestCommandLineInterface:
    """
    MustanAgent'ın giriş noktası ve uçuş öncesi kontrollerinin (Doctor) testleri.
    """

    @patch("commands.scan.ProjectAnalyzer.scan_directory")
    def test_cli_scan_routing(self, mock_scan):
        """
        Soru: CLI ayağa kalkıp doğru ajanı tetikliyor mu?
        Test: 'mustan-agent scan --dir src/' komutunun arkasındaki run_scan 
        tetiklendiğinde başarılı çıkış (True) dönmeli ve Analyzer çağrılmalıdır.
        """
        # Sahte (Mock) Zihin Haritası dönüşü
        mock_scan.return_value = "# Fake Proje Zihin Haritası"
        
        # Komut tetikleniyor
        result = run_scan(target_dir="src", memory_dir="test_memory")
        
        assert result is True
        mock_scan.assert_called_once_with(os.path.abspath("src"))

    @patch.dict(os.environ, clear=True)
    @patch("core.vault.keyring.get_password")
    def test_doctor_fallback_missing_keys(self, mock_keyring):
        """
        Soru: Ortamda API anahtarı yokken uçuş engelleniyor mu?
        Test: Çevre değişkenlerini ve kasayı (keyring) boşaltıp run_doctor()
        çalıştırdığımızda False dönerek sistemi durdurmalı.
        """
        # Kasanın her zaman None (boş) dönmesini sağla
        mock_keyring.return_value = None
        
        # Doctor komutu çalıştırılıyor
        result = run_doctor()
        
        # Hata tespit edilmeli ve uçuş (True) izni verilmemeli
        assert result is False
