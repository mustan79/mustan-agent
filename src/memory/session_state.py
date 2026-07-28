import os
import json
import logging
from pathlib import Path
from core.config import settings

logger = logging.getLogger("mustan_agent.memory.session_state")

def save_session_state(active_task: str, status: str = "in_progress"):
    """O anki aktif görevi ve durumu diske (session_memory.json) kaydeder."""
    mem_dir = settings.config.memory.base_dir
    state_path = Path(mem_dir) / "session_memory.json"
    
    os.makedirs(mem_dir, exist_ok=True)
    
    state_data = {
        "last_active_task": active_task,
        "status": status,
        "timestamp": __import__("datetime").datetime.now().isoformat()
    }
    
    try:
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=4)
    except Exception as e:
        logger.error(f"Oturum durumu kaydedilemedi: {str(e)}")

def load_session_state() -> dict | None:
    """Son kapatılan oturumun durumunu diskten okur."""
    state_path = Path(settings.config.memory.base_dir) / "session_memory.json"
    if state_path.exists():
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Oturum durumu okunamadı: {str(e)}")
    return None


