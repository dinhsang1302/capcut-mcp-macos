#!/bin/bash
set -euo pipefail

if [[ "$(uname -s)" != 'Darwin' ]]; then
  printf '%s\n' 'This is the macOS-only repository. Installation stopped.' >&2
  exit 1
fi
repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
configure=0
if [[ "${1:-}" == '--configure-codex' ]]; then
  configure=1
  shift
fi
if [[ $# -gt 0 ]]; then
  printf '%s\n' 'Usage: bash scripts/install.sh [--configure-codex]' >&2
  exit 2
fi
python="${CAPCUT_MCP_PYTHON:-python3.13}"
if ! command -v "$python" >/dev/null 2>&1; then
  printf '%s\n' 'Install Python 3.13 first; see README.md.' >&2
  exit 1
fi
"$python" -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11+ required"'
if [[ ! -x "$repo/.venv/bin/python" ]]; then
  "$python" -m venv "$repo/.venv"
fi
"$repo/.venv/bin/python" -m pip install -e "$repo"
"$repo/.venv/bin/python" -c 'from capcut_mcp import paths; print("FFmpeg:", paths.binary("ffmpeg")); print("FFprobe:", paths.binary("ffprobe"))'
"$repo/.venv/bin/python" "$repo/scripts/verify_tools.py"
if [[ "$configure" -eq 1 ]]; then
  "$repo/.venv/bin/python" "$repo/scripts/configure_codex.py" --exe "$repo/.venv/bin/capcut-mcp"
fi
printf '%s\n' 'Installed. Restart Codex, then run capcut_probe only.' 'No CapCut project was edited or saved.'
