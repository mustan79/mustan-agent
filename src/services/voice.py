"""
MustanAgent v3.3 PRO - Voice Service
Gürültü önleme, sessizlik/halüsinasyon filtresi ve pyttsx3/edge-tts destekli ses motoru.
"""

from __future__ import annotations

import logging
import re
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger("mustan_agent.services.voice")

# Singleton örneği
_voice_instance: Optional[VoiceService] = None


def get_voice_service(language: str = "tr-TR", tts_enabled: bool = True) -> VoiceService:
    """VoiceService için Singleton erişim fonksiyonu."""
    global _voice_instance
    if _voice_instance is None:
        _voice_instance = VoiceService(language=language, tts_enabled=tts_enabled)
    return _voice_instance


# Sessizlikte STT motorlarının sıklıkla ürettiği halüsinasyon kelimeleri
HALLUCINATION_PATTERNS = [
    r"^teşekkür(?:ler)?\.?$",
    r"^izlediğiniz için teşekkürler\.?$",
    r"^altyazı\.?$",
    r"^subtitles?\.?$",
    r"^mbc\.?$",
    r"^bye\.?$",
    r"^\.$",
]


class VoiceService:
    def __init__(self, language: str = "tr-TR", tts_enabled: bool = True):
        self.language = language
        self.tts_enabled = tts_enabled
        self.tts_engine_name = "yok"
        self._lock = threading.Lock()

        # STT Hazırlığı
        self.recognizer = None
        self.microphone = None
        self._init_stt()

        # TTS Hazırlığı
        self.engine = None
        self._init_tts()

    def _init_stt(self) -> None:
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            # Gürültü ve sessizlik hassasiyet ayarları
            self.recognizer.energy_threshold = 300  # Minimum ses enerjisi eşiği
            self.recognizer.dynamic_energy_threshold = True  # Dinamik gürültü adaptasyonu
            self.recognizer.pause_threshold = 1.0  # Duraksama süresi (saniye)
            self.microphone = sr.Microphone()
            logger.info("STT (speech_recognition) başarıyla başlatıldı.")
        except Exception as e:
            logger.warning("STT motoru başlatılamadı: %s", e)

    def _init_tts(self) -> None:
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", 175)  # Konuşma hızı
            self.engine.setProperty("volume", 1.0)  # Ses seviyesi %100

            # Türkçe ses var mı kontrol et
            voices = self.engine.getProperty("voices")
            for v in voices:
                if "turkish" in v.name.lower() or "tr" in v.id.lower():
                    self.engine.setProperty("voice", v.id)
                    break

            self.tts_engine_name = "pyttsx3"
            logger.info("TTS (pyttsx3) başarıyla başlatıldı.")
        except Exception as e:
            logger.warning("pyttsx3 başlatılamadı, alternatif deneniyor: %s", e)
            try:
                import edge_tts
                self.tts_engine_name = "edge-tts"
            except ImportError:
                self.tts_engine_name = "yok"

    def set_enabled(self, enabled: bool) -> None:
        self.tts_enabled = enabled

    def status(self) -> Dict[str, Any]:
        return {
            "tts_enabled": self.tts_enabled,
            "tts_engine": self.tts_engine_name,
            "tts_available": self.tts_engine_name != "yok",
            "stt_available": self.recognizer is not None,
            "stt_ok": self.recognizer is not None and self.microphone is not None,
            "language": self.language,
        }

    def _is_hallucination(self, text: str) -> bool:
        """Sessizlikte oluşan STT halüsinasyonlarını temizler."""
        clean_text = text.strip().lower()
        if len(clean_text) < 2:
            return True

        for pattern in HALLUCINATION_PATTERNS:
            if re.match(pattern, clean_text, re.IGNORECASE):
                return True
        return False

    def listen_and_transcribe(
        self,
        timeout: float = 5.0,
        phrase_time_limit: float = 12.0,
    ) -> Optional[str]:
        """Mikrofondan sesi dinler, gürültüyü filtreler ve metne dönüştürür."""
        if not self.recognizer or not self.microphone:
            logger.error("STT bileşenleri hazır değil.")
            return None

        import speech_recognition as sr

        try:
            with self.microphone as source:
                # Ortam gürültüsünü otomatik kalibre et (0.6 sn)
                self.recognizer.adjust_for_ambient_noise(source, duration=0.6)
                logger.debug("Dinleniyor...")
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit,
                )

            # Google STT ile dönüştür
            text = self.recognizer.recognize_google(audio, language=self.language)
            text = text.strip()

            # Sessizlik halüsinasyonu kontrolü
            if self._is_hallucination(text):
                logger.debug("STT Gürültü/Halüsinasyon engellendi: '%s'", text)
                return None

            return text

        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except Exception as e:
            logger.error("STT Dinleme hatası: %s", e)
            return None

    def speak(self, text: str) -> None:
        """Metni sesli olarak okur."""
        if not self.tts_enabled or not text:
            return

        with self._lock:
            try:
                if self.tts_engine_name == "pyttsx3" and self.engine:
                    self.engine.say(text)
                    self.engine.runAndWait()
                elif self.tts_engine_name == "edge-tts":
                    self._speak_edge_tts(text)
                else:
                    logger.warning("Aktif TTS motoru yok. Metin: %s", text)
            except Exception as e:
                logger.exception("TTS seslendirme hatası: %s", e)

    def _speak_edge_tts(self, text: str) -> None:
        """Yedek online TTS motoru (edge-tts)."""
        import asyncio
        import os
        import tempfile

        async def _generate():
            import edge_tts
            communicate = edge_tts.Communicate(text, "tr-TR-AhmetNeural")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                tmp_path = fp.name
            await communicate.save(tmp_path)
            return tmp_path

        try:
            mp3_path = asyncio.run(_generate())
            try:
                from playsound import playsound
                playsound(mp3_path)
            except Exception:
                if os.name == "nt":
                    os.system(f'start /min "" "{mp3_path}"')
                else:
                    os.system(f'afplay "{mp3_path}" || aplay "{mp3_path}"')
            finally:
                if os.path.exists(mp3_path):
                    try:
                        os.remove(mp3_path)
                    except Exception:
                        pass
        except Exception as e:
            logger.error("Edge TTS hatası: %s", e)
