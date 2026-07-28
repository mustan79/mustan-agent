"""
MustanAgent v3.3+ - Telemetry
Her LLM / önemli işlem çağrısını kaydeder:
caller, provider, model, tokens, cost, duration_ms, success.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

logger = logging.getLogger("mustan_agent.core.telemetry")


@dataclass
class TelemetryEvent:
    id: str
    ts: str
    kind: str  # llm | tool | command | intent | other
    caller: str
    provider: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    duration_ms: float = 0.0
    success: bool = True
    error: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TelemetryStore:
    """
    Thread-safe olay deposu.
    Günlük JSONL dosyasına yazar; bellek içinde son N olayı tutar.
    """

    _instance: Optional["TelemetryStore"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        memory_dir: str = "Aimemory",
        max_memory_events: int = 500,
    ):
        if getattr(self, "_initialized", False):
            return
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.telemetry_dir = self.memory_dir / "telemetry"
        self.telemetry_dir.mkdir(exist_ok=True)
        self.max_memory_events = max_memory_events
        self._events: List[TelemetryEvent] = []
        self._file_lock = threading.Lock()
        self._initialized = True

    def _today_path(self) -> Path:
        return self.telemetry_dir / f"events_{date.today().isoformat()}.jsonl"

    def record(self, event: TelemetryEvent) -> None:
        with self._lock:
            self._events.append(event)
            if len(self._events) > self.max_memory_events:
                self._events = self._events[-self.max_memory_events :]

        line = json.dumps(event.to_dict(), ensure_ascii=False)
        try:
            with self._file_lock:
                with open(self._today_path(), "a", encoding="utf-8") as f:
                    f.write(line + "\n")
        except Exception as e:
            logger.warning("Telemetry yazılamadı: %s", e)

        logger.debug(
            "telemetry %s %s tokens=%d cost=$%.5f ms=%.0f ok=%s",
            event.kind,
            event.caller,
            event.total_tokens,
            event.cost_usd,
            event.duration_ms,
            event.success,
        )

    def recent(self, n: int = 20, kind: Optional[str] = None) -> List[TelemetryEvent]:
        with self._lock:
            items = list(self._events)
        if kind:
            items = [e for e in items if e.kind == kind]
        return items[-n:]

    def summary_today(self) -> Dict[str, Any]:
        """Bugünkü özet: caller bazlı toplam token/maliyet/süre."""
        path = self._today_path()
        events: List[dict] = []
        if path.exists():
            try:
                for line in path.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        events.append(json.loads(line))
            except Exception as e:
                logger.warning("Telemetry okuma hatası: %s", e)

        by_caller: Dict[str, Dict[str, Any]] = {}
        total_tokens = 0
        total_cost = 0.0
        total_calls = 0
        fail_count = 0

        for e in events:
            total_calls += 1
            total_tokens += int(e.get("total_tokens") or 0)
            total_cost += float(e.get("cost_usd") or 0)
            if not e.get("success", True):
                fail_count += 1
            c = e.get("caller") or "unknown"
            slot = by_caller.setdefault(
                c,
                {"calls": 0, "tokens": 0, "cost_usd": 0.0, "fail": 0},
            )
            slot["calls"] += 1
            slot["tokens"] += int(e.get("total_tokens") or 0)
            slot["cost_usd"] += float(e.get("cost_usd") or 0)
            if not e.get("success", True):
                slot["fail"] += 1

        return {
            "date": str(date.today()),
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 6),
            "fail_count": fail_count,
            "by_caller": {
                k: {
                    **v,
                    "cost_usd": round(v["cost_usd"], 6),
                }
                for k, v in sorted(
                    by_caller.items(),
                    key=lambda x: x[1]["cost_usd"],
                    reverse=True,
                )
            },
        }


def get_telemetry(memory_dir: str = "Aimemory") -> TelemetryStore:
    return TelemetryStore(memory_dir=memory_dir)


@contextmanager
def track_llm(
    caller: str,
    provider: str = "",
    model: str = "",
    meta: Optional[Dict[str, Any]] = None,
    memory_dir: str = "Aimemory",
) -> Generator[Dict[str, Any], None, None]:
    """
    Kullanım:
        with track_llm("commands.plan") as ctx:
            text, stats = llm.generate_with_stats(...)
            ctx.update(stats)
    """
    store = get_telemetry(memory_dir)
    t0 = time.perf_counter()
    ctx: Dict[str, Any] = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "cost_usd": 0.0,
        "provider": provider,
        "model": model,
        "success": True,
        "error": "",
    }
    try:
        yield ctx
    except Exception as e:
        ctx["success"] = False
        ctx["error"] = str(e)[:500]
        raise
    finally:
        duration_ms = (time.perf_counter() - t0) * 1000
        event = TelemetryEvent(
            id=str(uuid.uuid4())[:8],
            ts=datetime.now().isoformat(timespec="seconds"),
            kind="llm",
            caller=caller,
            provider=str(ctx.get("provider") or provider),
            model=str(ctx.get("model") or model),
            input_tokens=int(ctx.get("input_tokens") or 0),
            output_tokens=int(ctx.get("output_tokens") or 0),
            total_tokens=int(
                ctx.get("total_tokens")
                or (
                    int(ctx.get("input_tokens") or 0)
                    + int(ctx.get("output_tokens") or 0)
                )
            ),
            cost_usd=float(ctx.get("cost_usd") or 0),
            duration_ms=round(duration_ms, 1),
            success=bool(ctx.get("success", True)),
            error=str(ctx.get("error") or ""),
            meta=meta or {},
        )
        store.record(event)


def record_command(
    caller: str,
    success: bool = True,
    duration_ms: float = 0.0,
    meta: Optional[Dict[str, Any]] = None,
    memory_dir: str = "Aimemory",
) -> None:
    store = get_telemetry(memory_dir)
    store.record(
        TelemetryEvent(
            id=str(uuid.uuid4())[:8],
            ts=datetime.now().isoformat(timespec="seconds"),
            kind="command",
            caller=caller,
            duration_ms=duration_ms,
            success=success,
            meta=meta or {},
        )
    )


