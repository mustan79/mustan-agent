import os
import logging
from pathlib import Path
from typing import Optional

from core.config import settings

# Loglama ayarı (Uygulama genelindeki loglayıcıyı kullanır)
logger = logging.getLogger("mustan_agent.commands.scope")

def run_scope(rules: str, memory_dir: Optional[str] = None) -> bool:
    """
    /scope komutunun çalışma mantığıdır.
    Kullanıcının verdiği veya ajanın belirlediği proje kurallarını (scope)
    Aimemory/mustan_instructions.md dosyasına kalıcı olarak mühürler.
    
    Bu kurallar, Koordinatör ve İşçi ajanlar çalışırken JIT (Just-in-Time)
    Prompting ile bağlama (context) otomatik olarak dahil edilir.
    """
    mem_dir = memory_dir or settings.config.memory.base_dir
    instructions_path = Path(mem_dir) / "mustan_instructions.md"
    
    logger.info("Scope (Proje Kuralları) mühürleme işlemi başlatılıyor...")

    if not rules.strip():
        print(instructions_path.read_text(encoding="utf-8") if instructions_path.exists() else "[~] Henüz proje kuralı yok.")
        return True

    try:
        # Hafıza dizinini oluştur (eğer yoksa)
        os.makedirs(mem_dir, exist_ok=True)

        # Dosya daha önceden varsa üzerine ekle (append), yoksa sıfırdan yarat (write)
        mode = "a" if instructions_path.exists() else "w"
        
        with open(instructions_path, mode, encoding="utf-8") as f:
            if mode == "w":
                # Yeni dosya için başlık şablonu
                f.write("# MustanAgent Proje Kuralları (Scope)\n")
                f.write("Bu dosya /scope komutu ile mühürlenmiş proje standartlarını içerir.\n")
                f.write("Ajan kod yazarken veya plan yaparken bu kurallara KESİNLİKLE uymak zorundadır.\n\n")
                f.write("## Aktif Kurallar:\n")
            
            # Yeni kuralı bir liste maddesi olarak mühürle
            f.write(f"- {rules.strip()}\n")

        print(f"\n[+] Proje kuralları başarıyla mühürlendi!")
        print(f"[+] Kayıt yeri: {instructions_path}")
        print(f"    (Eklenen Kural: '{rules.strip()}')")
        
        logger.info(f"Yeni kurallar {instructions_path} dosyasına mühürlendi.")
        return True

    except Exception as e:
        logger.error(f"Kurallar mühürlenirken hata oluştu: {str(e)}")
        print(f"\n[-] Scope mühürleme başarısız oldu: {str(e)}")
        return False


