#!/bin/sh
# Copy round 4 results from the rented GPU to the Mac every few minutes, so losing the instance loses nothing.
while true; do
  rsync -az -e "ssh -i $HOME/.ssh/id_ed25519 -o IdentitiesOnly=yes -o ConnectTimeout=20 -p 43371" --include='h4_*' --include='p_*' --include='f_*' --include='pilot_*' --include='final_*' --exclude='*' root@180.189.55.38:/workspace/t4/out/ out/h4/ >/dev/null 2>&1
  sleep 180
done
