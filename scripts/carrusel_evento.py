"""Carrusel de evento de los viernes (estilo San Andreas). Uso: python3 -I carrusel_evento.py spec.json

Arma los 4 slides de Instagram (1080x1350, 4:5), en este orden:
  1. portada.png         título del evento, fecha, horario España/Argentina, trofeos y "Premios en plata del juego"
  2. premios.png         trofeos 1°/2°/3° con los montos en verde (plata del juego)
  3. como-sumarte.png    3 pasos para entrar al server + SUMATE
  4. choques_edit.mp4    compilado de choques ("MANEJO HORRIBLE"), con recuadro de la cara y WASTED opcional

spec.json (rutas absolutas; los videos pueden ser 2560x1440 o 1920x1080 con la facecam abajo a la derecha):
{
  "out_dir": "/mnt/user-data/outputs/carrusel",
  "prefijo": "MTA_1106_torneo-carreras",            # nombre base de los archivos
  "titulo": ["TORNEO", "DE CARRERAS", "GTA SAN ANDREAS"],   # 3 líneas de la portada (la 3ra va en dorado)
  "fecha": "2026-11-06",                             # día del evento (ISO). El texto "VIERNES 6/11" sale solo
  "hora_es": 23,                                     # hora en España; la de Argentina se calcula con la fecha
  "premios": ["$150K", "$100K", "$50K"],
  "fondo_portada": {"video": "...mp4", "t": 1.6},    # o {"imagen": "...png"}: cuadro de una carrera
  "fondo_premios": {"imagen": "...png"},             # o {"video": ..., "t": ...}: ej. la línea de partida
  "fondo_sumate": {"video": "...mp4", "t": 0.5},     # se oscurece al 40 %
  "video": {
    "kicker": "SPOILER", "titulo": "MANEJO HORRIBLE", "pie": "ASÍ QUE TENÉS CHANCES",
    "clips": [                                       # de 2 a 4 clips; apuntá a 15-20 s en total
      {"video": "...mp4", "ini": 0.0, "dur": 7.1},
      {"video": "...mp4", "ini": 3.5, "dur": 5.1, "bips": [[1.2, 1.8]]},       # bips: tiempos DENTRO del tramo
      {"video": "...mp4", "ini": 2.4, "dur": 7.0, "wasted": [5.5, 7.0]}        # WASTED rojo en ese tramo
    ]
  }
}
Opcional en cada clip: "cara": [cx, cy] (si no, se calcula con seguir_cara.py) y "facecam": [x, y, w, h].
Opcional general:
  "facecam": [x, y, w, h]   recuadro de la cámara en px del video (por defecto el de 2560x1440 escalado:
                            [1916,1078,644,362]; los clips de 1920x1080 de nov. 2026 usan [1388,781,532,299]).
                            El juego se recorta por encima de la cámara, así no se ve nada de ella.
  "etiqueta": "FECHA 2"     sello dorado inclinado arriba a la derecha de la portada (para que cada semana cambie).
  "video": {"titulo_size": 110}   tamaño del título del video si es largo.
Requiere: ffmpeg, playwright (pip) y Chrome o Chromium. Fuentes en $ALITAA_BASE/fonts_all (setup.sh).
"""
import asyncio, json, os, subprocess, sys, tempfile, shutil, datetime
from zoneinfo import ZoneInfo
from pathlib import Path

BASE = Path(os.environ.get('ALITAA_BASE', '/home/claude'))
FONTS = BASE / 'fonts_all'
GOLD, GREEN, RED, WHITE, LILA = '#E7B140', '#4E9A3A', '#C0262B', '#F4F1EA', '#A78BFA'
DIAS = ['LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES', 'SÁBADO', 'DOMINGO']

spec = json.load(open(sys.argv[1]))
OUT = Path(spec['out_dir']); OUT.mkdir(parents=True, exist_ok=True)
PRE = spec.get('prefijo', 'carrusel')
TMP = Path(tempfile.mkdtemp(prefix='carrusel_'))

