"""
MustanAgent v3.3 PRO - Query Engine & LLMClient
Desteklenen provider'lar: gemini, openai, openrouter, ollama, ollama_cloud
CostTracker + RAG + Telemetry entegrasyonu.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from core.config import settings
from core.vault import MustanVault
from core.cost_tracker import get_cost_tracker, CostTracker
from memory.rag_buffer import get_rag_buffer, RAGBuffer
from core.telemetry import track_llm, get_telemetry

logger = logging.getLogger("mustan_agent.core.query_engine")


class QueryDeps(BaseModel):
    tools: List[Any] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LLMClient:
    _instance: Optional["LLMClient"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self.vault = MustanVault()
        try:
            budget = settings.config.llm.daily_budget_usd
        except Exception:
            budget = 5.0
        from pathlib import Path
        self.cost_tracker: CostTracker = get_cost_tracker(daily_limit=budget, stats_path=str(Path(settings.config.memory.base_dir) / "stats.json"))
        self._rag: Optional[RAGBuffer] = None
        self._initialized = True

    def _get_env_or_vault(self, key_name: str) -> Optional[str]:
        value = os.environ.get(key_name)
        if value:
            return value
        try:
            return self.vault.get_secret(key_name)
        except Exception:
            return None

    def _get_active_model_and_provider(self) -> Tuple[str, str]:
        try:
            llm_cfg = settings.config.llm
            provider = (llm_cfg.provider).lower()
            model = llm_cfg.model
        except Exception:
            provider, model = "gemini", "gemini-2.5-flash-lite"

        return provider, model

    def _get_rag(self, memory_dir: Optional[str] = None) -> RAGBuffer:
        if memory_dir is None:
            try:
                memory_dir = settings.config.memory.base_dir or "Aimemory"
            except Exception:
                memory_dir = "Aimemory"
        if self._rag is None or str(self._rag.memory_dir) != memory_dir:
            self._rag = get_rag_buffer(memory_dir)
        return self._rag

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def _call_gemini(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: str,
        temperature: float = 0.3,
        images: Optional[List[Any]] = None,
    ) -> Tuple[str, int, int]:
        try:
            from google import genai
            from google.genai import types
        except ImportError as e:
            raise RuntimeError("google-genai paketi yüklü değil") from e

        api_key = self._get_env_or_vault("GEMINI_API_KEY") or self._get_env_or_vault("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY / GOOGLE_API_KEY bulunamadı")

        client = genai.Client(api_key=api_key)
        contents = []
        if system_prompt:
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=f"[SYSTEM]\n{system_prompt}")],
                )
            )
            contents.append(
                types.Content(
                    role="model",
                    parts=[types.Part.from_text(text="Anlaşıldı.")],
                )
            )
        contents.append(
            types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
        )

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=8192,
            ),
        )
        text = response.text or ""
        usage = getattr(response, "usage_metadata", None)
        in_tok = getattr(usage, "prompt_token_count", None) or self._estimate_tokens(
            prompt + (system_prompt or "")
        )
        out_tok = getattr(usage, "candidates_token_count", None) or self._estimate_tokens(text)
        return text, int(in_tok), int(out_tok)

    def _call_openai_compatible(
        self,
        provider: str,
        prompt: str,
        system_prompt: Optional[str],
        model: str,
        temperature: float = 0.3,
        base_url: Optional[str] = None,
        api_key_name: str = "OPENAI_API_KEY",
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[str, int, int]:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError("openai paketi yüklü değil") from e

        api_key = self._get_env_or_vault(api_key_name)

        if not api_key:
            if provider in ("ollama",):
                api_key = "ollama"
            else:
                raise RuntimeError(
                    f"{api_key_name} bulunamadı (Vault veya ortam değişkeni). "
                    f"/set key {api_key_name} <değer> ile ekle."
                )

        client_kwargs: Dict[str, Any] = {
            "api_key": api_key,
            "base_url": base_url,
        }
        if extra_headers:
            client_kwargs["default_headers"] = extra_headers

        client = OpenAI(**client_kwargs)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=8192,
        )
        text = resp.choices[0].message.content or ""
        usage = resp.usage
        in_tok = getattr(usage, "prompt_tokens", None) or self._estimate_tokens(
            prompt + (system_prompt or "")
        )
        out_tok = getattr(usage, "completion_tokens", None) or self._estimate_tokens(text)
        return text, int(in_tok), int(out_tok)

    def generate_content(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        images: Optional[List[Any]] = None,
        use_rag: bool = False,
        rag_query: Optional[str] = None,
        memory_dir: Optional[str] = None,
        temperature: float = 0.3,
    ) -> str:
        text, _ = self.generate_with_stats(
            prompt=prompt,
            system_prompt=system_prompt,
            images=images,
            use_rag=use_rag,
            rag_query=rag_query,
            memory_dir=memory_dir,
            temperature=temperature,
        )
        return text

    def generate_with_stats(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        images: Optional[List[Any]] = None,
        use_rag: bool = False,
        rag_query: Optional[str] = None,
        memory_dir: Optional[str] = None,
        temperature: float = 0.3,
        max_retries: int = 3,
        caller: str = "llm.generate_with_stats",
    ) -> Tuple[str, Dict[str, Any]]:
        provider, model = self._get_active_model_and_provider()
        mem = memory_dir or settings.config.memory.base_dir or "Aimemory"
        from memory.workspace_md import get_workspace_rules
        rules = get_workspace_rules(mem)
        if rules:
            system_prompt = (system_prompt or "") + "\n\nPROJE KURALLARI:\n" + rules[:5000]

        final_prompt = prompt
        if use_rag:
            try:
                rag = self._get_rag(memory_dir)
                query = rag_query or prompt[:300]
                rag_context = rag.get_context(query, top_k=4, max_chars=3500)
                if rag_context:
                    final_prompt = f"{rag_context}\n\n---\n\n{prompt}"
            except Exception as e:
                logger.warning("RAG enjeksiyonu başarısız: %s", e)

        est_in = self._estimate_tokens(final_prompt + (system_prompt or ""))
        if not self.cost_tracker.can_spend(est_in, 1500, provider):
            raise RuntimeError(
                f"Günlük bütçe limiti aşıldı. {self.cost_tracker.status_report()}"
            )

        if self.cost_tracker.is_near_limit() and provider != "ollama":
            logger.warning(
                "Bütçe soft limitine yaklaşıldı: %s",
                self.cost_tracker.status_report(),
            )

        # TELEMETRY ENTEGRASYONU
        with track_llm(caller=caller, provider=provider, model=model, memory_dir=mem) as ctx:
            last_error: Optional[Exception] = None
            for attempt in range(1, max_retries + 1):
                try:
                    if provider in ("gemini", "google"):
                        text, in_tok, out_tok = self._call_gemini(
                            final_prompt, system_prompt, model, temperature, images
                        )

                    elif provider == "ollama":
                        try:
                            base_url = settings.config.llm.ollama_base_url or "http://localhost:11434"
                        except Exception:
                            base_url = "http://localhost:11434"
                        base_url = base_url.rstrip("/")
                        if not base_url.endswith("/v1"):
                            base_url = base_url + "/v1"
                        text, in_tok, out_tok = self._call_openai_compatible(
                            provider="ollama",
                            prompt=final_prompt,
                            system_prompt=system_prompt,
                            model=model,
                            temperature=temperature,
                            base_url=base_url,
                            api_key_name="OLLAMA_API_KEY",
                        )

                    elif provider == "ollama_cloud":
                        try:
                            base_url = getattr(settings.config.llm, "ollama_base_url", None)
                        except Exception:
                            base_url = "https://ollama.com/v1"
                        text, in_tok, out_tok = self._call_openai_compatible(
                            provider="ollama_cloud",
                            prompt=final_prompt,
                            system_prompt=system_prompt,
                            model=model,
                            temperature=temperature,
                            base_url=base_url,
                            api_key_name="OLLAMA_API_KEY",
                        )

                    elif provider == "openrouter":
                        text, in_tok, out_tok = self._call_openai_compatible(
                            provider="openrouter",
                            prompt=final_prompt,
                            system_prompt=system_prompt,
                            model=model,
                            temperature=temperature,
                            base_url="https://openrouter.ai/api/v1",
                            api_key_name="OPENROUTER_API_KEY",
                            extra_headers={
                                "HTTP-Referer": "https://github.com/mustan79/mustan-agent",
                                "X-Title": "MustanAgent",
                            },
                        )

                    else:  # openai
                        text, in_tok, out_tok = self._call_openai_compatible(
                            provider="openai",
                            prompt=final_prompt,
                            system_prompt=system_prompt,
                            model=model,
                            temperature=temperature,
                            base_url=None,
                            api_key_name="OPENAI_API_KEY",
                        )

                    cost = self.cost_tracker.record(in_tok, out_tok, provider)

                    # Telemetry nesnesine token ve maliyet verilerini aktarıyoruz
                    ctx["input_tokens"] = in_tok
                    ctx["output_tokens"] = out_tok
                    ctx["total_tokens"] = in_tok + out_tok
                    ctx["cost_usd"] = cost
                    ctx["provider"] = provider
                    ctx["model"] = model

                    stats = {
                        "provider": provider,
                        "model": model,
                        "input_tokens": in_tok,
                        "output_tokens": out_tok,
                        "total_tokens": in_tok + out_tok,
                        "cost_usd": round(cost, 6),
                        "spent_today_usd": round(self.cost_tracker.spent_today, 6),
                    }
                    logger.info(
                        "LLM OK | %s/%s | %d+%d token | $%.5f",
                        provider, model, in_tok, out_tok, cost,
                    )
                    return text, stats

                except Exception as e:
                    last_error = e
                    err = str(e).lower()
                    if any(x in err for x in ("429", "rate", "503", "unavailable", "timeout")):
                        wait = min(2 ** attempt + 1, 30)
                        logger.warning(
                            "Geçici hata (deneme %d/%d), %ds bekleniyor...",
                            attempt, max_retries, wait,
                        )
                        time.sleep(wait)
                        continue
                    raise

            raise RuntimeError(
                f"LLM çağrısı {max_retries} denemeden sonra başarısız: {last_error}"
            ) from last_error


class QueryEngine:
    def __init__(
        self,
        tools: Optional[List[Any]] = None,
        deps: Optional[QueryDeps] = None,
        system_prompt: Optional[str] = None,
    ):
        self.client = LLMClient()
        self.tools = tools or []
        self.deps = deps or QueryDeps()
        self.system_prompt = system_prompt or ""

    def ask(self, prompt: str, tools: Optional[List[Any]] = None) -> str:
        return self.client.generate_content(prompt, system_prompt=self.system_prompt)

