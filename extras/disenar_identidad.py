"""EJEMPLO de identidad visual (canal de leyendas): banner 2560x1440 y foto de perfil 800x800."""
import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

D = Path(__file__).parent
F_TITULO = str(D / "cinzel-decorative-latin-700-normal.ttf")
F_CINZEL = str(D / "cinzel-latin-700-normal.ttf")
F_CINZEL_R = str(D / "cinzel-latin-400-normal.ttf")

CIELO_ARRIBA = (6, 9, 22)
CIELO_ABAJO = (22, 34, 58)
LUNA = (236, 232, 214)
OJOS = (255, 178, 64)
DORADO = (214, 178, 110)


def degradado(w, h, c1, c2):
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(h - 1, 1)
        d.line([(0, y), (w, y)], fill=tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)))
    return img


def estrellas(img, n, semilla, y_max):
    rnd = random.Random(semilla)
    d = ImageDraw.Draw(img)
    w, _ = img.size
    for _ in range(n):
        x, y = rnd.randrange(w), rnd.randrange(int(y_max))
        b = rnd.randint(90, 200)
        r = rnd.choice([0, 0, 0, 1])
        d.ellipse([x - r, y - r, x + r, y + r], fill=(b, b, min(255, b + 20)))


def luna(img, cx, cy, r):
    w, h = img.size
    halo = Image.new("L", (w, h), 0)
    ImageDraw.Draw(halo).ellipse([cx - r * 2.6, cy - r * 2.6, cx + r * 2.6, cy + r * 2.6], fill=70)
    halo = halo.filter(ImageFilter.GaussianBlur(r * 0.9))
    img.paste(Image.new("RGB", (w, h), (120, 140, 170)), (0, 0), halo)
    disco = Image.new("L", (w, h), 0)
    ImageDraw.Draw(disco).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    disco = disco.filter(ImageFilter.GaussianBlur(1.5))
    img.paste(Image.new("RGB", (w, h), LUNA), (0, 0), disco)
    # manchas lunares sutiles
    rnd = random.Random(7)
    capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dc = ImageDraw.Draw(capa)
    for _ in range(0):
        a, dist = rnd.uniform(0, 6.28), rnd.uniform(0, r * 0.6)
        rr = rnd.uniform(r * 0.08, r * 0.22)
        x, y = cx + math.cos(a) * dist, cy + math.sin(a) * dist
        dc.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(170, 165, 150, 55))
    capa = capa.filter(ImageFilter.GaussianBlur(r * 0.05))
    capa.putalpha(ImageChops.multiply(capa.getchannel("A"), disco))
    img.paste(capa, (0, 0), capa)


def arbol(d, x, base, alto, ancho, rnd, color):
    """Silueta de árbol: tronco + ramas irregulares + copa en capas."""
    tronco = max(3, ancho * 0.07)
    d.polygon([(x - tronco, base), (x + tronco, base), (x + tronco * 0.4, base - alto), (x - tronco * 0.4, base - alto)],
              fill=color)
    capas = rnd.randint(7, 11)
    for i in range(capas):
        t = i / capas
        y = base - alto * (0.25 + 0.75 * t)
        semi = ancho * (1 - t) * rnd.uniform(0.45, 0.6)
        puntos = [(x - semi, y + alto * 0.09), (x, y - alto * 0.07), (x + semi, y + alto * 0.09)]
        d.polygon(puntos, fill=color)
    for _ in range(rnd.randint(2, 4)):
        y = base - alto * rnd.uniform(0.3, 0.7)
        lado = rnd.choice([-1, 1])
        largo = ancho * rnd.uniform(0.3, 0.55)
        d.line([(x, y), (x + lado * largo, y - largo * 0.5)], fill=color, width=max(2, int(tronco * 0.5)))


def bosque(img, base, alto_min, alto_max, n, color, semilla, ancho_f=0.32, valle=0.0):
    w, h = img.size
    capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    rnd = random.Random(semilla)
    d.rectangle([0, base, w, h], fill=color)
    xs = sorted(rnd.uniform(-60, w + 60) for _ in range(n))
    for x in xs:
        alto = rnd.uniform(alto_min, alto_max)
        if valle:
            dist = min(abs(x - w / 2) / (w / 2), 1)
            alto *= (1 - valle) + valle * dist ** 1.6
        arbol(d, x, base + rnd.uniform(0, 12), alto, alto * ancho_f, rnd, color)
    img.paste(capa, (0, 0), capa)


def niebla(img, y, alto, opacidad, semilla):
    w, h = img.size
    rnd = random.Random(semilla)
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    for _ in range(40):
        cx, cy = rnd.uniform(0, w), y + rnd.uniform(-alto * 0.4, alto * 0.4)
        rx, ry = rnd.uniform(w * 0.08, w * 0.22), rnd.uniform(alto * 0.15, alto * 0.35)
        d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=opacidad)
    m = m.filter(ImageFilter.GaussianBlur(alto * 0.35))
    img.paste(Image.new("RGB", (w, h), (150, 165, 185)), (0, 0), m)


