import os
import re
import subprocess
import tempfile
import numpy as np
import soundfile as sf


def sanitize_filename(text, max_words=5):
    """Generate a filename from the first N words of text."""
    words = text.split()[:max_words]
    name = "_".join(words)
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s]+", "_", name).strip("_").lower()
    if not name:
        name = "output"
    return name[:80]


def generate_speech(pipeline, text, voice, output_dir):
    """Generate M4A speech from text using Kokoro TTS.

    Returns the output filename (relative to output_dir).
    """
    # Build smart filename from first 5 words + timestamp
    from datetime import datetime

    base = sanitize_filename(text)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{base}_{timestamp}.m4a"
    output_path = os.path.join(output_dir, filename)

    # Collect all audio chunks from the pipeline
    chunks = []
    for _gs, _ps, audio in pipeline(text, voice=voice):
        chunks.append(audio)

    if not chunks:
        raise RuntimeError("Kokoro produced no audio output")

    combined = np.concatenate(chunks)

    # Write WAV to temp file, then convert to M4A
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_wav = tmp.name
        sf.write(tmp_wav, combined, 24000)

    try:
        subprocess.run(
            [
                "afconvert",
                "-f", "m4af",
                "-d", "aac",
                "-b", "64000",
                tmp_wav,
                output_path,
            ],
            check=True,
            capture_output=True,
        )
    finally:
        os.unlink(tmp_wav)

    return filename
