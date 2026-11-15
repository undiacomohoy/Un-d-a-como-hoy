# Guía para Claude: montar un canal de YouTube automático con agentes

**Para Claude:** este archivo es para vos. La persona quiere replicar un sistema que ya funciona en otra compu: un canal de YouTube que se produce y publica solo, con agentes de IA, gratis, y que corre en la nube (GitHub Actions) aunque la compu esté apagada. Tiene que ser con **sus propias cuentas** y con **otra temática de videos**.

Tu trabajo: guiarla paso a paso, hacer vos todo lo técnico y decirle con claridad lo que tiene que hacer a mano. Hablale en español, simple, un paso por vez. Antes de avanzar, verificá que el paso anterior quedó bien.

---

## Cómo funciona el sistema

Cada ejecución (`producir.py`) hace un Short vertical de unos 45 segundos:

| Agente | Archivo | Qué hace | Con qué |
|---|---|---|---|
| Productor | `producir.py` | Elige el tema y el formato del día y coordina | — |
| Investigador | `agentes/01_investigador.md` | Ficha del tema: datos, gancho, temas a evitar | Gemini |
| Guionista | `agentes/02_guionista.md` | Narración en 7 escenas, máximo 100 palabras | Gemini |
| Director visual | `agentes/03_director_visual.md` | Un prompt de imagen por escena | Gemini |
| SEO | `agentes/04_seo.md` | Título, descripción y tags | Gemini |
| Revisor | `agentes/05_revisor.md` | Aprueba o hace reescribir (gancho, largo, fidelidad, políticas) | Gemini |
| Ilustrador | `src/imagenes.py` | 7 imágenes verticales | Cloudflare Workers AI (FLUX.2) |
| Narrador | `src/voz.py` | Voz por escena | Gemini TTS, con Edge TTS de respaldo |
| Editor | `src/montaje.py` | Movimiento de cámara, subtítulos, música | FFmpeg |
| Publicador | `src/youtube.py` | Sube el video | YouTube Data API |
| Curador | `agentes/07_curador.md` | Agrega temas nuevos cuando quedan menos de 8 | Gemini |
| Recopilación | `recopilar.py` + `agentes/08_recopilacion.md` | Video largo horizontal con los Shorts de la semana | FFmpeg |
| Analista | `analizar.py` + `agentes/06_analista.md` | Lee estadísticas y deja aprendizajes que usan los demás | YouTube Analytics + Gemini |

- La lista de temas está en `data/leyendas.json` (el nombre quedó del canal original; cada item es `{"nombre": ..., "origen": ...}`; "origen" puede ser región, categoría o contexto).
- `data/historial.json` evita repetir temas. `data/aprendizajes.json` lo escribe el Analista.
- Los formatos rotan (en `config.yaml`) para que YouTube no lo considere contenido repetitivo.
- La configuración está toda en `config.yaml`; las claves, en `claves.txt` (o `.env`).

---

## Reglas que tenés que respetar

**Esto lo tiene que hacer la persona, no vos:**
- Crear cuentas: Google/Gmail, Cloudflare, GitHub.
- Crear el canal de YouTube (YouTube lo registra como una cuenta de marca nueva).
- Iniciar sesión y escribir contraseñas o códigos de verificación (2FA, códigos por mail).
- Aceptar términos y condiciones: Política de Datos de las APIs de Google, Biblioteca de audio de YouTube, etc. Si lo hacés vos desde un navegador, pedile un "sí" explícito antes.
- Pegar claves y tokens en formularios web. Las claves se las podés pedir para guardarlas en `claves.txt`, pero no las escribas vos en campos de páginas web.
- Elegir el país de residencia en YouTube Studio.
- Correr en su Terminal los comandos que vos no puedas ejecutar.

**Pedile confirmación antes de:** publicar videos públicos por primera vez, borrar algo o aceptar términos.

**Nunca:** subir `claves.txt`, `.env`, `client_secret.json` ni `token.json` a GitHub (ya están en `.gitignore`). En la nube van en un único secreto cifrado.

---

## Fase 0 — Definir el canal nuevo

