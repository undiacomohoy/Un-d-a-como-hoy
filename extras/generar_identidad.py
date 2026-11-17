"""Genera opciones de foto de perfil (800x800) y banner (2048x1152) para el canal con IA (Gemini; si no puede, Cloudflare).
Corré: 6_crear_perfil_y_banner.bat  -> resultados en salida/identidad/"""
import base64
import io
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from PIL import Image, ImageDraw, ImageFont

from src import cloudflare, gemini
from src.util import CARPETA_SALIDA, cargar_config, cargar_env

cargar_env()
cfg = cargar_config()
m = cfg["modelos"]
OUT = CARPETA_SALIDA / "identidad"
OUT.mkdir(parents=True, exist_ok=True)
VARIANTES = 3

ESTILO = ("vintage engraved illustration in the style of a 19th century etching with a sepia watercolor wash, "
          "warm sepia and parchment tones with deep red accents, highly detailed, rich textures, dramatic soft light, "
          "no text, no letters, no numbers, no watermark")
PROMPT_PERFIL = ("Square profile picture, centered symmetrical composition: a large ornate antique brass compass "
                 "resting on an open old calendar with torn pages, aged parchment background, " + ESTILO)
PROMPT_BANNER = ("Ultra-wide panoramic banner: an aged parchment world map; an ornate antique brass compass on the far left; "
                 "an old pocket watch, a quill pen and fluttering calendar pages on the far right; "
                 "the whole center area stays empty, clean parchment texture, left clear for a title, " + ESTILO)


def gemini_img(prompt, relacion, tamano):
    c = gemini.cliente()
    modelo = m.get("gemini_imagenes", "gemini-nano-banana-2.1")
    try:
        inter = c.interactions.create(model=modelo, input=prompt,
                                      response_format={"type": "image", "mime_type": "image/png",
                                                       "aspect_ratio": relacion, "image_size": tamano})
        if inter.output_image is not None and inter.output_image.data:
            return base64.b64decode(inter.output_image.data)
        raise RuntimeError("sin imagen (posible filtro)")
    except AttributeError:
        from google.genai import types
        r = c.models.generate_content(model=modelo, contents=prompt, config=types.GenerateContentConfig(
            response_modalities=["IMAGE"], image_config=types.ImageConfig(aspect_ratio=relacion, image_size=tamano)))
        for p in r.candidates[0].content.parts:
            if p.inline_data and p.inline_data.data:
                return p.inline_data.data
        raise RuntimeError("sin imagen (posible filtro)")


def cloudflare_img(prompt, ancho, alto):
    ultimo = None
    for mod in m.get("cloudflare_modelos", ["@cf/black-forest-labs/flux-2-klein-4b"]):
        try:
            return cloudflare.imagen(mod, prompt, ancho, alto)
        except Exception as e:
            ultimo = e
    raise ultimo


def generar(prompt, relacion, tamano, ancho_cf, alto_cf):
    try:
        return gemini_img(prompt, relacion, tamano), "Gemini"
    except Exception as e:
        print(f"    Gemini no pudo ({str(e)[:90]}); pruebo con Cloudflare")
        return cloudflare_img(prompt, ancho_cf, alto_cf), "Cloudflare"


def recorte_exacto(img, ancho, alto):
    r = max(ancho / img.width, alto / img.height)
    img = img.resize((round(img.width * r), round(img.height * r)), Image.LANCZOS)
    x, y = (img.width - ancho) // 2, (img.height - alto) // 2
    return img.crop((x, y, x + ancho, y + alto))


def fuente(tam):
    for f in ("georgiab.ttf", "timesbd.ttf", "DejaVuSerif-Bold.ttf"):
        try:
            return ImageFont.truetype(f, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def titulo_en_banner(img):
    img = img.convert("RGBA")
    W, H = img.size
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    caja = (W // 2 - 690, H // 2 - 190, W // 2 + 690, H // 2 + 190)
    d.rounded_rectangle(caja, radius=28, fill=(244, 233, 207, 215), outline=(43, 29, 18, 255), width=6)
    img = Image.alpha_composite(img, capa)
    d = ImageDraw.Draw(img)
    tam = 130
    while tam > 60:
        f = fuente(tam)
        if d.textlength("UN DÍA COMO HOY", font=f) <= 1180:
            break
        tam -= 4
    f = fuente(tam)
    t = "UN DÍA COMO HOY"
    d.text((W // 2, H // 2 - 40), t, font=f, fill=(43, 29, 18, 255), anchor="mm")
    d.rectangle([W // 2 - 340, H // 2 + 28, W // 2 + 340, H // 2 + 36], fill=(140, 47, 27, 255))
    d.text((W // 2, H // 2 + 100), "Efemérides en español", font=fuente(46), fill=(140, 47, 27, 255), anchor="mm")
    return img.convert("RGB")


def main():
    print(f"Guardando en: {OUT}\n")
    for i in range(1, VARIANTES + 1):
        for nombre, prompt, rel, tam, wcf, hcf, final in (
            ("perfil", PROMPT_PERFIL, "1:1", "1K", 1024, 1024, (800, 800)),
            ("banner", PROMPT_BANNER, "16:9", "2K", 1536, 864, (2048, 1152)),
        ):
            print(f"- {nombre} {i}/{VARIANTES}...", flush=True)
            try:
                datos, quien = generar(prompt, rel, tam, wcf, hcf)
                img = recorte_exacto(Image.open(io.BytesIO(datos)).convert("RGB"), *final)
                if nombre == "banner":
                    img = titulo_en_banner(img)
                img.save(OUT / f"{nombre}_{i}.png")
                print(f"    OK ({quien})")
            except Exception as e:
                print(f"    FALLÓ -> {str(e)[:200]}")
    print(f"\nListo. Mirá las opciones en: {OUT}")


if __name__ == "__main__":
    main()
