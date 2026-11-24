"""
AGENTE ANALISTA — corre una vez por semana.
Lee las estadísticas reales del canal, saca conclusiones y deja aprendizajes
que el Guionista, el SEO, el Curador y el selector de formatos usan en los próximos videos.

Uso:  python analizar.py
"""
import json
from datetime import datetime

from src import estado, youtube
from src.agentes import Equipo
from src.util import CARPETA_DATOS, cargar_config, cargar_env, configurar_logs


def main():
    cargar_env()
    config = cargar_config()
    log = configurar_logs("analisis")
    log.info("=" * 60)
    log.info("ANÁLISIS SEMANAL")
    stats = youtube.estadisticas(dias=28)
    (CARPETA_DATOS / f"metricas_{datetime.now():%Y%m%d}.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("  %s: %d suscriptores, %d vistas totales, %d videos con datos en el período",
             stats["canal"], stats["suscriptores"], stats["vistas_totales"], len(stats["videos"]))

    # cada video con su edad, vistas por día y etiquetas (formato, tema, ámbito, cierre), para comparar parejo
    por_id = {h.get("video_id"): h for h in estado.historial() if h.get("video_id")}
    ahora = datetime.now()
    for v in stats["videos"]:
        h = por_id.get(v.get("video"), {})
        try:
            dias = max(1, (ahora - datetime.fromisoformat(h["fecha"])).days)
        except Exception:
            dias = None
        v["dias_publicado"] = dias
        v["vistas_por_dia"] = round(v.get("views", 0) / dias, 1) if dias else None
        v["formato"], v["tema"] = h.get("formato", ""), h.get("categoria", "")
        v["ambito"] = h.get("ambito") or (estado.clasificar_ambito({"nombre": h.get("leyenda", "")}) if h else "")
        v["cierre"] = h.get("cierre", "") or ("comentarios" if h else "")
    stats["videos"].sort(key=lambda v: v.get("vistas_por_dia") or 0, reverse=True)

    equipo = Equipo(config)
    resultado = equipo.analizar(stats, estado.historial(), estado.aprendizajes())
    estado.guardar_aprendizajes(resultado)
    log.info("  Resumen: %s", resultado.get("resumen", ""))
    for a in resultado.get("aprendizajes", []):
        log.info("   - %s", a)
    log.info("  Experimento de la semana: %s", resultado.get("experimento_de_la_semana", ""))

    # reporte legible para vos
    lineas = [f"# Reporte semanal — {datetime.now():%d/%m/%Y}", "",
              f"**Suscriptores:** {stats['suscriptores']}  ·  **Vistas totales:** {stats['vistas_totales']}  ·  "
              f"**Videos:** {stats['videos_totales']}", "", resultado.get("resumen", ""), "", "## Aprendizajes"]
    lineas += [f"- {a}" for a in resultado.get("aprendizajes", [])]
    lineas += ["", f"**Experimento de la semana:** {resultado.get('experimento_de_la_semana', '')}", "",
               "## Top videos (últimos 28 días, ordenados por vistas por día)", "",
               "| Video | Vistas | Días | Vistas/día | % visto | Subs | Formato | Tema | Ámbito | Cierre |",
               "|---|---|---|---|---|---|---|---|---|---|"]
    for v in stats["videos"][:10]:
        lineas.append(f"| {v.get('titulo', v['video'])[:50]} | {v.get('views', 0)} | {v.get('dias_publicado') or '-'} | "
                      f"{v.get('vistas_por_dia') if v.get('vistas_por_dia') is not None else '-'} | "
                      f"{round(v.get('averageViewPercentage', 0))}% | {v.get('subscribersGained', 0)} | "
                      f"{v.get('formato') or '-'} | {v.get('tema') or '-'} | {v.get('ambito') or '-'} | {v.get('cierre') or '-'} |")
    (CARPETA_DATOS / "reporte_semanal.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    log.info("  Reporte guardado en data/reporte_semanal.md")

    # copia del informe en tu Drive, para los agentes de la oficina (si Drive no está autorizado, se omite)
    try:
        from src import drive
        texto = "\n".join(lineas) + "\n"
        drive.subir_texto(f"Informe {stats['canal']} {datetime.now():%Y-%m-%d}.md", texto)
        log.info("  Informe subido a Drive (carpeta 'Informes de canales')")
    except Exception as e:
        log.warning("  No se subió el informe a Drive (no es grave): %s", str(e)[:150])


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        configurar_logs("analisis").exception("ERROR en el análisis: %s", e)
