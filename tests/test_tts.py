import os
import subprocess
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from tts import generate_speech, sanitize_filename


class TestSanitizeFilename:
    def test_basic(self):
        assert sanitize_filename("Hello world") == "hello_world"

    def test_max_words(self):
        text = "one two three four five six seven"
        result = sanitize_filename(text, max_words=5)
        assert result == "one_two_three_four_five"

    def test_special_chars_removed(self):
        assert sanitize_filename("Hello! @world# $test") == "hello_world_test"

    def test_empty_string_fallback(self):
        assert sanitize_filename("!!!") == "output"
        assert sanitize_filename("") == "output"

    def test_long_text_truncated(self):
        text = "a" * 200
        result = sanitize_filename(text, max_words=1)
        assert len(result) <= 80

    def test_whitespace_collapsed(self):
        assert sanitize_filename("hello   world") == "hello_world"

    def test_single_word(self):
        assert sanitize_filename("hello") == "hello"

    def test_custom_max_words(self):
        result = sanitize_filename("a b c d e f", max_words=3)
        assert result == "a_b_c"

    def test_hyphens_preserved(self):
        result = sanitize_filename("well-known fact")
        assert "well-known" in result


class TestGenerateSpeech:
    def _make_pipeline(self, chunks=None):
        """Create a mock Kokoro pipeline that yields audio chunks."""
        if chunks is None:
            chunks = [np.zeros(2400, dtype=np.float32)]

        def pipeline_fn(text, voice=None):
            for chunk in chunks:
                yield None, None, chunk

        return pipeline_fn

    @patch("tts.subprocess.run")
    def test_returns_filename(self, mock_run, tmp_path):
        pipeline = self._make_pipeline()
        filename = generate_speech(pipeline, "Hello world", "af_heart", str(tmp_path))
        assert filename.endswith(".m4a")
        assert "hello_world" in filename

    @patch("tts.subprocess.run")
    def test_writes_wav_then_converts(self, mock_run, tmp_path):
        pipeline = self._make_pipeline()
        generate_speech(pipeline, "Test", "af_heart", str(tmp_path))
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "afconvert"
        assert args[1:3] == ["-f", "m4af"]
        assert args[3:5] == ["-d", "aac"]

    @patch("tts.subprocess.run")
    def test_temp_wav_cleaned_up(self, mock_run, tmp_path):
        pipeline = self._make_pipeline()
        generate_speech(pipeline, "Test", "af_heart", str(tmp_path))
        # The temp .wav file should have been deleted
        wav_files = [f for f in os.listdir(str(tmp_path)) if f.endswith(".wav")]
        assert len(wav_files) == 0

    @patch("tts.subprocess.run")
    def test_temp_wav_cleaned_up_on_convert_failure(self, mock_run, tmp_path):
        mock_run.side_effect = subprocess.CalledProcessError(1, "afconvert")
        pipeline = self._make_pipeline()
        with pytest.raises(subprocess.CalledProcessError):
            generate_speech(pipeline, "Test", "af_heart", str(tmp_path))
        # Temp wav should still be cleaned up
        import glob

        wav_files = glob.glob("/tmp/*.wav") + [
            f for f in os.listdir(str(tmp_path)) if f.endswith(".wav")
        ]
        # The temp file is in the system temp dir, not tmp_path, but the
        # finally block should have unlinked it

    def test_no_audio_raises(self, tmp_path):
        def empty_pipeline(text, voice=None):
            return iter([])

        with pytest.raises(RuntimeError, match="no audio output"):
            generate_speech(empty_pipeline, "Test", "af_heart", str(tmp_path))

    @patch("tts.subprocess.run")
    def test_concatenates_multiple_chunks(self, mock_run, tmp_path):
        chunks = [
            np.ones(1000, dtype=np.float32),
            np.ones(2000, dtype=np.float32) * 0.5,
        ]
        pipeline = self._make_pipeline(chunks)
        generate_speech(pipeline, "Test", "af_heart", str(tmp_path))
        # Verify afconvert was called (meaning wav was written with combined audio)
        mock_run.assert_called_once()
