# Utter

Local text-to-speech and speech-to-text web app powered by [Kokoro TTS](https://huggingface.co/hexgrad/Kokoro-82M) and [Whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper), optimized for Apple Silicon.

Everything runs on your machine. No cloud APIs, no data leaves your computer.

## Features

**Text to Speech** — Kokoro-82M via `kokoro`
- 3 built-in voices (af_heart, am_michael, bf_emma)
- Outputs M4A files (64kbps AAC) — 30 minutes of speech is ~15MB
- Smart filenames based on the first 5 words of input text
- Generation history with playback and download

**Speech to Text** — Distil-Whisper Large V3 via `mlx-whisper`
- Drag-and-drop audio file upload
- Runs natively on Apple Silicon via MLX
- Copy transcript or send it directly to the TTS tab

## Requirements

- macOS with Apple Silicon (M1/M2/M3/M4)
- Python 3.10+
- [espeak-ng](https://github.com/espeak-ng/espeak-ng) (`brew install espeak-ng`)

## Setup

```bash
git clone https://github.com/vishoo7/Utter.git
cd Utter
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
brew install espeak-ng
```

## Usage

```bash
./run.sh
```

Then open [http://localhost:5757](http://localhost:5757).

On first run, the Kokoro model (~330MB) and Whisper model (~750MB) will download from HuggingFace automatically and are cached for subsequent runs.

## Project Structure

```
Utter/
├── server.py          # Flask server (localhost:5757)
├── tts.py             # Kokoro TTS: text → WAV → M4A
├── stt.py             # Whisper STT: audio → text
├── templates/
│   └── index.html     # Single-page dark mode UI
├── static/            # Generated audio files
├── run.sh             # Launch script
└── requirements.txt
```

## How It Works

- **TTS**: Text is fed through Kokoro's `KPipeline`, which generates audio chunks. Chunks are concatenated, written as WAV, then converted to M4A via macOS `afconvert`.
- **STT**: Uploaded audio is transcribed using `mlx-whisper` with the `distil-whisper/distil-large-v3` model, running natively on Apple Silicon via the MLX framework.
- Both operations run in background threads so the UI stays responsive, with status polling every second.
