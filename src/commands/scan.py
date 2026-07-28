import os
import logging
from pathlib import Path
from typing import Optional

from tools.analyzer import ProjectAnalyzer
from core.config import settings

logger = logging.getLogger("mustan_agent.commands.scan")

def run_scan(target_dir: str = ".", memory_dir: Optional[str] = None) -> bool:
    """
    /scan komutunun çalışma mantığıdır.
    Belirtilen dizini AST tabanlı analiz motoru ile tarar ve çıkarılan iskeleti
    Aimemory/proje_mind.md dosyasına kalıcı olarak kaydeder.
    """
    mem_dir = memory_dir or settings.config.memory.base_dir
    output_path = Path(mem_dir) / "proje_mind.md"
    
    target_path = Path(target_dir).resolve()
    logger.info(f"Tarama başlatılıyor. Hedef: {target_path}")
    print(f"\n[>] Keşif Ajanı (Explorer) '{target_path.name}' dizinini tarıyor...")
    
    if not target_path.exists() or not target_path.is_dir():
        print(f"[-] Hata: Hedef dizin bulunamadı ({target_path})")
        return False

    try:
        # 1. ProjectAnalyzer ile dizini tara (AST iskeletini çıkar)
        mind_map_content = ProjectAnalyzer.scan_directory(str(target_path))
        
        # 2. Hafıza dizinini oluştur (eğer yoksa)
        os.makedirs(mem_dir, exist_ok=True)
        
        # 3. Sonucu proje_mind.md olarak mühürle
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(mind_map_content)
            
        print(f"[+] Proje Zihin Haritası başarıyla oluşturuldu!")
        print(f"[+] Kayıt yeri: {output_path}")
        logger.info(f"Tarama tamamlandı ve {output_path} kaydedildi.")
        
        return True
        
    except Exception as e:
        logger.error(f"Tarama sırasında beklenmeyen hata: {str(e)}")
        print(f"\n[-] Tarama başarısız oldu: {str(e)}")
        return False

