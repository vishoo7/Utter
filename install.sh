#!/bin/bash
#
# Utter — One-line installer for macOS (Apple Silicon)
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/vishoo7/Utter/main/install.sh | bash
#

set -e

# ── Colors ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

UTTER_DIR="$HOME/.utter"
REPO_URL="https://github.com/vishoo7/Utter.git"

info()  { echo -e "${BLUE}==>${NC} ${BOLD}$1${NC}"; }
ok()    { echo -e "${GREEN}  ✓${NC} $1"; }
warn()  { echo -e "${YELLOW}  !${NC} $1"; }
fail()  { echo -e "${RED}  ✗ $1${NC}"; exit 1; }

# ── Pre-flight checks ──────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}Utter Installer${NC}"
echo "Local text-to-speech & speech-to-text for Mac"
echo ""

# Must be macOS
if [ "$(uname)" != "Darwin" ]; then
    fail "Utter requires macOS. Detected: $(uname)"
fi

# Must be Apple Silicon
ARCH=$(uname -m)
if [ "$ARCH" != "arm64" ]; then
    fail "Utter requires Apple Silicon (M1/M2/M3/M4). Detected: $ARCH"
fi

# ── Step 1: Xcode Command Line Tools ───────────────────────────────────────
info "Checking Xcode Command Line Tools..."

if xcode-select -p &>/dev/null; then
    ok "Already installed"
else
    warn "Not found — installing now..."
    echo ""
    echo -e "    ${BOLD}A dialog box will appear on your screen.${NC}"
    echo -e "    ${BOLD}Click \"Install\" and wait for it to finish.${NC}"
    echo ""
    xcode-select --install 2>/dev/null || true
    echo "    Waiting for installation to complete..."
    until xcode-select -p &>/dev/null; do
        sleep 5
    done
    ok "Installed"
fi

# ── Step 2: Homebrew ───────────────────────────────────────────────────────
info "Checking Homebrew..."

# Make sure brew is in PATH (Apple Silicon installs to /opt/homebrew)
if [ -f /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
elif [ -f /usr/local/bin/brew ]; then
    eval "$(/usr/local/bin/brew shellenv)"
fi

if command -v brew &>/dev/null; then
    ok "Already installed"
else
    warn "Not found — installing Homebrew..."
    NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Add to PATH for the rest of this script
    if [ -f /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -f /usr/local/bin/brew ]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    ok "Installed"
fi

# ── Step 3: Brew packages ──────────────────────────────────────────────────
info "Checking brew packages..."

if brew list espeak-ng &>/dev/null; then
    ok "espeak-ng already installed"
else
    warn "Installing espeak-ng..."
    brew install espeak-ng
    ok "espeak-ng installed"
fi

if brew list python@3.11 &>/dev/null; then
    ok "python@3.11 already installed"
else
    warn "Installing python@3.11..."
    brew install python@3.11
    ok "python@3.11 installed"
fi

PYTHON="$(brew --prefix python@3.11)/bin/python3.11"
if [ ! -x "$PYTHON" ]; then
    fail "Could not find python3.11 at $PYTHON"
fi

# ── Step 4: Clone repository ──────────────────────────────────────────────
info "Setting up Utter in ~/.utter..."

if [ -d "$UTTER_DIR" ]; then
    warn "~/.utter already exists — removing and re-installing..."
    rm -rf "$UTTER_DIR"
fi

git clone "$REPO_URL" "$UTTER_DIR"
ok "Repository cloned"

# ── Step 5: Python virtual environment ─────────────────────────────────────
info "Creating Python virtual environment..."

"$PYTHON" -m venv "$UTTER_DIR/.venv"
ok "Virtual environment created"

info "Installing Python packages (this may take a few minutes)..."
"$UTTER_DIR/.venv/bin/pip" install --upgrade pip --quiet
"$UTTER_DIR/.venv/bin/pip" install -r "$UTTER_DIR/requirements.txt"
ok "Python packages installed"

# ── Step 6: Pre-download models ────────────────────────────────────────────
info "Downloading AI models (this may take a few minutes)..."

"$UTTER_DIR/.venv/bin/python" -c "
from kokoro import KPipeline
print('  Downloading Kokoro TTS model...')
pipeline = KPipeline(lang_code='a')
print('  Kokoro model ready.')
"
ok "Kokoro TTS model downloaded (~330 MB)"

"$UTTER_DIR/.venv/bin/python" -c "
from huggingface_hub import snapshot_download
print('  Downloading Whisper STT model...')
snapshot_download('mlx-community/distil-whisper-large-v3')
print('  Whisper model ready.')
"
ok "Whisper STT model downloaded (~750 MB)"

# ── Step 7: Create launcher command ────────────────────────────────────────
info "Creating 'utter' command..."

chmod +x "$UTTER_DIR/launcher.sh"

echo ""
echo "    Your Mac password is needed to create the 'utter' command."
echo "    (You won't see characters as you type — that's normal.)"
echo ""
sudo mkdir -p /usr/local/bin

sudo tee /usr/local/bin/utter > /dev/null << 'LAUNCHER'
#!/bin/bash
exec "$HOME/.utter/launcher.sh"
LAUNCHER
sudo chmod +x /usr/local/bin/utter
ok "Created /usr/local/bin/utter"

# ── Step 8: Create Utter.app ──────────────────────────────────────────────
info "Creating Utter.app in /Applications..."

# Write AppleScript source
APPLESCRIPT_SRC=$(mktemp /tmp/utter_app.XXXXXX)
cat > "$APPLESCRIPT_SRC" << 'APPLESCRIPT'
-- Utter.app — lightweight launcher
try
    do shell script "lsof -i :5757 -sTCP:LISTEN"
    -- Server already running, just open browser
    open location "http://localhost:5757"
on error
    -- Server not running, start it in Terminal
    tell application "Terminal"
        activate
        do script "/usr/local/bin/utter"
    end tell
end try
APPLESCRIPT

# Remove existing app if present
if [ -d "/Applications/Utter.app" ]; then
    rm -rf "/Applications/Utter.app"
fi

osacompile -o /Applications/Utter.app "$APPLESCRIPT_SRC"
rm -f "$APPLESCRIPT_SRC"

# Remove Gatekeeper quarantine so macOS doesn't block the app on first open
xattr -cr /Applications/Utter.app 2>/dev/null || true
ok "Created /Applications/Utter.app"

# ── Done! ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}Utter is installed!${NC}"
echo ""
echo "  To launch Utter:"
echo ""
echo "    • Double-click ${BOLD}Utter${NC} in /Applications"
echo "    • Or run ${BOLD}utter${NC} from Terminal"
echo ""
echo "  To uninstall:"
echo ""
echo "    bash ~/.utter/uninstall.sh"
echo ""