# ---------- Fecha y horarios ----------
d = datetime.date.fromisoformat(spec['fecha'])
es = datetime.datetime(d.year, d.month, d.day, spec['hora_es'], tzinfo=ZoneInfo('Europe/Madrid'))
ar = es.astimezone(ZoneInfo('America/Argentina/Buenos_Aires'))
FECHA = f"{DIAS[d.weekday()]} {d.day}/{d.month}"
HORA = f"{es.hour} H ESPAÑA · {ar.hour} H ARGENTINA"
HORA_MIN = f"{es.hour} h España · {ar.hour} h Argentina"
print('Fecha:', FECHA, '|', HORA)

def run(cmd):
    subprocess.run(cmd, check=True)

def probe(v):
    w, h = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                           '-of', 'csv=p=0', v], capture_output=True, text=True, check=True).stdout.strip().split(',')[:2]
    return int(w), int(h)

def fondo(src, name):
    """Devuelve una imagen 1152x1440 (cuadro de video recortado sin minimapa ni facecam) o la imagen tal cual."""
    if 'imagen' in src:
        return src['imagen']
    w, _ = probe(src['video']); s = w / 2560
    out = TMP / f'{name}.png'
    run(['ffmpeg', '-v', 'error', '-y', '-ss', str(src['t']), '-i', src['video'], '-frames:v', '1',
         '-vf', f"crop={int(1152*s)}:{int(1440*s)}:{int(600*s)}:0,scale=1152:1440", str(out)])
    return str(out)

# ---------- HTML de los slides ----------
CSS = f"""
@font-face{{font-family:PD;src:url(file://{FONTS}/Pricedown.ttf)}}
@font-face{{font-family:M;font-weight:800;src:url(file://{FONTS}/Montserrat-ExtraBold.ttf)}}
@font-face{{font-family:M;font-weight:900;src:url(file://{FONTS}/Montserrat-Black.ttf)}}
html,body{{margin:0;padding:0;background:transparent}}
.s{{width:1080px;height:1350px;box-sizing:border-box;position:relative;overflow:hidden;font-family:M;color:{WHITE}}}
.pd{{font-family:PD;line-height:.9;-webkit-text-stroke:9px #000;paint-order:stroke fill;letter-spacing:1px}}
.sub{{font-weight:900;text-shadow:-3px -3px 0 #000,3px -3px 0 #000,-3px 3px 0 #000,3px 3px 0 #000,0 3px 0 #000,0 -3px 0 #000,3px 0 0 #000,-3px 0 0 #000}}
.box{{background:rgba(0,0,0,.72);border-radius:6px}}
.bg{{position:absolute;inset:0;background-size:cover;background-position:center}}
"""

def trofeo(color, n, size):
    asa = lambda dp: f"<path d='{dp}' fill='none' stroke='#000' stroke-width='9'/><path d='{dp}' fill='none' stroke='{color}' stroke-width='4'/>"
    return (f"<svg width='{size}' height='{size}' viewBox='0 0 100 100' aria-hidden='true'>"
            f"<path d='M28 12 H72 V40 C72 56 62 64 50 64 C38 64 28 56 28 40 Z' fill='{color}' stroke='#000' stroke-width='5' stroke-linejoin='round'/>"
            + asa('M28 20 H14 V30 C14 40 22 46 30 46') + asa('M72 20 H86 V30 C86 40 78 46 70 46') +
            f"<rect x='44' y='63' width='12' height='14' fill='{color}' stroke='#000' stroke-width='5'/>"
            f"<rect x='30' y='76' width='40' height='14' rx='2' fill='{color}' stroke='#000' stroke-width='5'/>"
            f"<text x='50' y='48' text-anchor='middle' font-family='PD' font-size='34' fill='#000'>{n}</text></svg>")

TROF = [(GOLD, '1'), ('#C9CED6', '2'), ('#C77B3A', '3')]

def flecha():
    return (f"<div style='position:absolute;right:48px;bottom:44px;display:flex;align-items:center;gap:16px'>"
            f"<div class='sub' style='font-size:34px;letter-spacing:3px'>DESLIZÁ</div>"
            f"<div style='width:84px;height:84px;border-radius:50%;background:{GOLD};border:5px solid #000;display:flex;align-items:center;justify-content:center'>"
            f"<svg width='48' height='48' viewBox='0 0 24 24' fill='none' stroke='#000' stroke-width='3.2' stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'><path d='M5 12h14M13 6l6 6-6 6'/></svg></div></div>")

