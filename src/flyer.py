"""Flyer del día con identidad de marca: póster de época con marco, sello de fecha y la brújula del canal.
Gemini ilustra la escena; el programa escribe la fecha y el título (así nunca hay errores de ortografía).
Se deja en tu Drive (carpeta 'Flyers del día') junto con el texto para publicar."""
import logging
import math
import re
from pathlib import Path

log = logging.getLogger("mitos")

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]
PAPEL = (244, 234, 212)
TINTA = (52, 36, 28)
ROJO = (150, 36, 40)
DORADO = (176, 134, 58)
SERIF = ["C:/Windows/Fonts/georgiab.ttf", "C:/Windows/Fonts/timesbd.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf", "/Library/Fonts/Georgia Bold.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"]
ITALICA = ["C:/Windows/Fonts/georgiai.ttf", "C:/Windows/Fonts/timesi.ttf",
           "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf", "/Library/Fonts/Georgia Italic.ttf",
           "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"]
SANS = ["C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
CREMA = (250, 241, 220)
OSCURO = (24, 16, 14)
ACENTOS = {"historia": (222, 170, 78), "ciencia": (120, 196, 232), "deporte": (140, 214, 120),
           "cultura": (228, 128, 208), "homenaje": (214, 196, 160)}
LOGO = Path(__file__).resolve().parent.parent / "assets" / "logo.png"


def _fuente(lista: list, tam: int):
    from PIL import ImageFont

    for f in lista:
        if Path(f).exists():
            return ImageFont.truetype(f, tam)
    return ImageFont.load_default()


def _partir(draw, texto: str, fuente, ancho: int) -> list:
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = (actual + " " + palabra).strip()
        if draw.textlength(prueba, font=fuente) <= ancho:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


def _ilustracion(carpeta: Path, titulo: str, categoria: str, rutas_img: list, config: dict):
    """Pide a Gemini una ilustración para el póster. Si no puede, usa otro generador o la imagen del video."""
    estilo = (config.get("estilos_por_tema") or {}).get(categoria, config.get("estilo_visual", ""))
    prompt = (f"Vintage commemorative poster illustration about: {titulo}. Single clear focal subject, objects and "
              f"landscapes only, no people faces, no crowds, no text, no letters, no numbers. Centered composition, "
              f"rich detail, elegant poster art. Style: {estilo}")
    m = config["modelos"]
    try:
        from . import gemini

        png = gemini.imagen(m.get("gemini_imagenes", "gemini-nano-banana-2.1"), prompt, m.get("gemini_imagen_tamano", "1K"))
        log.info("  flyer: ilustración hecha con Gemini")
        return png
    except Exception as e:
        log.warning("  flyer: Gemini no pudo ilustrar (%s); uso otro generador", str(e)[:100])
    try:
        from .imagenes import _generadores

        nombre, generar = _generadores(config)[0]
        return generar(prompt)
    except Exception as e:
        log.warning("  flyer: tampoco el generador gratuito (%s); uso la imagen del video", str(e)[:100])
    return Path(rutas_img[0]).read_bytes()


def _espaciado(d, xy, texto, fuente, fill, sep=6, anchor="l"):
    """Texto con letras separadas. anchor: 'l' izquierda, 'r' derecha, 'm' centro."""
    ancho = sum(d.textlength(c, font=fuente) + sep for c in texto) - sep
    x, y = xy
    if anchor == "r":
        x -= ancho
    elif anchor == "m":
        x -= ancho / 2
    for c in texto:
        d.text((x, y), c, font=fuente, fill=fill, anchor="ls")
        x += d.textlength(c, font=fuente) + sep
    return ancho


def _sombra(img, xy, texto, fuente, fill, anchor="ls", radio=10, op=190):
    from PIL import Image, ImageDraw, ImageFilter

    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(capa).text((xy[0] + 3, xy[1] + 6), texto, font=fuente, fill=(0, 0, 0, op), anchor=anchor)
    img.alpha_composite(capa.filter(ImageFilter.GaussianBlur(radio)))
    ImageDraw.Draw(img).text(xy, texto, font=fuente, fill=fill, anchor=anchor)


def _fondo(foto, W: int, H: int):
    """Ilustración a pantalla completa, con color más vivo, viñeta, degradados y grano de papel."""
    import random

    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

    esc = max(W / foto.width, H / foto.height)
    foto = foto.resize((int(foto.width * esc) + 1, int(foto.height * esc) + 1), Image.LANCZOS)
    x0, y0 = (foto.width - W) // 2, int((foto.height - H) * 0.25)
    foto = foto.crop((x0, y0, x0 + W, y0 + H))
    foto = ImageEnhance.Contrast(ImageEnhance.Color(foto).enhance(1.12)).enhance(1.08).convert("RGBA")
    # viñeta
    vin = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vin).ellipse((-W * 0.25, -H * 0.15, W * 1.25, H * 1.0), fill=255)
    vin = vin.filter(ImageFilter.GaussianBlur(160))
    oscuro = Image.new("RGBA", (W, H), OSCURO + (255,))
    foto = Image.composite(foto, Image.blend(foto, oscuro, 0.62), vin)
    # degradados: abajo (para el texto) y arriba (para la marca)
    grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(grad)
    for y in range(H):
        a = 0
        if y > 520:
            a = min(1.0, (y - 520) / 300) ** 1.4 * 245
        if y < 280:
            a = max(a, (1 - y / 280) ** 1.5 * 190)
        g.line((0, y, W, y), fill=OSCURO + (int(a),))
    foto.alpha_composite(grad)
    # grano
    ruido = Image.effect_noise((W, H), 38).convert("RGBA")
    ruido.putalpha(22)
    foto.alpha_composite(ruido)
    return foto


