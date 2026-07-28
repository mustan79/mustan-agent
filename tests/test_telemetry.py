"""Telemetry birim testleri."""

import tempfile
from pathlib import Path

from core.telemetry import TelemetryStore, track_llm, TelemetryEvent


class TestTelemetry:

    def test_record_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = TelemetryStore(memory_dir=tmp)
            # singleton’ı bu dir ile kullan
            store.memory_dir = Path(tmp)
            store.telemetry_dir = Path(tmp) / "telemetry"
            store.telemetry_dir.mkdir(exist_ok=True)
            store._events = []

            store.record(
                TelemetryEvent(
                    id="a1",
                    ts="2026-07-26T12:00:00",
                    kind="llm",
                    caller="commands.plan",
                    provider="gemini",
                    model="gemini-1.5-pro",
                    input_tokens=100,
                    output_tokens=50,
                    total_tokens=150,
                    cost_usd=0.001,
                    duration_ms=120.0,
                    success=True,
                )
            )
            recent = store.recent(5)
            assert len(recent) >= 1
            assert recent[-1].caller == "commands.plan"

            summary = store.summary_today()
            assert summary["total_calls"] >= 1
            assert "commands.plan" in summary["by_caller"]

    def test_track_llm_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            with track_llm("test.caller", provider="ollama", model="llama", memory_dir=tmp) as ctx:
                ctx["input_tokens"] = 10
                ctx["output_tokens"] = 5
                ctx["total_tokens"] = 15
                ctx["cost_usd"] = 0.0
            store = TelemetryStore(memory_dir=tmp)
            # en az bir olay dosyaya yazılmış olmalı
            files = list((Path(tmp) / "telemetry").glob("events_*.jsonl"))
            assert files
