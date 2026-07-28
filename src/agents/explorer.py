import logging
from typing import Any

from agents.base import BaseAgent
from commands.scan import run_scan

logger = logging.getLogger("mustan_agent.agents.explorer")

class ExplorerAgent(BaseAgent):
    """
    Sistemin Keşif Ajanı.
    Kod tabanını tarar, AST iskeletini çıkarır ve proje zihin haritasını oluşturur.
    Değişiklik yapma yetkisi (Write) yoktur.
    """
    def __init__(self, memory_dir: str = "Aimemory"):
        super().__init__(memory_dir)

    def execute_task(self, task_description: str, target_dir: str = ".", **kwargs) -> Any:
        self.log_action("ExplorerAgent Start", f"Hedef: {target_dir} | Görev: {task_description}")
        
        # Daha önce yazdığımız scan komut fonksiyonunu yeniden kullanarak modülerliği koruyoruz
        success = run_scan(target_dir=target_dir, memory_dir=self.memory_dir)
        
        if success:
            self.log_action("ExplorerAgent Complete", f"Zihin haritası başarıyla çıkarıldı: {target_dir}")
            return True
        else:
            self.log_action("ExplorerAgent Error", "Tarama işlemi başarısız oldu.")
            return False
