"""
MustanAgent v3.3 PRO - /operate komutu
Otonom görev yürütücü.
Thought → Tool Call → Observation döngüsü.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import List

from core.runtime import AgentRuntime
from core.config import settings

logger = logging.getLogger("mustan_agent.commands.operate")


OPERATE_SYSTEM_PROMPT = """Sen MustanAgent'ın otonom operatörüsün.
Kullanıcının verdiği görevi adım adım yerine getirirsin.

ZORUNLU KURALLAR:
1. Her yanıtında önce <thought>...</thought> bloğu yaz.
2. Kod veya komut yazmadan önce mutlaka düşün.
3. Araç çağrılarını şu formatta yap:

```bash
komut buraya
```

veya

```smart_edit
file_path: src/ornek.py
old_text: eski kod
new_text: yeni kod
```

veya

```read_file
path: src/ornek.py
```

4. Görev bittiğinde <final>TAMAMLANDI: kısa özet</final> yaz.
5. Hata alırsan aynı hatayı körü körüne tekrarlama; strateji değiştir.
6. Maksimum 12 adımda bitirmeye çalış.
"""


def _get_memory_dir() -> str:
    try:
        return settings.config.memory.base_dir or "Aimemory"
    except Exception:
        return "Aimemory"


def run_operate(args: str) -> bool:
    task = (args or "").strip()
    if not task:
        print("[-] /operate için görev açıklaması gerekli.")
        print("    Örnek: /operate src/auth klasörüne basit login fonksiyonu ekle")
        return False

    memory_dir = _get_memory_dir()
    os.makedirs(memory_dir, exist_ok=True)

    context_parts: List[str] = [f"GÖREV:\n{task}\n"]

    mind_path = Path(memory_dir) / "proje_mind.md"
    if mind_path.exists():
        context_parts.append("PROJE ZİHİN HARİTASI (özet):\n")
        context_parts.append(mind_path.read_text(encoding="utf-8")[:6000])
        context_parts.append("\n")

    dag_path = Path(memory_dir) / "dag_plan.json"
    if dag_path.exists():
        try:
            dag_data = json.loads(dag_path.read_text(encoding="utf-8"))
            ready = [
                n for n in dag_data.get("nodes", {}).values()
                if n.get("status") in ("ready", "pending")
            ]
            if ready:
                context_parts.append("HAZIR İŞ PAKETLERİ:\n")
                for n in ready[:5]:
                    context_parts.append(f"- {n.get('id')}: {n.get('title')}\n")
        except Exception:
            pass

    initial_prompt = "\n".join(context_parts)

    print(f"[*] Operate başlatıldı → {task[:80]}{'...' if len(task) > 80 else ''}")
    print("    Thought → Tool → Observation döngüsü çalışıyor...\n")

    runtime = AgentRuntime()
    try:
        result = runtime.run_agent_loop(
            initial_prompt=initial_prompt,
            system_prompt=OPERATE_SYSTEM_PROMPT,
        )
        print("\n[+] Operate tamamlandı.")
        print(result[:2000] if result else "(boş sonuç)")
        return True
    except Exception as e:
        logger.exception("Operate hatası")
        print(f"[-] Operate başarısız: {e}")
        return False


if __name__ == "__main__":
    import sys
    arg = " ".join(sys.argv[1:]) or "Basit bir hello.py dosyası oluştur ve çalıştır"
    ok = run_operate(arg)
    raise SystemExit(0 if ok else 1)
