
"""
MustanAgent v3.3 PRO - DAGManager
Tek merkezden DAG yükleme, durum geçişi, kaydetme.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from models.datatypes import DAGPlan, WorkPackage, WPStatus

logger = logging.getLogger("mustan_agent.memory.dag_manager")


class DAGManager:
    _locks: dict[str, threading.RLock] = {}
    _global_lock = threading.Lock()

    def __init__(self, memory_dir: str = "Aimemory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.json_path = self.memory_dir / "dag_plan.json"
        self.md_path = self.memory_dir / "master_plan.md"

    def _get_lock(self) -> threading.RLock:
        key = str(self.json_path.resolve())
        with self._global_lock:
            if key not in self._locks:
                self._locks[key] = threading.RLock()
            return self._locks[key]

    def load(self) -> Optional[DAGPlan]:
        if not self.json_path.exists():
            return None
        try:
            data = json.loads(self.json_path.read_text(encoding="utf-8"))
            return DAGPlan.model_validate(data)
        except Exception as e:
            logger.error("DAG yüklenemedi: %s", e)
            return None

    def save(self, dag: DAGPlan, write_markdown: bool = True) -> bool:
        dag.updated_at = datetime.now()
        try:
            self.json_path.write_text(dag.model_dump_json(indent=2), encoding="utf-8")
            if write_markdown:
                try:
                    self.md_path.write_text(dag.to_markdown(), encoding="utf-8")
                except Exception as e:
                    logger.warning("master_plan.md yazılamadı: %s", e)
            return True
        except Exception as e:
            logger.error("DAG kaydedilemedi: %s", e)
            return False

    def exists(self) -> bool:
        return self.json_path.exists()

    _ALLOWED = {
        WPStatus.PENDING: {WPStatus.READY, WPStatus.RUNNING, WPStatus.BLOCKED, WPStatus.SKIPPED},
        WPStatus.READY: {WPStatus.RUNNING, WPStatus.BLOCKED, WPStatus.SKIPPED},
        WPStatus.RUNNING: {WPStatus.DONE, WPStatus.FAILED, WPStatus.BLOCKED},
        WPStatus.FAILED: {WPStatus.READY, WPStatus.RUNNING, WPStatus.BLOCKED, WPStatus.SKIPPED},
        WPStatus.BLOCKED: {WPStatus.READY, WPStatus.PENDING, WPStatus.SKIPPED},
        WPStatus.DONE: {WPStatus.READY},
        WPStatus.SKIPPED: {WPStatus.READY, WPStatus.PENDING},
    }

    def _can_transition(self, current: WPStatus, new: WPStatus) -> bool:
        if current == new:
            return True
        return new in self._ALLOWED.get(current, set())

    def transition(
        self,
        wp_id: str,
        new_status: WPStatus,
        *,
        error: Optional[str] = None,
        artifacts: Optional[List[str]] = None,
        force: bool = False,
    ) -> Tuple[bool, str]:
        with self._get_lock():
            dag = self.load()
            if dag is None:
                return False, "dag_plan.json yok"
            if wp_id not in dag.nodes:
                return False, f"{wp_id} plan içinde yok"
            wp = dag.nodes[wp_id]
            old = wp.status
            if not force and not self._can_transition(old, new_status):
                return False, f"Geçersiz geçiş: {old.value} → {new_status.value}"

            if new_status == WPStatus.READY:
                wp.mark_ready()
            elif new_status == WPStatus.RUNNING:
                wp.mark_running()
            elif new_status == WPStatus.DONE:
                wp.mark_done(artifacts=artifacts)
            elif new_status == WPStatus.FAILED:
                wp.mark_failed(error or "Bilinmeyen hata")
            elif new_status == WPStatus.BLOCKED:
                wp.mark_blocked(error or "")
            else:
                wp.status = new_status
                wp.updated_at = datetime.now()
                if error:
                    wp.error_log = error
                if artifacts:
                    wp.artifacts.extend(artifacts)

            dag.nodes[wp_id] = wp
            blocked: List[str] = []
            if new_status == WPStatus.FAILED:
                blocked = dag.propagate_block(wp_id)
            elif new_status == WPStatus.DONE:
                for candidate in dag.nodes.values():
                    if candidate.status == WPStatus.BLOCKED and (candidate.error_log or "").startswith("Bağımlı düğüm başarısız/engellendi:"):
                        if all(dag.nodes.get(dep) and dag.nodes[dep].status == WPStatus.DONE for dep in candidate.depends_on):
                            candidate.status = WPStatus.PENDING
                            candidate.error_log = None
                dag.get_ready_nodes()

            if not self.save(dag):
                return False, "Kayıt başarısız"
            msg = f"{wp_id}: {old.value} → {new_status.value}"
            if blocked:
                msg += f" | blocked: {', '.join(blocked)}"
            return True, msg

    def mark_running(self, wp_id: str, force: bool = False) -> Tuple[bool, str]:
        return self.transition(wp_id, WPStatus.RUNNING, force=force)

    def mark_done(self, wp_id: str, artifacts: Optional[List[str]] = None) -> Tuple[bool, str]:
        return self.transition(wp_id, WPStatus.DONE, artifacts=artifacts)

    def mark_failed(self, wp_id: str, error: str) -> Tuple[bool, str]:
        return self.transition(wp_id, WPStatus.FAILED, error=error)

    def mark_blocked(self, wp_id: str, reason: str = "") -> Tuple[bool, str]:
        return self.transition(wp_id, WPStatus.BLOCKED, error=reason)

    def refresh_ready(self) -> List[str]:
        with self._get_lock():
            dag = self.load()
            if dag is None:
                return []
            ready = dag.get_ready_nodes()
            self.save(dag)
            return [n.id for n in ready]

    def get_wp(self, wp_id: str) -> Optional[WorkPackage]:
        dag = self.load()
        if dag is None:
            return None
        return dag.nodes.get(wp_id)

    def get_ready_ids(self) -> List[str]:
        dag = self.load()
        if dag is None:
            return []
        return [n.id for n in dag.get_ready_nodes()]

    def summary(self) -> dict:
        dag = self.load()
        if dag is None:
            return {}
        return dag.get_status_summary()


