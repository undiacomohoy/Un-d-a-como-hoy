"""
PRODUCTOR — el agente jefe que coordina a todo el equipo.

Uso:
    python producir.py                         # hace 1 video con la próxima leyenda y lo sube
    python producir.py --leyenda "El Pombero"  # elige la leyenda
    python producir.py --sin-subir             # genera el video pero no lo sube
    python producir.py --cantidad 3            # hace 3 videos seguidos
    python producir.py --no-listado            # lo sube como "no listado" (para revisar antes)
"""
import argparse
import json
from datetime import datetime

from src import estado, imagenes, montaje, voz
from src.agentes import Equipo
from src.util import CARPETA_SALIDA, cargar_config, cargar_env, configurar_logs, slug


def asegurar_cola(equipo: Equipo, config: dict, log) -> None:
    """Agente Curador: si quedan pocas leyendas en cola, agrega nuevas."""
    p = config["produccion"]
    if len(estado.pendientes()) >= p.get("minimo_leyendas_en_cola", 8):
        return
    try:
        conocidas = [l["nombre"] for l in estado._todas()]
        nuevas = equipo.curar(conocidas, estado.aprendizajes(), p.get("leyendas_por_curaduria", 15))
        log.info("  Curador: %d leyendas nuevas en la cola", estado.agregar_leyendas(nuevas))
    except Exception as e:
        log.warning("  Curador no pudo agregar leyendas: %s", e)


def producir_uno(equipo: Equipo, config: dict, nombre: str, subir: bool, log) -> bool:
    asegurar_cola(equipo, config, log)
    leyenda = estado.elegir_leyenda(nombre)
    formato = estado.elegir_formato(config.get("formatos", []))
    aprend = estado.aprendizajes()
    recientes = estado.titulos_recientes()
    carpeta = CARPETA_SALIDA / f"{datetime.now():%Y%m%d_%H%M}_{slug(leyenda['nombre'])}"
    carpeta.mkdir(parents=True, exist_ok=True)
    log.info("=" * 60)
    log.info("NUEVO VIDEO: %s (formato: %s)  ->  %s", leyenda["nombre"], formato["nombre"], carpeta.name)

    # 1) investigación
    ficha = equipo.investigar(leyenda)

    # 2) guion + SEO, con control de calidad (el revisor puede pedir reescritura)
    correcciones, guion, meta, revision = "", None, None, None
    for intento in range(config["produccion"]["reintentos_guion"] + 1):
        guion = equipo.escribir_guion(ficha, recientes, correcciones, formato, aprend)
        palabras = sum(len(e["texto"].split()) for e in guion["escenas"])
        if palabras > 112:  # control propio: ahorra llamadas y le dice al guionista cuánto recortar
            correcciones = (f"Tu guion anterior tenía {palabras} palabras y el máximo es 110. Recortalo a unas 100 palabras "
                            f"(sacá {palabras - 100} palabras): menos adjetivos, frases más cortas, una sola idea por escena.")
            log.warning("  guion demasiado largo (%d palabras), pido recorte", palabras)
            continue
        meta = equipo.seo(ficha, guion, aprend)
        revision = equipo.revisar(ficha, guion, meta, recientes)
        if revision.get("aprobado"):
            log.info("  revisor: APROBADO (gancho %s/10)", revision.get("puntaje_gancho"))
            break
        correcciones = revision.get("correcciones", "") + " Problemas: " + "; ".join(revision.get("problemas", []))
        log.warning("  revisor: RECHAZADO -> %s", "; ".join(revision.get("problemas", [])))
    else:
        (carpeta / "rechazado.json").write_text(
            json.dumps({"ficha": ficha, "guion": guion, "revision": revision}, ensure_ascii=False, indent=2),
            encoding="utf-8")
        estado.registrar(leyenda["nombre"], "", "rechazado", carpeta.name, formato=formato["nombre"])
        log.error("El revisor rechazó el guion varias veces. No se produce este video.")
        return False

    # 3) visuales, voz y montaje
    prompts = equipo.dirigir_visual(guion)
    (carpeta / "produccion.json").write_text(
        json.dumps({"leyenda": leyenda, "formato": formato, "ficha": ficha, "guion": guion, "prompts": prompts,
                    "metadata": meta, "revision": revision}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    rutas_img = imagenes.ilustrar(prompts, carpeta, config)
    audios = voz.narrar(guion["escenas"], carpeta, config["voz"])
    video = montaje.armar(guion["escenas"], rutas_img, audios, carpeta, config["video"])

    # 4) publicación
    if subir:
        from src import youtube
        video_id = youtube.subir(video, meta, config["youtube"])
        estado.registrar(leyenda["nombre"], meta["titulo"], "publicado", carpeta.name, video_id,
                         formato=formato["nombre"])
    else:
        estado.registrar(leyenda["nombre"], meta["titulo"], "generado", carpeta.name, formato=formato["nombre"])
        log.info("No se subió (modo sin subir). Video en: %s", video)
    return True


def main():
    p = argparse.ArgumentParser(description="Productor automático de Shorts de mitos y leyendas")
    p.add_argument("--leyenda", default="", help="nombre de una leyenda específica")
    p.add_argument("--sin-subir", action="store_true", help="genera el video sin subirlo")
    p.add_argument("--cantidad", type=int, default=0, help="cuántos videos hacer")
    p.add_argument("--no-listado", action="store_true", help="sube como no listado para revisarlo antes")
    args = p.parse_args()

    cargar_env()
    config = cargar_config()
    log = configurar_logs("produccion")
    subir = config["youtube"]["subir"] and not args.sin_subir
    if args.no_listado:
        config["youtube"]["privacidad"] = "unlisted"
    cantidad = args.cantidad or config["produccion"]["videos_por_ejecucion"]
    equipo = Equipo(config)

    fallos = 0
    for i in range(cantidad):
        ok = False
        for intento in range(3):  # si falla (Gemini saturado, guion rechazado), reintenta con otro intento completo
            try:
                if producir_uno(equipo, config, args.leyenda if i == 0 else "", subir, log):
                    ok = True
                    break
            except Exception as e:
                log.exception("ERROR produciendo el video: %s", e)
            log.warning("Intento %d/3 fallido; espero 5 minutos y reintento", intento + 1)
            import time
            time.sleep(300)
        if not ok:
            fallos += 1
    if fallos:
        import sys
        sys.exit(1)  # que GitHub marque la ejecución en rojo y te avise por mail


if __name__ == "__main__":
    main()
