#!/bin/sh
# Copy sprint results from the rented GPU to the Mac every 3 minutes, so losing the instance loses nothing.
# Access details come from the environment only (GPU_HOST, GPU_PORT, GPU_KEY); never write them into a file.
#   GPU_HOST=user@host GPU_PORT=22 GPU_KEY=~/.ssh/key sh scripts/h5_sync.sh out/h5
: "${GPU_HOST:?set GPU_HOST}" "${GPU_PORT:?set GPU_PORT}" "${GPU_KEY:?set GPU_KEY}"
DEST="${1:-out/h5}"
mkdir -p "$DEST"
while true; do
  rsync -az --exclude='.*.tmp' -e "ssh -i $GPU_KEY -o IdentitiesOnly=yes -o ConnectTimeout=20 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 -p $GPU_PORT" "$GPU_HOST:/workspace/out/" "$DEST/" >/dev/null 2>&1 \
    && date -u +%FT%TZ > "$DEST/.last_sync"
  sleep 180
done