def sello():
    t = spec.get('etiqueta')
    if not t:
        return ''
    return (f"<div style='position:absolute;right:30px;top:24px;transform:rotate(7deg);background:{GOLD};border:6px solid #000;"
            f"border-radius:10px;padding:10px 26px 4px;box-shadow:6px 6px 0 #000'><div class='pd' style='font-size:64px;color:#000;"
            f"-webkit-text-stroke:0;letter-spacing:2px'>{t}</div></div>")

def bgdiv(img, extra=''):
    return f"<div class='bg' style=\"background-image:url('{Path(img).resolve().as_uri()}');{extra}\"></div>"

t1, t2, t3 = spec['titulo']
SL = {}
SL['portada'] = f"""<div class='s'>{bgdiv(fondo(spec['fondo_portada'], 'portada'))}
<div style='position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.55) 0%,rgba(0,0,0,0) 38%,rgba(0,0,0,0) 50%,rgba(0,0,0,.6) 70%)'></div>
<div style='position:absolute;left:56px;right:56px;top:60px;display:flex;flex-direction:column;align-items:center;text-align:center'>
<div class='pd' style='font-size:150px'>{t1}</div><div class='pd' style='font-size:118px'>{t2}</div>
<div class='pd' style='font-size:96px;color:{GOLD};margin-top:10px'>{t3}</div>
<div class='box' style='margin-top:26px;padding:14px 36px;display:flex;flex-direction:column;align-items:center;gap:4px'>
<div class='pd' style='font-size:76px;-webkit-text-stroke:6px #000'>{FECHA}</div><div class='sub' style='font-size:34px;letter-spacing:2px'>{HORA}</div></div></div>
<div class='box' style='position:absolute;left:56px;right:56px;bottom:150px;padding:22px 30px;display:flex;flex-direction:column;align-items:center;gap:8px'>
<div class='pd' style='font-size:62px;color:{GOLD};-webkit-text-stroke:6px #000'>PREMIOS EN PLATA DEL JUEGO</div>
<div style='display:flex;justify-content:space-around;width:100%'>
{''.join(f"<div style='display:flex;align-items:center;gap:10px'>{trofeo(c, n, 96)}<div class='pd' style='font-size:64px;-webkit-text-stroke:6px #000'>{n}°</div></div>" for c, n in TROF)}</div></div>
{sello()}{flecha()}</div>"""

SL['premios'] = f"""<div class='s' style='background:#000'>{bgdiv(fondo(spec['fondo_premios'], 'premios'), 'background-position:center top;filter:brightness(.55)')}
<div style='position:absolute;left:0;right:0;top:70px;text-align:center'><div class='pd' style='font-size:190px;color:{GOLD}'>PREMIOS</div></div>
<div style='position:absolute;left:70px;right:70px;top:330px;display:flex;flex-direction:column;gap:30px'>
{''.join(f"<div class='box' style='display:flex;align-items:center;gap:30px;padding:20px 40px;background:rgba(0,0,0,.85)'>{trofeo(c, n, 150)}<div class='sub' style='font-size:56px;flex-grow:1'>{n}°</div><div class='pd' style='font-size:{150 if n == '1' else 130}px;color:{GREEN}'>{v}</div></div>" for (c, n), v in zip(TROF, spec['premios']))}
<div class='box sub' style='font-size:36px;text-align:center;padding:26px 20px;background:rgba(0,0,0,.92)'>Plata del juego para gastar en el server</div></div>
{flecha()}</div>"""

PASOS = [('Bajá MTA gratis', 'multitheftauto.com'), ('Conectate al server', 'play.alitaatv.com:22003'),
         (f"Entrá el {FECHA.split()[0].lower()} {d.day}/{d.month}", HORA_MIN)]
