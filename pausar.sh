#!/bin/bash
# Pausa (o reanuda) la publicación automática.
#   bash ~/CanalAutomatico/pausar.sh          -> pausa todo
#   bash ~/CanalAutomatico/pausar.sh reanudar -> vuelve a activar
for t in shorts recopilacion analisis; do
  plist="$HOME/Library/LaunchAgents/com.canalautomatico.$t.plist"
  [ -f "$plist" ] || continue
  if [ "$1" = "reanudar" ]; then launchctl load "$plist" 2>/dev/null; echo "Reanudado: $t"
  else launchctl unload "$plist" 2>/dev/null; echo "Pausado: $t"; fi
done
