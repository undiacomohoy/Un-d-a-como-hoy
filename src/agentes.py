"""Los 5 agentes del canal. Cada uno es una llamada a Claude con su propio rol (archivos en /agentes)."""
import json
import logging
import os

from .util import CARPETA_AGENTES, extraer_json

log = logging.getLogger("mitos")


class Equipo:
    def __init__(self, config: dict):
        self.config = config
        self.proveedor = config["modelos"].get("proveedor_texto", "gemini")
        if self.proveedor == "claude":
            from anthropic import Anthropic

            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise RuntimeError("Falta ANTHROPIC_API_KEY en el archivo .env")
            self.cliente = Anthropic()
            self.modelo = config["modelos"]["claude"]
        else:
            from . import gemini

            gemini.cliente()  # valida la clave al arrancar
            modelos = config["modelos"]["gemini_texto"]
            self.modelos = [modelos] if isinstance(modelos, str) else list(modelos)
            self.modelo = self.modelos[0]
        log.info("Agentes usando %s (%s)", self.proveedor, self.modelo)

    def _generar(self, rol: str, mensaje: str, max_tokens: int) -> str:
        if self.proveedor == "claude":
            respuesta = self.cliente.messages.create(
                model=self.modelo,
                max_tokens=max_tokens,
                system=rol,
                messages=[{"role": "user", "content": mensaje}],
            )
            return "".join(b.text for b in respuesta.content if getattr(b, "type", "") == "text")
        from . import gemini

        # Nivel gratuito: si un modelo está saturado o llegó a su límite, pasamos al siguiente.
        # Si todos fallan, esperamos y hacemos hasta 3 rondas antes de rendirnos.
        import time

        ultimo_error = None
        for ronda in range(3):
            for modelo in self.modelos:  # siempre en orden de calidad: no nos quedamos pegados al modelo chico
                try:
                    texto = gemini.texto(modelo, rol, mensaje, max_tokens)
                    if modelo != self.modelos[0]:
                        log.info("  respondió el modelo de respaldo %s", modelo)
                    return texto
                except Exception as e:
                    ultimo_error = e
                    msg = str(e).lower()
                    if any(k in msg for k in ("429", "quota", "exhausted", "404", "not found", "permission", "403",
                                              "500", "503", "unavailable", "overloaded", "high demand", "internal")):
                        log.warning("  %s no disponible (%s), pruebo otro", modelo, str(e)[:120])
                        continue
                    raise
            if ronda < 2:
                log.warning("  todos los modelos ocupados; espero 60 s y reintento (ronda %d/3)", ronda + 2)
                time.sleep(60)
        raise RuntimeError(f"Ningún modelo de Gemini disponible ahora (límite gratuito diario?): {ultimo_error}")

    def _llamar(self, agente: str, datos: dict, max_tokens: int = 4000):
        rol = (CARPETA_AGENTES / f"{agente}.md").read_text(encoding="utf-8")
        mensaje = json.dumps(datos, ensure_ascii=False, indent=2)
        for intento in range(3):
            texto = self._generar(rol, mensaje, max_tokens)
            try:
                return extraer_json(texto)
            except (ValueError, json.JSONDecodeError):
                log.warning("  %s devolvió JSON inválido, reintento %d", agente, intento + 1)
        raise RuntimeError(f"El agente {agente} no devolvió JSON válido")

    # ---------------- agentes ----------------

    def investigar(self, leyenda: dict) -> dict:
        log.info("[1/5] Investigador: %s", leyenda["nombre"])
        return self._llamar("01_investigador", {"leyenda": leyenda})

    def escribir_guion(self, ficha: dict, recientes: list, correcciones: str = "",
                       formato: dict = None, aprendizajes: dict = None) -> dict:
        log.info("[2/5] Guionista%s", " (reescribiendo)" if correcciones else "")
        c, v = self.config["canal"], self.config["video"]
        datos = {
            "ficha": ficha,
            "canal": c,
            "duracion_objetivo_seg": v["duracion_objetivo_seg"],
            "cantidad_escenas": v["escenas"],
            "titulos_recientes": recientes,
        }
        if formato:
            datos["formato_de_este_video"] = formato
        if aprendizajes:
            datos["aprendizajes_del_analista"] = {k: aprendizajes.get(k) for k in
                                                  ("aprendizajes", "experimento_de_la_semana") if aprendizajes.get(k)}
        if correcciones:
            datos["correcciones_del_revisor"] = correcciones
        guion = self._llamar("02_guionista", datos)
        escenas = guion.get("escenas", [])
        if not escenas:
            raise RuntimeError("El guionista no devolvió escenas")
        return guion

    def dirigir_visual(self, guion: dict) -> list:
        log.info("[3/5] Director visual")
        datos = {"escenas": guion["escenas"], "estilo_visual": self.config["estilo_visual"]}
        prompts = self._llamar("03_director_visual", datos)["prompts"]
        if len(prompts) != len(guion["escenas"]):
            log.warning("  cantidad de prompts distinta a escenas; ajusto")
            while len(prompts) < len(guion["escenas"]):
                prompts.append(prompts[-1])
            prompts = prompts[: len(guion["escenas"])]
        return prompts

    def seo(self, ficha: dict, guion: dict, aprendizajes: dict = None) -> dict:
        log.info("[4/5] SEO")
        datos = {"ficha": ficha, "guion": guion, "canal": self.config["canal"]["nombre"]}
        if aprendizajes and aprendizajes.get("aprendizajes"):
            datos["aprendizajes_del_analista"] = aprendizajes["aprendizajes"]
        meta = self._llamar("04_seo", datos)
        meta = self._limpiar_meta(meta)
        return meta

    @staticmethod
    def _limpiar_meta(meta: dict) -> dict:
        meta["titulo"] = meta["titulo"][:100]
        meta["descripcion"] = meta["descripcion"][:4900]
        tags, total = [], 0
        for t in meta.get("tags", []):
            t = t.replace("<", "").replace(">", "").strip()
            if t and total + len(t) + 1 < 480:
                tags.append(t)
                total += len(t) + 1
        meta["tags"] = tags
        return meta

    def analizar(self, estadisticas: dict, historial: list, previos: dict) -> dict:
        log.info("Analista: estudiando %d videos", len(estadisticas.get("videos", [])))
        return self._llamar("06_analista", {"estadisticas": estadisticas, "historial": historial[-60:],
                                            "aprendizajes_anteriores": previos}, max_tokens=3000)

    def curar(self, conocidas: list, aprendizajes: dict, cantidad: int) -> list:
        log.info("Curador: buscando %d leyendas nuevas", cantidad)
        r = self._llamar("07_curador", {"leyendas_existentes": conocidas, "cantidad": cantidad,
                                         "aprendizajes": aprendizajes.get("regiones_o_temas_a_priorizar", [])},
                         max_tokens=3000)
        return r.get("leyendas", [])

    def seo_recopilacion(self, leyendas: list, capitulos: str) -> dict:
        log.info("SEO de la recopilación semanal")
        meta = self._llamar("08_recopilacion", {"leyendas": leyendas, "capitulos": capitulos,
                                                "canal": self.config["canal"]["nombre"]})
        if capitulos.splitlines()[0] not in meta.get("descripcion", ""):
            meta["descripcion"] = meta.get("descripcion", "") + "\n\n" + capitulos
        return self._limpiar_meta(meta)

    def revisar(self, ficha: dict, guion: dict, meta: dict, recientes: list) -> dict:
        log.info("[5/5] Revisor de calidad")
        palabras = sum(len(e["texto"].split()) for e in guion["escenas"])
        datos = {
            "ficha": ficha,
            "guion": guion,
            "metadata": meta,
            "duracion_objetivo_seg": self.config["video"]["duracion_objetivo_seg"],
            "palabras_totales": palabras,
            "cierre_fijo": self.config["canal"]["cierre_fijo"],
            "titulos_recientes": recientes,
        }
        return self._llamar("05_revisor", datos)
