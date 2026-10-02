"""
MustanAgent v3.3 PRO - CLI giriş noktası
"""

from __future__ import annotations

import logging
import os
import sys
import warnings
from pathlib import Path

# Gemini / google-genai çift key uyarılarını sustur
warnings.filterwarnings("ignore", message=".*Both GOOGLE_API_KEY and GEMINI_API_KEY.*")
os.environ.setdefault("GRPC_VERBOSITY", "ERROR")
os.environ.setdefault("GLOG_minloglevel", "2")

src_dir = os.path.dirname(os.path.abspath(__file__))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# =====================================================================
# LOG YAPILANDIRMASI: Konsol akışı kapatıldı, loglar Aimemory klasörüne aktarıldı
# =====================================================================
def setup_logging(log_dir_name: str = "Aimemory", log_file_name: str = "mustan_agent.log") -> None:
    """Tüm logları konsoldan siler, Aimemory altında dosyada saklar."""
    log_dir = Path(log_dir_name)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / log_file_name

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Mevcut konsol (StreamHandler) handler'larını tamamen temizle
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Sadece Aimemory/mustan_agent.log dosyasına UTF-8 formatında yazan handler ekle
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Gürültülü kütüphaneleri sessize al
    for noisy in ("google", "httpx", "httpcore", "openai", "urllib3", "comtypes", "grpc"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

logger = logging.getLogger("mustan_agent.main")


def main() -> int:
    # Windows redirected terminals may otherwise fail on Turkish text/emoji.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    if args and args[0] in {"--version", "-V", "version"}:
        from importlib.metadata import version
        print(version("mustan-agent"))
        return 0
    if args and args[0] in {"--help", "-h", "help", "/help", "list"}:
        from commands.help_cmd import run_help
        run_help()
        return 0
    setup_logging()
    print("=======================================================")
    print("MustanAgent v3.3 PRO - Sistem Baslatiliyor...")
    print("=======================================================")

    try:
        from agents.coordinator import MustanCoordinator
    except ImportError as e:
        logger.critical(f"Kritik baslatma hatasi: {e}")
        print(f"[-] Kritik baslatma hatasi: {e}")
        sys.exit(1)

    try:
        coordinator = MustanCoordinator()
    except Exception as e:
        logger.critical(f"Coordinator baslatilamadi: {e}")
        print(f"[-] Coordinator baslatilamadi: {e}")
        sys.exit(1)

    if args:
        cmd = args[0].lower()
        if not cmd.startswith("/"):
            cmd = "/" + cmd
        cmd_args = " ".join(args[1:])
        if not coordinator.is_known_command(cmd):
            print(f"[-] Bilinmeyen komut: {cmd}. /help yazin.")
            return 2
        try:
            return 0 if coordinator._route_command(cmd, cmd_args) else 1
        except Exception as exc:
            logger.exception("Komut hatası")
            print(f"[-] Komut başarısız: {exc}")
            return 1

    from services.away_summary import AwaySummaryService
    away_service = AwaySummaryService(timeout_seconds=300)
    print("Sistem cevrimici. Komut (/help) veya dogal dil kullanabilirsiniz.")
    print("Cikmak icin: exit | quit | /quit\n")

    while True:
        try:
            user_input = input("Mustan> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGorusmek uzere.")
            break

    # =========================================================
    # 1. KULLANICI DÖNDÜĞÜNDE İNAKTİF SÜREYİ KONTROL ET
    # Kullanıcı komutu yazıp Enter'a bastığı an aradan geçen zaman kontrol edilir.
    # =========================================================
        # Not: İstersen "recent_context" değerini "coordinator.get_history()" 
        # gibi bir metotla dinamik hale getirebilirsin.
        recent_context = "En son komut satırında eylem bekleniyordu." 
        summary = away_service.check_and_generate_summary(recent_context)
        if summary:
            print(f"\n🤖 {summary}\n")
    
        if not user_input:
            # Sadece Enter'a basıp geçerse döngü başa dönecektir.
            # Hatalı zaman ölçümünü önlemek için sayacı burada da sıfırlıyoruz.
            away_service.update_activity()
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
                if not coordinator.is_known_command(cmd):
                    print(f"[-] Bilinmeyen komut: {cmd}. /help ile listeyin.")
            else:
                coordinator.chat(user_input)
        except KeyboardInterrupt:
            print("\n[!] Islem iptal (Ctrl+C). Cikmak icin exit yazin.")
        except Exception as e:
            logger.exception("Dongu hatasi")
            print(f"[-] Hata: {e}")
        
    # =========================================================
        # 2. KOMUT ÇALIŞMASI BİTTİĞİNDE SAYACI SIFIRLA
        # Komut çalışırken geçen süreyi "inaktif" sanmaması için,
        # yeniden "Mustan>" sormadan hemen önce zamanı sıfırlıyoruz.
    # =========================================================
        away_service.update_activity()

    return 0


if __name__ == "__main__":
    sys.exit(main())

