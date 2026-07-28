"""
MustanAgent v3.3 PRO - PlannerAgent
Sistemin Baş Mimarı. Kod yazmaz; hedefi DAG iş paketlerine böler
ve istenirse belirli bir WP için DeepPlan üretir.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from agents.base import BaseAgent
from commands.plan import run_plan
from commands.deeplan import run_deeplan

logger = logging.getLogger("mustan_agent.agents.planner")


class PlannerAgent(BaseAgent):
    """
    Sistemin Baş Mimarı.
    Kod yazmaz, ancak projenin zihin haritasını okuyarak hedefi atomik
    iş paketlerine (DAG) böler.
    """

    def __init__(self, memory_dir: str = "Aimemory"):
        super().__init__(memory_dir)

    def execute_task(
        self,
        task_description: str,
        wp_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """
        wp_id verilmişse DeepPlan, yoksa Master Plan (DAG) üretir.
        """
        self.log_action(
            "PlannerAgent Start",
            f"Görev: {task_description} | WP_ID: {wp_id}",
        )

        if wp_id:
            success = run_deeplan(wp_id=wp_id, memory_dir=self.memory_dir)
            action_type = f"DeepPlan ({wp_id})"
        else:
            success = run_plan(goal=task_description, memory_dir=self.memory_dir)
            action_type = "Master Plan (DAG)"

        if success:
            self.log_action("PlannerAgent Complete", f"{action_type} başarıyla tamamlandı.")
            return True

        self.log_action("PlannerAgent Error", f"{action_type} başarısız oldu.")
        return False
