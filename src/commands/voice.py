"""
MustanAgent v3.3 PRO - /voice komutu
Test + dinle-konuş döngüsü.
"""

from __future__ import annotations

import logging
from typing import Any

from services.voice import get_voice_service

logger = logging.getLogger("mustan_agent.commands.voice")


def run_voice(args: str = "", coordinator: Any = None) -> bool:
    """
    /voice              → dinle-konuş döngüsü
    /voice test         → TTS test
    /voice status       → motor durumu
    /voice on | off     → TTS aç/kapa
    """
    parts = (args or "").strip().split(maxsplit=1)
    sub = parts[0].lower() if parts else ""

    voice = get_voice_service(language="tr-TR", tts_enabled=True)

    if sub == "status":
        st = voice.status()
        print("—— Voice Durumu ——")
        for k, v in st.items():
            print(f"  {k}: {v}")
        return True

    if sub in ("on", "enable"):
        voice.set_enabled(True)
        print("[+] TTS açıldı")
        voice.speak("Ses sistemi açıldı")
        return True

    if sub in ("off", "disable"):
        voice.set_enabled(False)
        print("[+] TTS kapatıldı")
        return True

    if sub == "test":
        print("[*] TTS test başlıyor...")
        voice.speak("Merhaba! Mustan Agent ses sistemi çalışıyor.")
        import time
        time.sleep(0.3)
        st = voice.status()
        if st["tts_engine"] == "yok":
            print("[-] Hiçbir TTS engine bulunamadı.")
            print("    pip install pyttsx3  veya  pip install edge-tts playsound")
            return False
        print(f"[+] Test kuyruğa alındı (engine: {st['tts_engine']})")
        return True

    print("🎤 Sesli mod aktif. Konuşun (çıkmak için 'iptal' / 'çıkış' veya Ctrl+C).")
    voice.speak("Sesli mod aktif. Dinliyorum.")

    try:
        while True:
            text = voice.listen_and_transcribe(timeout=6.0, phrase_time_limit=15.0)
            if not text:
                continue

            print(f"Siz: {text}")
            low = text.lower().strip()
            if low in ("iptal", "çıkış", "çık", "exit", "quit", "kapat"):
                voice.speak("Sesli mod kapatılıyor.")
                print("[+] Sesli mod sonlandı.")
                break

            if coordinator is not None:
                try:
                    if text.startswith("/"):
                        parts_cmd = text.split(maxsplit=1)
                        cmd = parts_cmd[0].lower()
                        cmd_args = parts_cmd[1] if len(parts_cmd) > 1 else ""
                        coordinator._route_command(cmd, cmd_args)
                    else:
                        if hasattr(coordinator, "chat"):
                            coordinator.chat(text)
                            voice.speak("Tamam, işledim.")
                        else:
                            voice.speak("Komut işlendi.")
                except Exception as e:
                    logger.exception("Voice → coordinator hatası")
                    voice.speak("Bir hata oluştu.")
                    print(f"[-] {e}")
            else:
                voice.speak(f"Anladım: {text}")

    except KeyboardInterrupt:
        print("\n[!] Sesli mod kesildi (Ctrl+C).")
        voice.speak("Sesli mod kapatıldı.")

    return True


def speak(text: str) -> None:
    get_voice_service().speak(text)


def get_tts_engine():
    return get_voice_service()