def ojos(img, cx, cy, sep, r):
    w, h = img.size
    glow = Image.new("L", (w, h), 0)
    dg = ImageDraw.Draw(glow)
    for ox in (-sep / 2, sep / 2):
        dg.ellipse([cx + ox - r * 4, cy - r * 3, cx + ox + r * 4, cy + r * 3], fill=120)
    glow = glow.filter(ImageFilter.GaussianBlur(r * 2.2))
    img.paste(Image.new("RGB", (w, h), (255, 120, 30)), (0, 0), glow)
    d = ImageDraw.Draw(img)
    for ox in (-sep / 2, sep / 2):
        x = cx + ox
        # ojo almendrado
        d.polygon([(x - r * 1.5, cy), (x - r * 0.5, cy - r * 0.75), (x + r * 0.9, cy - r * 0.55),
                   (x + r * 1.5, cy + r * 0.1), (x + r * 0.4, cy + r * 0.6), (x - r * 0.8, cy + r * 0.45)],
                  fill=OJOS)
        d.ellipse([x - r * 0.18, cy - r * 0.5, x + r * 0.18, cy + r * 0.45], fill=(40, 10, 0))


def texto_centrado(img, texto, y, fuente, tam, color, sombra=True, espaciado=0):
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(fuente, tam)
    anchos = [d.textlength(c, font=f) for c in texto]
    total = sum(anchos) + espaciado * (len(texto) - 1)
    x = (img.width - total) / 2
    if sombra:
        s = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ds = ImageDraw.Draw(s)
        xx = x
        for c, a in zip(texto, anchos):
            ds.text((xx, y), c, font=f, fill=(0, 0, 0, 230))
            xx += a + espaciado
        s = s.filter(ImageFilter.GaussianBlur(tam * 0.12))
        img.paste(s, (0, 0), s)
    for c, a in zip(texto, anchos):
        d.text((x, y), c, font=f, fill=color)
        x += a + espaciado


def banner():
    W, H = 2560, 1440
    img = degradado(W, H, CIELO_ARRIBA, CIELO_ABAJO)
    estrellas(img, 700, 1, H * 0.8)
    luna(img, 2230, 690, 110)
    niebla(img, 900, 260, 55, 2)
    bosque(img, 960, 120, 420, 40, (16, 24, 38), 3, valle=0.75)
    niebla(img, 960, 200, 60, 4)
    bosque(img, 1010, 140, 560, 26, (9, 13, 22), 5, valle=0.8)
    bosque(img, 1060, 160, 820, 16, (3, 5, 10), 6, 0.36, valle=0.85)
    ojos(img, 1280, 905, 44, 11)
    v = Image.new("L", (W, H), 0)
    ImageDraw.Draw(v).ellipse([-W * 0.15, -H * 0.3, W * 1.15, H * 1.3], fill=255)
    v = v.filter(ImageFilter.GaussianBlur(220))
    img = Image.composite(img, Image.new("RGB", (W, H), (0, 0, 0)), v)
    # zona segura (1546x423 centrada en y 509-932)
    texto_centrado(img, "NOMBRE DEL CANAL", 575, F_TITULO, 96, (240, 232, 214), espaciado=5)
    d = ImageDraw.Draw(img)
    d.line([(1000, 712), (1560, 712)], fill=DORADO, width=2)
    d.ellipse([1274, 706, 1286, 718], fill=DORADO)
    texto_centrado(img, "MITOS Y LEYENDAS QUE NO DEBERÍAS CONTAR DE NOCHE", 738, F_CINZEL_R, 36, DORADO, espaciado=3)
    img.save(D / "banner.png", optimize=True)
    return img


def perfil():
    S = 800
    img = degradado(S, S, CIELO_ARRIBA, (26, 38, 64))
    estrellas(img, 90, 11, S * 0.55)
    luna(img, 400, 250, 135)
    niebla(img, 540, 140, 55, 12)
    bosque(img, 620, 120, 380, 14, (10, 15, 26), 13, 0.4, valle=0.85)
    capa = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dc = ImageDraw.Draw(capa)
    dc.rectangle([0, 650, S, S], fill=(3, 5, 10))
    rnd = random.Random(15)
    for x, alto in ((70, 780), (730, 760)):
        arbol(dc, x, 820, alto, 330, rnd, (3, 5, 10))
    img.paste(capa, (0, 0), capa)
    ojos(img, 400, 590, 120, 30)
    img.save(D / "perfil.png", optimize=True)
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).ellipse([0, 0, S, S], fill=255)
    prev = Image.new("RGB", (S, S), (255, 255, 255))
    prev.paste(img, (0, 0), m)
    return prev


if __name__ == "__main__":
    b = banner()
    p = perfil()
    # hoja de control: banner + cómo se ve recortado en celular + perfil circular
    hoja = Image.new("RGB", (1400, 1000), (255, 255, 255))
    hoja.paste(b.resize((1280, 720)), (60, 20))
    movil = b.crop((507, 509, 2053, 932)).resize((773, 211))
    hoja.paste(b.crop((0, 509, 2560, 932)).resize((1280, 211)), (60, 760 - 0)) if False else None
    hoja.paste(movil, (60, 760))
    hoja.paste(p.resize((200, 200)), (1100, 760))
    hoja.save(D / "control.png")
    print("ok")
