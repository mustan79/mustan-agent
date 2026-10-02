"""
MustanAgent v3.3 PRO - MustanCoordinator
Sistemin Orkestratörü.
Slash komutlarını ve doğal dil niyetlerini ilgili ajan / komuta yönlendirir.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from core.query_engine import LLMClient
from core.config import settings
from agents.explorer import ExplorerAgent
from agents.planner import PlannerAgent
from agents.worker import WorkerAgent
from agents.verifier import VerifierAgent

from commands.scan import run_scan
from commands.plan import run_plan
from commands.deeplan import run_deeplan
from commands.operate import run_operate
from commands.reflect import run_reflect
from commands.rewind import run_rewind
from commands.btw import run_btw
from commands.ide import run_ide
from commands.set_config import run_set
from commands.help_cmd import run_help
from commands.doctor import run_doctor
from commands.status_summary import run_status
from commands.status_summary import run_summary
from commands.status_summary import run_telemetry_report
from commands.scope import run_scope

logger = logging.getLogger("mustan_agent.agents.coordinator")


INTENT_SYSTEM_PROMPT = """Sen MustanAgent niyet analistisin.
Kullanıcı mesajını tek bir komuta eşle.
Sadece aşağıdaki listeden birini döndür (başka hiçbir şey yazma):

/scan
/plan
/deeplan
/operate
/doctor
/scope
/reflect
/rewind
/btw
/ide
/status
/summary
/set
/worker
/verify
/voice
/chat
/unknown

