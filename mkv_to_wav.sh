#!/usr/bin/env bash

# Usage: ./mkv_to_wav.sh [target_directory]
# If no directory is given, uses current working directory.
TARGET_DIR="${1:-.}"

# Find all .mkv files and convert them to .wav via find -exec
find "$TARGET_DIR" -type f -iname '*.mkv' -exec bash -c '
    mkv="$1"
    wav="${mkv%.mkv}.wav"
    echo "Converting: $mkv → $wav"
    ffmpeg -i "$mkv" -vn -acodec pcm_s16le -ar 44100 -ac 2 "$wav"
' _ {} \;
