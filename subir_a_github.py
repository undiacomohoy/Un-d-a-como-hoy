r"""
Sube el proyecto a tu repositorio de GitHub y guarda las claves como secreto (CONFIG_B64),
para que el canal funcione en la nube aunque la compu esté apagada.

Uso (en la Terminal):
    cd <carpeta del proyecto> && .venv/bin/python subir_a_github.py   (en Windows: venv\Scripts\python subir_a_github.py)

Te pide un token de GitHub (lo pegás vos; no se muestra ni se guarda).
"""
import base64
import getpass
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent
import yaml

REPO = (yaml.safe_load((RAIZ / "config.yaml").read_text(encoding="utf-8")).get("github", {}) or {}).get("repositorio", "")
API = f"https://api.github.com/repos/{REPO}"
WORKFLOW = 'name: Canal automatico\n\non:\n  schedule:\n    - cron: "30 9 * * *"    # Short 06:30 (Argentina, UTC-3): sale publicado a la mañana\n    - cron: "0 21 * * 0"    # Recopilación: domingo 18:00\n    - cron: "0 12 * * 1"    # Análisis: lunes 09:00\n  workflow_dispatch:\n    inputs:\n      tarea:\n        description: "Qué correr"\n        type: choice\n        options: [short, recopilacion, analisis, prueba]\n        default: short\n\npermissions:\n  contents: write\n\nconcurrency:\n  group: canal\n  cancel-in-progress: false\n\njobs:\n  correr:\n    runs-on: ubuntu-latest\n    timeout-minutes: 150\n    env:\n      GH_TOKEN: ${{ github.token }}\n      PYTHONUNBUFFERED: "1"\n      TZ: America/Argentina/Mendoza\n    steps:\n      - uses: actions/checkout@v4\n\n      - name: Elegir tarea\n        id: t\n        run: |\n          case "${{ github.event.schedule }}" in\n            "0 21 * * 0") T=recopilacion ;;\n            "0 12 * * 1") T=analisis ;;\n            "") T="${{ inputs.tarea }}" ;;\n            *) T=short ;;\n          esac\n          echo "tarea=$T" >> "$GITHUB_OUTPUT"\n          echo "Tarea: $T"\n\n      - uses: actions/setup-python@v5\n        with:\n          python-version: "3.12"\n          cache: pip\n\n      - name: Instalar FFmpeg y librerías\n        run: |\n          sudo apt-get update -qq\n          sudo apt-get install -y -qq ffmpeg fonts-liberation > /dev/null\n          pip install -q -r requirements.txt\n\n      - name: Cargar claves (secreto CONFIG_B64)\n        env:\n          CONFIG_B64: ${{ secrets.CONFIG_B64 }}\n        run: |\n          if [ -z "$CONFIG_B64" ]; then echo "Falta el secreto CONFIG_B64"; exit 1; fi\n          echo "$CONFIG_B64" | base64 -d | tar xz\n          ls claves.txt client_secret.json token.json > /dev/null\n\n      - name: Prueba de servicios\n        if: steps.t.outputs.tarea == \'prueba\'\n        run: python probar_gemini.py\n\n      - name: Producir y publicar un Short\n        if: steps.t.outputs.tarea == \'short\'\n        run: python producir.py\n\n      - name: Guardar el Short para la recopilación del domingo\n        if: steps.t.outputs.tarea == \'short\'\n        run: |\n          gh release view semana > /dev/null 2>&1 || gh release create semana --title "Shorts de la semana" --notes "Videos temporales para la recopilación semanal" --prerelease\n          for f in salida/*/final.mp4; do\n            [ -f "$f" ] || continue\n            nombre="$(basename "$(dirname "$f")").mp4"\n            cp "$f" "/tmp/$nombre"\n            gh release upload semana "/tmp/$nombre" --clobber\n          done\n\n      - name: Traer los Shorts de la semana\n        if: steps.t.outputs.tarea == \'recopilacion\'\n        run: |\n          mkdir -p /tmp/semana\n          gh release download semana --dir /tmp/semana || true\n          for f in /tmp/semana/*.mp4; do\n            [ -f "$f" ] || continue\n            d="salida/$(basename "$f" .mp4)"; mkdir -p "$d"; mv "$f" "$d/final.mp4"\n          done\n\n      - name: Recopilación semanal\n        if: steps.t.outputs.tarea == \'recopilacion\'\n        run: python recopilar.py\n\n      - name: Limpiar los Shorts ya recopilados\n        if: steps.t.outputs.tarea == \'recopilacion\'\n        run: |\n          if ls salida/*_recopilacion/recopilacion.mp4 > /dev/null 2>&1; then\n            for a in $(gh release view semana --json assets -q \'.assets[].name\'); do gh release delete-asset semana "$a" -y; done\n          fi\n\n      - name: Análisis semanal\n        if: steps.t.outputs.tarea == \'analisis\'\n        run: python analizar.py\n\n      - name: Guardar historial y aprendizajes\n        if: always()\n        run: |\n          git config user.name "Canal automatico"\n          git config user.email "actions@users.noreply.github.com"\n          git add data/\n          git diff --cached --quiet || (git commit -m "Estado: ${{ steps.t.outputs.tarea }} $(date -u +%F)" && git push)\n\n      - name: Guardar registros\n        if: always()\n        uses: actions/upload-artifact@v4\n        with:\n          name: logs-${{ steps.t.outputs.tarea }}-${{ github.run_id }}\n          path: logs/\n          retention-days: 14\n          if-no-files-found: ignore\n'
EXCLUIR_DIRS = {".venv", "venv", "canal-efemerides-adaptado", "originales", "salida", "logs", "bin", "__pycache__", ".git"}
EXCLUIR_ARCH = {"claves.txt", ".env", "client_secret.json", "token.json", "secreto_para_github.txt", ".DS_Store",
                "correr_diario.sh"}