SL['como-sumarte'] = f"""<div class='s' style='background:#000'>{bgdiv(fondo(spec['fondo_sumate'], 'sumate'), 'background-size:135%;background-position:center 85%;filter:brightness(.4)')}
<div style='position:absolute;left:64px;right:64px;top:70px;display:flex;flex-direction:column;gap:30px'>
<div class='pd' style='font-size:150px'>CÓMO<br><span style='color:{GOLD}'>SUMARTE</span></div>
{''.join(f"<div class='box' style='display:flex;gap:30px;align-items:center;padding:24px 34px'><div class='pd' style='font-size:96px;color:{GOLD};-webkit-text-stroke:7px #000;width:70px;text-align:center'>{i + 1}</div><div><div class='sub' style='font-size:46px'>{a}</div><div class='sub' style='font-size:32px;font-weight:800;color:#DDD'>{b}</div></div></div>" for i, (a, b) in enumerate(PASOS))}
<div class='sub' style='font-size:28px;font-weight:800;color:#DDD'>Necesitás GTA San Andreas en PC. Sin inscripción: entrá cuando arranca el stream.</div></div>
<div style='position:absolute;left:0;right:0;bottom:70px;display:flex;flex-direction:column;align-items:center;gap:10px'>
<div class='pd' style='font-size:210px;color:{GOLD};-webkit-text-stroke:11px #000'>SUMATE</div>
<div class='sub' style='font-size:36px;letter-spacing:2px'>twitch.tv/alitaatv</div></div></div>"""

V = spec['video']
SL['marco'] = f"""<div class='s'>
<div style='position:absolute;left:0;right:0;top:0;height:300px;background:#000;display:flex;flex-direction:column;justify-content:center;padding:0 60px'>
<div class='sub' style='font-size:36px;letter-spacing:6px;color:{GOLD}'>{V.get('kicker', 'SPOILER')}</div>
<div class='pd' style='font-size:{V.get("titulo_size", 122)}px;white-space:nowrap'>{V.get('titulo', 'MANEJO HORRIBLE')}</div></div>
<div style='position:absolute;left:0;right:0;bottom:0;height:200px;background:#000;display:flex;align-items:center;justify-content:center'>
<div class='pd' style='font-size:84px;color:{GOLD};-webkit-text-stroke:7px #000'>{V.get('pie', 'ASÍ QUE TENÉS CHANCES')}</div></div></div>"""
N = len(V['clips'])
for i in range(1, N + 1):
    SL[f'L{i}'] = f"<div class='pd' style='display:inline-block;font-size:72px;padding:10px 18px;-webkit-text-stroke:8px #000;color:{WHITE}'>CHOQUE <span style='color:{GOLD}'>{i}/{N}</span></div>"
SL['LW'] = f"<div class='pd' style='display:inline-block;font-size:200px;padding:20px 30px;color:{RED};-webkit-text-stroke:12px #000'>WASTED</div>"

def chrome():
    for c in ['/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser']:
        if os.path.exists(c):
            return c
    return None