def _marco(d, W: int, H: int, color):
    d.rectangle((26, 26, W - 26, H - 26), outline=color, width=4)
    d.rectangle((44, 44, W - 44, H - 44), outline=color, width=1)
    for x, y in ((26, 26), (W - 26, 26), (26, H - 26), (W - 26, H - 26)):
        d.regular_polygon((x, y, 17), 4, rotation=45, fill=color)


def _texto_publicacion(fecha_txt: str, leyenda: dict, ficha: dict, meta: dict) -> str:
    titulo = re.sub(r"\s*#\w+", "", meta.get("titulo") or leyenda["nombre"]).strip()
    gancho = ficha.get("dato_gancho", "").strip()
    resumen = re.split(r"(?<=[.!?])\s+", ficha.get("resumen", "").strip())
    cuerpo = " ".join(resumen[:2]).strip()
    partes = [f"📅 Un día como hoy, {fecha_txt}", titulo, "", gancho, cuerpo, "",
              "¿Lo sabías? Contanos en los comentarios 👇", "▶ Mirá el Short de hoy en el canal."]
    return "\n".join(partes)


def crear(carpeta: Path, leyenda: dict, ficha: dict, meta: dict, rutas_img: list, categoria: str, hoy,
          config: dict = None) -> Path:
    from io import BytesIO

    from PIL import Image, ImageDraw

    config = config or {"modelos": {}}
    W, H = 1080, 1350
    acento = ACENTOS.get(categoria, ACENTOS["historia"])
    titulo = re.sub(r"\s*#\w+", "", meta.get("titulo") or leyenda["nombre"])
    titulo = re.sub(r"\s*\(\d{1,2} de \w+\)", "", titulo).strip()
    anio = None
    m_anio = re.search(r"\((\d{4})\)", leyenda.get("nombre", "")) or re.search(r"\b(1\d{3}|20\d{2})\b", titulo)
    if m_anio:
        anio = int(m_anio.group(1))
    titulo_sin_anio = re.sub(r"\s*\(\d{4}\)", "", titulo).strip()

    foto = Image.open(BytesIO(_ilustracion(carpeta, titulo_sin_anio, categoria, rutas_img, config))).convert("RGB")
    img = _fondo(foto, W, H)
    d = ImageDraw.Draw(img)

    # --- marca arriba: brújula + nombre del canal
    if LOGO.exists():
        logo = Image.open(LOGO).convert("RGB").resize((124, 124), Image.LANCZOS)
        masc = Image.new("L", (124, 124), 0)
        ImageDraw.Draw(masc).ellipse((0, 0, 123, 123), fill=255)
        img.paste(logo, (78, 70), masc)
        d.ellipse((75, 67, 205, 197), outline=acento, width=3)
    _espaciado(d, (234, 126), "UN DÍA COMO HOY", _fuente(SERIF, 44), CREMA, sep=5)
    d.line((234, 146, W - 78, 146), fill=acento, width=2)
    _espaciado(d, (234, 182), "UNA EFEMÉRIDE POR DÍA", _fuente(SANS, 22), acento, sep=5)

    # --- fecha gigante
    dia, mes = str(hoy.day), MESES[hoy.month - 1].upper()
    f_dia = _fuente(SERIF, 300)
    base = 850
    _sombra(img, (74, base), dia, f_dia, CREMA)
    d = ImageDraw.Draw(img)
    x_der = 74 + d.textlength(dia, font=f_dia) + 36
    tam = 66
    while tam > 30 and d.textlength(mes, font=_fuente(SANS, tam)) + len(mes) * 5 > W - 74 - x_der:
        tam -= 2
    _espaciado(d, (x_der, base - 140), mes, _fuente(SANS, tam), CREMA, sep=5)
    d.line((x_der, base - 112, W - 74, base - 112), fill=acento, width=3)
    if anio:
        hace = hoy.year - anio
        txt = f"{anio}  ·  HACE {hace} AÑOS" if hace > 0 else str(anio)
        f_b = _fuente(SANS, 30)
        wb = d.textlength(txt, font=f_b) + 44
        d.rectangle((x_der, base - 88, x_der + wb, base - 30), fill=ROJO)
        d.text((x_der + wb / 2, base - 59), txt, font=f_b, fill=CREMA, anchor="mm")

    # --- título y gancho
    d.rectangle((74, 892, 74 + 120, 898), fill=acento)
    f_t = _fuente(SERIF, 58)
    lineas = _partir(d, titulo_sin_anio, f_t, W - 148)[:3]
    y = 962
    for linea in lineas:
        d.text((74, y), linea, font=f_t, fill=CREMA, anchor="ls")
        y += 68
    gancho = (ficha.get("dato_gancho") or "").strip()
    if len(gancho) > 120:
        gancho = gancho[:118].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    if gancho and len(lineas) <= 2:
        f_g = _fuente(ITALICA, 33)
        y += 8
        for linea in _partir(d, gancho, f_g, W - 148)[:3]:
            d.text((74, y), linea, font=f_g, fill=acento, anchor="ls")
            y += 44

    # --- pie
    d.line((74, 1236, W - 74, 1236), fill=acento, width=2)
    d.text((74, 1282), "Seguinos y no te pierdas ninguna", font=_fuente(SANS, 26), fill=CREMA, anchor="ls")
    d.rectangle((W - 74 - 250, 1252, W - 74, 1298), fill=ROJO)
    d.polygon([(W - 74 - 226, 1263), (W - 74 - 226, 1287), (W - 74 - 206, 1275)], fill=CREMA)
    d.text((W - 74 - 190, 1275), "MIRÁ EL SHORT", font=_fuente(SANS, 24), fill=CREMA, anchor="lm")
    _marco(d, W, H, acento)
    img = img.convert("RGB")

    salida = carpeta / "flyer.png"
    img.save(salida)
    fecha_txt = f"{hoy.day} de {MESES[hoy.month - 1]}"
    texto = _texto_publicacion(fecha_txt, leyenda, ficha, meta)
    (carpeta / "flyer.txt").write_text(texto, encoding="utf-8")
    try:
        from . import drive

        sello = hoy.strftime("%Y-%m-%d")
        drive.subir_archivo(f"{sello} flyer.png", salida.read_bytes(), "image/png")
        drive.subir_archivo(f"{sello} texto.txt", texto.encode("utf-8"), "text/plain")
        log.info("Flyer y texto del día guardados en tu Drive (carpeta 'Flyers del día')")
    except Exception as e:
        log.warning("No pude subir el flyer a Drive (%s). Queda en %s", str(e)[:100], salida)
    return salida
