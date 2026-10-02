"""
MustanAgent v3.3 PRO - WorkerAgent
DAGManager üzerinden durum günceller; otonom kodlama döngüsü çalıştırır.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, List

from agents.base import BaseAgent
from core.runtime import AgentRuntime
from memory.dag_manager import DAGManager
from models.datatypes import WPStatus

logger = logging.getLogger("mustan_agent.agents.worker")


WORKER_SYSTEM_PROMPT = """Sen MustanAgent Worker ajanısın. Görevin sana verilen iş paketini (WP) eksiksiz tamamlamaktır.

KESİN YANIT FORMATI ZORUNLULUĞU:
Sistem bir otomasyondur ve yanıtların bir yazılım tarafından (Regex ile) ayrıştırılacaktır. Bu yüzden sohbet etme, açıklama yapma, kurallar hakkında yorum yapma! YALNIZCA aşağıdaki şablonlara BİREBİR uy. 

Her yanıtın İSTİSNASIZ BİR ŞEKİLDE <thought> bloğu ile başlamak ZORUNDADIR. <thought> etiketleri dışında asla düz metin yazma.

--- ŞABLON 1: ARAÇ (TOOL) KULLANIRKEN ---
<thought>
Buraya adım adım ne yapacağını ve ne düşündüğünü yazacaksın.
</thought>
```bash
ls -la

```

--- ŞABLON 2: GÖREVİ BİTİRİRKEN ---

<thought>Doğrulamalar tamamlandı.</thought>
<final>Görev başarıyla tamamlandı. İşte sonuçlar: ...</final>

GEÇERLİ ARAÇLAR (Sadece Markdown formatında):

1. Bash için: `bash \n komut \n`
2. Dosya okumak için: `read_file \n path: dosya_yolu.txt \n`
3. Dosya yazmak için: `write_file \n path: dosya.txt \n content: icerik \n`
4. Dosya düzenlemek için: `smart_edit \n path: dosya.txt \n old_text: eski \n new_text: yeni \n`

UNUTMA: <thought> ve <final> etiketlerinin DIŞINDA tek bir kelime bile normal metin yazman YASAKTIR. Sadece düşünce bloğu ve ardından araç kodu ya da  etiketi kullan.
"""


class WorkerAgent(BaseAgent):
    def __init__(self, memory_dir: str = "Aimemory"):
        super().__init__(memory_dir)
        self.runtime = AgentRuntime(memory_dir=memory_dir)
        self.dag = DAGManager(memory_dir)

    def _load_deeplan(self, wp_id: str) -> str:
        path = Path(self.memory_dir) / "deeplans" / f"{wp_id}.md"
        if path.exists():
            try:
                return path.read_text(encoding="utf-8")
            except Exception:
                pass
        return ""

    def _extract_artifacts(self, final_text: str) -> List[str]:
        candidates = re.findall(
            r"[\w./\\-]+\.(?:py|md|json|yaml|yml|txt|toml)",
            final_text or "",
        )
        return list(dict.fromkeys(candidates))

    def execute_task(self, wp_id: str, force: bool = False, **kwargs: Any) -> bool:
        if not wp_id:
            print("[-] WorkerAgent: wp_id gerekli")
            return False

        wp_id = wp_id.strip().upper()
        if not wp_id.startswith("WP-"):
            wp_id = f"WP-{int(wp_id):03d}" if wp_id.isdigit() else wp_id

        self.log_action("WorkerAgent Start", f"WP: {wp_id} | force={force}")

        if not self.dag.exists():
            print("[-] dag_plan.json yok. Önce /plan çalıştırın.")
            return False

        wp = self.dag.get_wp(wp_id)
        if wp is None:
            print(f"[-] {wp_id} plan içinde yok.")
            return False

        if wp.status == WPStatus.DONE and not force:
            print(f"[~] {wp_id} zaten tamamlanmış.")
            return True

        if wp.status == WPStatus.BLOCKED and not force:
            print(f"[-] {wp_id} engellenmiş (blocked).")
            return False

        if wp.status not in (WPStatus.READY, WPStatus.FAILED) and not force:
            self.dag.refresh_ready()
            wp = self.dag.get_wp(wp_id)
            if wp is None or (wp.status != WPStatus.READY and not force):
                print(
                    f"[-] {wp_id} henüz ready değil "
                    f"(status={wp.status.value if wp else '?'})."
                )
                return False

        ok, msg = self.dag.mark_running(wp_id, force=force)
        if not ok:
            print(f"[-] Durum güncellenemedi: {msg}")
            return False
        print(f"[*] Worker → {msg}")
        print(f"    {wp_id}: {wp.title}")

        deeplan = self._load_deeplan(wp_id)
        mind = ""
        mind_path = Path(self.memory_dir) / "proje_mind.md"
        if mind_path.exists():
            try:
                mind = mind_path.read_text(encoding="utf-8")[:5000]
            except Exception:
                pass

        parts = [
            f"## İş Paketi: {wp.id}",
            f"**Başlık:** {wp.title}",
            f"**Açıklama:** {wp.description}",
            f"**Bağımlılıklar:** {wp.depends_on or 'yok'}",
            f"**Etiketler:** {wp.tags or 'yok'}",
            "",
        ]
        if deeplan:
            parts += ["## DeepPlan Checklist", deeplan, ""]
        if mind:
            parts += ["## Proje Zihin Haritası (özet)", mind, ""]
        if wp.error_log:
            parts += ["## Önceki hata (onarılmalı)", wp.error_log, ""]
        parts.append("Yukarıdaki iş paketini tamamla. <final> ile bitir.")
        initial_prompt = "\n".join(parts)

        try:
            result = self.runtime.run_agent_loop(
                initial_prompt=initial_prompt,
                system_prompt=WORKER_SYSTEM_PROMPT,
                max_steps=30,
            )
        except Exception as e:
            logger.exception("Worker runtime hatası")
            self.dag.mark_failed(wp_id, str(e))
            print(f"[-] Worker hata: {e}")
            self.log_action("WorkerAgent Failed", str(e))
            return False

        success = bool(getattr(self.runtime, "completed", False))

        if success:
            artifacts = sorted(self.runtime.modified_files) or self._extract_artifacts(result or "")
            art_dir = Path(self.memory_dir) / "artifacts" / wp_id
            art_dir.mkdir(parents=True, exist_ok=True)
            ok, msg = self.dag.mark_done(wp_id, artifacts=artifacts)
            if not ok:
                print(f"[-] {msg}")
                return False
            print(f"[+] {msg}")
            if artifacts:
                print(f"    Üretilenler: {', '.join(artifacts)}")
            self.log_action("WorkerAgent Complete", f"{wp_id} | {artifacts}")
            return True

        err = (result or "Bilinmeyen hata")[:500]
        ok, msg = self.dag.mark_failed(wp_id, err)
        print(f"[-] {msg}")
        print(f"    {err[:200]}")
        self.log_action("WorkerAgent Failed", err)
        return False

    def repair_task(self, wp_id: str) -> bool:
        wp_id = wp_id.strip().upper()
        if wp_id.isdigit():
            wp_id = f"WP-{int(wp_id):03d}"
        wp = self.dag.get_wp(wp_id)
        if wp is None or wp.status != WPStatus.FAILED:
            print("[-] Yalnızca başarısız iş paketleri onarılabilir.")
            return False
        if not wp.can_retry():
            print("[-] Onarım denemesi sınırı doldu.")
            return False
        return self.execute_task(wp_id)
