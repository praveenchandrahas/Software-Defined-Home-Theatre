#!/bin/bash
# usage: build.sh [voice-name]     (default af_heart; run get-voice-model.sh once first)
set -euo pipefail
cd "$(dirname "$0")"
python3 voice.py ${1:+"$1"}
python3 audio.py film.wav
python3 video.py hdr.mkv sdr.mkv
for v in hdr:sdht-intro.mkv sdr:sdht-intro-sdr.mkv; do
  ffmpeg -v error -y -i "${v%%:*}.mkv" -i film.wav -map 0:v -map 1:a -c:v copy -c:a flac -sample_fmt s32 \
    -bits_per_raw_sample 24 -channel_layout 7.1 -metadata title="SDHT: a file becomes a room" "${v##*:}"
done
python3 testfile.py
