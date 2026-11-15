"""Chequea que todo esté instalado y configurado antes de producir. Corré: python verificar.py"""
import os
import shutil
import sys

from src.util import RAIZ, CARPETA_MUSICA, cargar_config, cargar_env, ffmpeg_bin

OK, MAL, AVISO = "  [OK]  ", "  [FALTA]", "  [aviso]"
problemas = 0


def check(condicion: bool, texto_ok: str, texto_mal: str, critico: bool = True):
    global problemas
    if condicion:
        print(OK, texto_ok)
    else:
        print(MAL if critico else AVISO, texto_mal)
        problemas += critico


print("\nVerificando instalación...\n")
check(sys.version_info >= (3, 10), f"Python {sys.version.split()[0]}", "Necesitás Python 3.10 o más nuevo")
def _hay(n):
    try:
        ffmpeg_bin(n)
        return True
    except RuntimeError:
        return False


check(_hay("ffmpeg"), "FFmpeg instalado",
      "FFmpeg no está instalado o no está en el PATH")
for paquete in ["google.genai", "edge_tts", "yaml", "requests", "googleapiclient", "google_auth_oauthlib"]:
    try:
        __import__(paquete)
        print(OK, f"librería {paquete}")
    except ImportError:
        check(False, "", f"librería {paquete} (corré: pip install -r requirements.txt)")

cargar_env()
config = cargar_config()
m = config["modelos"]
check((RAIZ / ".env").exists() or (RAIZ / "claves.txt").exists(), "archivo de claves", "archivo .env o claves.txt con tus claves")
usa_gemini = "gemini" in (m.get("proveedor_texto"), m.get("proveedor_imagenes"), config["voz"]["proveedor"])
if usa_gemini:
    check(bool(os.environ.get("GEMINI_API_KEY")), "clave de Gemini", "GEMINI_API_KEY en .env")
if m.get("proveedor_imagenes", "cloudflare") == "cloudflare":
    check(bool(os.environ.get("CLOUDFLARE_ACCOUNT_ID")) and bool(os.environ.get("CLOUDFLARE_API_TOKEN")),
          "Cloudflare (imágenes gratis)", "CLOUDFLARE_ACCOUNT_ID y CLOUDFLARE_API_TOKEN en .env")
if m.get("proveedor_texto") == "claude":
    check(bool(os.environ.get("ANTHROPIC_API_KEY")), "clave de Anthropic", "ANTHROPIC_API_KEY en .env")
if m.get("proveedor_imagenes") == "openai":
    check(bool(os.environ.get("OPENAI_API_KEY")), "clave de OpenAI (imágenes)", "OPENAI_API_KEY en .env")

if config["voz"]["proveedor"] == "elevenlabs":
    check(bool(os.environ.get("ELEVENLABS_API_KEY")), "clave de ElevenLabs", "ELEVENLABS_API_KEY en .env")
    check(bool(config["voz"]["elevenlabs_voice_id"] or os.environ.get("ELEVENLABS_VOICE_ID")),
          "voz de ElevenLabs elegida", "elevenlabs_voice_id en config.yaml")
else:
    try:
        __import__("edge_tts")
        print(OK, "voz gratuita (edge-tts)")
    except ImportError:
        check(False, "", "librería edge-tts (pip install edge-tts)")

if config["youtube"]["subir"]:
    check((RAIZ / "client_secret.json").exists(), "client_secret.json de Google",
          "client_secret.json de Google Cloud (README, paso 4)")
    check((RAIZ / "token.json").exists(), "YouTube autorizado", "autorizar YouTube: python autorizar_youtube.py")

musica = list(CARPETA_MUSICA.glob("*.mp3")) + list(CARPETA_MUSICA.glob("*.wav"))
check(bool(musica), f"{len(musica)} pista(s) de música", "sin música de fondo en assets/musica (opcional)", critico=False)

print("\n" + ("Todo listo. Probá:  python producir.py --sin-subir" if not problemas
              else f"Hay {problemas} cosa(s) por resolver arriba."))
