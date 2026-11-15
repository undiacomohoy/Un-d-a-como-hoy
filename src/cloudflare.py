"""Imágenes GRATIS con Cloudflare Workers AI (10.000 'neurons' gratis por día ≈ 15 videos diarios)."""
import base64
import os

import requests


def _credenciales():
    cuenta = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    token = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not cuenta or not token:
        raise RuntimeError("Faltan CLOUDFLARE_ACCOUNT_ID o CLOUDFLARE_API_TOKEN en el archivo .env (ver README)")
    return cuenta, token


def _decodificar(r: requests.Response) -> bytes:
    if r.status_code != 200:
        raise RuntimeError(f"Cloudflare respondió {r.status_code}: {r.text[:300]}")
    if r.headers.get("content-type", "").startswith("image/"):
        return r.content
    datos = r.json()
    resultado = datos.get("result") or {}
    imagen = resultado.get("image") if isinstance(resultado, dict) else None
    if not imagen:
        raise RuntimeError(f"Cloudflare no devolvió imagen: {str(datos)[:300]}")
    return base64.b64decode(imagen)


def imagen(modelo: str, prompt: str, ancho: int = 720, alto: int = 1280) -> bytes:
    cuenta, token = _credenciales()
    url = f"https://api.cloudflare.com/client/v4/accounts/{cuenta}/ai/run/{modelo}"
    cabecera = {"Authorization": f"Bearer {token}"}
    if "flux-2" in modelo:
        # los modelos FLUX.2 reciben formulario multipart y permiten formato vertical
        campos = {"prompt": (None, prompt), "width": (None, str(ancho)), "height": (None, str(alto))}
        r = requests.post(url, headers=cabecera, files=campos, timeout=180)
    else:
        # flux-1-schnell: JSON, sale cuadrada (el editor la recorta a vertical)
        r = requests.post(url, headers=cabecera, json={"prompt": prompt, "steps": 8}, timeout=180)
    return _decodificar(r)
