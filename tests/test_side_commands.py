import time
import pytest
from unittest.mock import patch, MagicMock
from services.away_summary import AwaySummaryService

class TestSideCommands:
    @patch("services.away_summary.LLMClient")
    def test_away_summary_timeout(self, mock_llm_class):
        mock_llm_instance = mock_llm_class.return_value
        mock_llm_instance.generate_content.return_value = "Hoş geldin! En son şurada kalmıştık."
        
        service = AwaySummaryService(timeout_seconds=0) # Anında tetiklensin
        service.last_activity_time = time.time() - 10 # 10 saniye geçmiş gibi yap
        
        # ESKİ (Hatalı) method adı düzeltildi
        result = service.check_and_generate_summary("test bağlamı")
        
        assert result == "Hoş geldin! En son şurada kalmıştık."
