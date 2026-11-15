#!/bin/bash
# Lo ejecuta el programador de la Mac (launchd). Uso: bash correr.sh producir.py | recopilar.py | analizar.py
cd "$(dirname "$0")" || exit 1
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"
PY=".venv/bin/python"
export SSL_CERT_FILE="$("$PY" -c 'import certifi; print(certifi.where())' 2>/dev/null)"
mkdir -p logs
echo "---- $(date '+%Y-%m-%d %H:%M') $1 ----" >> "logs/tareas.log"
# caffeinate evita que la Mac se duerma mientras se arma el video
caffeinate -i "$PY" "$@" >> "logs/tareas.log" 2>&1
