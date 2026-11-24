"""Memoria del canal: efemérides hechas, formatos usados, títulos publicados y aprendizajes del Analista.
Versión para "Un Día Como Hoy": elige primero la efeméride cuya fecha (MM-DD) es la de hoy."""
import json
import random
from datetime import datetime, timedelta

from .util import CARPETA_DATOS

HISTORIAL = CARPETA_DATOS / "historial.json"
LEYENDAS = CARPETA_DATOS / "leyendas.json"
APRENDIZAJES = CARPETA_DATOS / "aprendizajes.json"


def _hoy() -> datetime:
    """Fecha de hoy en Argentina (los servidores de GitHub trabajan en UTC)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))
    except Exception:
        return datetime.now() - timedelta(hours=3)


def _leer() -> list:
    if HISTORIAL.exists():
        return json.loads(HISTORIAL.read_text(encoding="utf-8"))
    return []


def historial() -> list:
    return _leer()


def titulos_recientes(n: int = 15) -> list:
    return [h["titulo"] for h in _leer()[-n:] if h.get("titulo")]


def _todas() -> list:
    return json.loads(LEYENDAS.read_text(encoding="utf-8"))


def _hechas() -> set:
    return {h["leyenda"] for h in _leer() if h.get("estado") in ("publicado", "generado")}


def pendientes() -> list:
    hechas = _hechas()
    return [l for l in _todas() if l["nombre"] not in hechas]


def agregar_leyendas(nuevas: list) -> int:
    todas = _todas()
    existentes = {l["nombre"].strip().lower() for l in todas}
    agregadas = 0
    for l in nuevas:
        nombre = (l.get("nombre") or "").strip()
        if nombre and nombre.lower() not in existentes:
            todas.append({"nombre": nombre, "origen": l.get("origen", ""), "fecha": l.get("fecha", "")})
            existentes.add(nombre.lower())
            agregadas += 1
    LEYENDAS.write_text(json.dumps(todas, ensure_ascii=False, indent=2), encoding="utf-8")
    return agregadas


def _distancia_dias(fecha_mmdd: str, hoy: datetime) -> int:
    """Días que faltan desde hoy hasta MM-DD (0 = hoy). Si ya pasó este año, cuenta hasta el año próximo."""
    try:
        mes, dia = (int(x) for x in fecha_mmdd.split("-"))
        objetivo = datetime(hoy.year, mes, dia)
    except Exception:
        return 9999
    hoy_plano = datetime(hoy.year, hoy.month, hoy.day)
    if objetivo < hoy_plano:
        try:
            objetivo = datetime(hoy.year + 1, mes, dia)
        except ValueError:
            return 9999
    return (objetivo - hoy_plano).days


def elegir_leyenda(nombre: str = "") -> dict:
    if nombre:
        for l in _todas():
            if l["nombre"].lower() == nombre.lower():
                return l
        return {"nombre": nombre, "origen": "a determinar por el investigador"}
    # 0) agenda de la reunión de pre-producción: si hay una efeméride planificada para HOY, va primero
    try:
        hoy_iso = _hoy().strftime("%Y-%m-%d")
        ya = _hechas()
        for a in json.loads((LEYENDAS.parent / "agenda.json").read_text(encoding="utf-8")):
            if a.get("fecha_exacta") == hoy_iso and a["nombre"] not in ya:
                return a
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[agenda] no se pudo leer: {e}")
    cola = pendientes()
    if not cola:
        raise RuntimeError("Ya se usaron todas las efemérides de data/leyendas.json. Agregá más a la lista.")
    # 1) la efeméride de HOY (o la de mañana/pasado si hoy no hay); un día como hoy es el corazón del canal
    hoy = _hoy()
    con_fecha = [(l, _distancia_dias(l.get("fecha", ""), hoy)) for l in cola if l.get("fecha")]
    cercanas = [(l, d) for l, d in con_fecha if d <= 2]
    if cercanas:
        cercanas.sort(key=lambda x: x[1])
        mejor = cercanas[0][1]
        return random.choice([l for l, d in cercanas if d == mejor])
    # 2) si no hay nada cerca, priorizamos temas/regiones que el Analista marcó como ganadores
    prioridades = [p.lower() for p in aprendizajes().get("regiones_o_temas_a_priorizar", [])]
    if prioridades and random.random() < 0.6:
        preferidas = [l for l in cola if any(p.split()[-1] in l.get("origen", "").lower() for p in prioridades if p)]
        if preferidas:
            return random.choice(preferidas[:5])
    # 3) si no, la que tenga la fecha más próxima
    if con_fecha:
        con_fecha.sort(key=lambda x: x[1])
        return con_fecha[0][0]
    return random.choice(cola[:5])


def elegir_formato(formatos: list) -> dict:
    """Rota formatos: nunca repite los 2 últimos y favorece los que el Analista marcó como ganadores."""
    if not formatos:
        return {"nombre": "relato", "instrucciones": ""}
    ultimos = [h.get("formato") for h in _leer()[-2:]]
    a = aprendizajes()
    evitar = set(a.get("formatos_a_evitar", []))
    ganadores = set(a.get("formatos_ganadores", []))
    candidatos = [f for f in formatos if f["nombre"] not in ultimos and f["nombre"] not in evitar] or formatos
    pesos = [3 if f["nombre"] in ganadores else 1 for f in candidatos]
    return random.choices(candidatos, weights=pesos, k=1)[0]


def aprendizajes() -> dict:
    if APRENDIZAJES.exists():
        try:
            return json.loads(APRENDIZAJES.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def guardar_aprendizajes(datos: dict) -> None:
    datos["fecha"] = datetime.now().isoformat(timespec="seconds")
    APRENDIZAJES.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def recientes_publicados(dias: int) -> list:
    limite = datetime.now() - timedelta(days=dias)
    return [h for h in _leer()
            if h.get("estado") == "publicado" and h.get("tipo", "short") == "short"
            and datetime.fromisoformat(h["fecha"]) >= limite]


def registrar(leyenda: str, titulo: str, estado: str, carpeta: str, video_id: str = "",
              formato: str = "", tipo: str = "short") -> None:
    historial = _leer()
    historial.append({
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "tipo": tipo,
        "leyenda": leyenda,
        "formato": formato,
        "titulo": titulo,
        "estado": estado,
        "carpeta": carpeta,
        "video_id": video_id,
        "url": (f"https://youtube.com/{'shorts/' if tipo == 'short' else 'watch?v='}{video_id}" if video_id else ""),
    })
    HISTORIAL.write_text(json.dumps(historial, ensure_ascii=False, indent=2), encoding="utf-8")
