"""Utilidades compartidas: rutas, configuración, logs y parseo de JSON."""
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_AGENTES = RAIZ / "agentes"
CARPETA_DATOS = RAIZ / "data"
CARPETA_SALIDA = RAIZ / "salida"
CARPETA_LOGS = RAIZ / "logs"
CARPETA_MUSICA = RAIZ / "assets" / "musica"


def cargar_env() -> None:
    """Carga las claves desde .env o claves.txt (sin depender de librerías extra)."""
    for nombre in (".env", "claves.txt"):
        ruta = RAIZ / nombre
        if ruta.exists():
            _leer_env(ruta)


def _leer_env(ruta: Path) -> None:
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


def cargar_config() -> dict:
    with open(RAIZ / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def configurar_logs(nombre: str) -> logging.Logger:
    CARPETA_LOGS.mkdir(exist_ok=True)
    log = logging.getLogger("mitos")
    if log.handlers:
        return log
    log.setLevel(logging.INFO)
    formato = logging.Formatter("%(asctime)s  %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")
    archivo = logging.FileHandler(CARPETA_LOGS / f"{nombre}.log", encoding="utf-8")
    archivo.setFormatter(formato)
    consola = logging.StreamHandler(sys.stdout)
    consola.setFormatter(formato)
    log.addHandler(archivo)
    log.addHandler(consola)
    return log


def extraer_json(texto: str):
    """Saca el JSON de la respuesta de un modelo aunque venga con ```json o texto extra."""
    texto = texto.strip()
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto)
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        inicio = min([i for i in (texto.find("{"), texto.find("[")) if i != -1], default=-1)
        fin = max(texto.rfind("}"), texto.rfind("]"))
        if inicio == -1 or fin == -1:
            raise ValueError(f"La respuesta no contiene JSON:\n{texto[:500]}")
        return json.loads(texto[inicio:fin + 1])


def slug(texto: str) -> str:
    texto = texto.lower()
    for a, b in zip("áéíóúüñ", "aeiouun"):
        texto = texto.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", texto).strip("-")[:50]


def ffmpeg_bin(nombre: str = "ffmpeg") -> str:
    """Busca FFmpeg: carpeta bin/ del proyecto, el sistema, o el incluido en la librería imageio-ffmpeg."""
    local = RAIZ / "bin" / nombre
    if local.exists():
        return str(local)
    ruta = shutil.which(nombre)
    if ruta:
        return ruta
    if nombre == "ffmpeg":
        try:
            import imageio_ffmpeg

            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            pass
    raise RuntimeError(f"No encuentro '{nombre}'. Corré:  pip install imageio-ffmpeg")


def carpeta_fuentes() -> str:
    """Carpeta del sistema donde está Arial (para los subtítulos)."""
    for d in ("/System/Library/Fonts/Supplemental", "/Library/Fonts", "C:/Windows/Fonts", "/usr/share/fonts"):
        if Path(d).is_dir():
            return d
    return ""


def correr(cmd: list, cwd=None) -> None:
    resultado = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if resultado.returncode != 0:
        raise RuntimeError(f"Falló el comando:\n{' '.join(map(str, cmd))}\n\n{resultado.stderr[-2000:]}")


def duracion_audio(ruta: Path) -> float:
    """Duración en segundos. Para WAV usa Python directo; si no, lee la salida de ffmpeg."""
    if str(ruta).lower().endswith(".wav"):
        import wave

        with wave.open(str(ruta), "rb") as w:
            return w.getnframes() / float(w.getframerate())
    resultado = subprocess.run([ffmpeg_bin(), "-hide_banner", "-i", str(ruta)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", resultado.stderr)
    if not m:
        raise RuntimeError(f"No pude leer la duración de {ruta}")
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)
