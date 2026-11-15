"""Agente PUBLICADOR: sube el video a YouTube con la API oficial (YouTube Data API v3)."""
import logging
import time
from pathlib import Path

from .util import RAIZ

log = logging.getLogger("mitos")

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",          # subir videos
    "https://www.googleapis.com/auth/youtube.readonly",        # leer datos del canal
    "https://www.googleapis.com/auth/yt-analytics.readonly",   # leer estadísticas (agente Analista)
]
CLIENT_SECRET = RAIZ / "client_secret.json"
TOKEN = RAIZ / "token.json"


def obtener_credenciales(interactivo: bool = False):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if creds and not set(SCOPES).issubset(set(creds.scopes or [])):
        creds = None  # el permiso guardado es viejo y no incluye estadísticas: hay que reautorizar
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            TOKEN.write_text(creds.to_json(), encoding="utf-8")
            return creds
        except Exception as e:
            log.warning("No se pudo renovar el permiso de YouTube: %s", e)
    if not interactivo:
        raise RuntimeError("YouTube no está autorizado. Corré:  python autorizar_youtube.py")
    if not CLIENT_SECRET.exists():
        raise RuntimeError("Falta client_secret.json en la carpeta del proyecto (ver README, paso 4)")
    flujo = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
    creds = flujo.run_local_server(port=0, prompt="consent", access_type="offline")
    TOKEN.write_text(creds.to_json(), encoding="utf-8")
    return creds


def subir(video: Path, meta: dict, cfg: dict, es_short: bool = True) -> str:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    youtube = build("youtube", "v3", credentials=obtener_credenciales())
    cuerpo = {
        "snippet": {
            "title": meta["titulo"],
            "description": meta["descripcion"],
            "tags": meta["tags"],
            "categoryId": cfg["categoria_id"],
            "defaultLanguage": "es",
            "defaultAudioLanguage": "es",
        },
        "status": {
            "privacyStatus": cfg["privacidad"],
            "selfDeclaredMadeForKids": cfg["apto_para_ninos"],
            "containsSyntheticMedia": cfg["contenido_sintetico"],
        },
    }
    media = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    pedido = youtube.videos().insert(part="snippet,status", body=cuerpo, media_body=media)

    log.info("YouTube: subiendo '%s' (%s)", meta["titulo"], cfg["privacidad"])
    respuesta, errores = None, 0
    while respuesta is None:
        try:
            estado, respuesta = pedido.next_chunk()
            if estado:
                log.info("  %d%%", int(estado.progress() * 100))
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504) and errores < 5:
                errores += 1
                time.sleep(2 ** errores)
                continue
            if e.resp.status == 403 and "quota" in str(e).lower():
                raise RuntimeError("Se agotó la cuota diaria de la API de YouTube. Probá mañana.") from e
            raise
    video_id = respuesta["id"]
    log.info("  subido: https://youtube.com/%s%s", "shorts/" if es_short else "watch?v=", video_id)
    return video_id


def estadisticas(dias: int = 28) -> dict:
    """Estadísticas del canal y por video de los últimos `dias` días (para el agente Analista)."""
    from datetime import date, timedelta

    from googleapiclient.discovery import build

    creds = obtener_credenciales()
    yt = build("youtube", "v3", credentials=creds)
    yta = build("youtubeAnalytics", "v2", credentials=creds)
    canal = yt.channels().list(part="statistics,snippet", mine=True).execute()["items"][0]
    fin, inicio = date.today(), date.today() - timedelta(days=dias)
    rep = yta.reports().query(
        ids="channel==MINE", startDate=inicio.isoformat(), endDate=fin.isoformat(),
        metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,comments,shares,subscribersGained",
        dimensions="video", sort="-views", maxResults=50,
    ).execute()
    cols = [c["name"] for c in rep.get("columnHeaders", [])]
    filas = [dict(zip(cols, r)) for r in rep.get("rows", [])]
    ids = [f["video"] for f in filas]
    titulos = {}
    for i in range(0, len(ids), 50):
        r = yt.videos().list(part="snippet", id=",".join(ids[i:i + 50])).execute()
        titulos.update({v["id"]: v["snippet"]["title"] for v in r.get("items", [])})
    for f in filas:
        f["titulo"] = titulos.get(f["video"], "")
    return {
        "canal": canal["snippet"]["title"],
        "suscriptores": int(canal["statistics"].get("subscriberCount", 0)),
        "vistas_totales": int(canal["statistics"].get("viewCount", 0)),
        "videos_totales": int(canal["statistics"].get("videoCount", 0)),
        "periodo": f"{inicio} a {fin}",
        "videos": filas,
    }
