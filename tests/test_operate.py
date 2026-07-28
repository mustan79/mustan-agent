"""Operate komutu testleri."""

from unittest.mock import patch, MagicMock

from commands.operate import run_operate


class TestOperateCommand:

    def test_empty_args(self):
        assert run_operate("") is False
        assert run_operate("   ") is False

    @patch("commands.operate.AgentRuntime")
    def test_run_operate_success(self, mock_runtime_cls):
        mock_runtime = MagicMock()
        mock_runtime.run_agent_loop.return_value = "TAMAMLANDI: hello.py oluşturuldu"
        mock_runtime_cls.return_value = mock_runtime

        ok = run_operate("basit bir hello.py oluştur")
        assert ok is True
        mock_runtime.run_agent_loop.assert_called_once()

    @patch("commands.operate.AgentRuntime")
    def test_run_operate_runtime_error(self, mock_runtime_cls):
        mock_runtime = MagicMock()
        mock_runtime.run_agent_loop.side_effect = RuntimeError("bütçe aşıldı")
        mock_runtime_cls.return_value = mock_runtime

        ok = run_operate("herhangi bir görev")
        assert ok is False


