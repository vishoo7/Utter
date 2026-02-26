import mlx_whisper


def load_whisper_model():
    """Return the model path string. The model downloads on first use."""
    return "mlx-community/distil-whisper-large-v3"


def transcribe(model_path, audio_path):
    """Transcribe an audio file and return the text."""
    result = mlx_whisper.transcribe(
        audio_path,
        path_or_hf_repo=model_path,
    )
    return result["text"].strip()
