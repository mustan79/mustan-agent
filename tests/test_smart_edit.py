import os
import tempfile
import pytest
from tools.smart_edit import SmartEditTool, SmartEditInput

class TestSmartEditSafety:
    """
    Kodu diske yazmadan önce sözdizimi (syntax) kontrolü ve katı bağlam
    korumalarını test eden Kalite Güvence senaryoları.
    """

    def test_syntax_protection(self):
        """
        Soru: SmartEdit bozulan kodu (Syntax Error) diske yazar mı?
        Test: Sonuna ':' konulmamış bozuk bir Python fonksiyonunu yazmaya çalışıp 
        reddedilmesini ve hatanın iade edilmesini doğrulayacağız.
        """
        # 1. Geçici, çalışan bir Python dosyası yarat
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def valid_func():\n    pass\n")
            temp_path = f.name

        try:
            # 2. Ajanın bozuk bir kodla değiştirmeye çalıştığını simüle et
            input_data = SmartEditInput(
                file_path=temp_path,
                old_text="def valid_func():",
                new_text="def valid_func()",  # HATA: İki nokta (:) eksik!
                replace_all=False
            )
            result = SmartEditTool.execute(input_data)

            # 3. Beklentiler (Assertions)
            assert "[-] Sözdizimi (Syntax) Hatası" in result
            assert "YAZILMADI" in result
            
            # Asıl dosyanın bozulmadığını (hala geçerli olduğunu) kontrol et
            with open(temp_path, "r") as f:
                assert "def valid_func():" in f.read()
        finally:
            os.remove(temp_path)

    def test_strict_context_multiple_matches(self):
        """
        Soru: Dosyada birden fazla eşleşme varsa yanlış yeri değiştirir mi?
        Test: İki aynı print olan dosyada replace_all=False iken işlemi reddetmeli.
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("print('hello')\nprint('hello')\n")
            temp_path = f.name

        try:
            input_data = SmartEditInput(
                file_path=temp_path,
                old_text="print('hello')",
                new_text="print('world')",
                replace_all=False
            )
            result = SmartEditTool.execute(input_data)

            assert "belirsiz" in result
            assert "2 defa geçiyor" in result
        finally:
            os.remove(temp_path)
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
        mock_scan.assert_called_once_with(os.path.abspath("src"), memory_dir="test_memory")

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
