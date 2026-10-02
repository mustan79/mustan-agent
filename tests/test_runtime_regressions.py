"""Exercise actual file operations and completion checks without API calls."""
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.runtime import AgentRuntime
from commands.plan import _build_dag_from_llm
from commands.set_config import run_set
from core.vault import MustanVault
from memory.snapshot import restore_checkpoint
from tools.file_ops import FileWriteTool, FileWriteInput


def test_parser_preserves_python_indentation_and_colons():
    runtime = AgentRuntime()
    parsed = runtime._parse_tool_input("write_file", "path: sample.py\ncontent:\ndef greet():\n    value = {'x': 1}\n    return value\n")
    assert parsed["content"] == "def greet():\n    value = {'x': 1}\n    return value"
    assert runtime._parse_tool_input("smart_edit", "path: a\nold_text: a\nnew_text: b\nreplace_all: false")["replace_all"] is False


def test_write_read_rewrite_requires_fresh_verification(tmp_path):
    runtime = AgentRuntime()
    path = str(tmp_path / "hello.py")
    assert runtime._execute_tool("write_file", {"file_path": path, "content": "x = 1"}).success
    assert not runtime._verify_completion("")[0]
    assert runtime._execute_tool("read_file", {"file_path": path}).success
    assert runtime._verify_completion("")[0]
    assert runtime._execute_tool("smart_edit", {"file_path": path, "old_text": "1", "new_text": "2"}).success
    assert not runtime._verify_completion("")[0]


def test_invalid_python_never_overwrites_existing_file(tmp_path):
    target = tmp_path / "hello.py"
    target.write_text("x = 1", encoding="utf-8")
    result = FileWriteTool.execute(FileWriteInput(file_path=str(target), content="def broken(\n"))
    assert result.startswith("[-]")
    assert target.read_text(encoding="utf-8") == "x = 1"


def test_agent_loop_creates_and_verifies_file_then_resets(tmp_path):
    runtime = AgentRuntime()
    path = str(tmp_path / "hello.py")
    runtime.llm = MagicMock()
    runtime.llm.generate_with_stats.side_effect = [
        ("<thought>Create</thought>\n```write_file\n" + json.dumps({"file_path": path, "content": "print('hello')\n"}) + "\n```", {}),
        ("<thought>Check</thought>\n```read_file\n" + json.dumps({"file_path": path}) + "\n```", {}),
        ("<thought>Finish</thought><final>Created hello.py</final>", {}),
        ("<thought>Finish</thought><final>Done</final>", {}),
    ]
    assert runtime.run_agent_loop("create file", "", max_steps=3) == "Created hello.py"
    assert runtime.completed
    assert Path(path).read_text(encoding="utf-8") == "print('hello')\n"
    assert runtime.run_agent_loop("another task", "", max_steps=1).startswith("[-]")
    assert not runtime.completed


@pytest.mark.parametrize("nodes", [
    [{"id": "WP-001", "depends_on": ["WP-999"]}],
    [{"id": "WP-001", "depends_on": ["WP-002"]}, {"id": "WP-002", "depends_on": ["WP-001"]}],
    [{"id": "WP-001"}, {"id": "WP-001"}],
])
def test_bad_plan_is_rejected(nodes):
    with pytest.raises(ValueError):
        _build_dag_from_llm({"nodes": nodes}, "goal")


def test_failed_vault_write_is_not_success(monkeypatch):
    monkeypatch.setattr(MustanVault, "set_secret", lambda *args: False)
    assert not run_set("key OPENAI_API_KEY dummy")


def test_rewind_rejects_traversal():
    assert restore_checkpoint("../..").startswith("[-]")


def test_repair_releases_dependent_work_package(tmp_path):
    from memory.dag_manager import DAGManager
    from models.datatypes import WPStatus
    dag = _build_dag_from_llm({"nodes": [{"id": "WP-001"}, {"id": "WP-002", "depends_on": ["WP-001"]}]}, "goal")
    manager = DAGManager(str(tmp_path))
    assert manager.save(dag)
    assert manager.mark_running("WP-001")[0]
    assert manager.mark_failed("WP-001", "test error")[0]
    assert manager.get_wp("WP-002").status == WPStatus.BLOCKED
    assert manager.mark_running("WP-001")[0]
    assert manager.mark_done("WP-001")[0]
    assert manager.get_wp("WP-002").status == WPStatus.READY


def test_provider_switch_selects_local_and_cloud_endpoints(tmp_path):
    from core.config import ConfigManager
    config = ConfigManager(str(tmp_path / "config.json"))
    assert config.update_provider("ollama")
    assert config.config.llm.ollama_base_url == "http://localhost:11434/v1"
    assert config.update_provider("ollama_cloud")
    assert config.config.llm.ollama_base_url == "https://ollama.com/v1"


def test_cli_exit_codes_and_help_without_project_state(tmp_path):
    import subprocess
    import sys
    result = subprocess.run([sys.executable, "-m", "main", "--help"], cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0
    assert not (tmp_path / "mustan_settings.json").exists()
    result = subprocess.run([sys.executable, "-m", "main", "nonexistent"], cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 2
    result = subprocess.run([sys.executable, "-m", "main", "scan", "missing-directory"], cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 1


def test_real_ide_connection():
    import asyncio
    import importlib.util
    if importlib.util.find_spec("websockets") is None:
        pytest.skip("IDE extra not installed")
    import websockets
    from bridge.ide_server import MustanBridge
    bridge = MustanBridge(port=0)
    assert bridge.start(), bridge.last_error
    async def communicate():
        async with websockets.connect(f"ws://127.0.0.1:{bridge.port}") as ws:
            await ws.send(json.dumps({"type": "cursor_move", "file": "sample.py", "selection": "x = 1"}))
            for _ in range(20):
                if bridge.active_file == "sample.py":
                    return
                await asyncio.sleep(0.01)
            pytest.fail("IDE context not received")
    try:
        asyncio.run(communicate())
    finally:
        bridge.stop()
    assert not bridge.is_running
