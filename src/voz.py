"""Agente de VOZ: genera la narración escena por escena (así cada imagen queda sincronizada)."""
import asyncio
import logging
import os
import time
from pathlib import Path

import requests

from .util import correr, duracion_audio, ffmpeg_bin

log = logging.getLogger("mitos")


def _elevenlabs(texto: str, destino: Path, cfg: dict, anterior: str, siguiente: str) -> None:
    clave = os.environ.get("ELEVENLABS_API_KEY")
    voz_id = cfg["elevenlabs_voice_id"] or os.environ.get("ELEVENLABS_VOICE_ID", "")
    if not clave or not voz_id:
        raise RuntimeError("Falta ELEVENLABS_API_KEY en .env o elevenlabs_voice_id en config.yaml")
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voz_id}",
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": clave, "Content-Type": "application/json"},
        json={
            "text": texto,
            "model_id": cfg["elevenlabs_modelo"],
            "previous_text": anterior or None,
            "next_text": siguiente or None,
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.35},
        },
        timeout=120,
    )
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs respondió {r.status_code}: {r.text[:300]}")
    destino.write_bytes(r.content)


def _edge(texto: str, destino: Path, cfg: dict) -> None:
    import edge_tts

    async def _hablar():
        await edge_tts.Communicate(texto, cfg["edge_voz"], rate="-5%").save(str(destino))

    asyncio.run(_hablar())


def narrar(escenas: list, carpeta: Path, cfg: dict) -> list:
    """Devuelve una lista de (ruta_wav, duracion) por escena.
    Si el proveedor principal falla (ej. límite gratuito de Gemini), rehace TODO el video
    con la voz gratuita de respaldo, para que no cambie de voz a mitad del video."""
    try:
        return _narrar(escenas, carpeta, cfg, cfg["proveedor"])
    except Exception as e:
        respaldo = cfg.get("respaldo", "edge")
        if not respaldo or respaldo == cfg["proveedor"]:
            raise
        log.warning("Voz %s no disponible (%s). Uso la voz de respaldo: %s",
                    cfg["proveedor"], str(e)[:150], respaldo)
        return _narrar(escenas, carpeta, cfg, respaldo)


def _narrar(escenas: list, carpeta: Path, cfg: dict, proveedor: str) -> list:
    log.info("Voz: narrando %d escenas con %s", len(escenas), proveedor)
    resultados = []
    for i, escena in enumerate(escenas):
        mp3 = carpeta / f"voz_{i:02d}_original"
        wav = carpeta / f"voz_{i:02d}.wav"
        texto = escena["texto"]
        anterior = escenas[i - 1]["texto"] if i > 0 else ""
        siguiente = escenas[i + 1]["texto"] if i + 1 < len(escenas) else ""
        if proveedor == "gemini":
            from . import gemini

            if i > 0:  # el nivel gratuito permite pocas narraciones por minuto: espaciamos las escenas
                time.sleep(float(cfg.get("pausa_gemini_seg", 21)))

            for intento in range(3):
                try:
                    mp3.write_bytes(gemini.voz(cfg["gemini_modelo"], cfg["gemini_voz"],
                                               cfg.get("gemini_estilo", ""), texto))
                    break
                except Exception as e:
                    log.warning("  voz escena %d falló (%s), reintento", i + 1, str(e)[:200])
                    if "exceeded your current quota" in str(e).lower():
                        raise  # límite diario agotado: no tiene sentido reintentar, pasamos a la voz de respaldo
                    if "429" in str(e) or "quota" in str(e).lower():
                        time.sleep(25)  # límite por minuto del nivel gratuito
                    else:
                        time.sleep(4 * (intento + 1))
            else:
                raise RuntimeError(f"No se pudo generar la voz de la escena {i + 1}")
        elif proveedor == "elevenlabs":
            _elevenlabs(texto, mp3, cfg, anterior, siguiente)
        else:
            _edge(texto, mp3, cfg)
        # pasamos a WAV y agregamos una pausa corta al final de cada escena
        vel = float(cfg.get("velocidad", 1.0) or 1.0)
        filtro = (f"atempo={vel}," if abs(vel - 1.0) > 0.01 else "") + "apad=pad_dur=0.35"
        correr([ffmpeg_bin(), "-y", "-i", str(mp3), "-af", filtro,
                "-ar", "44100", "-ac", "2", str(wav)])
        resultados.append((wav, duracion_audio(wav)))
    return resultados
