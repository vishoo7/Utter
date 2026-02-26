#!/bin/bash
#
# Utter — Launcher
# Starts the Flask server, opens the browser, and handles clean shutdown.
#

UTTER_DIR="$HOME/.utter"

if [ ! -d "$UTTER_DIR" ]; then
    echo "Error: Utter is not installed. Run the install script first."
    echo "  curl -fsSL https://raw.githubusercontent.com/vishoo7/Utter/main/install.sh | bash"
    exit 1
fi

cd "$UTTER_DIR"
export PYTORCH_ENABLE_MPS_FALLBACK=1

# If server is already running, just open the browser
if lsof -i :5757 -sTCP:LISTEN &>/dev/null; then
    echo "Utter is already running."
    open "http://localhost:5757"
    exit 0
fi

# Clean shutdown on Ctrl+C, terminal close, or app quit
cleanup() {
    echo ""
    echo "Shutting down Utter..."
    kill "$SERVER_PID" 2>/dev/null
    wait "$SERVER_PID" 2>/dev/null
    echo "Goodbye!"
    exit 0
}
trap cleanup INT TERM HUP

# Start server in background
.venv/bin/python server.py &
SERVER_PID=$!

echo "Starting Utter..."

# Wait for server to become ready (up to 90 seconds)
for i in $(seq 1 90); do
    # Check if server process died
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        echo "Error: Server failed to start."
        exit 1
    fi
    if curl -s -o /dev/null http://127.0.0.1:5757 2>/dev/null; then
        echo "Utter is running at http://localhost:5757"
        open "http://localhost:5757"
        break
    fi
    sleep 1
done

# Keep running until server exits or user quits
wait "$SERVER_PID"
