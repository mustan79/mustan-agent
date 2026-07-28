import os
import platform
import subprocess
import logging
from pathlib import Path
from typing import Dict

# Kendi yazdığımız kural okuyucusunu çağırıyoruz
from memory.workspace_md import get_workspace_rules

logger = logging.getLogger("mustan_agent.memory.context")

def get_git_status() -> str:
    """projenin mevcut Git durumunu (varsa) çeker."""
    try:
        # Eğer git dizini yoksa hata vermemesi için timeout ile çalıştır
        result = subprocess.run(
            ["git", "status", "-s"], 
            capture_output=True, 
            text=True, 
            timeout=2,
            cwd=str(Path.cwd())
        )
        if result.returncode == 0:
            changes = result.stdout.strip()
            return f"Git Değişiklikleri:\n{changes}" if changes else "Git: Temiz (Değişiklik yok)"
    except Exception:
        pass
    return "Git reposu bulunamadı veya git yüklü değil."

def build_system_context() -> str:
    """
    LLM'in her promptunun başına eklenecek olan dinamik ortam bilgilerini oluşturur.
    (İşletim sistemi, dizin, git durumu ve mühürlü proje kuralları)
    """
    os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"
    cwd = str(Path.cwd())
    git_info = get_git_status()
    rules = get_workspace_rules()

    context_parts = [
        f"### AKTİF ÇALIŞMA BAĞLAMI",
        f"- **OS:** {os_info}",
        f"- **Dizin:** {cwd}",
        f"- **{git_info}**"
    ]
    
    if rules:
        context_parts.append(f"\n### PROJE KURALLARI (Kesinlikle Uyulacak):\n{rules}")
        
    return "\n".join(context_parts)

