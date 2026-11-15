"""Genera subtítulos .ass grandes, estilo Shorts, sincronizados escena por escena."""
from pathlib import Path


def _tiempo(seg: float) -> str:
    h = int(seg // 3600)
    m = int(seg % 3600 // 60)
    s = seg % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _trozos(texto: str, max_palabras: int = 4) -> list:
    palabras = texto.split()
    trozos, actual = [], []
    for p in palabras:
        actual.append(p)
        if len(actual) >= max_palabras or p[-1:] in ".,;:?!…":
            trozos.append(" ".join(actual))
            actual = []
    if actual:
        trozos.append(" ".join(actual))
    return trozos


def generar(escenas: list, duraciones: list, destino: Path, video_cfg: dict, pausa: float = 0.35) -> None:
    ancho, alto = video_cfg["ancho"], video_cfg["alto"]
    fuente, tam = video_cfg["fuente_subtitulos"], video_cfg["tamano_subtitulos"]
    margen_v = int(alto * 0.28)  # por encima de la interfaz de Shorts
    cabecera = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {ancho}
PlayResY: {alto}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Leyenda,{fuente},{tam},&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,6,3,2,80,80,{margen_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lineas = []
    t0 = 0.0
    for escena, dur in zip(escenas, duraciones):
        hablado = max(dur - pausa, 0.5)
        trozos = _trozos(escena["texto"])
        total_chars = sum(len(t) for t in trozos) or 1
        t = t0
        for trozo in trozos:
            d = hablado * len(trozo) / total_chars
            texto = trozo.replace("{", "(").replace("}", ")").upper()
            # pequeño efecto de aparición
            lineas.append(f"Dialogue: 0,{_tiempo(t)},{_tiempo(t + d)},Leyenda,,0,0,0,,{{\\fad(60,0)}}{texto}")
            t += d
        t0 += dur
    destino.write_text(cabecera + "\n".join(lineas) + "\n", encoding="utf-8")