Kurallar:
- Kod yaz, dosya oluştur, değiştir, düzelt → /operate
- Plan çıkar, iş paketlerine böl → /plan
- Belirli WP detaylandır → /deeplan
- Projeyi tara / zihin haritası → /scan
- Sistem sağlığı → /doctor
- Sohbet / genel soru → /chat
"""


class MustanCoordinator:
    @staticmethod
    def is_known_command(cmd: str) -> bool:
        return cmd.lower().lstrip("/") in {
            "help", "list", "komutlar", "doctor", "status", "summary", "telemetry",
            "scope", "scan", "plan", "deeplan", "operate", "coder", "reflect",
            "rewind", "btw", "ide", "set", "worker", "verify", "voice", "buddy", "repair",
        }

    def __init__(self, memory_dir: Optional[str] = None):
        try:
            default_mem = settings.config.memory.base_dir
        except Exception:
            default_mem = "Aimemory"

        self.memory_dir = memory_dir or default_mem or "Aimemory"
        os.makedirs(self.memory_dir, exist_ok=True)

        self.llm = LLMClient()
        self.explorer = ExplorerAgent(memory_dir=self.memory_dir)
        self.planner = PlannerAgent(memory_dir=self.memory_dir)
        self.worker = WorkerAgent(memory_dir=self.memory_dir)
        self.verifier = VerifierAgent(memory_dir=self.memory_dir)

        self.buddy = None
        try:
            from buddy.companion import BuddyManager
            from buddy.types import Species
            self.buddy = BuddyManager(species=Species.ROBOT, voice_enabled=False)
        except Exception as e:
            logger.debug("Buddy yüklenemedi: %s", e)

        logger.info("MustanCoordinator hazır | memory=%s", self.memory_dir)

    def _analyze_intent(self, user_input: str) -> str:
        try:
            response, _ = self.llm.generate_with_stats(
                prompt=f"Kullanıcı mesajı:\n{user_input}",
                system_prompt=INTENT_SYSTEM_PROMPT,
                use_rag=False,
                temperature=0.0,
            )
            cmd = response.strip().split()[0].lower()
            if not cmd.startswith("/"):
                cmd = "/" + cmd
            valid = {
                "/scan", "/plan", "/deeplan", "/operate", "/doctor",
                "/scope", "/reflect", "/rewind", "/btw", "/ide",
                "/status", "/summary", "/set", "/worker", "/verify",
                "/voice", "/chat", "/unknown",
            }
            if cmd not in valid:
                return "/chat"
            return cmd
        except Exception as e:
            logger.warning("Intent analizi başarısız: %s", e)
            return "/chat"

    def _route_command(self, cmd: str, args: str) -> bool:
        cmd = cmd.lower().strip()
        args = (args or "").strip()
        if cmd in ("/help", "help", "/list", "list", "/komutlar"):
            return bool(run_help(args))

        elif cmd in ("/doctor", "doctor"):
            return bool(run_doctor())  # True/False — main "bilinmeyen" basmaz

        elif cmd in ("/status", "status"):
            return bool(run_status())

        elif cmd in ("/summary", "summary"):
            use_llm = "llm" in args.lower()
            return bool(run_summary(use_llm=use_llm))

        elif cmd in ("/telemetry", "telemetry"):
            return bool(run_telemetry_report(self.memory_dir))

        elif cmd in ("/scope", "scope"):
            return bool(run_scope(rules=args, memory_dir=self.memory_dir))
       
        elif cmd in ("/scan", "scan"):
            target = args if args else "."
            return bool(run_scan(target_dir=target, memory_dir=self.memory_dir))

        elif cmd in ("/plan", "plan"):
            if not args:
                print("[-] /plan için hedef gerekli. Örnek: /plan kullanıcı girişi ekle")
                return False
            return bool(self.planner.execute_task(task_description=args))

        elif cmd in ("/deeplan", "deeplan"):
            if not args:
                print("[-] /deeplan için WP id gerekli. Örnek: /deeplan WP-001")
                return False
            return bool(self.planner.execute_task(task_description="", wp_id=args))

        elif cmd in ("/operate", "operate", "/coder", "coder"):
            return bool(run_operate(args))

        elif cmd in ("/reflect", "reflect"):
            return bool(run_reflect())

        elif cmd in ("/rewind", "rewind"):
            return bool(run_rewind(args))

        elif cmd in ("/btw", "btw"):
            return bool(run_btw(args))

        elif cmd in ("/ide", "ide"):
            return bool(run_ide(args))

        elif cmd in ("/set", "set"):
            return bool(run_set(args))

        elif cmd in ("/worker", "worker"):
            if not args:
                print("[-] /worker için WP id gerekli")
                return False
            return bool(self.worker.execute_task(wp_id=args))

        elif cmd in ("/repair", "repair"):
            if not args:
                print("[-] /repair için WP id gerekli")
                return False
            return self.worker.repair_task(args)

        elif cmd in ("/verify", "verify"):
            if args.upper().startswith("WP-") or (args.isdigit()):
                return bool(self.verifier.execute_task(wp_id=args))
            if args and ("/" in args or args.endswith(".py")):
                return bool(self.verifier.execute_task(target_file=args))
            return bool(
                self.verifier.execute_task(
                    task_description=args or "Son değişiklikleri doğrula"
                )
            )

        elif cmd in ("/voice", "voice"):
            from commands.voice import run_voice
            return bool(run_voice(args, coordinator=self))

        elif cmd in ("/buddy", "buddy") and self.buddy:
            from commands.buddy import run_buddy
            return bool(run_buddy(args, self.buddy))

        else:
            return False

    def _handle_chat(self, user_input: str) -> str:
        system = (
            "Sen MustanAgent'sın — otonom yazılım geliştirme asistanı.\n"
            "Kısa, net ve profesyonel cevap ver. "
            "Gerekirse kullanıcıya /plan, /operate, /scan gibi komutları öner."
        )
        try:
            response, stats = self.llm.generate_with_stats(
                prompt=user_input,
                system_prompt=system,
                use_rag=True,
                rag_query=user_input,
                memory_dir=self.memory_dir,
                temperature=0.5,
            )
            cost = stats.get("cost_usd", 0)
            print(f"   (token: {stats.get('total_tokens', '?')} | ${cost:.5f})")
            return response
        except Exception as e:
            return f"[-] Sohbet hatası: {e}"

    def chat(self, user_input: str) -> bool:
        text = (user_input or "").strip()
        if not text:
            return True

        if self.buddy and self.buddy.process_input(text):
            return True

        from core.intent_router import IntentRouter, Intent
        match = IntentRouter().route(text)
        if match.source == "rule":
            intent = match.intent.value
            args = match.args
            if match.intent == Intent.SCAN and not (args.endswith("/") or os.path.isdir(args)):
                args = ""
        else:
            intent = self._analyze_intent(text)
            args = text
        logger.info("Intent: %s ← %s", intent, text[:80])

        if intent in ("/chat", "/unknown"):
            reply = self._handle_chat(text)
            print(reply)
            return True

        return self._route_command(intent, args)

    def start_interactive_session(self) -> None:
        print("🤖 MustanAgent v3.3 PRO hazır. Komut veya doğal dil yazabilirsiniz.")
        print("   Çıkmak için: exit / quit / /quit\n")

        while True:
            try:
                user_input = input("Mustan> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGörüşmek üzere.")
                break

            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit", "/quit", "/exit"}:
                print("Sistem kapatılıyor...")
                break

            if user_input.startswith("/"):
                parts = user_input.split(maxsplit=1)
                cmd = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""
                handled = self._route_command(cmd, args)
                if not self.is_known_command(cmd):
                    print(f"[-] Bilinmeyen komut: {cmd}")
            else:
                self.chat(user_input)
