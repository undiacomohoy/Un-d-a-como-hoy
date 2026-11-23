"""Conexión con Gemini (Google AI Studio): texto para los agentes, imágenes (Nano Banana) y voz (TTS)."""
import base64
import os
from functools import lru_cache


def _clave():
    """En la PC, si hay una clave de pruebas (GEMINI_API_KEY_PRUEBAS) se usa esa, así tus pruebas no gastan la cuota de la nube."""
    if not os.environ.get("GITHUB_ACTIONS"):
        k = os.environ.get("GEMINI_API_KEY_PRUEBAS")
        if k:
            return k
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


@lru_cache(maxsize=1)
def cliente():
    from google import genai

    clave = _clave()
    if not clave:
        raise RuntimeError("Falta GEMINI_API_KEY en el archivo .env (sacala en https://aistudio.google.com/apikey)")
    from google.genai import types

    # Tope de espera por llamada (ms): si Gemini no responde, falla y se pasa al modelo siguiente en vez de colgarse.
    return genai.Client(api_key=clave, http_options=types.HttpOptions(timeout=120_000))


def _transitorio(e: Exception) -> bool:
    m = str(e).lower()
    return any(k in m for k in ("503", "500", "unavailable", "overloaded", "high demand", "internal", "deadline",
                                      "peer closed", "incomplete", "remoteprotocol", "connection", "timed out", "timeout", "reset"))


def texto(modelo: str, sistema: str, mensaje: str, max_tokens: int = 4000) -> str:
    import time

    from google.genai import types

    for intento in range(3):
        try:
            r = cliente().models.generate_content(
                model=modelo,
                contents=mensaje,
                config=types.GenerateContentConfig(
                    system_instruction=sistema,
                    response_mime_type="application/json",
                    max_output_tokens=max_tokens,
                    temperature=0.9,
                ),
            )
            return r.text or ""
        except Exception as e:
            if _transitorio(e) and intento < 2:
                time.sleep(5)  # modelo saturado: un reintento corto y después pasamos al modelo de respaldo
                continue
            raise


def imagen(modelo: str, prompt: str, tamano: str = "1K") -> bytes:
    import time

    for intento in range(3):
        try:
            return _imagen(modelo, prompt, tamano)
        except Exception as e:
            if _transitorio(e) and intento < 2:
                time.sleep(5)
                continue
            raise


def _imagen(modelo: str, prompt: str, tamano: str = "1K") -> bytes:
    """Imagen vertical 9:16. Usa la API Interactions; si no está disponible, cae a generate_content."""
    c = cliente()
    try:
        inter = c.interactions.create(
            model=modelo,
            input=prompt,
            response_format={"type": "image", "mime_type": "image/png",
                             "aspect_ratio": "9:16", "image_size": tamano},
        )
        if inter.output_image is not None and inter.output_image.data:
            return base64.b64decode(inter.output_image.data)
        raise RuntimeError("La respuesta no trajo imagen (posible filtro de contenido)")
    except AttributeError:
        from google.genai import types

        r = c.models.generate_content(
            model=modelo,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio="9:16", image_size=tamano),
            ),
        )
        for parte in r.candidates[0].content.parts:
            if parte.inline_data and parte.inline_data.data:
                return parte.inline_data.data
        raise RuntimeError("La respuesta no trajo imagen (posible filtro de contenido)")


def voz(modelo: str, nombre_voz: str, estilo: str, texto_narrado: str) -> bytes:
    """Devuelve un WAV (24 kHz, mono). Llama a la API REST v1beta directamente."""
    import time

    import requests

    clave = _clave()
    if not clave:
        raise RuntimeError("Falta GEMINI_API_KEY en el archivo de claves")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
    parte = {"text": texto_narrado}
    if estilo:
        parte["speech_metadata"] = {"style": estilo}
    cuerpos = [
        {"contents": [{"role": "user", "parts": [parte]}],
         "generationConfig": {"responseModalities": ["AUDIO"],
                              "speechConfig": {"voiceConfig": {"voice": nombre_voz}}}},
        # formato anterior (modelos TTS más viejos)
        {"contents": [{"role": "user", "parts": [{"text": texto_narrado}]}],
         "generationConfig": {"responseModalities": ["AUDIO"],
                              "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": nombre_voz}}}}},
    ]
    ultimo = ""
    for cuerpo in cuerpos:
        for intento in range(3):
            r = requests.post(url, headers={"x-goog-api-key": clave, "Content-Type": "application/json"},
                              json=cuerpo, timeout=120)
            if r.status_code == 200:
                datos = r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
                return _a_wav(base64.b64decode(datos))
            ultimo = f"{r.status_code}: {r.text[:300]}"
            if r.status_code in (500, 503):
                time.sleep(8 * (intento + 1))
                continue
            break  # 400 u otro: probamos el formato siguiente
        if not ultimo.startswith("400"):
            break
    raise RuntimeError(f"Gemini TTS respondió {ultimo}")


def _a_wav(audio: bytes) -> bytes:
    if audio[:4] == b"RIFF":
        return audio
    import io
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(audio)
    return buf.getvalue()


def revisar_imagen(modelo: str, png: bytes, escena: str) -> dict:
    """Mira una imagen generada y dice si tiene errores visibles. Devuelve {"ok": bool, "problemas": [...]}."""
    import json

    from google.genai import types

    pedido = (
        "Sos un control de calidad de imágenes para un video vertical. Mirá la imagen y respondé SOLO con JSON "
        '{"ok": true/false, "problemas": ["..."]}. Marcá ok=false si hay: texto o letras (aunque sean ilegibles), '
        "manos, dedos o brazos deformes o fusionados, caras deformes, cuerpos o extremidades fundidos o de más, "
        "más de 2 personas, multitudes, objetos mal armados (cámaras, pelotas, armas) o cosas cortadas de forma rara. "
        "NO juzgues si la imagen coincide con una escena ni si es bonita: solo errores técnicos visibles. "
        "Si solo hay detalles menores de estilo, ok=true."
    )
    r = cliente().models.generate_content(
        model=modelo,
        contents=[types.Part.from_bytes(data=png, mime_type="image/png"), pedido],
        config=types.GenerateContentConfig(response_mime_type="application/json", max_output_tokens=400,
                                           temperature=0.1),
    )
    datos = json.loads(r.text or "{}")
    return {"ok": bool(datos.get("ok", True)), "problemas": datos.get("problemas", [])}
