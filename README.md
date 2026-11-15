# Canal automático de YouTube con agentes de IA

Un equipo de agentes de IA que investiga un tema, escribe el guion, lo revisa, genera imágenes y voz, edita un Short vertical con subtítulos y música, y lo publica en YouTube. Todos los días, solo, gratis y en la nube (GitHub Actions), aunque la compu esté apagada. Además, todas las semanas arma un video largo de recopilación y analiza las estadísticas para mejorar.

## Cómo empezar

Abrí esta carpeta con **Claude** (Claude Code o la app de Claude con acceso a la carpeta) y pedile:

> "Leé GUIA_PARA_CLAUDE.md y guiame para montar mi canal."

Claude te va a ir diciendo qué hace él y qué tenés que hacer vos: crear cuentas, iniciar sesión, aceptar términos.

## Qué vas a necesitar (todo gratis)

- Una cuenta de Google, para YouTube, Gemini y Google Cloud.
- Una cuenta de Cloudflare, para las imágenes.
- Una cuenta de GitHub, para que funcione en la nube.
- Python 3.12 en tu compu, solo para las pruebas iniciales y para autorizar YouTube.

## Archivos principales

| Archivo | Qué es |
|---|---|
| `config.yaml` | Toda la configuración del canal (lo marcado `<<CAMBIAR>>` se adapta a tu temática) |
| `agentes/` | Las instrucciones de cada agente |
| `data/leyendas.json` | La lista de temas (el Curador agrega más solo) |
| `producir.py` | Hace y publica un Short |
| `recopilar.py` | Arma el video largo semanal |
| `analizar.py` | Analiza las estadísticas y deja aprendizajes |
| `subir_a_github.py` | Sube todo a tu GitHub y guarda tus claves como secreto cifrado |
| `.github/workflows/canal.yml` | Los horarios en la nube |
| `GUIA_PARA_CLAUDE.md` | La guía completa paso a paso |
