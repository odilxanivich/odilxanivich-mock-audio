#!/usr/bin/env bash
# Usage: bash tools/convert.sh <input-audio> <section-number> [test-id]
# Example: bash tools/convert.sh ~/recordings/s1.wav 1
# Output : ielts/odilxanivich-1-listening-section-1.mp3  (mono, 64 kbps, ~0.5 MB per minute)
set -euo pipefail
[ $# -ge 2 ] || { echo "Usage: $0 <input-audio> <section 1-4> [test-id]"; exit 1; }
command -v ffmpeg >/dev/null || { echo "ffmpeg is not installed (https://ffmpeg.org/download.html)"; exit 1; }
IN="$1"; N="$2"; ID="${3:-odilxanivich-1-listening}"
OUT="$(dirname "$0")/../ielts/${ID}-section-${N}.mp3"
ffmpeg -y -i "$IN" -ac 1 -ar 44100 -b:a 64k "$OUT"
echo "Created: $OUT ($(du -h "$OUT" | cut -f1))"
