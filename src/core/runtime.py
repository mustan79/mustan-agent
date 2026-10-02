"""
MustanAgent v3.3 PRO - AgentRuntime Motoru
Verifier (Doğrulayıcı) ve Guardrail korumalı otonom ajan döngüsü.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

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

    def __init__(self, system_info: Optional[Dict[str, str]] = None, memory_dir: Optional[str] = None):
        self.llm = LLMClient()
        self.history: List[str] = []
        self.system_info = system_info or {}
        self.memory_dir = memory_dir
        self._tool_registry = self._build_tool_registry()
        
        # Verifier & State Takibi
        self.executed_tools_history: List[ToolExecutionResult] = []
        self.modified_files: Set[str] = set()
        self.verified_files: Set[str] = set()
        self.completed = False

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

        thought_match = re.search(r"<thought>([\s\S]*?)</thought>", llm_response, re.IGNORECASE)
        if thought_match:
            result.thought = thought_match.group(1).strip()

        final_match = re.search(r"<final>([\s\S]*?)</final>", llm_response, re.IGNORECASE)
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

        # Recognize only schema fields: colons in code/content are not headers.
        import json
        if body.lstrip().startswith("{"):
            data = json.loads(body)
            if not isinstance(data, dict):
                raise ValueError("Tool input must be a JSON object")
            return data
        fields = {"file_path", "path", "content", "text", "old_text", "old", "new_text", "new", "replace_all", "start_line", "end_line"}
        data: Dict[str, Any] = {}
        current_key = None
        buffer: List[str] = []
        for line in body.splitlines():
            key, separator, val = line.partition(":")
            if separator and key.strip() in fields and line == line.lstrip():
                if current_key is not None:
                    data[current_key] = "\n".join(buffer)
                current_key = key.strip()
                buffer = [val.lstrip()] if val.strip() else []
            elif current_key is not None:
                buffer.append(line)
        if current_key is not None:
            data[current_key] = "\n".join(buffer)
        if "replace_all" in data:
            data["replace_all"] = str(data["replace_all"]).lower() in {"true", "1", "yes"}

        if "file_path" not in data and "path" in data:
            data["file_path"] = data["path"]
        if "content" not in data and "text" in data:
            data["content"] = data["text"]

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
            target_file = tool_input.get("file_path") or tool_input.get("path", "")
            if target_file:
                target_file = str(Path(target_file).resolve())
            
            if tool_name == "bash":
                cmd = tool_input.get("command", "")
                # Windows Otomatik Düzeltme İpucu
                if self.system_info.get("os") == "Windows" and cmd.startswith("ls "):
                    cmd = cmd.replace("ls ", "dir ")
                inp = InputCls(command=cmd)
            elif tool_name == "smart_edit":
                inp = InputCls(
                    file_path=target_file,
                    old_text=tool_input.get("old_text") or tool_input.get("old", ""),
                    new_text=tool_input.get("new_text") or tool_input.get("new", ""),
                    replace_all=str(tool_input.get("replace_all", False)).lower() in {"true", "1", "yes"},
                )
            elif tool_name == "read_file":
                inp = InputCls(file_path=target_file, start_line=tool_input.get("start_line"), end_line=tool_input.get("end_line"))
            elif tool_name == "write_file":
                inp = InputCls(
                    file_path=target_file,
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
            success = not output.startswith("[-]")
            
            res = ToolExecutionResult(
                success=success,
                output=output,
                tool_name=tool_name,
                error=None if success else output,
            )
            if tool_name in {"smart_edit", "write_file"} and success and target_file:
                self.modified_files.add(target_file)
                self.verified_files.discard(target_file)
            if tool_name == "read_file" and success and target_file in self.modified_files and not inp.start_line and not inp.end_line:
                self.verified_files.add(target_file)
            self.executed_tools_history.append(res)
            return res
        except Exception as e:
            logger.exception("Tool çalıştırma hatası: %s", tool_name)
            result = ToolExecutionResult(
                success=False,
                output="",
                tool_name=tool_name,
                error=str(e),
            )
            self.executed_tools_history.append(result)
            return result

    def _verify_completion(self, initial_prompt: str) -> Tuple[bool, str]:
        """
        Görevin fiziksel olarak tamamlandığını denetleyen Runtime Verifier.
        """
        if not self.executed_tools_history:
            return False, "SİSTEM REDDİ: Görevde hiçbir araç (tool) çalıştırılmadı. Eylem almadan tamamlandı diyemezsin."

        last_tool = self.executed_tools_history[-1]
        if not last_tool.success:
            return False, f"SİSTEM REDDİ: Son çalıştırılan araç ({last_tool.tool_name}) başarısız oldu. Hatayı düzeltmeden <final> veremezsin."

        unverified = self.modified_files - self.verified_files
        if unverified:
            unverified_str = ", ".join(unverified)
            return False, f"SİSTEM REDDİ: Değiştirilen dosyalar ({unverified_str}) henüz 'read_file' aracı ile okunup doğrulanmadı. Lütfen içeriği okuyup kontrol et."

        return True, "OK"

    def run_agent_loop(
        self,
        initial_prompt: str,
        system_prompt: str,
        max_steps: Optional[int] = None,
    ) -> str:
        self.executed_tools_history.clear()
        self.modified_files.clear()
        self.verified_files.clear()
        self.completed = False
        max_steps = max_steps or self.MAX_STEPS
        conversation = initial_prompt
        final_result = ""

        for step in range(1, max_steps + 1):
            logger.info("🔄 [ADIM %d/%d] LLM Düşünüyor ve İcra Ediyor...", step, max_steps)

            try:
                response, _ = self.llm.generate_with_stats(
                    prompt=conversation,
                    system_prompt=system_prompt,
                    use_rag=True,
                    memory_dir=self.memory_dir,
                    temperature=0.2,
                    caller="agent.runtime",  # Telemetry için caller belirlendi
                )
            except Exception as e:
                msg = f"[-] Runtime LLM Hatası: {e}"
                logger.error(msg)
                return msg

            parsed = self._parse_response(response)

            # 1. THOUGHT KONTROLÜ
            if not parsed.thought:
                logger.warning("⚠️ <thought> bloğu eksik. LLM'e geri uyarı gönderiliyor.")
                reject = (
                    "[SİSTEM REDDİ] <thought>...</thought> bloğu eksik.\n"
                    "Lütfen eylem yapmadan önce düşünceni açıkla."
                )
                conversation += f"\n\n[ASSISTANT]\n{response}\n\n[SYSTEM]\n{reject}\n"
                continue

            logger.info("💭 Thought: %s", parsed.thought)

            # 2. FINAL ANSWER KONTROLÜ VE RUNTIME VERIFIER
            if parsed.final_answer and not parsed.tool_calls:
                is_valid, reason = self._verify_completion(initial_prompt)
                if not is_valid:
                    logger.warning("❌ [VERIFIER REDDİ] %s", reason)
                    conversation += (
                        f"\n\n[ASSISTANT]\n{response}\n\n"
                        f"[SYSTEM - VERIFIER REDDİ]\n{reason}\n"
                    )
                    continue

                logger.info("✅ [KONTROL BAŞARILI] Final Yanıtı Kabul Edildi.")
                logger.info("📢 Final Özet: %s", parsed.final_answer)
                self.completed = True
                final_result = parsed.final_answer
                break

            # 3. TOOL ÇALIŞTIRMA VE LOGLAMA
            if not parsed.tool_calls:
                if self.modified_files and self.modified_files.issubset(self.verified_files):
                    logger.info("💡 [RUNTIME] Tüm dosyalar doğrulandı. LLM'e görevi <final> ile kapatması bildiriliyor.")
                    conversation += (
                        f"\n\n[ASSISTANT]\n{response}\n\n"
                        "[SYSTEM]\nTüm adımlar ve dosya doğrulamaları başarıyla tamamlandı. "
                        "Lütfen yeni bir araç ÇAĞIRMA. Görevi sonlandırmak için yanıtını <final>...</final> etiketleri arasına alarak özetle.\n"
                    )
                else:
                    logger.warning("⚠️ Araç çağrısı bulunamadı. LLM'den eylem bekleniyor.")
                    conversation += (
                        f"\n\n[ASSISTANT]\n{response}\n\n"
                        "[SYSTEM]\nEylem yapabilmek için geçerli bir araç (write_file, read_file, bash, smart_edit) çağır "
                        "veya işlem bittiyse yanıtını <final>...</final> içine al.\n"
                    )
                continue

            observations = []
            for call in parsed.tool_calls:
                name = call["name"]
                body = call["body"]
                logger.info("🛠️ Tool Çağrısı: [%s]", name)
                
                try:
                    inp = self._parse_tool_input(name, body)
                    result = self._execute_tool(name, inp)
                except Exception as exc:
                    result = ToolExecutionResult(False, "", name, str(exc))
                    self.executed_tools_history.append(result)

                if result.success:
                    logger.info("   └─ ✓ Başarılı | Çıktı Boyutu: %d karakter", len(result.output))
                    if result.output:
                        preview = result.output[:200].replace('\n', ' ')
                        logger.info("   └─ 📄 Özet: %s...", preview)
                else:
                    logger.error("   └─ ✗ HATA: %s", result.error or result.output[:200])

                observations.append(
                    f"### Tool Result [{name}]\n"
                    f"Success: {result.success}\n"
                    f"Output:\n{(result.error or result.output)[:3000]}\n"
                )

            obs_text = "\n".join(observations)
            conversation += (
                f"\n\n[ASSISTANT]\n{response}\n\n"
                f"[OBSERVATION]\n{obs_text}\n"
            )

        else:
            final_result = (
                f"[-] Maksimum adım sayısı ({max_steps}) aşıldı. "
                "Görev tamamlanamadı veya kilitlendi."
            )
            logger.error(final_result)

        return final_result

