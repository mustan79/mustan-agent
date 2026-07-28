"""DeepPlan testleri."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from commands.deeplan import run_deeplan
from models.datatypes import DAGPlan, WorkPackage, WPStatus


def _make_sample_dag(path: Path) -> None:
    dag = DAGPlan(goal="test")
    dag.add_node(WorkPackage(
        id="WP-001",
        title="Auth modeli",
        description="User + login",
        depends_on=[],
        status=WPStatus.READY,
    ))
    path.write_text(dag.model_dump_json(indent=2), encoding="utf-8")


MOCK_DEEPLAN = {
    "wp_id": "WP-001",
    "title": "Auth modeli",
    "checklist": [
        {
            "step": 1,
            "action": "models.py oluştur",
            "details": "class User",
            "acceptance": "py_compile geçer",
        },
        {
            "step": 2,
            "action": "login fonksiyonu yaz",
            "details": "def login()",
            "acceptance": "test geçer",
        },
    ],
    "estimated_files": ["src/models.py"],
}


class TestDeeplanCommand:

    @patch("commands.deeplan.LLMClient")
    def test_run_deeplan_success(self, mock_llm_cls):
        mock_llm = MagicMock()
        mock_llm.generate_with_stats.return_value = (
            json.dumps(MOCK_DEEPLAN),
            {"total_tokens": 80},
        )
        mock_llm_cls.return_value = mock_llm

        with tempfile.TemporaryDirectory() as tmp:
            dag_path = Path(tmp) / "dag_plan.json"
            _make_sample_dag(dag_path)

            ok = run_deeplan("WP-001", memory_dir=tmp)
            assert ok is True
            md = Path(tmp) / "deeplans" / "WP-001.md"
            assert md.exists()
            content = md.read_text(encoding="utf-8")
            assert "Checklist" in content
            assert "Adım 1" in content

    def test_run_deeplan_missing_wp(self):
        with tempfile.TemporaryDirectory() as tmp:
            dag_path = Path(tmp) / "dag_plan.json"
            _make_sample_dag(dag_path)
            assert run_deeplan("WP-999", memory_dir=tmp) is False

    def test_run_deeplan_no_dag(self):
        with tempfile.TemporaryDirectory() as tmp:
            assert run_deeplan("WP-001", memory_dir=tmp) is False


