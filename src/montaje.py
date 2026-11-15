"""Agente EDITOR: arma el video final con FFmpeg (movimiento de cámara, voz, música y subtítulos)."""
import logging
import math
import random
from pathlib import Path

from . import subtitulos
from .util import CARPETA_MUSICA, carpeta_fuentes, correr, ffmpeg_bin

log = logging.getLogger("mitos")

# Movimientos de cámara que se van alternando para que no todas las escenas se vean iguales
MOVIMIENTOS = [
    ("1+0.14*on/{n}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),            # acercamiento al centro
    ("1.14-0.14*on/{n}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),         # alejamiento
    ("1.12", "(iw-iw/zoom)*on/{n}", "ih/2-(ih/zoom/2)"),                  # paneo a la derecha
    ("1+0.12*on/{n}", "iw/2-(iw/zoom/2)", "(ih-ih/zoom)*0.35"),           # acercamiento arriba
    ("1.12", "(iw-iw/zoom)*(1-on/{n})", "ih/2-(ih/zoom/2)"),              # paneo a la izquierda
]


def _clip(imagen: Path, dur: float, destino: Path, idx: int, cfg: dict) -> None:
    fps, ancho, alto = cfg["fps"], cfg["ancho"], cfg["alto"]
    n = max(int(math.ceil(dur * fps)), 1)
    z, x, y = (s.format(n=n) for s in MOVIMIENTOS[idx % len(MOVIMIENTOS)])
    filtro = (
        f"scale={ancho * 2}:{alto * 2}:force_original_aspect_ratio=increase,"
        f"crop={ancho * 2}:{alto * 2},"
        f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={ancho}x{alto}:fps={fps},"
        f"eq=contrast=1.05:saturation=0.95,format=yuv420p"
    )
    correr([ffmpeg_bin(), "-y", "-loop", "1", "-framerate", str(fps), "-i", str(imagen),
            "-vf", filtro, "-frames:v", str(n), "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(fps), str(destino)])


def armar(escenas: list, imagenes: list, audios: list, carpeta: Path, cfg_video: dict) -> Path:
    log.info("Montaje: armando %d escenas", len(escenas))
    duraciones = [d for _, d in audios]

    # 1) un clip con movimiento por escena
    clips = []
    for i, (img, dur) in enumerate(zip(imagenes, duraciones)):
        clip = carpeta / f"clip_{i:02d}.mp4"
        _clip(img, dur, clip, i, cfg_video)
        clips.append(clip)

    # 2) unir clips y audios
    (carpeta / "clips.txt").write_text("".join(f"file '{c.name}'\n" for c in clips), encoding="utf-8")
    (carpeta / "audios.txt").write_text("".join(f"file '{a.name}'\n" for a, _ in audios), encoding="utf-8")
    correr([ffmpeg_bin(), "-y", "-f", "concat", "-safe", "0", "-i", "clips.txt", "-c", "copy", "video_mudo.mp4"],
           cwd=carpeta)
    correr([ffmpeg_bin(), "-y", "-f", "concat", "-safe", "0", "-i", "audios.txt", "-c:a", "pcm_s16le", "voz.wav"],
           cwd=carpeta)

    # 3) subtítulos
    subtitulos.generar(escenas, duraciones, carpeta / "subs.ass", cfg_video)

    # 4) mezcla final: voz + música de fondo (si hay) + subtítulos quemados
    total = sum(duraciones)
    fade = max(total - 0.6, 0)
    musicas = sorted(list(CARPETA_MUSICA.glob("*.mp3")) + list(CARPETA_MUSICA.glob("*.wav")))
    vol = cfg_video.get("musica_volumen", 0)
    cmd = [ffmpeg_bin(), "-y", "-i", "video_mudo.mp4", "-i", "voz.wav"]
    if musicas and vol > 0:
        musica = random.choice(musicas)
        log.info("  música: %s", musica.name)
        cmd += ["-stream_loop", "-1", "-i", str(musica.resolve())]
        filtro_audio = (
            f"[2:a]volume={vol},afade=t=in:d=1.5[m];"
            f"[1:a][m]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
            f"afade=t=out:st={fade}:d=0.6,loudnorm=I=-14:TP=-1.5:LRA=11[a]"
        )
    else:
        filtro_audio = f"[1:a]afade=t=out:st={fade}:d=0.6,loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    fuentes = carpeta_fuentes()
    # En Windows los ":" de "C:/..." hay que escaparlos para el filtro de ffmpeg
    fuentes_f = str(fuentes).replace("\\", "/").replace(":", "\\:") if fuentes else ""
    subs = f"subtitles=subs.ass:fontsdir='{fuentes_f}'" if fuentes else "subtitles=subs.ass"
    filtro = f"[0:v]{subs},fade=t=out:st={fade}:d=0.6[v];{filtro_audio}"
    cmd += ["-filter_complex", filtro, "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
            "-t", f"{total:.2f}", "final.mp4"]
    correr(cmd, cwd=carpeta)
    final = carpeta / "final.mp4"
    log.info("  video listo: %s (%.1f s)", final, total)
    return final
