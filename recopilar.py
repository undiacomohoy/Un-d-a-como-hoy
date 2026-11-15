"""
RECOPILACIÓN SEMANAL — un video largo horizontal con los Shorts de la semana.
Suma horas de reproducción (camino a la monetización) y los videos largos pagan más por vista.

Uso:  python recopilar.py            (junta los Shorts publicados en los últimos 7 días y lo sube)
      python recopilar.py --sin-subir
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

from src import estado
from src.agentes import Equipo
from src.util import (CARPETA_SALIDA, RAIZ, cargar_config, cargar_env, configurar_logs, correr,
                      duracion_audio, ffmpeg_bin)

W, H, FPS = 1920, 1080, 30


def _tiempo(seg: float) -> str:
    seg = int(seg)
    return f"{seg // 3600}:{seg % 3600 // 60:02d}:{seg % 60:02d}" if seg >= 3600 else f"{seg // 60:02d}:{seg % 60:02d}"


def _horizontal(origen: Path, destino: Path) -> None:
    """Short vertical -> 1920x1080 con fondo desenfocado del mismo video."""
    filtro = (f"[0:v]split=2[a][b];"
              f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:5,eq=brightness=-0.15[fondo];"
              f"[b]scale=-2:{H}[frente];"
              f"[fondo][frente]overlay=(W-w)/2:0,fps={FPS},format=yuv420p[v]")
    correr([ffmpeg_bin(), "-y", "-i", str(origen), "-filter_complex", filtro, "-map", "[v]", "-map", "0:a",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-ac", "2", str(destino)])


def _intro(destino: Path, segundos: float = 4) -> None:
    banner = RAIZ / "canal" / "banner.png"
    if banner.exists():
        entrada = ["-loop", "1", "-i", str(banner)]
        vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fade=t=in:d=0.8,fade=t=out:st={segundos - 0.8}:d=0.8"
    else:
        entrada = ["-f", "lavfi", "-i", f"color=c=0x070b18:s={W}x{H}"]
        vf = "null"
    correr([ffmpeg_bin(), "-y", *entrada, "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", str(segundos),
            "-vf", f"{vf},fps={FPS},format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
            "-c:a", "aac", "-b:a", "192k", "-shortest", str(destino)])


def _duracion_video(ruta: Path) -> float:
    return duracion_audio(ruta)  # lee la duración con ffmpeg (sirve para mp4)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sin-subir", action="store_true")
    args = p.parse_args()
    cargar_env()
    config = cargar_config()
    rc = config.get("recopilacion", {})
    log = configurar_logs("recopilacion")
    log.info("=" * 60)
    log.info("RECOPILACIÓN SEMANAL")
    if not rc.get("activa", True):
        log.info("  desactivada en config.yaml")
        return

    videos = []
    for h in estado.recientes_publicados(rc.get("dias", 7)):
        final = CARPETA_SALIDA / h["carpeta"] / "final.mp4"
        if final.exists():
            videos.append((h, final))
    if len(videos) < rc.get("minimo_videos", 4):
        log.info("  solo hay %d Shorts esta semana (mínimo %d). No se hace recopilación.",
                 len(videos), rc.get("minimo_videos", 4))
        return

    carpeta = CARPETA_SALIDA / f"{datetime.now():%Y%m%d}_recopilacion"
    carpeta.mkdir(parents=True, exist_ok=True)
    partes, capitulos, t = [], [], 0.0
    intro = carpeta / "00_intro.mp4"
    _intro(intro)
    partes.append(intro)
    capitulos.append(f"{_tiempo(0)} Intro")
    t += _duracion_video(intro)
    leyendas = []
    for i, (h, final) in enumerate(videos, 1):
        log.info("  agregando %s", h["leyenda"])
        destino = carpeta / f"{i:02d}.mp4"
        _horizontal(final, destino)
        partes.append(destino)
        capitulos.append(f"{_tiempo(t)} {h['leyenda']}")
        leyendas.append(h["leyenda"])
        t += _duracion_video(destino)
    (carpeta / "lista.txt").write_text("".join(f"file '{x.name}'\n" for x in partes), encoding="utf-8")
    final = carpeta / "recopilacion.mp4"
    correr([ffmpeg_bin(), "-y", "-f", "concat", "-safe", "0", "-i", "lista.txt", "-c:v", "libx264", "-preset",
            "veryfast", "-crf", "21", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", final.name],
           cwd=carpeta)
    texto_capitulos = "\n".join(capitulos)
    log.info("  video listo: %s (%s)", final, _tiempo(t))

    equipo = Equipo(config)
    try:
        meta = equipo.seo_recopilacion([{"nombre": n} for n in leyendas], texto_capitulos)
    except Exception as e:
        log.warning("  SEO falló (%s), uso título genérico", e)
        meta = {"titulo": f"{len(leyendas)} historias de la semana | {config['canal']['nombre']}",
                "descripcion": f"Las leyendas de la semana en un solo video.\n\n{texto_capitulos}\n\n"
                               "Narración e imágenes creadas con ayuda de inteligencia artificial.\n"
                               "#leyendas #mitos #terror",
                "tags": ["leyendas", "mitos", "leyendas argentinas", "historias de terror", "mitos y leyendas"]}
    (carpeta / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.sin_subir or not config["youtube"]["subir"]:
        estado.registrar(", ".join(leyendas), meta["titulo"], "generado", carpeta.name, tipo="recopilacion")
        log.info("  no se subió (modo sin subir)")
        return
    from src import youtube
    cfg = dict(config["youtube"], privacidad=rc.get("privacidad", "public"))
    video_id = youtube.subir(final, meta, cfg, es_short=False)
    estado.registrar(", ".join(leyendas), meta["titulo"], "publicado", carpeta.name, video_id, tipo="recopilacion")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        configurar_logs("recopilacion").exception("ERROR en la recopilación: %s", e)
