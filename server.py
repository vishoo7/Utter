import json
import os
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory

from tts import generate_speech

app = Flask(__name__)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "history.json")
os.makedirs(STATIC_DIR, exist_ok=True)

# Global state
pipeline = None
generation_lock = threading.Lock()
status = {"state": "idle", "filename": None, "error": None}


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
    global pipeline
    from kokoro import KPipeline
    print("Loading Kokoro pipeline...")
    pipeline = KPipeline(lang_code="a")
    print("Pipeline ready.")


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
