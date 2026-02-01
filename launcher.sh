#!/usr/bin/env bash
set -euo pipefail

# In den Ordner wechseln, in dem dieses Script liegt (wichtig für relative Pfade).
SCRIPT_DIR="$(cd "$(dirname -- "$(readlink -f "$0")")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="venv"
PYTHON_BIN="python3"

# 1) venv erstellen, falls nicht vorhanden
if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# 2) venv aktivieren
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# 3) requirements installieren (wenn Datei existiert)
if [ -f "program_files/requirements.txt" ]; then
  python -m pip install --upgrade pip
  python -m pip install -r program_files/requirements.txt
fi

# 4) Python-Script starten
python launcher.py