def archivos():
    for p in sorted(RAIZ.rglob("*")):
        rel = p.relative_to(RAIZ)
        if p.is_dir() or any(parte in EXCLUIR_DIRS for parte in rel.parts) or p.name in EXCLUIR_ARCH:
            continue
        if p.suffix == ".pyc":
            continue
        if "(1)" in p.name or p.suffix in (".bak", ".bat") or p.name.startswith("token"):
            continue
        yield rel


def main():
    try:
        from nacl import encoding, public
    except ImportError:
        print("Instalando una librería de cifrado...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "--prefer-binary", "pynacl"])
        from nacl import encoding, public

    if not REPO or "/" not in REPO:
        sys.exit("Completá github.repositorio en config.yaml (formato usuario/repositorio)")
    for f in ("claves.txt", "client_secret.json", "token.json"):
        if not (RAIZ / f).exists():
            sys.exit(f"Falta {f} en {RAIZ}")

    token = input("Pegá tu token de GitHub (clic derecho) y apretá Enter: ").strip()
    import os
    os.system("cls" if os.name == "nt" else "clear")  # borra la pantalla para que el token no quede visible
    print(f"Recibí {len(token)} caracteres; empieza con '{token[:4]}'. (Un token correcto tiene ~40 y empieza con 'ghp_')")
    if not token.startswith(("ghp_", "github_pat_")):
        sys.exit("Eso no parece un token de GitHub. Copialo de nuevo con el ícono de copiar y volvé a probar.")
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                      "X-GitHub-Api-Version": "2022-11-28"})

    r = s.get(API)
    if r.status_code != 200:
        sys.exit(f"No pude acceder al repositorio ({r.status_code}). Revisá que el token tenga acceso a {REPO}.")

    # 1) primer commit si el repo está vacío
    ref = s.get(f"{API}/git/ref/heads/main")
    if ref.status_code != 200:
        print("Repositorio vacío: creo el primer archivo...")
        contenido = base64.b64encode((RAIZ / "README.md").read_bytes()).decode()
        r = s.put(f"{API}/contents/README.md", json={"message": "Primer archivo", "content": contenido, "branch": "main"})
        r.raise_for_status()
        ref = s.get(f"{API}/git/ref/heads/main")
    ref.raise_for_status()
    padre = ref.json()["object"]["sha"]
    base_tree = s.get(f"{API}/git/commits/{padre}").json()["tree"]["sha"]

    # 2) subir todos los archivos
    lista = list(archivos())
    arbol = []
    for i, rel in enumerate(lista, 1):
        datos = (RAIZ / rel).read_bytes()
        print(f"  [{i}/{len(lista)}] {rel}")
        r = s.post(f"{API}/git/blobs", json={"content": base64.b64encode(datos).decode(), "encoding": "base64"})
        r.raise_for_status()
        modo = "100755" if rel.suffix == ".sh" else "100644"
        arbol.append({"path": rel.as_posix(), "mode": modo, "type": "blob", "sha": r.json()["sha"]})
    r = s.post(f"{API}/git/blobs", json={"content": base64.b64encode(WORKFLOW.encode()).decode(), "encoding": "base64"})
    r.raise_for_status()
    arbol = [a for a in arbol if a["path"] != ".github/workflows/canal.yml"]
    arbol.append({"path": ".github/workflows/canal.yml", "mode": "100644", "type": "blob", "sha": r.json()["sha"]})
    r = s.post(f"{API}/git/trees", json={"base_tree": base_tree, "tree": arbol})
    r.raise_for_status()
    r = s.post(f"{API}/git/commits", json={"message": "Sistema de agentes para el canal",
                                           "tree": r.json()["sha"], "parents": [padre]})
    r.raise_for_status()
    s.patch(f"{API}/git/refs/heads/main", json={"sha": r.json()["sha"], "force": False}).raise_for_status()
    print("Código subido.")

    # 3) secreto CONFIG_B64 con las claves y el permiso de YouTube
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for f in ("claves.txt", "client_secret.json", "token.json"):
            tar.add(RAIZ / f, arcname=f)
    valor = base64.b64encode(buf.getvalue()).decode()
    clave = s.get(f"{API}/actions/secrets/public-key")
    clave.raise_for_status()
    k = clave.json()
    sellado = public.SealedBox(public.PublicKey(k["key"].encode(), encoding.Base64Encoder())).encrypt(valor.encode())
    r = s.put(f"{API}/actions/secrets/CONFIG_B64",
              json={"encrypted_value": base64.b64encode(sellado).decode(), "key_id": k["key_id"]})
    r.raise_for_status()
    print("Claves guardadas como secreto cifrado en GitHub.")

    # 4) primera prueba en la nube
    import time

    for _ in range(6):  # GitHub tarda unos segundos en reconocer el workflow recién subido
        r = s.post(f"{API}/actions/workflows/canal.yml/dispatches", json={"ref": "main", "inputs": {"tarea": "prueba"}})
        if r.status_code in (204, 200):
            break
        time.sleep(10)
    if r.status_code in (204, 200):
        print("Lancé una prueba en la nube. Mirala en: https://github.com/%s/actions" % REPO)
    else:
        print(f"No pude lanzar la prueba ({r.status_code}): {r.text[:200]}")
    print("\nListo. Ya podés borrar el token si querés (GitHub → Settings → Developer settings).")


if __name__ == "__main__":
    main()
