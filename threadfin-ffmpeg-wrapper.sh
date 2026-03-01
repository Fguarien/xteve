#!/bin/bash

# Wrapper pour utiliser FFmpeg du conteneur externe
# Ce script redirige les appels FFmpeg de Threadfin vers le conteneur FFmpeg

# Variables
FFMPEG_CONTAINER="ffmpeg-worker"
FFMPEG_BIN="/usr/local/bin/ffmpeg"

# Log pour debug
echo "[$(date)] FFmpeg call: $*" >> /tmp/ffmpeg-calls.log

# Construire la commande FFmpeg
CMD="$FFMPEG_BIN"
for arg in "$@"; do
    CMD="$CMD \"$arg\""
done

# Exécuter dans le conteneur FFmpeg
docker exec $FFMPEG_CONTAINER sh -c "$CMD"
