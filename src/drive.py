"""Deja los informes del canal en tu Google Drive (para que los agentes de la oficina los lean).
Usa su propio permiso (token_drive.json), separado de YouTube: si falta, el canal sigue funcionando igual."""
import logging

from .util import RAIZ

log = logging.getLogger("mitos")

SCOPES = ["https://www.googleapis.com/auth/drive.file"]  # solo archivos que crea esta app
CLIENT_SECRET = RAIZ / "client_secret.json"
TOKEN = RAIZ / "token_drive.json"
CARPETA = "Informes de canales"


def obtener_credenciales(interactivo: bool = False):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES) if TOKEN.exists() else None
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN.write_text(creds.to_json(), encoding="utf-8")
        return creds
    if not interactivo:
        raise RuntimeError("Drive no está autorizado (falta token_drive.json). Corré autorizar_drive.py")
    flujo = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
    creds = flujo.run_local_server(port=0, prompt="consent", access_type="offline")
    TOKEN.write_text(creds.to_json(), encoding="utf-8")
    return creds


def subir_texto(nombre: str, texto: str) -> str:
    """Crea (si hace falta) la carpeta 'Informes de canales' y sube el informe. Devuelve el id del archivo."""
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaInMemoryUpload

    svc = build("drive", "v3", credentials=obtener_credenciales(), cache_discovery=False)
    q = f"name = '{CARPETA}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    carpetas = svc.files().list(q=q, fields="files(id)", spaces="drive").execute().get("files", [])
    if carpetas:
        carpeta_id = carpetas[0]["id"]
    else:
        carpeta_id = svc.files().create(body={"name": CARPETA, "mimeType": "application/vnd.google-apps.folder"},
                                        fields="id").execute()["id"]
    media = MediaInMemoryUpload(texto.encode("utf-8"), mimetype="text/markdown")
    f = svc.files().create(body={"name": nombre, "parents": [carpeta_id]}, media_body=media, fields="id").execute()
    return f["id"]
