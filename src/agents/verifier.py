"""
MustanAgent v3.3 PRO - VerifierAgent
QA / TDD uzmanı. DAGManager ile durum günceller.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, List, Optional

from agents.base import BaseAgent
from core.query_engine import LLMClient
from memory.dag_manager import DAGManager
from models.datatypes import WPStatus
from tools.bash_ops import BashTool, BashInput

logger = logging.getLogger("mustan_agent.agents.verifier")


VERIFY_ANALYSIS_PROMPT = """Sen MustanAgent Verifier (QA) ajanısın.
Aşağıdaki komut/test çıktısını incele.

Yanıt formatı:
KÖK_NEDEN: ...
ÖNERİLEN_DÜZELTME: ...
ETKİLENEN_DOSYALAR: ...
CİDDİYET: low|medium|high
"""


class VerifierAgent(BaseAgent):
    def __init__(self, memory_dir: str = "Aimemory"):
        super().__init__(memory_dir)
        self.llm = LLMClient()
        self.dag = DAGManager(memory_dir)

    def _run_command(self, command: str) -> str:
        try:
            return str(BashTool.execute(BashInput(command=command)))
        except Exception as e:
            return f"[-] Komut hatası: {e}"

    def _run_pytest(self, target: Optional[str] = None) -> str:
        cmd = "python -m pytest -q --tb=short"
        if target:
            cmd += f" {target}"
        return self._run_command(cmd)

    def _run_py_compile(self, file_path: str) -> str:
        return self._run_command(f'python -m py_compile "{file_path}"')

    def _analyze_failure(self, output: str) -> str:
        try:
            analysis, _ = self.llm.generate_with_stats(
                prompt=f"Komut / test çıktısı:\n\n{output[:6000]}",
                system_prompt=VERIFY_ANALYSIS_PROMPT,
                use_rag=False,
                temperature=0.2,
            )
            return analysis
        except Exception as e:
            return f"Analiz yapılamadı: {e}"

    def execute_task(
        self,
        task_description: str = "",
        target_file: Optional[str] = None,
        wp_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        self.log_action(
            "VerifierAgent Start",
            f"task={task_description[:60]} | file={target_file} | wp={wp_id}",
        )

        results: List[str] = []
        overall_success = True

        if target_file:
            print(f"[*] Verifier → py_compile: {target_file}")
            out = self._run_py_compile(target_file)
            results.append(f"### py_compile ({target_file})\n{out}")
            if any(x in out for x in ("[-]", "Error", "SyntaxError")):
                overall_success = False
                results.append(f"### Analiz\n{self._analyze_failure(out)}")

        if wp_id:
            wp_id = wp_id.strip().upper()
            if not wp_id.startswith("WP-"):
                wp_id = f"WP-{wp_id}" if wp_id.isdigit() else wp_id

            wp = self.dag.get_wp(wp_id)
            if wp is None:
                results.append(f"[-] {wp_id} DAG içinde yok.")
                overall_success = False
            else:
                print(f"[*] Verifier → WP: {wp_id} ({wp.title})")

                for art in wp.artifacts:
                    if art.endswith(".py") and Path(art).exists():
                        out = self._run_py_compile(art)
                        results.append(f"### py_compile ({art})\n{out}")
                        if any(x in out for x in ("Error", "SyntaxError", "[-]")):
                            overall_success = False

                tags = [t.lower() for t in wp.tags]
                if "test" in tags or any("test" in a.lower() for a in wp.artifacts):
                    out = self._run_pytest()
                    results.append(f"### pytest\n{out}")
                    if any(x in out.lower() for x in ("failed", "error")):
                        overall_success = False
                        results.append(f"### Analiz\n{self._analyze_failure(out)}")

                if overall_success:
                    ok, msg = self.dag.mark_done(wp_id)
                    print(f"[+] {msg}")
                    self.log_action("VerifierAgent Complete", wp_id)
                else:
                    ok, msg = self.dag.mark_failed(wp_id, "Verifier doğrulaması başarısız")
                    print(f"[-] {msg}")
                    self.log_action("VerifierAgent Failed", wp_id)

        if not target_file and not wp_id:
            print("[*] Verifier → genel pytest")
            out = self._run_pytest()
            results.append(f"### pytest\n{out}")
            if any(x in out.lower() for x in ("failed", "error")):
                overall_success = False
                results.append(f"### Analiz\n{self._analyze_failure(out)}")

        report = "\n\n".join(results)
        print("\n—— Verifier Raporu ——")
        print(report[:3000] + ("..." if len(report) > 3000 else ""))
        return overall_success
