# tests/test_voice.py
import sys
from unittest.mock import MagicMock, patch, call
import pytest

# speech_recognition’ı en baştan sahte yap
class FakeWaitTimeoutError(Exception):
    pass

mock_sr = MagicMock()
mock_sr.WaitTimeoutError = FakeWaitTimeoutError
mock_sr.UnknownValueError = type("UnknownValueError", (Exception,), {})
mock_sr.RequestError = type("RequestError", (Exception,), {})
sys.modules["speech_recognition"] = mock_sr

# pyttsx3 / edge_tts / playsound da patlamasın
sys.modules["pyttsx3"] = MagicMock()
sys.modules["edge_tts"] = MagicMock()
sys.modules["playsound"] = MagicMock()
sys.modules["pygame"] = MagicMock()

from commands.voice import run_voice


class TestVoiceCommand:

    @patch("commands.voice.get_voice_service")
    def test_run_voice_success_and_routing(self, mock_get_voice):
        """Bir kez dinler → metin gelir → coordinator.chat çağrılır → 'çıkış' ile döngü biter"""
        mock_voice = MagicMock()
        mock_get_voice.return_value = mock_voice

        # İlk çağrıda metin, ikinci çağrıda çıkış komutu
        mock_voice.listen_and_transcribe.side_effect = [
            "Sistemi test eder misin",
            "çıkış",
        ]

        mock_coordinator = MagicMock()
        mock_coordinator.chat.return_value = True

        result = run_voice(coordinator=mock_coordinator)

        assert result is True
        mock_coordinator.chat.assert_called_once_with("Sistemi test eder misin")
        # speak en az bir kez çağrılmış olmalı (giriş + "Tamam, işledim.")
        assert mock_voice.speak.call_count >= 2

    @patch("commands.voice.get_voice_service")
    def test_run_voice_timeout_then_exit(self, mock_get_voice):
        """Timeout → None döner → döngü devam eder → sonra 'iptal' ile çıkar"""
        mock_voice = MagicMock()
        mock_get_voice.return_value = mock_voice

        mock_voice.listen_and_transcribe.side_effect = [
            None,          # timeout / anlaşılmadı
            None,          # tekrar
            "iptal",       # çıkış
        ]

        result = run_voice(coordinator=None)

        assert result is True          # kod her zaman True döner (döngüden çıkınca)
        assert mock_voice.listen_and_transcribe.call_count == 3

    @patch("commands.voice.get_voice_service")
    def test_run_voice_status(self, mock_get_voice):
        mock_voice = MagicMock()
        mock_voice.status.return_value = {
            "tts_enabled": True,
            "tts_engine": "pyttsx3",
            "stt_ok": True,
            "language": "tr-TR",
            "queue_size": 0,
        }
        mock_get_voice.return_value = mock_voice

        result = run_voice(args="status")
        assert result is True
        mock_voice.status.assert_called_once()
