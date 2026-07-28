import logging
from memory.snapshot import restore_checkpoint

logger = logging.getLogger("mustan_agent.commands.rewind")

def run_rewind(checkpoint_id: str) -> bool:
    """
    /rewind komutu.
    Git commitlerinden bağımsız olarak Aimemory/snapshots içindeki bir yedeği geri yükler.
    """
    if not checkpoint_id.strip():
        print("[-] Lütfen dönülecek yedek (checkpoint) adını girin.")
        print("    Örn: /rewind cp_20260404_120000_auto")
        return False

    print(f"\n[>] Zaman Yolculuğu Başlatılıyor... Hedef: '{checkpoint_id}'")
    
    result = restore_checkpoint(checkpoint_id.strip())
    print(f"\n{result}")
    
    # '[+]' stringi başarılı işlemlerin prefix'idir (snapshot.py'de tanımlandığı üzere)
    if result.startswith("[+]"):
        logger.info(f"Proje başarıyla {checkpoint_id} durumuna sarıldı.")
        return True
        
    logger.error(f"Geri sarma başarısız: {result}")
    return False


