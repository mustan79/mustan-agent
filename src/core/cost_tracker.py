"""
MustanAgent v3.3 PRO - Aktif Bütçe / Token Takipçisi
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("mustan_agent.core.cost_tracker")

DEFAULT_PRICES: Dict[str, Dict[str, float]] = {
    "gemini": {"input": 1.25, "output": 5.00},
    "openai": {"input": 2.50, "output": 10.00},
    "openrouter": {"input": 0.50, "output": 1.50},
    "ollama": {"input": 0.0, "output": 0.0},
    "ollama_cloud": {"input": 0.20, "output": 0.40},
    "default": {"input": 1.25, "output": 5.00},
}


class CostTracker:
    _instance: Optional["CostTracker"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        daily_limit_usd: float = 5.0,
        stats_path: Optional[str] = None,
        soft_limit_ratio: float = 0.85,
    ):
        if getattr(self, "_initialized", False):
            return
        self.daily_limit_usd = daily_limit_usd
        self.soft_limit_ratio = soft_limit_ratio
        self.stats_path = Path(stats_path or "Aimemory/stats.json")
        self.spent_today: float = 0.0
        self.input_tokens_today: int = 0
        self.output_tokens_today: int = 0
        self.last_reset: str = str(date.today())
        self._load()
        self._initialized = True

    def _load(self) -> None:
        if not self.stats_path.exists():
            return
        try:
            data = json.loads(self.stats_path.read_text(encoding="utf-8"))
            today = str(date.today())
            if data.get("date") != today:
                self._archive_and_reset(data)
                return
            self.spent_today = float(data.get("spent_usd", 0.0))
            self.input_tokens_today = int(data.get("input_tokens", 0))
            self.output_tokens_today = int(data.get("output_tokens", 0))
            self.last_reset = today
        except Exception as e:
            logger.warning("stats.json okunamadı: %s", e)

    def _archive_and_reset(self, old_data: dict) -> None:
        archive_dir = self.stats_path.parent / "stats_archive"
        archive_dir.mkdir(exist_ok=True)
        day = old_data.get("date", "unknown")
        try:
            (archive_dir / f"stats_{day}.json").write_text(
                json.dumps(old_data, indent=2), encoding="utf-8"
            )
        except Exception:
            pass
        self.spent_today = 0.0
        self.input_tokens_today = 0
        self.output_tokens_today = 0
        self.last_reset = str(date.today())
        self._save()

    def _save(self) -> None:
        self.stats_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "date": str(date.today()),
            "spent_usd": round(self.spent_today, 6),
            "input_tokens": self.input_tokens_today,
            "output_tokens": self.output_tokens_today,
            "daily_limit_usd": self.daily_limit_usd,
            "updated_at": datetime.now().isoformat(),
        }
        try:
            self.stats_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error("stats.json yazılamadı: %s", e)

    def estimate_cost(self, input_tokens: int, output_tokens: int, provider: str = "default") -> float:
        prices = DEFAULT_PRICES.get(provider.lower(), DEFAULT_PRICES["default"])
        cost = (input_tokens / 1_000_000) * prices["input"]
        cost += (output_tokens / 1_000_000) * prices["output"]
        return cost

    def can_spend(self, estimated_input: int = 2000, estimated_output: int = 1000, provider: str = "default") -> bool:
        if provider.lower() == "ollama":
            return True
        est = self.estimate_cost(estimated_input, estimated_output, provider)
        return (self.spent_today + est) <= self.daily_limit_usd

    def is_near_limit(self) -> bool:
        if self.daily_limit_usd <= 0:
            return False
        return self.spent_today >= self.daily_limit_usd * self.soft_limit_ratio

    def record(self, input_tokens: int, output_tokens: int, provider: str = "default") -> float:
        cost = self.estimate_cost(input_tokens, output_tokens, provider)
        self.spent_today += cost
        self.input_tokens_today += input_tokens
        self.output_tokens_today += output_tokens
        self._save()
        return cost

    def status_report(self) -> str:
        pct = (self.spent_today / self.daily_limit_usd * 100) if self.daily_limit_usd else 0
        return (
            f"Bugün: ${self.spent_today:.4f} / ${self.daily_limit_usd:.2f} ({pct:.1f}%) | "
            f"Token {self.input_tokens_today} in + {self.output_tokens_today} out"
        )


def get_cost_tracker(daily_limit: float = 5.0) -> CostTracker:
    return CostTracker(daily_limit_usd=daily_limit)


