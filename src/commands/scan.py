import os
import logging
import shutil
from pathlib import Path
from typing import Optional

from tools.analyzer import ProjectAnalyzer
from core.config import settings

logger = logging.getLogger("mustan_agent.commands.scan")

def run_scan(target_dir: str = ".", memory_dir: Optional[str] = None) -> bool:
    """
    /scan komutunun çalışma mantığıdır.
    Belirtilen dizini gelişmiş AST tabanlı analiz motoru ile tarar.
    Çıktıları JSON ve md formatlarında Aimemory/ dizinine kaydeder.
    """
    mem_dir = memory_dir or settings.config.memory.base_dir
    target_path = Path(target_dir).resolve()
    
    logger.info(f"Tarama başlatılıyor. Hedef: {target_path}")
    print(f"\n[>] Gelişmiş Keşif Ajanı (AST Explorer) '{target_path.name}' dizinini tarıyor...")
    
    if not target_path.exists() or not target_path.is_dir():
        print(f"[-] Hata: Hedef dizin bulunamadı ({target_path})")
        return False

    try:
        # AST iskeletini çıkar, Grafikleri oluştur ve JSON + TXT olarak yaz
        ProjectAnalyzer.scan_directory(str(target_path), memory_dir=mem_dir)
        
        txt_output = Path(mem_dir) / "proje_mind.md"
        json_output = Path(mem_dir) / "proje_mind.json"
            
        print(f"[+] Proje Zihin Haritası ve Call Graph başarıyla oluşturuldu!")
        print(f"[+] Kayıt yerleri:\n  - {txt_output}\n  - {json_output}")
        logger.info(f"Tarama tamamlandı ve {mem_dir} dizinine kaydedildi.")
        
        return True
        
    except Exception as e:
        logger.error(f"Tarama sırasında beklenmeyen hata: {str(e)}")
        print(f"\n[-] Tarama başarısız oldu: {str(e)}")
        return False
