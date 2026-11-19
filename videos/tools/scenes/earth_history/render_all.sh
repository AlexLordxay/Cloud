#!/bin/bash
# Render the given acts one after another (resumable): EH_RES=960x540 ./render_all.sh hook birth …
cd "$(dirname "$0")"
for a in "$@"; do python3 acts.py "$a" render 2>&1 | grep -v Warning | tail -1; echo "done $a"; done
