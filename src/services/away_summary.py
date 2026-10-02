import time
import logging
from core.query_engine import LLMClient

logger = logging.getLogger("mustan_agent.services.away_summary")

class AwaySummaryService:
    """
    Kullanıcının inaktif olduğu süreyi ölçer ve belirli bir eşiği aşarsa 
    merkezi LLMClient'i kullanarak kaldığı yeri hatırlatan kısa bir özet (Away Summary) üretir.
    """
    def __init__(self, timeout_seconds: int = 300):
        # Varsayılan olarak 5 dakika (300 saniye) inaktivite sınırı
        self.timeout_seconds = timeout_seconds
        self.last_activity_time = time.time()
        self.llm = LLMClient()

    def update_activity(self):
        """Kullanıcı bir işlem yaptığında sayacı sıfırlar."""
        self.last_activity_time = time.time()

    def check_and_generate_summary(self, recent_context: str) -> str | None:
        """Süre aşıldıysa son işlemleri LLM'e özetletir."""
        idle_time = time.time() - self.last_activity_time
        if idle_time < self.timeout_seconds:
            return None

        print(f"\n[⏳] Uzun süre inaktif kaldınız ({int(idle_time//60)} dk). Son durum özetleniyor...")
        
        sys_prompt = """Sen bir asistan ajansın. Kullanıcı bilgisayar başından bir süreliğine 
ayrı kaldı. Ona döndüğünde nerede kaldığımızı hatırlatan çok kısa, cana yakın ve 2 cümleyi 
geçmeyen bir hoş geldin/özet metni hazırla."""

        prompt = f"Son konuşma / eylem bağlamımız: {recent_context}"

        try:
            summary = self.llm.generate_content(prompt=prompt, system_prompt=sys_prompt)
            self.update_activity()
            return summary.strip()
        except Exception as e:
            logger.error(f"Away Summary üretim hatası: {e}")
            return None