async def render():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=chrome(), args=['--no-sandbox', '--allow-file-access-from-files'])
        pg = await b.new_page(viewport={'width': 1080, 'height': 1350})
        for n, body in SL.items():
            hp = TMP / f'{n}.html'
            hp.write_text(f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>", encoding='utf-8')
            await pg.goto('file://' + str(hp), wait_until='load'); await pg.evaluate('document.fonts.ready'); await pg.wait_for_timeout(300)
            if n[0] == 'L':
                await pg.locator('body > div').first.screenshot(path=str(TMP / f'{n}.png'), omit_background=True)
            else:
                await pg.screenshot(path=str(TMP / f'{n}.png'), omit_background=(n == 'marco'))
        await b.close()

asyncio.run(render())
for i, n in enumerate(['portada', 'premios', 'como-sumarte'], 1):
    shutil.copy(TMP / f'{n}.png', OUT / f'{PRE}_{i}-{n}.png')

# ---------- Video de choques ----------
VY, VH = 300, 850

def camara(c):
    w, _ = probe(c['video']); s = w / 2560
    return c.get('facecam') or spec.get('facecam') or [int(v * s) for v in (1916, 1078, 644, 362)]

def cara(c, fc):
    if 'cara' in c:
        return c['cara']
    j = TMP / 'caras.json'
    run(['python3', '-I', str(BASE / 'scripts' / 'seguir_cara.py'), c['video'], *[str(v) for v in fc], str(j)])
    a = [r for r in json.load(open(j)) if r[2] < fc[1] + 0.67 * fc[3]]   # descarta la cara del dibujo de la remera
    xs, ys = sorted(r[1] for r in a), sorted(r[2] for r in a)
    return [xs[len(xs) // 2], ys[len(ys) // 2]]

def tramo(i, c):
    w, h = probe(c['video'])
    fc = camara(c); cx, cy = cara(c, fc)
    # recuadro de la cara: 80 % del alto de la cámara, proporción 505:290, dentro de la facecam
    ch = int(fc[3] * 0.8) // 2 * 2; cw = int(ch * 505 / 290) // 2 * 2
    fx = int(min(max(cx - cw / 2, fc[0]), fc[0] + fc[2] - cw)); fy = int(min(max(cy + 0.07 * fc[3] - ch / 2, fc[1]), fc[1] + fc[3] - ch))
    # juego: por encima de la cámara y sin pasar su borde izquierdo
    gh = min(h, fc[1]) // 2 * 2; gw = int(gh * 1080 / VH) // 2 * 2
    gx = int(min(max(w / 2 - gw / 2, 0), w - gw))
    dur = c['dur']; iy = VY + VH - 210 - 20
    ins = ['-ss', str(c['ini']), '-t', str(dur), '-i', c['video'], '-loop', '1', '-i', str(TMP / 'marco.png'),
           '-loop', '1', '-i', str(TMP / f'L{i}.png')]
    f = (f"[0:v]fps=30,split=2[g][c];[g]crop={gw}:{gh}:{gx}:0,scale=1080:{VH},setsar=1[gv];"
         f"[c]crop={cw}:{ch}:{fx}:{fy},scale=352:202,pad=360:210:4:4:color=0xA78BFA[cv];"
         f"color=black:s=1080x1350:r=30:d={dur}[bg];[bg][gv]overlay=0:{VY}[a];[a][cv]overlay=704:{iy}[b];"
         f"[b][1:v]overlay=0:0:shortest=1[o];[o][2:v]overlay=16:{VY + 14}:shortest=1[v]")
    if 'wasted' in c:
        ins += ['-loop', '1', '-i', str(TMP / 'LW.png')]
        t0, t1 = c['wasted']
        f += f";[v][3:v]overlay=(W-w)/2:{VY}+({VH}-h)/2:shortest=1:enable='between(t,{t0},{t1})'[v2]"
        vo = '[v2]'
    else:
        vo = '[v]'
    bips = c.get('bips', [])
    a = "[0:a]aresample=48000,aformat=channel_layouts=stereo" + ''.join(f",volume=0:enable='between(t,{b0},{b1})'" for b0, b1 in bips)
    if bips:
        cond = '+'.join(f'between(t,{b0},{b1})' for b0, b1 in bips)
        a += f"[a0];aevalsrc='0.35*sin(2*PI*1000*t)*({cond})':s=48000:d={dur},aformat=channel_layouts=stereo[bp];[a0][bp]amix=inputs=2:normalize=0[ao]"
    else:
        a += "[ao]"
    out = TMP / f'c{i}.mkv'
    run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', f + ';' + a, '-map', vo, '-map', '[ao]', '-t', str(dur),
         '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'pcm_s16le', str(out)])
    return out

partes = [tramo(i, c) for i, c in enumerate(V['clips'], 1)]
(TMP / 'lista.txt').write_text(''.join(f"file '{p}'\n" for p in partes))
run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(TMP / 'lista.txt'), '-c', 'copy', str(TMP / 'video.mkv')])
run(['ffmpeg', '-v', 'error', '-y', '-i', str(TMP / 'video.mkv'), '-af', 'loudnorm=I=-15:TP=-1.5:LRA=11,volume=-1dB',
     '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-r', '30',
     '-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-movflags', '+faststart', str(OUT / f'{PRE}_4-choques_edit.mp4')])
shutil.rmtree(TMP, ignore_errors=True)
print('Listo:', *sorted(p.name for p in OUT.glob(f'{PRE}_*')), sep='\n  ')
