"""
MustanAgent v3.3 PRO - /voice komutu
Test + dinle-konuş döngüsü ve LLM yanıt seslendirme entegrasyonu.
"""

from __future__ import annotations

import logging
import time
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
        logger.info("[+] TTS açıldı")
        print("[+] TTS açıldı")

        voice.speak("Ses sistemi açıldı")
        return True

    if sub in ("off", "disable"):
        voice.set_enabled(False)
        print("[+] TTS kapatıldı")
        logger.info("[+] TTS kapatıldı")
        return True

    if sub == "test":
        print("[*] TTS test başlıyor...")
        logger.info("[*] TTS test başlıyor...")
        st = voice.status()
        if st["tts_engine"] == "yok":
            logger.info("[-] Hiçbir TTS engine bulunamadı.")
            print("[-] Hiçbir TTS engine bulunamadı.")
            print("    pip install pyttsx3  veya  pip install edge-tts playsound")
            return False
        
        logger.info(f"[+] Test başlatılıyor (engine: {st['tts_engine']})...")
        print(f"[+] Test başlatılıyor (engine: {st['tts_engine']})...")
        voice.speak("Merhaba! Mustan Agent ses sistemi sorunsuz çalışıyor.")
        return True

    st = voice.status()
    if st.get("stt_available") is False or st.get("stt_ok") is False:
        print("[-] Mikrofon/STT kullanılabilir değil. speech_recognition ve PyAudio kurulumunu kontrol edin.")
        return False

    print("🎤 Sesli mod aktif. Konuşun (çıkmak için 'iptal' / 'çıkış' veya Ctrl+C).")
    voice.speak("Sesli mod aktif. Dinliyorum.")

    try:
        while True:
            # 5 saniye dinle, maximum 12 saniye konuşma limiti
            text = voice.listen_and_transcribe(timeout=5.0, phrase_time_limit=12.0)
            if not text:
                continue

            print(f"\n🗣️ Siz: {text}")
            logger.info(f"\n🗣️ Siz: {text}")
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
                        response_text = ""
                        # Coordinator içinden dönen yanıtı yakalayıp seslendiriyoruz
                        if hasattr(coordinator, "chat"):
                            response_text = coordinator.chat(text)
                        elif hasattr(coordinator, "run"):
                            response_text = coordinator.run(text)

                        # Dönüş tipi string ise seslendir
                        if isinstance(response_text, str) and response_text.strip():
                            # Çok uzun yanıtların sadece ilk kısmını seslendir, ekrana tamamını bas
                            speak_part = response_text.split("\n\n")[0][:250]
                            voice.speak(speak_part)
                        else:
                            voice.speak("İşlem tamamlandı.")

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

