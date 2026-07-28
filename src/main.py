"""
MustanAgent v3.3 PRO - CLI giriş noktası
"""

from __future__ import annotations

import logging
import os
import sys
import warnings

# Gemini / google-genai çift key uyarılarını sustur (ekran okuyucu + gürültü)
warnings.filterwarnings("ignore", message=".*Both GOOGLE_API_KEY and GEMINI_API_KEY.*")
os.environ.setdefault("GRPC_VERBOSITY", "ERROR")
os.environ.setdefault("GLOG_minloglevel", "2")

src_dir = os.path.dirname(os.path.abspath(__file__))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
# Gürültülü kütüphaneler
for noisy in ("google", "httpx", "httpcore", "openai", "urllib3"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

logger = logging.getLogger("mustan_agent.main")


def main() -> None:
    print("=======================================================")
    print("MustanAgent v3.3 PRO - Sistem Baslatiliyor...")
    print("=======================================================")

    try:
        from agents.coordinator import MustanCoordinator
    except ImportError as e:
        print(f"[-] Kritik baslatma hatasi: {e}")
        sys.exit(1)

    try:
        coordinator = MustanCoordinator()
    except Exception as e:
        print(f"[-] Coordinator baslatilamadi: {e}")
        sys.exit(1)

    args = sys.argv[1:]
    if args:
        cmd = args[0].lower()
        if not cmd.startswith("/"):
            cmd = "/" + cmd
        cmd_args = " ".join(args[1:])
        handled = coordinator._route_command(cmd, cmd_args)
        if not handled:
            print(f"[-] Bilinmeyen komut: {cmd}. /help yazin.")
        return

    print("Sistem cevrimici. Komut (/help) veya dogal dil kullanabilirsiniz.")
    print("Cikmak icin: exit | quit | /quit\n")

    while True:
        try:
            user_input = input("Mustan> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGorusmek uzere.")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "/quit", "/exit"}:
            print("Sistem kapatiliyor...")
            break

        try:
            if user_input.startswith("/"):
                parts = user_input.split(maxsplit=1)
                cmd = parts[0].lower()
                cmd_args = parts[1] if len(parts) > 1 else ""
                handled = coordinator._route_command(cmd, cmd_args)
                if not handled:
                    print(f"[-] Bilinmeyen komut: {cmd}. /help ile listeyin.")
            else:
                coordinator.chat(user_input)
        except KeyboardInterrupt:
            print("\n[!] Islem iptal (Ctrl+C). Cikmak icin exit yazin.")
        except Exception as e:
            logger.exception("Dongu hatasi")
            print(f"[-] Hata: {e}")


if __name__ == "__main__":
    main()
