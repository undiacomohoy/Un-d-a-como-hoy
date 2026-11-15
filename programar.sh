#!/bin/bash
# Deja el canal funcionando solo. Se corre UNA vez:  bash ~/Documents/mitos-shorts/programar.sh
#
#  - 2 Shorts por día (12:30 y 19:30)
#  - Recopilación larga los domingos 18:00
#  - Agente Analista los lunes 09:00
#
# macOS no deja que las tareas automáticas lean la carpeta Documentos, así que el proyecto
# se mueve a tu carpeta personal:  ~/CanalAutomatico

set -e
ORIGEN="$(cd "$(dirname "$0")" && pwd)"
DESTINO="$HOME/CanalAutomatico"

if [ "$ORIGEN" != "$DESTINO" ]; then
  if [ -e "$DESTINO" ]; then
    echo "Ya existe $DESTINO. Uso esa carpeta."
  else
    echo "Moviendo el proyecto a $DESTINO ..."
    mv "$ORIGEN" "$DESTINO"
  fi
fi
cd "$DESTINO"
chmod +x correr.sh
mkdir -p logs "$HOME/Library/LaunchAgents"

crear_tarea () {   # nombre, script, bloque de horarios
  local etiqueta="com.canalautomatico.$1"
  local plist="$HOME/Library/LaunchAgents/$etiqueta.plist"
  cat > "$plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$etiqueta</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>$DESTINO/correr.sh</string><string>$2</string></array>
  <key>WorkingDirectory</key><string>$DESTINO</string>
  <key>StartCalendarInterval</key>
  $3
  <key>StandardOutPath</key><string>$DESTINO/logs/launchd.log</string>
  <key>StandardErrorPath</key><string>$DESTINO/logs/launchd.log</string>
</dict>
</plist>
EOF
  launchctl unload "$plist" 2>/dev/null || true
  launchctl load "$plist"
  echo "  [OK] $1"
}

echo "Programando tareas automáticas..."
crear_tarea shorts producir.py '<array>
    <dict><key>Hour</key><integer>12</integer><key>Minute</key><integer>30</integer></dict>
    <dict><key>Hour</key><integer>19</integer><key>Minute</key><integer>30</integer></dict>
  </array>'
crear_tarea recopilacion recopilar.py '<dict><key>Weekday</key><integer>0</integer><key>Hour</key><integer>18</integer><key>Minute</key><integer>0</integer></dict>'
crear_tarea analisis analizar.py '<dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>'

echo ""
echo "Listo. El canal ahora funciona solo:"
echo "  - Shorts: todos los días 12:30 y 19:30"
echo "  - Recopilación larga: domingos 18:00"
echo "  - Análisis y mejoras: lunes 09:00"
echo ""
echo "Proyecto en: $DESTINO"
echo "Qué pasó en cada tarea: $DESTINO/logs/tareas.log"
echo "Reporte semanal: $DESTINO/data/reporte_semanal.md"
echo ""
echo "Importante: la Mac tiene que estar prendida (puede estar con la pantalla apagada)."
echo "Si está dormida a la hora programada, la tarea corre apenas se despierte."
