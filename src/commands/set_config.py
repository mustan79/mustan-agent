"""
MustanAgent v3.3 PRO - /set komutu
API anahtarı ve provider ayarlarını güvenli şekilde değiştirir.
"""

from __future__ import annotations

import logging

from core.vault import MustanVault
from core.config import settings

logger = logging.getLogger("mustan_agent.commands.set_config")


def run_set(args: str) -> bool:
    """
    Kullanım:
      /set provider ollama_cloud
      /set model llama3.1
      /set key OLLAMA_API_KEY sk-...
      /set base_url https://ollama.com/api
    """
    parts = (args or "").strip().split(maxsplit=2)
    if len(parts) < 2:
        print("Kullanım:")
        print("  /set provider <gemini|openai|openrouter|ollama|ollama_cloud>")
        print("  /set model <model_adı>")
        print("  /set key <KEY_NAME> <değer>")
        print("  /set base_url <url>          # sadece ollama / ollama_cloud")
        return False

    action = parts[0].lower()
    vault = MustanVault()

    if action == "provider":
        provider = parts[1].lower()
        allowed = {"gemini", "openai", "openrouter", "ollama", "ollama_cloud"}
        if provider not in allowed:
            print(f"[-] Geçersiz provider. İzin verilenler: {', '.join(allowed)}")
            return False
        model = parts[2] if len(parts) > 2 else None
        settings.update_provider(provider, model=model)
        print(f"[+] Provider → {provider}" + (f" | model → {model}" if model else ""))
        return True

    elif action == "model":
        model = parts[1]
        settings.update_llm_model(model)
        print(f"[+] Model → {model}")
        return True

    elif action == "key":
        if len(parts) < 3:
            print("[-] /set key <KEY_NAME> <değer>")
            return False
        key_name = parts[1].upper()
        value = parts[2]
        try:
            vault.set_secret(key_name, value)
            print(f"[+] Vault'a kaydedildi: {key_name}")
            return True
        except Exception as e:
            print(f"[-] Kayıt hatası: {e}")
            return False

    elif action == "base_url":
        url = parts[1]
        try:
            settings.config.llm.ollama_base_url = url
            settings.save_config()
            print(f"[+] Ollama base_url → {url}")
            return True
        except Exception as e:
            print(f"[-] {e}")
            return False

    else:    
        print(f"[-] Bilinmeyen alt komut: {action}")
        return False
