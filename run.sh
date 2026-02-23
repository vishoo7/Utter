#!/bin/bash
cd "$(dirname "$0")"
PYTORCH_ENABLE_MPS_FALLBACK=1 .venv/bin/python server.py
