"""Prueba rápida (todo gratis): un texto de Gemini, una imagen de Cloudflare y las dos voces.
Corré: python probar_gemini.py -> resultados en salida/_prueba/ para que mires y escuches."""
import asyncio

from src import cloudflare, gemini
from src.util import CARPETA_SALIDA, cargar_config, cargar_env

cargar_env()
cfg = cargar_config()
m, v = cfg["modelos"], cfg["voz"]
out = CARPETA_SALIDA / "_prueba"
out.mkdir(parents=True, exist_ok=True)
frase = "Un día como hoy, en mil ochocientos ochenta y nueve, una periodista salió a dar la vuelta al mundo."


def paso(nombre, funcion):
    print(f"- {nombre}...", end=" ", flush=True)
    try:
        funcion()
        print("OK")
    except Exception as e:
        print(f"FALLÓ -> {str(e)[:250]}")


modelos_texto = m["gemini_texto"] if isinstance(m["gemini_texto"], list) else [m["gemini_texto"]]


def _texto():
    errores = []
    for mod in modelos_texto:
        try:
            r = gemini.texto(mod, "Respondé solo con JSON.", '{"pedido": "decime una efeméride argentina en 5 palabras"}', 200)
            print(f"[{mod}] {r.strip()[:120]}", end=" ")
            return
        except Exception as e:
            errores.append(f"{mod}: {str(e)[:120]}")
    raise RuntimeError(" | ".join(errores))


paso("Texto (Gemini)", _texto)

paso("Imagen (Cloudflare)", lambda: (out / "imagen.png").write_bytes(cloudflare.imagen(
    m["cloudflare_modelos"][0],
    "A nineteenth-century steamship leaving a busy harbor at sunrise, crowd of townspeople waving on the pier, "
    "historical engraving and watercolor illustration, sepia and earth tones, soft light, vertical composition, no text",
    m.get("cloudflare_ancho", 720), m.get("cloudflare_alto", 1280))))

paso("Voz Gemini", lambda: (out / "voz_gemini.wav").write_bytes(
    gemini.voz(v["gemini_modelo"], v["gemini_voz"], v.get("gemini_estilo", ""), frase)))


def _edge():
    import edge_tts

    asyncio.run(edge_tts.Communicate(frase, v["edge_voz"], rate="-5%").save(str(out / "voz_edge.mp3")))


paso("Voz de respaldo (Edge)", _edge)

print(f"\nMirá y escuchá los archivos en: {out}")
print("Si preferís la voz de Edge, poné proveedor: \"edge\" en la sección voz de config.yaml.")
