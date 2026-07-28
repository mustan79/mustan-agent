import os
import json
import logging
from datetime import datetime
from core.config import settings

logger = logging.getLogger("mustan_agent.memory.stats")

# Örnek Maliyetler (Gemini 1.5 Pro veya OpenAI baz alınmıştır)
# 1M Token Input = $1.25, 1M Token Output = $5.00
COST_PER_1K_INPUT = 0.00125
COST_PER_1K_OUTPUT = 0.00500

def record_usage(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Her LLM çağrısında Aimemory/stats.json dosyasını günceller.
    Harcanan dolar maliyetini döndürür.
    """
    mem_dir = settings.config.memory.base_dir
    stats_path = os.path.join(mem_dir, settings.config.memory.stats_file)
    os.makedirs(mem_dir, exist_ok=True)

    stats = {
        "total_prompt_tokens": 0, 
        "total_completion_tokens": 0, 
        "total_cost_usd": 0.0, 
        "history": []
    }
    
    if os.path.exists(stats_path):
        try:
            with open(stats_path, "r", encoding="utf-8") as f:
                stats = json.load(f)
        except Exception:
            logger.warning("stats.json bozulmuş, istatistikler sıfırlanıyor.")

    # Maliyet hesaplama
    cost = (prompt_tokens / 1000 * COST_PER_1K_INPUT) + (completion_tokens / 1000 * COST_PER_1K_OUTPUT)

    # Güncelleme
    stats["total_prompt_tokens"] += prompt_tokens
    stats["total_completion_tokens"] += completion_tokens
    stats["total_cost_usd"] += cost

    # Geçmişe ekle
    stats["history"].append({
        "timestamp": datetime.now().isoformat(),
        "model": model_name,
        "input": prompt_tokens,
        "output": completion_tokens,
        "cost": round(cost, 6)
    })

    # Dosyaya kaydet
    try:
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=4)
    except Exception as e:
        logger.error(f"İstatistikler kaydedilemedi: {str(e)}")

    return cost

