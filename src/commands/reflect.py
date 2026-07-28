import logging
from services.reflection import MustanReflectService

logger = logging.getLogger("mustan_agent.commands.reflect")

def run_reflect() -> bool:
    """
    /reflect komutu.
    Ajanın geçmiş logları tarayarak hem kuralları güncellemesini (Dream) 
    hem de Geliştirici Deneyimi (Insights) raporu sunmasını sağlar.
    """
    try:
        service = MustanReflectService()
        result = service.run_deep_reflection()
        print(f"\n{result}\n")
        return True
    except Exception as e:
        logger.error(f"/reflect komutu hatası: {str(e)}")
        print(f"[-] İçgörü döngüsü başlatılamadı: {str(e)}")
        return False

