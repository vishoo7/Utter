import json
import os
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory

import tempfile
from tts import generate_speech
from stt import load_whisper_model, transcribe

app = Flask(__name__)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "history.json")
os.makedirs(STATIC_DIR, exist_ok=True)

# Global state
pipeline = None
whisper_model = None
generation_lock = threading.Lock()
status = {"state": "idle", "filename": None, "error": None}
transcribe_status = {"state": "idle", "text": None, "error": None}


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []


def save_history():
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


history = load_history()


def load_pipeline():
    global pipeline, whisper_model
    from kokoro import KPipeline
    print("Loading Kokoro pipeline...")
    pipeline = KPipeline(lang_code="a")
    print("Pipeline ready.")
    print("Loading Whisper model reference...")
    whisper_model = load_whisper_model()
    print("Whisper ready (will download on first transcription).")


def run_generation(text, voice):
    global status
    try:
        status = {"state": "generating", "filename": None, "error": None}
        filename = generate_speech(pipeline, text, voice, STATIC_DIR)
        from datetime import datetime
        history.insert(0, {
            "filename": filename,
            "text": text[:200],
            "voice": voice,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        save_history()
        status = {"state": "done", "filename": filename, "error": None}
    except Exception as e:
        status = {"state": "error", "filename": None, "error": str(e)}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    text = data.get("text", "").strip()
    voice = data.get("voice", "af_heart")

    if not text:
        return jsonify({"status": "error", "message": "No text provided"}), 400

    if status["state"] == "generating":
        return jsonify({"status": "error", "message": "Generation already in progress"}), 409

    thread = threading.Thread(target=run_generation, args=(text, voice))
    thread.start()

    return jsonify({"status": "ok"})


UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def run_transcription(audio_path):
    global transcribe_status
    try:
        transcribe_status = {"state": "transcribing", "text": None, "error": None}
        text = transcribe(whisper_model, audio_path)
        transcribe_status = {"state": "done", "text": text, "error": None}
    except Exception as e:
        transcribe_status = {"state": "error", "text": None, "error": str(e)}
    finally:
        if os.path.exists(audio_path):
            os.unlink(audio_path)


@app.route("/transcribe", methods=["POST"])
def transcribe_audio():
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded"}), 400

    if transcribe_status["state"] == "transcribing":
        return jsonify({"status": "error", "message": "Transcription already in progress"}), 409

    f = request.files["file"]
    suffix = os.path.splitext(f.filename)[1] or ".wav"
    tmp = tempfile.NamedTemporaryFile(dir=UPLOAD_DIR, suffix=suffix, delete=False)
    f.save(tmp.name)
    tmp.close()

    thread = threading.Thread(target=run_transcription, args=(tmp.name,))
    thread.start()

    return jsonify({"status": "ok"})


@app.route("/transcribe/status")
def get_transcribe_status():
    return jsonify(transcribe_status)


@app.route("/audio/<path:filename>")
def audio(filename):
    return send_from_directory(STATIC_DIR, filename, mimetype="audio/mp4")


@app.route("/status")
def get_status():
    return jsonify(status)


@app.route("/history")
def get_history():
    return jsonify(history)


if __name__ == "__main__":
    load_pipeline()
    app.run(host="127.0.0.1", port=5757, debug=False)
