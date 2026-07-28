import pytest
from unittest.mock import patch, MagicMock
from services.reflection import MustanReflectService

MOCK_LLM_RESPONSE = """
##### YENİ_KURALLAR
* API çağrılarında her zaman hata yönetimi kullanılmalı.
##### KARAR_GÜNLÜĞÜ
* SQLite yerine PostgreSQL'e geçildi.
##### TEKNİK_BORÇ
* Regex fonksiyonu çok karmaşık.
##### DX_RAPORU
* Kullanıcı DB adını sürekli yanlış veriyor.
"""

class TestReflectionAndInsights:
    @patch("services.reflection.LLMClient")
    @patch("services.reflection.MustanReflectService._read_recent_logs")
    def test_distribute_insights_to_files(self, mock_read_logs, mock_llm_class):
        mock_read_logs.return_value = "eski loglar..."
        
        # HATA BURADAYDI: LLM string dönmeli, MagicMock objesi değil!
        mock_llm_instance = mock_llm_class.return_value
        mock_llm_instance.generate_content.return_value = MOCK_LLM_RESPONSE
        
        service = MustanReflectService()
        
        with patch.object(service, '_append') as mock_append:
            result = service.run_deep_reflection()
            
            assert "✅ Sentez tamamlandı" in result
            assert mock_append.call_count >= 2

