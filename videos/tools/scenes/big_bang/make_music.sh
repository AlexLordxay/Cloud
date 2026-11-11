#!/bin/bash
# Re-renders the score: music.js -> music.wav (48 kHz, 378.53 s, not in git) -> music.mp3 (320 kbps).
set -e
cd "$(dirname "$0")"
node render_music.js music.wav
ffmpeg -y -loglevel error -i music.wav -t 378.53 -c:a libmp3lame -b:a 320k music.mp3
ffmpeg -nostats -i music.wav -af ebur128=peak=true -f null - 2>&1 | grep -A12 Summary
