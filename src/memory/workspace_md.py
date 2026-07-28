import logging
from pathlib import Path
from core.config import settings

logger = logging.getLogger("mustan_agent.memory.workspace_md")

def get_workspace_rules(memory_dir: str = None) -> str:
    """
    Aimemory/mustan_instructions.md dosyasında kayıtlı olan,
    projeye özel kural ve sınırları (scope) okuyup döner.
    """
    mem_dir = memory_dir or settings.config.memory.base_dir
    instructions_path = Path(mem_dir) / "mustan_instructions.md"
    
    if not instructions_path.exists() or not instructions_path.is_file():
        return ""

    try:
        with open(instructions_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            # İçerik çok uzunsa (token israfı) uyar
            if len(content) > 5000:
                logger.warning("mustan_instructions.md çok uzun! LLM token bütçeni tüketebilir.")
            return content
    except Exception as e:
        logger.error(f"Proje kuralları okunamadı: {str(e)}")
        return ""