Preguntale y acordá:
1. Temática, nombre del canal e identificador (@).
2. Idioma, tono de la narración y frase de cierre fija.
3. Estilo visual de las imágenes, siempre el mismo para que el canal sea reconocible.

Recomendaciones:
- Nichos con RPM alto (dinero y economía, historia, ciencia, tecnología) pagan más que el entretenimiento.
- Evitá consejos financieros o médicos: YouTube los revisa más.
- Que sea bien distinto de otros canales automáticos de la misma persona.

## Fase 1 — Adaptar el sistema a la temática (lo hacés vos)

1. `config.yaml`: completá todo lo marcado `<<CAMBIAR>>`: canal, estilo_visual, formatos, voz y `github.repositorio`.
2. Reescribí los prompts de `agentes/01` a `08` para la temática nueva. Mantené la estructura y, sobre todo, el formato JSON de respuesta, porque el código depende de esas claves. Ajustá además:
   - Las reglas de fidelidad y los temas a evitar de la temática.
   - Qué cuenta como gancho.
   - La línea "Narración e imágenes creadas con ayuda de inteligencia artificial" en el SEO.
3. Generá 30 temas reales para `data/leyendas.json` (está vacío). Si queda vacío, el Curador lo llena solo en la primera ejecución.
4. `probar_gemini.py` tiene un prompt de imagen de ejemplo (una criatura en un bosque); adaptalo si querés.
5. `recopilar.py` usa `canal/banner.png` como intro si existe. `extras/disenar_identidad.py` es un ejemplo para generar banner y foto de perfil con Pillow; adaptalo al estilo nuevo, o diseñá la identidad de otra forma.

## Fase 2 — Cuentas y claves (gratis, sin tarjeta)

**A) Gemini** (texto y voz)
- La persona entra a https://aistudio.google.com/apikey → "Create API key" → **"Create API key in new project"**, **sin activar facturación** (así queda en el nivel gratuito y nunca cobra).
- Si ya tiene otro canal con otra clave, que use un **proyecto nuevo**: el cupo gratuito es por proyecto.

**B) Cloudflare** (imágenes)
- Cuenta gratis en https://dash.cloudflare.com/sign-up (no pide tarjeta).
- **Account ID:** es el código de 32 caracteres que aparece en la URL del panel (`dash.cloudflare.com/<ACCOUNT_ID>/...`), o en Workers & Pages → panel derecho.
- **Token:** My Profile → API Tokens → Create Token → "View all templates" → plantilla **"Workers AI"** → Continue to summary → Create Token. Se muestra una sola vez.
- 10.000 unidades gratis por día; cada video usa unas 650.

**C) Archivo de claves**
- Copiá `.env.example` a `claves.txt` (o `.env`) con `GEMINI_API_KEY`, `CLOUDFLARE_ACCOUNT_ID` y `CLOUDFLARE_API_TOKEN`.
- El programa lee `.env` o `claves.txt`. Si tenés herramientas que no pueden escribir `.env`, usá `claves.txt`.

## Fase 3 — YouTube y Google Cloud

1. **Canal:** la persona lo crea en youtube.com/account → "Crear un canal nuevo" → nombre e identificador.
   - Ojo: si no tenía canal, YouTube puede convertir directamente el canal personal. Revisá cuál quedó (Studio → Personalización) y avisale.
   - Después cargan banner, foto, descripción y vínculos en Studio → Personalización → Publicar.
   - Palabras clave y país (este último lo elige la persona) en Studio → Configuración → Canal. Sin país no deja guardar las palabras clave.
