import os
import logging
from pathlib import Path
from core.query_engine import LLMClient
from core.config import settings

logger = logging.getLogger("mustan_agent.services.reflection")

class MustanReflectService:
    """
    Ajanın geçmiş logları tarayarak proje kurallarını (scope) güncellemesini ve
    Geliştirici Deneyimi (Insights) raporu sunmasını sağlayan servis.
    """
    def __init__(self):
        self.llm_client = LLMClient()
        self.mem_dir = Path(settings.config.memory.base_dir)
        self.log_file = self.mem_dir / "session_log.md"

    def _read_recent_logs(self, max_lines: int = 1000) -> str:
        if not self.log_file.exists():
            return "Geçmiş log bulunamadı."
        
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                return "".join(lines[-max_lines:])
        except Exception as e:
            logger.error(f"Log okuma hatası: {e}")
            return f"Log okuma hatası: {str(e)}"

    def run_deep_reflection(self) -> str:
        print("[🧠] MustanAgent geçmiş deneyimleri sentezliyor (Deep Reflection)...")
        logs = self._read_recent_logs()
        
        sys_prompt = """Sen projeyi analiz edip içgörü (Insight) çıkaran bir 'Reflect' ajanısın.
Gönderilen logları inceleyerek şu 4 başlığı oluştur:
##### YENİ_KURALLAR
(Projeye eklenecek genel geçer yeni kurallar)
##### KARAR_GÜNLÜĞÜ
(Alınan teknik kararlar ve nedenleri)
##### TEKNİK_BORÇ
(Düzeltilmesi gereken, ertelenmiş sorunlar)
##### DX_RAPORU
(Geliştirici deneyimini engelleyen sürtünme noktaları ve tavsiyeler)"""

        prompt = f"Aşağıdaki logları analiz et ve formatlı şekilde raporla:\n\n{logs}"

        try:
            response_text = self.llm_client.generate_content(prompt=prompt, system_prompt=sys_prompt)
            self._distribute_insights_to_files(response_text)
            return "✅ Sentez tamamlandı. İçgörüler Aimemory dosyalarına aktarıldı.\n\n" + response_text
        except Exception as e:
            logger.error(f"Sentez hatası: {e}")
            return f"[-] Sentez sırasında hata oluştu: {str(e)}"

    def _extract_section(self, text: str, section_name: str) -> str:
        lines = text.split('\n')
        capture = False
        captured_lines = []
        for line in lines:
            if line.strip().startswith(f"##### {section_name}"):
                capture = True
                continue
            if capture and line.strip().startswith("##### "):
                break
            if capture and line.strip():
                captured_lines.append(line)
        return "\n".join(captured_lines)

    def _distribute_insights_to_files(self, response_text: str):
        yeni_kurallar = self._extract_section(response_text, "YENİ_KURALLAR")
        kararlar = self._extract_section(response_text, "KARAR_GÜNLÜĞÜ")
        
        if yeni_kurallar:
            self._append(self.mem_dir / "mustan_instructions.md", "\n### Sentezlenmiş Yeni Kurallar\n", yeni_kurallar)
        if kararlar:
            self._append(self.mem_dir / "decision_log.md", "\n### Karar Günlüğü\n", kararlar)

    def _append(self, file_path: Path, title: str, content: str):
        try:
            mode = "a" if file_path.exists() else "w"
            with open(file_path, mode, encoding="utf-8") as f:
                f.write(f"{title}{content}\n")
        except Exception as e:
            logger.error(f"Dosyaya yazma hatası ({file_path}): {e}")

