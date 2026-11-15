#!/bin/bash
# Instala todo y prueba las claves. Uso:  bash ~/Documents/mitos-shorts/instalar_y_probar.sh
cd "$(dirname "$0")" || exit 1
echo "== Fábrica de Shorts: instalación =="

# Preferimos una versión de Python estable con todas las librerías disponibles
PY=""
for v in python3.13 python3.12 python3.11 python3; do
  if command -v $v >/dev/null; then PY=$(command -v $v); break; fi
done
if [ -z "$PY" ]; then echo "No encuentro Python. Instalalo desde python.org"; exit 1; fi
echo "Python: $($PY --version)"
# Si bajaste FFmpeg a Descargas, lo usamos
if [ ! -x bin/ffmpeg ] && [ -f "$HOME/Downloads/ffmpeg" ]; then
  mkdir -p bin && cp "$HOME/Downloads/ffmpeg" bin/ffmpeg && chmod +x bin/ffmpeg
  xattr -d com.apple.quarantine bin/ffmpeg 2>/dev/null
fi
[ -x bin/ffmpeg ] && bin/ffmpeg -version >/dev/null 2>&1 && echo "FFmpeg: OK"

if [ ! -x ".venv/bin/python" ]; then
  echo "Creando entorno..."
  "$PY" -m venv .venv || exit 1
fi
echo "Instalando librerías y FFmpeg (puede tardar unos minutos la primera vez)..."
.venv/bin/python -m pip install -q --upgrade pip
.venv/bin/python -m pip install -q --prefer-binary -r requirements.txt certifi || {
  echo "Reintento con versiones compatibles con este Mac..."
  .venv/bin/python -m pip install -q --prefer-binary "cryptography<=48.0.1" -r requirements.txt certifi || exit 1
}
export SSL_CERT_FILE="$(.venv/bin/python -c 'import certifi; print(certifi.where())')"

chmod +x correr_diario.sh 2>/dev/null
echo ""
.venv/bin/python verificar.py
echo ""
echo "== Probando Gemini, Cloudflare y las voces =="
.venv/bin/python probar_gemini.py
open salida/_prueba 2>/dev/null
