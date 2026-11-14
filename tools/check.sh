#!/usr/bin/env bash
# Usage: bash tools/check.sh [test-id]
# Checks the 4 local files (size) and whether the CDN serves them.
ID="${1:-odilxanivich-1-listening}"
BASE="https://cdn.jsdelivr.net/gh/odilxanivich/odilxanivich-mock-audio@main/ielts/"
cd "$(dirname "$0")/.."
for n in 1 2 3 4; do
  f="ielts/${ID}-section-${n}.mp3"
  if [ -f "$f" ]; then
    size=$(du -h "$f" | cut -f1)
    code=$(curl -s -o /dev/null -w "%{http_code}" -I "${BASE}${ID}-section-${n}.mp3" 2>/dev/null || echo "---")
    echo "section $n: local $size | CDN HTTP $code"
  else
    echo "section $n: MISSING ($f)"
  fi
done
echo "(CDN 404 right after pushing is normal for a minute or two; 200 means it is live.)"
