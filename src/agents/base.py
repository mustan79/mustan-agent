### `src/agents/base.py`
import os
import logging
from datetime import datetime
from typing import Any, Optional
from pathlib import Path

# Ortak LLM İstemcisi ve Ayarlar
from core.query_engine import LLMClient
from core.config import settings

class BaseAgent:
    """
    MustanAgent v3.3 PRO - Tüm uzman ajanların (Worker, Planner, Explorer, Verifier)
    miras aldığı temel (Base) sınıf. 
    
    Ortak LLM bağlantısını, hafıza yönetimini ve oturum loglamasını (session_log) tek 
    merkezden yönetir, kod tekrarını (DRY) önler.
    """
    def __init__(self, memory_dir: Optional[str] = None):
        # Hafıza dizinini belirle (Varsayılan: Aimemory)
        self.memory_dir = memory_dir or settings.config.memory.base_dir
        
        # 🚀 EKSİK GİDERİLDİ: Tüm alt sınıfların kullanacağı merkezi LLM motoru bağlandı.
        # Her ajan kendi LLMClient'ını başlatmak yerine bu paylaşımlı örneği kullanabilir.
        self.llm_client = LLMClient()
        
        # Her alt sınıf için kendi adıyla otomatik loglayıcı oluştur
        self.logger = logging.getLogger(f"mustan_agent.agents.{self.__class__.__name__.lower()}")
        
        # "session_log.md" (Oturum Geçmişi) dosyası
        self.log_path = Path(self.memory_dir) / "session_log.md"
        
        # Hafıza dizininin var olduğundan emin ol
        os.makedirs(self.memory_dir, exist_ok=True)

    def execute_task(self, task_description: str, **kwargs: Any) -> Any:
        """
        Görevi çalıştıran ana metot. 
        Bu sınıfı miras alan her uzman ajan (Örn: WorkerAgent) kendi uzmanlığına göre 
        bu metodu EZMELİDİR (override).
        """
        raise NotImplementedError(f"{self.__class__.__name__} alt sınıfı 'execute_task' metodunu uygulamalıdır.")

    def log_action(self, action_type: str, details: str) -> None:
        """
        Ajanların yaptığı eylemleri (Hata, Başarı, Araç Kullanımı) 
        Aimemory/session_log.md dosyasına Markdown formatında mühürler.
        Bu sayede uzun bir seansın ardından geriye dönüp ajanın ne düşündüğünü 
        ve ne yaptığını okuyabilirsin.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Markdown formatında estetik log kaydı
        log_entry = (
            f"### [{timestamp}] {self.__class__.__name__} - {action_type}\n"
            f"{details}\n\n"
            f"---\n\n"
        )
        
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            self.logger.error(f"Log kaydı session_log.md dosyasına yazılamadı: {str(e)}")


