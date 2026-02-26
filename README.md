# Utter

Local text-to-speech and speech-to-text web app powered by [Kokoro TTS](https://huggingface.co/hexgrad/Kokoro-82M) and [Whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper), optimized for Apple Silicon.

Everything runs on your machine. No cloud APIs, no data leaves your computer.

## Install

**Requirements:**
- Mac with Apple Silicon (M1/M2/M3/M4)
- macOS 13 Ventura or later
- ~2.5 GB of disk space (Python packages + AI models)

Paste in Terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/vishoo7/Utter/main/install.sh | bash
```

The script installs everything automatically (~5-10 min depending on internet speed): Homebrew, Python, AI models, and a ready-to-use app. When done, launch Utter by:
- Double-clicking **Utter** in /Applications, or
- Running `utter` from Terminal

To uninstall: `bash ~/.utter/uninstall.sh`

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

## Manual Setup

If you prefer to set things up yourself instead of using the install script:

**Requirements:** macOS with Apple Silicon, Python 3.10+, [espeak-ng](https://github.com/espeak-ng/espeak-ng)

```bash
git clone https://github.com/vishoo7/Utter.git
cd Utter
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
brew install espeak-ng
./run.sh
```

Then open [http://localhost:5757](http://localhost:5757). On first run, the Kokoro model (~330 MB) and Whisper model (~750 MB) will download automatically.

## Project Structure

```
Utter/
├── server.py          # Flask server (localhost:5757)
├── tts.py             # Kokoro TTS: text → WAV → M4A
├── stt.py             # Whisper STT: audio → text
├── templates/
│   └── index.html     # Single-page dark mode UI
├── static/            # Generated audio files
├── install.sh         # One-line installer
├── uninstall.sh       # Clean removal
├── launcher.sh        # App launcher (server + browser)
├── run.sh             # Dev launch script
└── requirements.txt
```

## How It Works

- **TTS**: Text is fed through Kokoro's `KPipeline`, which generates audio chunks. Chunks are concatenated, written as WAV, then converted to M4A via macOS `afconvert`.
- **STT**: Uploaded audio is transcribed using `mlx-whisper` with the `distil-whisper/distil-large-v3` model, running natively on Apple Silicon via the MLX framework.
- Both operations run in background threads so the UI stays responsive, with status polling every second.
