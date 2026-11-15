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


def ilustrar(prompts: list, carpeta: Path, config: dict) -> list:
    generadores = _generadores(config)
    rutas = []
    for i, prompt in enumerate(prompts):
        destino = carpeta / f"img_{i:02d}.png"
        log.info("Imágenes: %d/%d", i + 1, len(prompts))
        listo = False
        for nombre, generar in generadores:
            p = prompt
            for intento in range(3):
                try:
                    destino.write_bytes(generar(p))
                    listo = True
                    break
                except Exception as e:  # filtro de contenido o límite: suavizamos y reintentamos
                    log.warning("  %s, imagen %d falló (%s)", nombre, i + 1, str(e)[:200])
                    p = "Atmospheric, non-graphic, family-safe illustration. " + prompt
                    time.sleep(4 * (intento + 1))
            if listo:
                break
        if not listo:
            raise RuntimeError(f"No se pudo generar la imagen {i + 1}")
        rutas.append(destino)
    return rutas
