from unittest.mock import patch

from stt import load_whisper_model, transcribe


def test_load_whisper_model_returns_path():
    model = load_whisper_model()
    assert isinstance(model, str)
    assert "whisper" in model.lower()


@patch("stt.mlx_whisper")
def test_transcribe_returns_stripped_text(mock_whisper):
    mock_whisper.transcribe.return_value = {"text": "  Hello world  "}
    result = transcribe("model-path", "/tmp/audio.wav")
    assert result == "Hello world"
    mock_whisper.transcribe.assert_called_once_with(
        "/tmp/audio.wav", path_or_hf_repo="model-path"
    )


@patch("stt.mlx_whisper")
def test_transcribe_empty_result(mock_whisper):
    mock_whisper.transcribe.return_value = {"text": "   "}
    result = transcribe("model-path", "/tmp/audio.wav")
    assert result == ""
