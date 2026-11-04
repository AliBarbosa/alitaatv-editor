# AlitaaTV · Editor de shorts

Herramientas para pasar un clip de Twitch (16:9) a un short vertical 1080x1920 con el estilo de AlitaaTV: hook, subtítulos, zooms a la cara, mensajes del chat, memes, efectos de sonido y placa de cierre.

Lo usa Claude dentro del proyecto "AlitaaTV Agente". El flujo completo (Notion, Drive, Metricool) está en el skill **alitaatv-produccion**.

## Preparar el entorno

```bash
git clone https://github.com/AliBarbosa/alitaatv-editor.git /home/claude/alitaatv-editor
bash /home/claude/alitaatv-editor/setup.sh
```

Tarda menos de un minuto. Deja:

| Qué | Dónde |
|---|---|
| Scripts | `/home/claude/scripts/` |
| Modelo de Whisper (small int8) | `/home/claude/models/whisper-small-int8/` |
| Clasificador de caras | `/home/claude/models/haar_face.xml` |
| Fuentes (`fonts_dir`) | `/home/claude/fonts_all/` (incluye Pricedown, que se baja en el setup) |

Para usar otra carpeta base: `ALITAA_BASE=/otra/ruta bash setup.sh`.

## Scripts

- `scripts/transcribir.py audio.wav salida.json`: transcripción con marcas de tiempo por palabra (wav mono 16 kHz).
- `scripts/seguir_cara.py video.mp4 x y w h salida.json`: ubica la cara dentro de la facecam, 5 veces por segundo.
- `scripts/editar_short.py spec.json`: arma el short. Todas las opciones del `spec.json` están documentadas al principio del archivo.
- `scripts/carrusel_evento.py spec.json`: arma el carrusel de Instagram de los eventos de los viernes (estilo San Andreas): portada, premios, cómo sumarte y video de choques, en 1080x1350. El horario de Argentina se calcula solo a partir de la fecha y la hora en España. Opciones documentadas al principio del archivo. Necesita Chrome o Chromium.

## Reglas

- Acá no van contraseñas, tokens ni claves. Metricool, Notion y Drive se conectan aparte.
- Nada de clips ni videos: el material vive en el Drive de AlitaaTV.
- Cada cambio de estilo aprobado por Ali o Giuly se hace en un commit con un mensaje claro, así se puede volver atrás.

## Fuentes

Montserrat (SIL Open Font License, ver `fonts/OFL-Montserrat.txt`) y Luckiest Guy (Apache 2.0, ver `fonts/LICENSE-LuckiestGuy.txt`).

Pricedown (Ray Larabie) no se guarda en el repo: `setup.sh` la baja de una copia pública fija y la verifica con sha256.
