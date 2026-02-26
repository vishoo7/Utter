#!/bin/bash
#
# Utter — Uninstaller
#
# Usage:
#   bash ~/.utter/uninstall.sh
#

set -e

BOLD='\033[1m'
GREEN='\033[0;32m'
NC='\033[0m'

echo ""
echo -e "${BOLD}Utter Uninstaller${NC}"
echo ""

# Remove ~/.utter
if [ -d "$HOME/.utter" ]; then
    rm -rf "$HOME/.utter"
    echo "  Removed ~/.utter"
else
    echo "  ~/.utter not found (skipped)"
fi

# Remove /usr/local/bin/utter
if [ -f /usr/local/bin/utter ]; then
    sudo rm -f /usr/local/bin/utter
    echo "  Removed /usr/local/bin/utter"
else
    echo "  /usr/local/bin/utter not found (skipped)"
fi

# Remove /Applications/Utter.app
if [ -d /Applications/Utter.app ]; then
    rm -rf /Applications/Utter.app
    echo "  Removed /Applications/Utter.app"
else
    echo "  /Applications/Utter.app not found (skipped)"
fi

echo ""
echo -e "${GREEN}Utter has been uninstalled.${NC}"
echo ""
echo "  Note: Homebrew, espeak-ng, and cached AI models were left in place."
echo "  To also remove cached models: rm -rf ~/.cache/huggingface"
echo ""