2. **Proyecto de Google Cloud** (https://console.cloud.google.com, con la cuenta del canal): crear un proyecto.
3. **Habilitar 2 APIs:** **YouTube Data API v3** y **YouTube Analytics API** (la usa el Analista).
4. **Google Auth Platform → Crear la configuración:**
   - Nombre de la app y mail de soporte.
   - Público: **Usuarios externos**.
   - Mail de contacto.
   - Aceptar la política (lo acepta la persona).
5. **Pasar a producción (imprescindible):** en "Público" → **Publicar app**. En modo "Prueba", el permiso **vence cada 7 días** y la automatización se corta.
   - Para publicar, Google pide **página principal** y **política de privacidad** en "Información de marca". Sirve una página simple que explique que la app solo sube videos al canal del dueño, no comparte datos y cómo revocar el acceso; podés publicarla como artifact o en GitHub Pages.
   - El logo **no** es obligatorio, y subirlo obliga a verificar la app: no lo subas.
6. **Clientes → Crear cliente de OAuth → App de escritorio.** Del cuadro que aparece se obtienen el client ID y el secret, o se descarga el JSON. Guardalo como `client_secret.json` con este formato:
   `{"installed":{"client_id":..., "project_id":..., "auth_uri":"https://accounts.google.com/o/oauth2/auth", "token_uri":"https://oauth2.googleapis.com/token", "auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs", "client_secret":..., "redirect_uris":["http://localhost"]}}`
7. **Autorizar** (en la compu de la persona, con navegador):
   - Comando: `python autorizar_youtube.py`. Se abre el navegador: elegir la cuenta y el **canal correcto**.
   - Ante "Google no verificó esta app": Configuración avanzada → Ir a (nombre de la app) → Continuar.
   - Genera `token.json`, que incluye los permisos de subida, lectura y estadísticas. Si cambian los permisos (SCOPES en `src/youtube.py`), hay que reautorizar.
8. **Cuota de la API de YouTube:** 10.000 unidades por día por proyecto, y cada subida cuesta 1.600 (unas 6 subidas por día). Alcanza para 2 canales por proyecto.

## Fase 4 — Instalar y probar en la compu

- Requisitos: Python 3.11–3.13 y FFmpeg.
  - En Mac/Linux, `bash instalar_y_probar.sh` crea el `.venv`, instala todo y corre las pruebas.
  - En Windows, hacelo a mano: `python -m venv .venv`, `.venv\Scripts\pip install --prefer-binary -r requirements.txt`, `.venv\Scripts\python verificar.py`, `.venv\Scripts\python probar_gemini.py`.
- Comandos de prueba:
  - `python probar_gemini.py`: tiene que dar OK en texto, imagen, voz de Gemini y voz de Edge. Genera archivos en `salida/_prueba` para mirar y escuchar.
  - `python producir.py --sin-subir`: arma un video completo sin publicarlo, en `salida/<fecha>_<tema>/final.mp4`. Revisá duración (40–60 s), imágenes, voz y subtítulos.
  - `python producir.py --no-listado`: lo sube como no listado, para que la persona lo revise en Studio.

**Problemas que ya aparecieron y cómo se resolvieron:**
- **Sin FFmpeg en el sistema:** el código usa el FFmpeg que trae la librería `imageio-ffmpeg` (está en `requirements.txt`). También busca un binario en `bin/ffmpeg`. En Macs viejas, Homebrew puede tardar horas; evitalo.
- **pip intenta compilar `cryptography`** (error de Rust u OpenSSL): instalar con `--prefer-binary`.
- **Python muy nuevo (3.14+):** algunas librerías todavía no tienen paquetes listos. Usá 3.12.
- **Error SSL en Mac** con el Python de python.org: definí `SSL_CERT_FILE` con la ruta de `certifi` (lo hacen `instalar_y_probar.sh` y `correr.sh`).
- **Gemini 503 "high demand":** es normal. El código reintenta, pasa a los modelos de respaldo de `config.yaml` (`gemini_texto`) y, si todos fallan, espera 60 s y hace hasta 3 rondas.
- **Gemini TTS 429:** el límite por minuto se resuelve con `pausa_gemini_seg`. Si se agotó el límite diario ("exceeded your current quota"), el video entero pasa a la voz de Edge, para no mezclar voces.
- **Videos muy largos:** la voz de Gemini con estilo "lento" alargaba los Shorts a 96 s. Por eso existen `velocidad: 1.15` en la voz y el máximo de 100 palabras en el Guionista y el Revisor.

## Fase 5 — Pasarlo a la nube (GitHub Actions: funciona con la compu apagada)

1. **Repositorio:** la persona crea una cuenta en GitHub (o inicia sesión). Creá un repositorio **privado** y poné `usuario/repo` en `config.yaml` → `github.repositorio`.
2. **Token clásico:** github.com/settings/tokens/new?scopes=repo,workflow
   - Puede pedir un código de verificación por mail (lo pone la persona).
   - Generate token → copiarlo (se muestra una sola vez).
3. **Subida:** la persona corre `python subir_a_github.py` y pega el token cuando lo pide (queda oculto). El script:
   - Sube el código, incluido `.github/workflows/canal.yml`, que va embebido en el script por si la carpeta `.github` no se puede escribir.
   - Guarda `claves.txt`, `client_secret.json` y `token.json` como **un solo secreto cifrado** llamado `CONFIG_B64`.
   - Lanza una prueba.
4. **Verificación:** pestaña Actions → la ejecución de "prueba" tiene que mostrar OK en los 4 servicios.
   - Si el workflow no aparece en el repo, crealo desde la web: Add file → crear `.github/workflows/canal.yml`.
   - Si `CONFIG_B64` no está en Settings → Secrets and variables → Actions, el script falló.
5. **Borrar el token:** después de la subida, borrá el token en github.com/settings/tokens. La nube usa su propio permiso interno (GITHUB_TOKEN).
6. **Horarios en `.github/workflows/canal.yml`:** cron en **UTC**; Argentina es UTC-3, así que 15:30 UTC = 12:30 AR.
   - Si la persona ya tiene otro canal, **desfasá los horarios** para no superponer.
   - GitHub puede demorar entre 5 y 30 minutos.
7. **Minutos:** cada canal usa unos 1.000 de los 2.000 gratis por mes de los repos privados (2 canales como máximo). Con repos **públicos** los minutos son ilimitados y las claves siguen protegidas.
8. **Estado y recopilación:** el workflow guarda `data/` en el repo después de cada tarea. Los Shorts de la semana se guardan en un release llamado "semana" para la recopilación del domingo, que después los borra.

## Fase 6 — Música (opcional, recomendado)

- Fuente: YouTube Studio → Biblioteca de audio → filtros **"Atribución no obligatoria"** + Ánimo acorde a la temática. Usar la biblioteca implica aceptar sus términos (que acepte la persona).
- Destino: 4 o 5 pistas MP3 en `assets/musica/`. El Editor elige una al azar en cada video.
- Si la nube ya está andando, subilas al repo (en `assets/musica/`).

## Fase 7 — Ejecución local (solo si no se usa la nube)

- En Mac: `bash programar.sh` mueve el proyecto a `~/CanalAutomatico` (macOS no deja que las tareas lean Documentos) y crea 3 tareas de launchd. Para pausar: `bash pausar.sh`.
- **No dejes local y nube activos a la vez**, porque se publica todo dos veces.

---

## Expectativas para contarle a la persona (datos de 2026)

- **Volumen:** según vidIQ (sept. 2026), de los canales que suben más de 52 videos al año, el ~31 % llega a 1.000 suscriptores en un año.
- **Cuánto paga un Short:** en audiencias latinoamericanas, unos US$ 0,03–0,05 cada 1.000 vistas.
- **Monetización desde el 1/2/2027:** 1.000 suscriptores **y además** 20 M de vistas de Shorts en 90 días, o 8.000 horas de videos largos en un año. Es de largo plazo y la mayoría de los canales no llega.
- **Contenido repetitivo:** YouTube no monetiza contenido repetitivo hecho con plantilla. Por eso hay formatos que rotan, recopilaciones largas y, si se puede, la voz o presencia real de la persona en algunos videos.
- **Primer chequeo:** a los 30 días, mirar el % promedio visto (ideal más de 70 %). A los 90 días, si ningún Short pasó las 10.000 vistas, replantear el formato.

## Checklist final

- [ ] `probar_gemini.py` da OK en todo
- [ ] Un video de prueba revisado y subido como no listado
- [ ] App de Google en **producción** (no en "Prueba")
- [ ] Workflow en GitHub con la prueba en verde y el secreto `CONFIG_B64` cargado
- [ ] Token de GitHub borrado
- [ ] Tareas locales pausadas, si se usa la nube
- [ ] La persona sabe dónde ver qué pasó (pestaña Actions) y cómo pausar ("Disable workflow")
