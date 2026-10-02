"""
MustanAgent v3.3 PRO - /operate Komutu
Otonom Görev Yürütücü: Sistem Keşfi -> Planlama -> Çalıştırma -> Kanıt Doğrulama (Verifier)
"""

from __future__ import annotations

import json
import logging
import os
import platform
import sys
from pathlib import Path
from typing import Dict, Any, List

from core.runtime import AgentRuntime
from core.config import settings
from core.query_engine import LLMClient

logger = logging.getLogger("mustan_agent.commands.operate")


def _get_pc_system_info() -> Dict[str, str]:
    """Sistem ortam bilgilerini toplayarak LLM'in OS hataları yapmasını engeller."""
    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "python_version": sys.version.split()[0],
        "working_dir": os.getcwd(),
        "shell_hint": "cmd/powershell (Windows)" if platform.system() == "Windows" else "bash/zsh (Unix)"
    }


def _generate_execution_plan(task: str, sys_info: Dict[str, str], project_mind: str) -> List[str]:
    """Görev başlamadan önce adımları belirleyen Planner modülü."""
    llm = LLMClient()
    planner_prompt = f"""
Sen MustanAgent Task Planner modülüsün.
Kullanıcı Görevi: {task}

Sistem Ortamı:
- OS: {sys_info['os']} ({sys_info['shell_hint']})
- Çalışma Dizini: {sys_info['working_dir']}

Proje Özeti:
{project_mind[:2000]}

Görevi başarmak için yapılması gereken net, sıralı adımları liste yap (En fazla 5 adım).
Sadece adımları JSON listesi olarak döndür. Örnek format:
["1. Dizin ve readme.md dosyasının varlığını kontrol et", "2. Dosyayı oku", "3. İçeriğe alibaba metnini ekle ve yaz", "4. Dosyayı tekrar okuyarak doğrula"]
"""
    try:
        response, _ = llm.generate_with_stats(prompt=planner_prompt, temperature=0.1)
        # JSON ayrıştırma
        start = response.find("[")
        end = response.rfind("]") + 1
        if start != -1 and end != -1:
            plan = json.loads(response[start:end])
            if isinstance(plan, list) and plan and all(isinstance(step, str) for step in plan):
                return plan[:5]
    except Exception as e:
        logger.warning(f"Plan oluşturulurken hata alındı, varsayılan plana geçiliyor: {e}")
    
    return [
        f"1. Ortamı ve hedef dosyaları incele ({sys_info['os']})",
        "2. İstenen değişikliği/eylemi gerçekleştir",
        "3. İşlem sonucunu oku ve doğrula (Kanıt üret)",
        "4. Görevi tamamla"
    ]


def _get_memory_dir() -> str:
    try:
        return settings.config.memory.base_dir or "Aimemory"
    except Exception:
        return "Aimemory"


def run_operate(args: str) -> bool:
    task = (args or "").strip()
    if not task:
        print("[-] /operate için görev açıklaması gerekli.")
        print("    Örnek: /operate readme.md oku ve içine alibaba yaz")
        return False

    memory_dir = _get_memory_dir()
    os.makedirs(memory_dir, exist_ok=True)

    # 1. PC Sistem Bilgisini Topla
    sys_info = _get_pc_system_info()
    
    logger.info(f"🚀 MUSTAN AGENT v3.3 OPERATE BAŞLATILDI")
    logger.info(f"💻 Sistem Bilgisi  : {sys_info['os']} ({sys_info['architecture']}) | Shell: {sys_info['shell_hint']}")
    logger.info(f"📁 Çalışma Dizini  : {sys_info['working_dir']}")
    logger.info(f"🎯 Hedef Görev     : {task}")

    # 2. Proje Zihin Haritası Okuma
    project_mind = ""
    mind_path = Path(memory_dir) / "proje_mind.md"
    if mind_path.exists():
        project_mind = mind_path.read_text(encoding="utf-8")

    # 3. Adım Adım Plan Oluştur (Planner)
    print("📋 [PLANNER] Görev analiz ediliyor ve adımlar belirleniyor...")
    plan_steps = _generate_execution_plan(task, sys_info, project_mind)
    
    print("📝 Oluşturulan İcra Planı:")
    for step in plan_steps:
        print(f"   {step}")
    print("-" * 60)

    # 4. Prompt Yapılandırması
    system_prompt = f"""Sen MustanAgent'ın v3.3 Otonom Operatörüsün.
Kullanıcının görevini adım adım gerçekleştireceksin.

SİSTEM VE ORTAM BİLGİLERİ:
- İşletim Sistemi: {sys_info['os']}
- Kabuk İpucu: {sys_info['shell_hint']}
- Çalışma Dizini: {sys_info['working_dir']}

İCRA PLANI:
{json.dumps(plan_steps, ensure_ascii=False, indent=2)}

ZORUNLU MİMARİ KURALLAR:
1. Her yanıtında önce <thought>...</thought> bloğunda yapacağın işlemi açıkla.
2. Araçları şu formatlarda çağır:
```read_file
path: dosya_yolu.txt

```

```write_file
path: dosya_yolu.txt
content: yazılacak içerik

```

```bash
komut

```

3. KANIT KURALI: Bir dosyayı yazdıktan veya değiştirdikten sonra KESİNLİKLE 'read_file' ile okuyup kontrol etmelisin.
4. GÖREV BİTİŞ KURALI: Doğrulama tamamlandığında <thought>Doğrulamalar tamamlandı.</thought> ve <final>Yapılan işlemler özeti</final> ile bitir.
5. Dosya araçlarında JSON nesnesi kullanabilirsin: {{"file_path": "hello.py", "content": "print('hello')\n"}}. Girintileri koru.
"""
    initial_prompt = f"GÖREV: {task}\n\nLütfen belirlenen icra planına uygun olarak ilk adımla başla."
    runtime = AgentRuntime(system_info=sys_info)
    try:
        result = runtime.run_agent_loop(
            initial_prompt=initial_prompt,
            system_prompt=system_prompt,
            max_steps=12
        )
        print("\n" + "=" * 60)
        print("🏁 OPERATE İŞLEM RAPORU")
        print("=" * 60)
        print(result if result else "(Boş sonuç)")
        print("=" * 60)
        if not result or result.lstrip().startswith("[-]"):
            return False
        return True
    except Exception as e:
        logger.exception("Operate hatası")
        print(f"\n[-] Operate başarısız oldu: {e}")
        return False


