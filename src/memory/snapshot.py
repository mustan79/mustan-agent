# Dosya Yolu:** `src/memory/snapshot.py`
import os
import shutil
import logging
from pathlib import Path
from core.config import settings

logger = logging.getLogger("mustan_agent.memory.snapshot")

def restore_checkpoint(checkpoint_id: str) -> str:
    """
    Belirtilen checkpoint_id (yedek klasörü) içeriğini ana projeye geri yükler.
    Zaman yolculuğu (/rewind) komutunun çekirdek aracıdır.
    """
    try:
        # Yedeklerin (snapshot) tutulduğu ana dizin
        mem_dir = settings.config.memory.base_dir
        snapshot_base_dir = Path(mem_dir) / "snapshots"
        target_snapshot = snapshot_base_dir / checkpoint_id

        if not target_snapshot.exists():
            return f"[-] Hata: '{checkpoint_id}' adında bir yedek bulunamadı. Lütfen 'Aimemory/snapshots/' klasörünü kontrol edin."

        # Projenin çalıştırıldığı kök dizin
        project_root = Path(os.getcwd())

        # Geri yükleme işlemi (Snapshot içindeki her şeyi projeye yaz)
        for item in target_snapshot.glob("*"):
            target_path = project_root / item.name
            if item.is_file():
                shutil.copy2(item, target_path)
            elif item.is_dir():
                shutil.copytree(item, target_path, dirs_exist_ok=True)

        logger.info(f"Checkpoint '{checkpoint_id}' başarıyla geri yüklendi.")
        return f"[+] Proje başarıyla '{checkpoint_id}' durumuna sarıldı!"
        
    except Exception as e:
        logger.error(f"Geri sarma hatası: {str(e)}")
        return f"[-] Geri sarma işlemi başarısız oldu: {str(e)}"


