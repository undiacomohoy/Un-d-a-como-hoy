"""Agente ILUSTRADOR: genera una imagen vertical por escena.

Proveedores:
  cloudflare -> GRATIS (FLUX.2 klein en Cloudflare Workers AI; si falla prueba FLUX.1 schnell)
  gemini     -> Nano Banana (necesita facturación o créditos de Google Cloud)
  openai     -> pago
"""
import base64
import logging
import os
import time
from pathlib import Path

import requests

log = logging.getLogger("mitos")


def _openai(cliente, prompt: str, m: dict) -> bytes:
    params = {"model": m["imagenes"], "prompt": prompt, "size": m["imagen_tamano"], "n": 1}
    if m.get("imagen_calidad"):
        params["quality"] = m["imagen_calidad"]
    dato = cliente.images.generate(**params).data[0]
    if getattr(dato, "b64_json", None):
        return base64.b64decode(dato.b64_json)
    return requests.get(dato.url, timeout=120).content


def _generadores(config: dict) -> list:
    """Lista de (nombre, función) a probar en orden."""
    m = config["modelos"]
    proveedor = m.get("proveedor_imagenes", "cloudflare")
    if proveedor == "openai":
        from openai import OpenAI

        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("Falta OPENAI_API_KEY en el archivo .env")
        cliente = OpenAI()
        return [("openai", lambda p: _openai(cliente, p, m))]
    if proveedor == "gemini":
        from . import gemini

        return [("gemini", lambda p: gemini.imagen(m["gemini_imagenes"], p, m.get("gemini_imagen_tamano", "1K")))]
    from . import cloudflare

    w, h = m.get("cloudflare_ancho", 720), m.get("cloudflare_alto", 1280)
    return [(mod.split("/")[-1], lambda p, mod=mod: cloudflare.imagen(mod, p, w, h))
            for mod in m.get("cloudflare_modelos", ["@cf/black-forest-labs/flux-2-klein-4b"])]


_control_apagado = {"si": False}


def _revisar(png: bytes, escena: str, config: dict):
    """Control de calidad con Gemini. Si el control mismo falla (cuota), se apaga para el resto del video."""
    from . import gemini

    if _control_apagado["si"]:
        return None
    modelos = config["modelos"].get("gemini_texto", [])
    modelos = [modelos] if isinstance(modelos, str) else list(modelos)
    for modelo in modelos:
        try:
            return gemini.revisar_imagen(modelo, png, escena)
        except Exception as e:
            log.warning("  control de imagen no disponible con %s (%s)", modelo, str(e)[:80])
    log.warning("  control de imagen apagado para este video (sin cuota); sigo sin revisar")
    _control_apagado["si"] = True
    return None


SIMPLIFICAR = " Simplify: a single object or empty landscape only, no people, no text, no crowds."


def ilustrar(prompts: list, carpeta: Path, config: dict, escenas: list = None) -> list:
    generadores = _generadores(config)
    # La revisión gasta muchas llamadas a Gemini: en la nube va apagada; en las pruebas de la PC se prende con REVISAR_IMAGENES=1
    import os
    revisar = bool(config.get("produccion", {}).get("revisar_imagenes", False)) or os.environ.get("REVISAR_IMAGENES") == "1"
    rutas = []
    for i, prompt in enumerate(prompts):
        destino = carpeta / f"img_{i:02d}.png"
        log.info("Imágenes: %d/%d", i + 1, len(prompts))
        escena = (escenas[i].get("que_se_ve") or escenas[i].get("texto", "")) if escenas and i < len(escenas) else ""
        listo = False
        mejor = None
        for intento_calidad in range(3):  # hasta 3 versiones; si una tiene errores, se genera de nuevo más simple
            p = prompt if intento_calidad == 0 else prompt + SIMPLIFICAR
            png = None
            for nombre, generar in generadores:
                for intento in range(3):
                    try:
                        png = generar(p)
                        break
                    except Exception as e:  # filtro de contenido o límite: suavizamos y reintentamos
                        log.warning("  %s, imagen %d falló (%s)", nombre, i + 1, str(e)[:200])
                        p = "Atmospheric, non-graphic, family-safe illustration. " + p
                        time.sleep(4 * (intento + 1))
                if png:
                    break
            if not png:
                continue
            mejor = png
            res = _revisar(png, escena, config) if revisar else None
            if res is None or res["ok"]:
                listo = True
                break
            log.warning("  imagen %d con errores (%s); la genero de nuevo (%d/3)", i + 1,
                        "; ".join(res["problemas"])[:150], intento_calidad + 1)
        if mejor is None:
            raise RuntimeError(f"No se pudo generar la imagen {i + 1}")
        destino.write_bytes(mejor)  # si ninguna salió limpia, se usa la última (la más simple)
        rutas.append(destino)
    return rutas
