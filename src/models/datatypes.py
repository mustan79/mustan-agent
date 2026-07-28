"""
MustanAgent v3.3 PRO - Ortak Veri Modelleri
Dinamik DAG planlama yapıları.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WPStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class WorkPackage(BaseModel):
    id: str
    title: str
    description: str
    depends_on: List[str] = Field(default_factory=list)
    status: WPStatus = Field(default=WPStatus.PENDING)
    repair_attempts: int = Field(default=0, ge=0)
    max_repair_attempts: int = Field(default=3, ge=1)
    artifacts: List[str] = Field(default_factory=list)
    error_log: Optional[str] = None
    estimated_tokens: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def mark_ready(self) -> None:
        self.status = WPStatus.READY
        self.updated_at = datetime.now()

    def mark_running(self) -> None:
        self.status = WPStatus.RUNNING
        self.updated_at = datetime.now()

    def mark_done(self, artifacts: Optional[List[str]] = None) -> None:
        self.status = WPStatus.DONE
        if artifacts:
            self.artifacts.extend(artifacts)
        self.updated_at = datetime.now()

    def mark_failed(self, error: str) -> None:
        self.status = WPStatus.FAILED
        self.error_log = error
        self.repair_attempts += 1
        self.updated_at = datetime.now()

    def mark_blocked(self, reason: str = "") -> None:
        self.status = WPStatus.BLOCKED
        if reason:
            self.error_log = reason
        self.updated_at = datetime.now()

    def can_retry(self) -> bool:
        return self.repair_attempts < self.max_repair_attempts


class DAGPlan(BaseModel):
    goal: str
    nodes: Dict[str, WorkPackage] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    version: str = "1.0"
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_node(self, wp: WorkPackage) -> None:
        self.nodes[wp.id] = wp
        self.updated_at = datetime.now()

    def get_ready_nodes(self) -> List[WorkPackage]:
        ready = []
        for wp in self.nodes.values():
            if wp.status not in (WPStatus.PENDING, WPStatus.READY):
                continue
            deps_ok = all(
                self.nodes.get(d) and self.nodes[d].status == WPStatus.DONE
                for d in wp.depends_on
            )
            if deps_ok:
                if wp.status == WPStatus.PENDING:
                    wp.mark_ready()
                ready.append(wp)
        return ready

    def propagate_block(self, failed_id: str) -> List[str]:
        blocked_ids: List[str] = []
        changed = True
        while changed:
            changed = False
            for wp in self.nodes.values():
                if wp.status in (WPStatus.DONE, WPStatus.FAILED, WPStatus.BLOCKED, WPStatus.SKIPPED):
                    continue
                if any(
                    dep in self.nodes
                    and self.nodes[dep].status in (WPStatus.FAILED, WPStatus.BLOCKED)
                    for dep in wp.depends_on
                ):
                    wp.mark_blocked(f"Bağımlı düğüm başarısız/engellendi: {failed_id}")
                    blocked_ids.append(wp.id)
                    changed = True
        self.updated_at = datetime.now()
        return blocked_ids

    def get_status_summary(self) -> Dict[str, int]:
        summary = {s.value: 0 for s in WPStatus}
        for wp in self.nodes.values():
            summary[wp.status.value] += 1
        return summary

    def topological_order(self) -> List[str]:
        from collections import defaultdict, deque
        in_degree = {nid: 0 for nid in self.nodes}
        graph = defaultdict(list)
        for nid, wp in self.nodes.items():
            for dep in wp.depends_on:
                if dep not in self.nodes:
                    continue
                graph[dep].append(nid)
                in_degree[nid] += 1
        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        order = []
        while queue:
            current = queue.popleft()
            order.append(current)
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        if len(order) != len(self.nodes):
            raise ValueError("DAG içinde döngü tespit edildi!")
        return order

    def to_markdown(self) -> str:
        lines = [
            "# DAG Plan",
            f"**Hedef:** {self.goal}",
            f"**Oluşturulma:** {self.created_at.isoformat()}",
            f"**Güncelleme:** {self.updated_at.isoformat()}",
            "",
            "## Durum Özeti",
        ]
        for status, count in self.get_status_summary().items():
            if count > 0:
                lines.append(f"- {status}: {count}")
        lines += ["", "## İş Paketleri"]
        try:
            order = self.topological_order()
        except ValueError:
            order = list(self.nodes.keys())
        for nid in order:
            wp = self.nodes[nid]
            deps = ", ".join(wp.depends_on) if wp.depends_on else "—"
            lines += [
                f"### {wp.id} — {wp.title}",
                f"- **Durum:** `{wp.status.value}`",
                f"- **Bağımlılıklar:** {deps}",
                f"- **Açıklama:** {wp.description}",
            ]
            if wp.artifacts:
                lines.append(f"- **Üretilenler:** {', '.join(wp.artifacts)}")
            if wp.error_log:
                lines.append(f"- **Hata:** {wp.error_log}")
            lines.append("")
        return "\n".join(lines)


class SessionState(BaseModel):
    last_active_task: Optional[str] = None
    status: str = "idle"
    timestamp: datetime = Field(default_factory=datetime.now)
    extra: Dict[str, Any] = Field(default_factory=dict)

