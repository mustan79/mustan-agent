"""
MustanAgent v3.3 PRO - VoiceService
Tek instance (singleton), kuyruklu TTS, platform-aware engine,
pyttsx3 → edge-tts fallback, thread-safe STT.
"""

from __future__ import annotations

import logging
import platform
import queue
import threading
import time
from typing import Optional

logger = logging.getLogger("mustan_agent.services.voice")


class VoiceService:
    _instance: Optional["VoiceService"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(
        self,
        language: str = "tr-TR",
        tts_enabled: bool = True,
        prefer_edge: bool = False,
        rate: int = 175,
        volume: float = 0.9,
    ):
        if getattr(self, "_initialized", False):
            return

        self.language = language
        self.tts_enabled = tts_enabled
        self.prefer_edge = prefer_edge
        self.rate = rate
        self.volume = max(0.0, min(1.0, volume))

        self._tts_queue: queue.Queue[Optional[str]] = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._engine = None
        self._engine_ok = False
        self._use_edge = False
        self._stop_event = threading.Event()

        self._recognizer = None
        self._mic = None
        self._stt_ok = False

        if self.tts_enabled:
            self._init_tts()
            self._start_worker()

        self._init_stt()
        self._initialized = True
        logger.info(
            "VoiceService hazır | TTS=%s | STT=%s | edge=%s",
            self._engine_ok or self._use_edge,
            self._stt_ok,
            self._use_edge,
        )

    def _init_tts(self) -> None:
        if self.prefer_edge:
            if self._try_edge_import():
                self._use_edge = True
                logger.info("TTS: edge-tts tercih edildi")
                return

        try:
            import pyttsx3

            system = platform.system().lower()
            if system == "windows":
                self._engine = pyttsx3.init(driverName="sapi5")
            elif system == "darwin":
                self._engine = pyttsx3.init(driverName="nsss")
            else:
                try:
                    self._engine = pyttsx3.init(driverName="espeak")
                except Exception:
                    self._engine = pyttsx3.init()

            self._engine.setProperty("rate", self.rate)
            self._engine.setProperty("volume", self.volume)

            try:
                voices = self._engine.getProperty("voices") or []
                for v in voices:
                    name = (getattr(v, "name", "") or "").lower()
                    lang = str(getattr(v, "languages", [])).lower()
                    if "turkish" in name or "tr" in lang or "türk" in name:
                        self._engine.setProperty("voice", v.id)
                        logger.info("Türkçe ses seçildi: %s", v.name)
                        break
            except Exception:
                pass

            self._engine_ok = True
            logger.info("TTS: pyttsx3 engine hazır (%s)", platform.system())
        except Exception as e:
            logger.warning("pyttsx3 başlatılamadı: %s", e)
            self._engine = None
            self._engine_ok = False
            if self._try_edge_import():
                self._use_edge = True
                logger.info("TTS: edge-tts fallback aktif")

    def _try_edge_import(self) -> bool:
        try:
            import edge_tts  # noqa: F401
            import asyncio  # noqa: F401
            return True
        except ImportError:
            return False

    def _start_worker(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._stop_event.clear()
        self._worker = threading.Thread(
            target=self._tts_worker,
            name="MustanTTSWorker",
            daemon=True,
        )
        self._worker.start()

    def _tts_worker(self) -> None:
        while not self._stop_event.is_set():
            try:
                text = self._tts_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if text is None:
                break
            try:
                if self._use_edge:
                    self._speak_edge(text)
                elif self._engine_ok and self._engine is not None:
                    self._engine.say(text)
                    self._engine.runAndWait()
                else:
                    logger.debug("TTS atlandı (engine yok): %s", text[:60])
            except Exception as e:
                logger.error("TTS worker hatası: %s", e)
                if not self._use_edge:
                    try:
                        self._init_tts()
                    except Exception:
                        pass
            finally:
                self._tts_queue.task_done()

    def _speak_edge(self, text: str) -> None:
        import asyncio
        import tempfile
        import os

        async def _gen():
            import edge_tts
            voice = (
                "tr-TR-AhmetNeural"
                if self.language.startswith("tr")
                else "en-US-ChristopherNeural"
            )
            communicate = edge_tts.Communicate(text, voice)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp = f.name
            await communicate.save(tmp)
            return tmp

        try:
            loop = asyncio.new_event_loop()
            tmp_path = loop.run_until_complete(_gen())
            loop.close()

            try:
                from playsound import playsound
                playsound(tmp_path)
            except Exception:
                try:
                    import pygame
                    pygame.mixer.init()
                    pygame.mixer.music.load(tmp_path)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.05)
                except Exception as e:
                    logger.error("edge-tts çalma hatası: %s", e)
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
        except Exception as e:
            logger.error("edge-tts üretim hatası: %s", e)

    def speak(self, text: str) -> None:
        if not self.tts_enabled or not text or not text.strip():
            return
        if not (self._engine_ok or self._use_edge):
            logger.debug("TTS devre dışı: %s", text[:40])
            return
        self._tts_queue.put(text.strip())

    def speak_and_wait(self, text: str, timeout: float = 30.0) -> None:
        if not text:
            return
        self.speak(text)
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._tts_queue.unfinished_tasks == 0:
                break
            time.sleep(0.05)

    def set_enabled(self, enabled: bool) -> None:
        self.tts_enabled = enabled

    def _init_stt(self) -> None:
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._recognizer.dynamic_energy_threshold = True
            self._recognizer.pause_threshold = 0.8
            self._mic = sr.Microphone()
            self._stt_ok = True
            logger.info("STT: speech_recognition + Microphone hazır")
        except Exception as e:
            logger.warning("STT başlatılamadı: %s", e)
            self._stt_ok = False

    def listen_and_transcribe(
        self,
        timeout: float = 5.0,
        phrase_time_limit: float = 12.0,
        adjust_noise: bool = True,
    ) -> Optional[str]:
        if not self._stt_ok or self._recognizer is None or self._mic is None:
            logger.warning("STT kullanılamıyor")
            return None

        import speech_recognition as sr

        try:
            with self._mic as source:
                if adjust_noise:
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.6)
                print("🎤 Dinleniyor...")
                audio = self._recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit,
                )

            try:
                text = self._recognizer.recognize_google(
                    audio, language=self.language
                )
                logger.info("STT: %s", text)
                return text.strip()
            except sr.UnknownValueError:
                print("[~] Anlaşılamadı, tekrar deneyin.")
                return None
            except sr.RequestError as e:
                logger.error("Google STT isteği başarısız: %s", e)
                print("[-] Ses tanıma servisine ulaşılamadı.")
                return None
        except sr.WaitTimeoutError:
            print("[~] Süre doldu, ses algılanmadı.")
            return None
        except Exception as e:
            logger.error("STT hatası: %s", e)
            return None

    def status(self) -> dict:
        return {
            "tts_enabled": self.tts_enabled,
            "tts_engine": (
                "edge-tts" if self._use_edge
                else ("pyttsx3" if self._engine_ok else "yok")
            ),
            "stt_ok": self._stt_ok,
            "language": self.language,
            "queue_size": self._tts_queue.qsize(),
        }

    def shutdown(self) -> None:
        self._stop_event.set()
        self._tts_queue.put(None)
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=2.0)
        logger.info("VoiceService kapatıldı")


def get_voice_service(**kwargs) -> VoiceService:
    return VoiceService(**kwargs)
