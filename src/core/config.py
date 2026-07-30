"""
MustanAgent v3.3 PRO - Yapılandırma Yönetimi
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("mustan_agent.core.config")


class LLMSettings(BaseModel):
    """Dil modeli ve API bağlantı ayarları.
    API anahtarları burada tutulmaz; MustanVault üzerinden çekilir.
    """
    provider: str = Field(
        default="gemini",
        description="gemini | openai | openrouter | ollama | ollama_cloud",
    )
    model: str = Field(default="gemini-2.5-flash-lite")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    daily_budget_usd: float = Field(default=5.0, ge=0.0)

    # Ollama / Ollama Cloud özel
    ollama_base_url: str = Field(
        default="https://ollama.com/v1",
        description="Ollama Cloud veya self-hosted OpenAI-compatible endpoint",
    )
#    ollama_model: str = Field(default="gemma-4-31b-it")


class MemorySettings(BaseModel):
    base_dir: str = Field(default="Aimemory")
    max_log_lines: int = Field(default=500)


class WorkspaceSettings(BaseModel):
    project_rules_file: str = Field(default="mustan_instructions.md")


class MustanConfigSchema(BaseModel):
    llm: LLMSettings = Field(default_factory=LLMSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    workspace: WorkspaceSettings = Field(default_factory=WorkspaceSettings)


class ConfigManager:
    def __init__(self, config_filename: str = "mustan_settings.json"):
        self.config_path = Path(config_filename)
        self.config: MustanConfigSchema = self._load_config()

    def _load_config(self) -> MustanConfigSchema:
        if not self.config_path.exists():
            cfg = MustanConfigSchema()
            self.save_config(cfg)
            return cfg
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            return MustanConfigSchema.model_validate(data)
        except Exception as e:
            logger.warning("Config okunamadı, varsayılan yükleniyor: %s", e)
            return MustanConfigSchema()

    def save_config(self, cfg: Optional[MustanConfigSchema] = None) -> bool:
        cfg = cfg or self.config
        try:
            self.config_path.write_text(
                cfg.model_dump_json(indent=2),
                encoding="utf-8",
            )
            self.config = cfg
            return True
        except Exception as e:
            logger.error("Config kaydedilemedi: %s", e)
            return False

    def update_llm_model(self, new_model: str, provider: Optional[str] = None) -> None:
        self.config.llm.model = new_model
        if provider:
            self.config.llm.provider = provider
        self.save_config()

    def update_provider(
        self,
        provider: str,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self.config.llm.provider = provider.lower()
        if model:
            self.config.llm.model = model
        if base_url and provider.lower() in ("ollama", "ollama_cloud"):
            self.config.llm.ollama_base_url = base_url
        self.save_config()


# Global erişim
settings = ConfigManager()


