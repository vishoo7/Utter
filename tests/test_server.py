import io
import json
import os
import time
from unittest.mock import MagicMock, patch

import pytest


class TestIndex:
    def test_index_returns_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Utter" in resp.data


class TestGenerate:
    def test_missing_text(self, client):
        resp = client.post("/generate", json={"text": ""})
        assert resp.status_code == 400
        assert "No text" in resp.get_json()["message"]

    def test_missing_text_whitespace(self, client):
        resp = client.post("/generate", json={"text": "   "})
        assert resp.status_code == 400

    @patch("server.generate_speech")
    def test_successful_generate(self, mock_gen, client):
        mock_gen.return_value = "test_output.m4a"
        resp = client.post("/generate", json={"text": "Hello", "voice": "af_heart"})
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"

    @patch("server.generate_speech")
    def test_concurrent_generation_rejected(self, mock_gen, client):
        import server

        server.status = {"state": "generating", "filename": None, "error": None}
        resp = client.post("/generate", json={"text": "Hello"})
        assert resp.status_code == 409

    @patch("server.generate_speech")
    def test_default_voice(self, mock_gen, client):
        mock_gen.return_value = "out.m4a"
        resp = client.post("/generate", json={"text": "Hello"})
        assert resp.status_code == 200


class TestStatus:
    def test_idle_status(self, client):
        resp = client.get("/status")
        data = resp.get_json()
        assert data["state"] == "idle"

    def test_status_reflects_state(self, client):
        import server

        server.status = {"state": "done", "filename": "test.m4a", "error": None}
        resp = client.get("/status")
        data = resp.get_json()
        assert data["state"] == "done"
        assert data["filename"] == "test.m4a"


class TestHistory:
    def test_empty_history(self, client):
        resp = client.get("/history")
        assert resp.get_json() == []

    def test_history_with_entries(self, client):
        import server

        server.history = [
            {"filename": "a.m4a", "text": "hello", "voice": "af_heart", "timestamp": "2025-01-01"}
        ]
        resp = client.get("/history")
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["filename"] == "a.m4a"


class TestAudio:
    def test_audio_serves_file(self, client):
        import server

        # Create a test audio file in the static dir
        audio_path = os.path.join(server.STATIC_DIR, "test.m4a")
        with open(audio_path, "wb") as f:
            f.write(b"fake audio content")

        resp = client.get("/audio/test.m4a")
        assert resp.status_code == 200
        assert resp.data == b"fake audio content"

    def test_audio_missing_file(self, client):
        resp = client.get("/audio/nonexistent.m4a")
        assert resp.status_code == 404


class TestTranscribe:
    def test_no_file_uploaded(self, client):
        resp = client.post("/transcribe")
        assert resp.status_code == 400
        assert "No file" in resp.get_json()["message"]

    def test_concurrent_transcription_rejected(self, client):
        import server

        server.transcribe_status = {"state": "transcribing", "text": None, "error": None}
        data = {"file": (io.BytesIO(b"audio"), "test.wav")}
        resp = client.post("/transcribe", data=data, content_type="multipart/form-data")
        assert resp.status_code == 409

    @patch("server.transcribe")
    def test_successful_transcribe(self, mock_transcribe, client):
        mock_transcribe.return_value = "Hello world"
        data = {"file": (io.BytesIO(b"audio data"), "test.wav")}
        resp = client.post("/transcribe", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"

    def test_transcribe_status_endpoint(self, client):
        resp = client.get("/transcribe/status")
        data = resp.get_json()
        assert data["state"] == "idle"


class TestRunGeneration:
    @patch("server.generate_speech")
    def test_run_generation_success(self, mock_gen, tmp_path):
        import server

        mock_gen.return_value = "output.m4a"
        server.run_generation("Hello", "af_heart")
        assert server.status["state"] == "done"
        assert server.status["filename"] == "output.m4a"
        assert len(server.history) == 1
        assert server.history[0]["text"] == "Hello"

    @patch("server.generate_speech")
    def test_run_generation_error(self, mock_gen):
        import server

        mock_gen.side_effect = RuntimeError("TTS failed")
        server.run_generation("Hello", "af_heart")
        assert server.status["state"] == "error"
        assert "TTS failed" in server.status["error"]

    @patch("server.generate_speech")
    def test_run_generation_saves_history(self, mock_gen, tmp_path):
        import server

        mock_gen.return_value = "out.m4a"
        server.run_generation("A long text that should be truncated", "am_michael")
        assert server.history[0]["voice"] == "am_michael"
        assert os.path.exists(server.HISTORY_FILE)
        with open(server.HISTORY_FILE) as f:
            saved = json.load(f)
        assert len(saved) == 1


class TestRunTranscription:
    @patch("server.transcribe")
    def test_run_transcription_success(self, mock_transcribe, tmp_path):
        import server

        mock_transcribe.return_value = "Transcribed text"
        audio_file = tmp_path / "audio.wav"
        audio_file.write_bytes(b"fake audio")
        server.run_transcription(str(audio_file))
        assert server.transcribe_status["state"] == "done"
        assert server.transcribe_status["text"] == "Transcribed text"
        assert not audio_file.exists()  # temp file cleaned up

    @patch("server.transcribe")
    def test_run_transcription_error(self, mock_transcribe, tmp_path):
        import server

        mock_transcribe.side_effect = Exception("Whisper failed")
        audio_file = tmp_path / "audio.wav"
        audio_file.write_bytes(b"fake audio")
        server.run_transcription(str(audio_file))
        assert server.transcribe_status["state"] == "error"
        assert "Whisper failed" in server.transcribe_status["error"]
        assert not audio_file.exists()  # cleaned up even on error

    @patch("server.transcribe")
    def test_run_transcription_cleans_up_on_error(self, mock_transcribe, tmp_path):
        import server

        mock_transcribe.side_effect = Exception("fail")
        audio_file = tmp_path / "audio.wav"
        audio_file.write_bytes(b"data")
        server.run_transcription(str(audio_file))
        assert not audio_file.exists()


class TestLoadHistory:
    def test_load_history_no_file(self, tmp_path):
        import server

        server.HISTORY_FILE = str(tmp_path / "nonexistent.json")
        result = server.load_history()
        assert result == []

    def test_load_history_with_file(self, tmp_path):
        import server

        history_file = tmp_path / "history.json"
        history_file.write_text(json.dumps([{"filename": "a.m4a"}]))
        server.HISTORY_FILE = str(history_file)
        result = server.load_history()
        assert len(result) == 1
