"""
MustanAgent v3.3 PRO - /doctor
Uçuş öncesi sistem sağlığı kontrolü.
"""

from __future__ import annotations

import importlib.util
import logging
import shutil
import sys
from typing import List, Tuple

from core.vault import MustanVault
from core.config import settings

logger = logging.getLogger("mustan_agent.commands.doctor")


def _check_dependency(module_name: str, display_name: str) -> Tuple[bool, str]:
    spec = importlib.util.find_spec(module_name)
    if spec is None:
        return False, f"[-] {display_name} eksik (pip install {module_name})"
    return True, f"[+] {display_name} kurulu"


def _check_system_tool(command: str) -> Tuple[bool, str]:
    if shutil.which(command):
        return True, f"[+] Sistem aracı: {command}"
    return False, f"[-] Sistem aracı bulunamadı: {command}"


def _check_vault_key(key_name: str) -> Tuple[bool, str]:
    vault = MustanVault()
    try:
        val = vault.get_secret(key_name)
        if val:
            return True, f"[+] Vault: {key_name} mevcut"
        return False, f"[-] Vault: {key_name} yok"
    except Exception as e:
        return False, f"[-] Vault kontrol hatası ({key_name}): {e}"


def run_doctor() -> bool:
    print("=======================================================")
    print("🩺 MustanAgent Doctor – Sistem Sağlığı Kontrolü")
    print("=======================================================\n")

    results: List[Tuple[bool, str]] = []

    deps = [
        ("google.genai", "google-genai"),
        ("openai", "openai"),
        ("pydantic", "pydantic"),
        ("keyring", "keyring"),
        ("yaml", "PyYAML"),
        ("playwright", "playwright"),
    ]
    for mod, name in deps:
        results.append(_check_dependency(mod, name))

    for tool in ("git", "python"):
        results.append(_check_system_tool(tool))

    try:
        provider = (settings.config.llm.provider or "gemini").lower()
    except Exception:
        provider = "gemini"

    print(f"Aktif provider: {provider}\n")

    key_map = {
        "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "openai": ["OPENAI_API_KEY"],
        "openrouter": ["OPENROUTER_API_KEY"],
        "ollama": ["OLLAMA_API_KEY"],
        "ollama_cloud": ["OLLAMA_API_KEY"],
    }

    required_keys = key_map.get(provider, ["GEMINI_API_KEY"])
    key_ok = False
    for k in required_keys:
        ok, msg = _check_vault_key(k)
        results.append((ok, msg))
        if ok:
            key_ok = True

    if provider == "ollama" and not key_ok:
        results.append((True, "[~] Ollama local – API key opsiyonel"))
        key_ok = True

    print("\n--- Sonuçlar ---")
    all_critical_ok = True
    for ok, msg in results:
        print(msg)
        if not ok and "Vault" in msg and provider != "ollama":
            all_critical_ok = False
        if not ok and "eksik" in msg:
            all_critical_ok = False

    if not key_ok and provider != "ollama":
        print("\n[-] Aktif provider için API anahtarı bulunamadı.")
        print("    /set komutu veya keyring ile ekleyin.")
        print("    Örnek: /set key OLLAMA_API_KEY sk-...")
        all_critical_ok = False

    if all_critical_ok:
        print("\n[+] Doctor: Sistem uçuşa hazır.")
    else:
        print("\n[-] Doctor: Eksikler var, lütfen giderin.")

    return all_critical_ok

if __name__ == "__main__":
    ok = run_doctor()
    sys.exit(0 if ok else 1)
