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


WORKER_SYSTEM_PROMPT = """Sen MustanAgent Worker ajanısın.
Sana bir iş paketi (WP) ve varsa DeepPlan checklist'i verilecek.
Görevin: Bu paketi eksiksiz tamamlamak.

ZORUNLU KURALLAR:
1. Her yanıtında önce <thought>...</thought> yaz.
2. Kod yazmadan önce mevcut dosyaları oku (read_file).
3. Değişiklikleri smart_edit veya write_file ile yap.
4. Sözdizimi hatası olan kod yazma.
5. İş bittiğinde <final>TAMAMLANDI: kısa özet + üretilen dosyalar</final> yaz.
6. Hata alırsan aynı hatayı tekrarlama; strateji değiştir.
"""


class WorkerAgent(BaseAgent):
    def __init__(self, memory_dir: str = "Aimemory"):
        super().__init__(memory_dir)
        self.runtime = AgentRuntime()
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
            wp_id = f"WP-{wp_id}" if wp_id.isdigit() else wp_id

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
        parts.append("Yukarıdaki iş paketini tamamla. <final> ile bitir.")
        initial_prompt = "\n".join(parts)

        try:
            result = self.runtime.run_agent_loop(
                initial_prompt=initial_prompt,
                system_prompt=WORKER_SYSTEM_PROMPT,
                max_steps=12,
            )
        except Exception as e:
            logger.exception("Worker runtime hatası")
            self.dag.mark_failed(wp_id, str(e))
            print(f"[-] Worker hata: {e}")
            self.log_action("WorkerAgent Failed", str(e))
            return False

        success = any(
            x in (result or "").lower()
            for x in ("tamamlandı", "done", "success", "başarılı")
        )

        if success:
            artifacts = self._extract_artifacts(result or "")
            art_dir = Path(self.memory_dir) / "artifacts" / wp_id
            art_dir.mkdir(parents=True, exist_ok=True)
            ok, msg = self.dag.mark_done(wp_id, artifacts=artifacts)
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
