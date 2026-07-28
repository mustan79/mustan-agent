"""Coordinator routing ve intent testleri."""

from unittest.mock import patch, MagicMock

from agents.coordinator import MustanCoordinator


class TestCoordinatorRouting:

    @patch("agents.coordinator.run_plan")
    def test_route_plan(self, mock_run_plan):
        mock_run_plan.return_value = True
        coord = MustanCoordinator(memory_dir="test_memory")
        with patch.object(coord.planner, "execute_task", return_value=True) as mock_exec:
            ok = coord._route_command("/plan", "login ekle")
            assert ok is True
            mock_exec.assert_called_once()

    @patch("agents.coordinator.run_operate")
    def test_route_operate(self, mock_operate):
        mock_operate.return_value = True
        coord = MustanCoordinator(memory_dir="test_memory")
        ok = coord._route_command("/operate", "hello.py yaz")
        assert ok is True
        mock_operate.assert_called_once_with("hello.py yaz")

    @patch("agents.coordinator.run_scan")
    def test_route_scan(self, mock_scan):
        mock_scan.return_value = True
        coord = MustanCoordinator(memory_dir="test_memory")
        ok = coord._route_command("/scan", "src")
        assert ok is True
        mock_scan.assert_called_once()

    def test_route_unknown(self):
        coord = MustanCoordinator(memory_dir="test_memory")
        ok = coord._route_command("/nonexistent", "")
        assert ok is False


class TestCoordinatorIntent:

    @patch("agents.coordinator.LLMClient")
    def test_analyze_intent_operate(self, mock_llm_cls):
        mock_llm = MagicMock()
        mock_llm.generate_with_stats.return_value = ("/operate", {})
        mock_llm_cls.return_value = mock_llm

        coord = MustanCoordinator(memory_dir="test_memory")
        coord.llm = mock_llm
        intent = coord._analyze_intent("src altına login fonksiyonu ekle")
        assert intent == "/operate"

    @patch("agents.coordinator.LLMClient")
    def test_analyze_intent_chat(self, mock_llm_cls):
        mock_llm = MagicMock()
        mock_llm.generate_with_stats.return_value = ("/chat", {})
        mock_llm_cls.return_value = mock_llm

        coord = MustanCoordinator(memory_dir="test_memory")
        coord.llm = mock_llm
        intent = coord._analyze_intent("merhaba nasılsın")
        assert intent == "/chat"
