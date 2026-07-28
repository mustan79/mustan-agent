"""DAG plan üretimi testleri."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from commands.plan import run_plan, _extract_json, _build_dag_from_llm
from models.datatypes import DAGPlan


MOCK_PLAN_JSON = {
    "goal": "Basit login sistemi ekle",
    "nodes": [
        {
            "id": "WP-001",
            "title": "Auth modeli oluştur",
            "description": "User modeli ve login fonksiyonu",
            "depends_on": [],
            "tags": ["backend"],
        },
        {
            "id": "WP-002",
            "title": "Login testleri yaz",
            "description": "pytest ile login testleri",
            "depends_on": ["WP-001"],
            "tags": ["test"],
        },
    ],
}


class TestPlanCommand:

    def test_extract_json_clean(self):
        raw = json.dumps(MOCK_PLAN_JSON)
        assert _extract_json(raw)["goal"] == "Basit login sistemi ekle"

    def test_extract_json_with_markdown(self):
        raw = "İşte plan:\n```json\n" + json.dumps(MOCK_PLAN_JSON) + "\n```\n"
        data = _extract_json(raw)
        assert data is not None
        assert len(data["nodes"]) == 2

    def test_build_dag(self):
        dag = _build_dag_from_llm(MOCK_PLAN_JSON, "test goal")
        assert isinstance(dag, DAGPlan)
        assert "WP-001" in dag.nodes
        assert dag.nodes["WP-002"].depends_on == ["WP-001"]
        ready = dag.get_ready_nodes()
        assert any(n.id == "WP-001" for n in ready)

    @patch("commands.plan.LLMClient")
    def test_run_plan_success(self, mock_llm_cls):
        mock_llm = MagicMock()
        mock_llm.generate_with_stats.return_value = (
            json.dumps(MOCK_PLAN_JSON),
            {"total_tokens": 100, "cost_usd": 0.001},
        )
        mock_llm_cls.return_value = mock_llm

        with tempfile.TemporaryDirectory() as tmp:
            ok = run_plan("Basit login sistemi ekle", memory_dir=tmp)
            assert ok is True
            dag_path = Path(tmp) / "dag_plan.json"
            assert dag_path.exists()
            data = json.loads(dag_path.read_text(encoding="utf-8"))
            assert "nodes" in data
            assert "WP-001" in data["nodes"]

    @patch("commands.plan.LLMClient")
    def test_run_plan_empty_goal(self, mock_llm_cls):
        assert run_plan("") is False
        mock_llm_cls.assert_not_called()


