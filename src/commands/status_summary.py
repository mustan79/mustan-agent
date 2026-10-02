"""
MustanAgent v3.3+ - /status, /summary, /telemetry
CostTracker + (varsa) Telemetry + DAG ozeti.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("mustan_agent.commands.status_summary")
from core.config import settings


def _memory_dir() -> str:
    try:
        return settings.config.memory.base_dir or "Aimemory"
    except Exception:
        return "Aimemory"


def _cwd_info() -> str:
    return str(Path.cwd())


def run_status() -> bool:
    print(" 📡 MustanAgent v3.3 PRO - Sistem Durumu")
    print(f"  OS / cwd     : {os.name} | {_cwd_info()}")

    # Provider / model
    try:
        llm = settings.config.llm
        print(f"  Provider     : {llm.provider}")
        print(f"  Model        : {llm.model}")
    except Exception as e:
        print(f"  Config       : okunamadi ({e})")

    # CostTracker (asıl kaynak)
    try:
        from core.cost_tracker import get_cost_tracker
        ct = get_cost_tracker()
        print(f"  {ct.status_report()}")
    except Exception as e:
        print(f"  CostTracker  : yok ({e})")

    # Telemetry (opsiyonel)
    try:
        from core.telemetry import get_telemetry
        s = get_telemetry(_memory_dir()).summary_today()
        if s.get("total_calls"):
            print(
                f"  Telemetry    : {s['total_calls']} cagri | "
                f"{s['total_tokens']} tok | ${s['total_cost_usd']:.4f} | "
                f"fail={s['fail_count']}"
            )
    except Exception:
        pass

    # DAG
    try:
        from memory.dag_manager import DAGManager
        dag = DAGManager(_memory_dir())
        if dag.exists():
            sm = dag.summary()
            parts = [f"{k}={v}" for k, v in sm.items() if v]
            print(f"  DAG          : {' | '.join(parts) if parts else '(bos)'}")
            ready = dag.get_ready_ids()
            if ready:
                print(f"  Ready        : {', '.join(ready)}")
        else:
            print("  DAG          : yok (once /plan)")
    except Exception as e:
        print(f"  DAG          : ({e})")

    print("=" * 50)
    return True


def run_summary(use_llm: bool = False) -> bool:
    """Once SummaryEngine; yoksa status + kisa metin."""
    mem = _memory_dir()
    try:
        from services.summary_engine import SummaryEngine
        engine = SummaryEngine(mem)
        print(engine.render_with_narrative(use_llm=use_llm))
        return True
    except Exception as e:
        logger.debug("SummaryEngine yok/hata: %s — fallback", e)

    # Fallback: status + CostTracker
    run_status()
    try:
        from core.cost_tracker import get_cost_tracker
        print("\n[Ozet] " + get_cost_tracker().status_report())
    except Exception:
        pass
    return True


def run_telemetry_report(memory_dir: Optional[str] = None) -> bool:
    try:
        from core.telemetry import get_telemetry
    except ImportError:
        print("[-] Telemetry henuz yuklu degil.")
        return False

    store = get_telemetry(memory_dir or _memory_dir())
    s = store.summary_today()
    print("—— Telemetry (bugun) ——")
    print(
        f"Cagri: {s.get('total_calls', 0)} | Token: {s.get('total_tokens', 0)} | "
        f"${s.get('total_cost_usd', 0):.4f} | Hata: {s.get('fail_count', 0)}"
    )
    print("\nCaller bazli:")
    for caller, v in (s.get("by_caller") or {}).items():
        print(
	            f"  {caller}: {v.get('calls', 0)}x | "
            f"{v.get('tokens', 0)} tok | ${v.get('cost_usd', 0):.4f} | "
            f"fail={v.get('fail', 0)}"
        )
    if not s.get("total_calls"):
        print("  (bugun kayit yok)")
    return True
