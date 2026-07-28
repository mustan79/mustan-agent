"""
MustanAgent v3.3 PRO - AgentRuntime
Otonom döngü motoru.
Thought bloğu zorunludur; yoksa döngü reddeder.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.query_engine import LLMClient

logger = logging.getLogger("mustan_agent.core.runtime")


@dataclass
class ToolExecutionResult:
    success: bool
    output: str
    tool_name: str = ""
    error: Optional[str] = None


@dataclass
class ParsedResponse:
    thought: Optional[str] = None
    tool_calls: List[Dict[str, str]] = field(default_factory=list)
    final_answer: Optional[str] = None
    raw: str = ""


class AgentRuntime:
    MAX_STEPS = 12
    THOUGHT_REQUIRED = True

    def __init__(self):
        self.llm = LLMClient()
        self.history: List[str] = []
        self._tool_registry = self._build_tool_registry()

    def _build_tool_registry(self) -> Dict[str, Any]:
        registry = {}
        try:
            from tools.bash_ops import BashTool, BashInput
            registry["bash"] = (BashTool, BashInput)
        except Exception as e:
            logger.warning("BashTool yüklenemedi: %s", e)

        try:
            from tools.smart_edit import SmartEditTool, SmartEditInput
            registry["smart_edit"] = (SmartEditTool, SmartEditInput)
        except Exception as e:
            logger.warning("SmartEditTool yüklenemedi: %s", e)

        try:
            from tools.file_ops import (
                FileReadTool, FileReadInput,
                FileWriteTool, FileWriteInput,
            )
            registry["read_file"] = (FileReadTool, FileReadInput)
            registry["write_file"] = (FileWriteTool, FileWriteInput)
        except Exception as e:
            logger.warning("File tools yüklenemedi: %s", e)

        return registry

    def _parse_response(self, llm_response: str) -> ParsedResponse:
        result = ParsedResponse(raw=llm_response)

        thought_match = re.search(
            r"<thought>([\s\S]*?)</thought>",
            llm_response,
            re.IGNORECASE,
        )
        if thought_match:
            result.thought = thought_match.group(1).strip()

        final_match = re.search(
            r"<final>([\s\S]*?)</final>",
            llm_response,
            re.IGNORECASE,
        )
        if final_match:
            result.final_answer = final_match.group(1).strip()

        pattern = re.compile(
            r"```(bash|smart_edit|read_file|write_file)\s*([\s\S]*?)```",
            re.IGNORECASE,
        )
        for match in pattern.finditer(llm_response):
            tool_name = match.group(1).lower()
            body = match.group(2).strip()
            result.tool_calls.append({"name": tool_name, "body": body})

        return result

    def _parse_tool_input(self, tool_name: str, body: str) -> Dict[str, Any]:
        if tool_name == "bash":
            return {"command": body.strip()}

        data: Dict[str, Any] = {}
        current_key = None
        buffer: List[str] = []

        for line in body.splitlines():
            if ":" in line and not line.strip().startswith("#"):
                if current_key is not None:
                    data[current_key] = "\n".join(buffer).strip()
                key, _, val = line.partition(":")
                current_key = key.strip().lower().replace(" ", "_")
                buffer = [val.strip()] if val.strip() else []
            else:
                if current_key is not None:
                    buffer.append(line)
        if current_key is not None:
            data[current_key] = "\n".join(buffer).strip()

        if "file_path" not in data and "path" in data:
            data["file_path"] = data["path"]
        if "old_text" not in data and "old" in data:
            data["old_text"] = data["old"]
        if "new_text" not in data and "new" in data:
            data["new_text"] = data["new"]

        return data

    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> ToolExecutionResult:
        if tool_name not in self._tool_registry:
            return ToolExecutionResult(
                success=False,
                output="",
                tool_name=tool_name,
                error=f"Bilinmeyen araç: {tool_name}",
            )

        ToolCls, InputCls = self._tool_registry[tool_name]
        try:
            if tool_name == "bash":
                inp = InputCls(command=tool_input.get("command", ""))
            elif tool_name == "smart_edit":
                inp = InputCls(
                    file_path=tool_input.get("file_path") or tool_input.get("path", ""),
                    old_text=tool_input.get("old_text") or tool_input.get("old", ""),
                    new_text=tool_input.get("new_text") or tool_input.get("new", ""),
                    replace_all=bool(tool_input.get("replace_all", False)),
                )
            elif tool_name == "read_file":
                inp = InputCls(
                    file_path=tool_input.get("file_path") or tool_input.get("path", "")
                )
            elif tool_name == "write_file":
                inp = InputCls(
                    file_path=tool_input.get("file_path") or tool_input.get("path", ""),
                    content=tool_input.get("content") or tool_input.get("new_text", ""),
                )
            else:
                inp = InputCls(**tool_input)

            if hasattr(ToolCls, "execute"):
                raw = ToolCls.execute(inp)
            else:
                instance = ToolCls()
                raw = instance.execute(inp)

            output = str(raw) if raw is not None else ""
            success = not output.startswith("[-]") and "Hata" not in output[:80]
            return ToolExecutionResult(
                success=success,
                output=output,
                tool_name=tool_name,
                error=None if success else output,
            )
        except Exception as e:
            logger.exception("Tool çalıştırma hatası: %s", tool_name)
            return ToolExecutionResult(
                success=False,
                output="",
                tool_name=tool_name,
                error=str(e),
            )

    def run_agent_loop(
        self,
        initial_prompt: str,
        system_prompt: str,
        max_steps: Optional[int] = None,
    ) -> str:
        max_steps = max_steps or self.MAX_STEPS
        conversation = initial_prompt
        final_result = ""

        for step in range(1, max_steps + 1):
            logger.info("AgentRuntime adım %d/%d", step, max_steps)
            print(f"\n── Adım {step}/{max_steps} ──")

            try:
                response, stats = self.llm.generate_with_stats(
                    prompt=conversation,
                    system_prompt=system_prompt,
                    use_rag=True,
                    temperature=0.25,
                )
            except RuntimeError as e:
                msg = f"[-] Runtime durdu: {e}"
                print(msg)
                return msg

            parsed = self._parse_response(response)

            if self.THOUGHT_REQUIRED and not parsed.thought:
                reject = (
                    "Sistem reddi: <thought>...</thought> bloğu eksik.\n"
                    "Lütfen önce düşün, sonra araç çağır veya final ver.\n"
                    "Örnek:\n"
                    "<thought>\nGörev X. Önce dosyayı okumalıyım.\n</thought>\n"
                    "```read_file\npath: src/main.py\n```"
                )
                print("[!] Thought eksik – LLM'e geri bildiriliyor.")
                conversation += f"\n\n[ASSISTANT]\n{response}\n\n[SYSTEM]\n{reject}\n"
                continue

            if parsed.thought:
                print(
                    f"💭 Thought: {parsed.thought[:300]}"
                    f"{'...' if len(parsed.thought) > 300 else ''}"
                )

            if parsed.final_answer:
                print(f"✅ Final: {parsed.final_answer[:400]}")
                final_result = parsed.final_answer
                break

            if not parsed.tool_calls:
                warn = (
                    "Ne tool çağrısı ne de <final> bloğu var. "
                    "Ya bir araç kullan ya da görevi <final> ile bitir."
                )
                print(f"[!] {warn}")
                conversation += f"\n\n[ASSISTANT]\n{response}\n\n[SYSTEM]\n{warn}\n"
                continue

            observations = []
            for call in parsed.tool_calls:
                name = call["name"]
                body = call["body"]
                print(f"🔧 Tool: {name}")
                inp = self._parse_tool_input(name, body)
                result = self._execute_tool(name, inp)

                if result.success:
                    print(f"   ✓ Başarılı ({len(result.output)} karakter)")
                else:
                    print(f"   ✗ Hata: {result.error or result.output[:200]}")

                observations.append(
                    f"### Tool Result [{name}]\n"
                    f"Success: {result.success}\n"
                    f"Output:\n{result.output[:3000]}\n"
                )

            obs_text = "\n".join(observations)
            conversation += (
                f"\n\n[ASSISTANT]\n{response}\n\n"
                f"[OBSERVATION]\n{obs_text}\n"
            )

            fail_count = sum(1 for o in observations if "Success: False" in o)
            if fail_count >= 3 and step > 4:
                conversation += (
                    "\n[SYSTEM]\n"
                    "Son adımlarda birden fazla tool hatası alındı. "
                    "Aynı yaklaşımı tekrarlama. Stratejini değiştir veya "
                    "sorunu <final> ile raporla.\n"
                )

        else:
            final_result = (
                f"[-] Maksimum adım ({max_steps}) aşıldı. "
                "Görev tamamlanamadı veya çok karmaşıktı."
            )
            print(final_result)

        return final_result



