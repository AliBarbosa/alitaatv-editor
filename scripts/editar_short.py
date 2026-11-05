#!/usr/bin/env python3
"""Edita un clip de Twitch (16:9) en un short vertical 1080x1920 con el estilo AlitaaTV.

Uso:  python3 -I editar_short.py spec.json

spec.json (claves; las opcionales tienen valor por defecto):
{
  "input": "/ruta/corte.mp4", "output": "/ruta/salida_edit.mp4",
  "fonts_dir": "/home/claude/fonts_all",   # Montserrat-Black, Montserrat-ExtraBold, LuckiestGuy (busca recursivo)
  "start": 0.0, "end": null,               # segundos dentro del input (null = hasta el final)
  "layout": "split",                       # split | cam | game
  "cam_pos": "bottom",                     # en split: bottom | top
  "game_crop": null,                       # [x,y,w,h]; null = centro
  "game_x": [[16.4, 21.4, 0]],             # corre el recorte del juego en esos tramos (x del original)
  "facecam": [1916, 1038, 644, 402],       # REGLA (Giuly 05/11): en el juego no se ve NADA de la cámara de Ali;
                                           # el recorte del juego se corre para terminar antes de esta x
  "cam_crop": [2036, 1125, 505, 290],      # recorte de la cámara (obligatorio en split/cam)
  "split_y": 1300,                         # alto de la parte de juego en split
  "hook": "EL POLI Y|EL LADRÓN|{ERAN SOCIOS}",   # {} = amarillo, | = salto de línea
  "hook_font": "Luckiest Guy", "hook_size": 165, "hook_outline": 10, "hook_pos": [540, 600], "hook_seconds": 3.0,
  "subs": [[0.0, 1.2, "HOY {VAMOS} A"]],
  "end_text": "SUMATE AL VIVO", "end_seconds": 2.5, "twitch_glyph": null,
  # REGLA (Giuly, 05/11/2026): cámara siempre abajo; el zoom a la cara va DENTRO del cuadro de la cámara
  # con "zooms": [[ini, fin, "cam", 1.35]]. No usar cam_zooms (la cámara grande tapa el juego).
  "shake": [[5.3, 6.0, 14]],               # temblor del juego [ini, fin, px]
  "flash": [[5.35, 0.25]],                 # destello blanco en el juego [ini, duración]
  "sub_size": 80, "sub_outline": 6,        # tamaño y borde de los subtítulos
  "sub_y": null,                           # alto del centro de los subtítulos (por defecto, la unión juego/cámara)
  "sub_margin": 50,                        # márgenes laterales; 130 = no pisan los botones de Instagram
  "cam_focus": [0.5, 0.5],                 # punto fijo del zoom en la cámara (fracción x, y): poné el mentón
  "cam_fit": null,                         # "width": la facecam entera a lo ancho, pegada arriba (cara más arriba y más chica)
  # ZONAS DE INSTAGRAM (Giuly, 05/11/2026): la interfaz tapa y<220, y>1540 y x>960 entre y 900-1700.
  # Con cámara abajo usá split_y 1150 y un cam_crop con la cara al ~30 % del alto del cuadro,
  # cam_focus [0.5, 0.3] y zoom de cámara ≤ 1.25. Verificá con ig_check.py.
  "end_sub": null,                         # línea amarilla arriba del texto de cierre (ej. "VIERNES 19 H ARG")
  "cam_zooms": [[3.55, 4.55, 2289, 1242]], # (no usar) cámara grande centrada en la cara [ini, fin, cara_x, cara_y]
  "cam_zoom_h": 960, "cam_zoom_src_h": 330, "cam_zoom_push": 0.15,
  "zooms": [[4.6, 6.0, "game", 1.3]],      # [ini, fin, cam|game|full, factor, [foco_x, foco_y]?]  foco opcional (fracción)
  "bw": [[21.0, 22.4]],
  "chat": [[2.0, 5.0, "usuario", "y sino {Vladimir}!"]],
  "images": [[6.0, 7.5, "/ruta/meme.png", "center", 700, "pop"]],   # "pop" opcional: rebote + latido
  "sfx": [[14.05, "/ruta/fbi.mp3", -4, 1.75, 0.0]],   # [segundo, archivo, dB, duración?, inicio_en_el_archivo?]
  "crf": 20
}
"""
import json, os, subprocess, sys, glob, tempfile
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
WHITE, YELLOW, BLACK = "&H00FFFFFF", "&H0000E1FF", "&H00000000"   # ASS usa BGR
TWITCH = (145, 70, 255)                                             # #9146FF


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("ffmpeg falló:\n" + r.stderr[-3000:])
    return r


def probe(path):
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
               "stream=width,height:format=duration", "-of", "json", path]).stdout
    d = json.loads(out)
    s = d["streams"][0]
    return s["width"], s["height"], float(d["format"]["duration"])


def find_font(fonts_dir, name):
    hits = glob.glob(os.path.join(fonts_dir, "**", name), recursive=True)
    if not hits:
        sys.exit(f"No encontré la fuente {name} en {fonts_dir}")
    return hits[0]


def ass_text(t):
    """{palabra} -> amarillo, | -> salto de línea. Mayúsculas siempre."""
    out = ""
    for ch in t.upper():
        if ch == "|":
            out += "\\N"
        elif ch == "{":
            out += "{\\c" + YELLOW + "&}"
        elif ch == "}":
            out += "{\\c" + WHITE + "&}"
        else:
            out += ch
    return out


def ts(sec):
    h = int(sec // 3600); m = int(sec % 3600 // 60); s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def build_ass(spec, dur, hook_y, sub_y, path):
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Hook,{spec.get('hook_font', 'Montserrat Black')},{spec.get('hook_size', 92)},{WHITE},{WHITE},{BLACK},&H80000000,{0 if spec.get('hook_font') else 1},0,0,0,100,100,0,0,1,{spec.get('hook_outline', 7)},3,8,40,40,{hook_y},1",
        f"Style: Sub,Montserrat ExtraBold,{spec.get('sub_size', 80)},{WHITE},{WHITE},{BLACK},&H80000000,1,0,0,0,100,100,0,0,1,{spec.get('sub_outline', 6)},3,5,{spec.get('sub_margin', 50)},{spec.get('sub_margin', 50)},0,1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    hook = spec.get("hook")
    if hook:
        hs = min(spec.get("hook_seconds", 3.0), dur)
        pos = spec.get("hook_pos")   # [x, y] = centro del bloque del hook; sin esto va arriba
        tag = f"\\an5\\pos({pos[0]},{pos[1]})" if pos else ""
        # pop-in corto: escala 80% -> 100% en 120 ms
        lines.append(f"Dialogue: 1,{ts(0)},{ts(hs)},Hook,,0,0,0,,{{{tag}\\fscx80\\fscy80\\t(0,120,\\fscx100\\fscy100)}}{ass_text(hook)}")
    czs = spec.get("cam_zooms", []); top_cz = H - int(spec.get("cam_zoom_h", 960)) - 60
    for s, e, txt in spec.get("subs", []):
        y_ = top_cz if any(a - 0.05 <= s < b for a, b, *_ in czs) else sub_y   # suben si está la cámara grande
        lines.append(f"Dialogue: 0,{ts(s)},{ts(min(e, dur))},Sub,,0,0,0,,{{\\pos({W//2},{y_})\\fscx85\\fscy85\\t(0,80,\\fscx100\\fscy100)}}{ass_text(txt)}")
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def pill(text, font_path, glyph=None, size=44):
    f = ImageFont.truetype(font_path, size)
    tw = int(f.getlength(text)); th = size
    gw = th if glyph else 0
    pad = 22
    img = Image.new("RGBA", (tw + gw + pad * 2 + (14 if glyph else 0), th + pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius=img.height // 2, fill=TWITCH + (255,))
    x = pad
    if glyph:
        g = Image.open(glyph).convert("RGBA"); g.thumbnail((gw, gw))
        img.alpha_composite(g, (x, (img.height - g.height) // 2)); x += gw + 14
    d.text((x, img.height // 2), text, font=f, fill="white", anchor="lm")
    return img


def chat_bubble(user, msg, fonts_dir, path):
    """Mensaje del chat: tarjeta violeta oscura, borde violeta, usuario arriba, mensaje en blanco ({} = amarillo)."""
    fu = ImageFont.truetype(find_font(fonts_dir, "Montserrat-ExtraBold.ttf"), 34)
    fm = ImageFont.truetype(find_font(fonts_dir, "Montserrat-Black.ttf"), 54)
    parts, cur, hl = [], "", False
    for ch in msg:
        if ch in "{}":
            if cur: parts.append((cur, hl)); cur = ""
            hl = ch == "{"
        else:
            cur += ch
    if cur: parts.append((cur, hl))
    mw = int(sum(fm.getlength(t) for t, _ in parts))
    av = 96; pad = 30
    wbox = max(mw, int(fu.getlength(user))) + av + pad * 3
    hbox = 150
    img = Image.new("RGBA", (wbox + 8, hbox + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([4, 4, wbox + 3, hbox + 3], radius=28, fill=(28, 12, 52, 235), outline=TWITCH + (255,), width=5)
    cx, cy = 4 + pad, 4 + (hbox - av) // 2
    d.ellipse([cx, cy, cx + av, cy + av], fill=(80, 50, 130, 255))
    d.text((cx + av // 2, cy + av // 2), user[:1].upper(), font=fm, fill="white", anchor="mm")
    x = cx + av + pad
    d.text((x, 30), user, font=fu, fill=(190, 160, 255), anchor="la")
    for t, h in parts:
        d.text((x, 76), t, font=fm, fill=(255, 225, 0) if h else "white", anchor="la")
        x += int(fm.getlength(t))
    img.save(path)
    return img.size


def end_card(spec, fonts_dir, path):
    black = find_font(fonts_dir, "Montserrat-Black.ttf")
    card = Image.new("RGBA", (W, H), (8, 4, 18, 215))          # violeta casi negro, como #10051F
    d = ImageDraw.Draw(card)
    d.text((W // 2, H // 2 - 70), spec.get("end_text", "SUMATE AL VIVO").upper(),
           font=ImageFont.truetype(black, 84), fill="white", anchor="mm",
           stroke_width=4, stroke_fill="black")
    if spec.get("end_sub"):   # segunda línea en amarillo (ej. horario del evento)
        d.text((W // 2, H // 2 - 175), spec["end_sub"].upper(), font=ImageFont.truetype(black, 58),
               fill=(255, 225, 0), anchor="mm", stroke_width=4, stroke_fill="black")
    p = pill("AlitaaTV", find_font(fonts_dir, "Montserrat-ExtraBold.ttf"), spec.get("twitch_glyph"), 60)
    card.alpha_composite(p, ((W - p.width) // 2, H // 2 + 20))
    d.text((W // 2, H // 2 + 20 + p.height + 50), "twitch.tv/alitaatv",
           font=ImageFont.truetype(find_font(fonts_dir, "Montserrat-ExtraBold.ttf"), 40),
           fill=(232, 228, 223), anchor="mm")
    card.save(path)


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    src = spec["input"]; out = spec["output"]; fonts_dir = spec["fonts_dir"]
    sw, sh, sdur = probe(src)
    start = float(spec.get("start", 0)); end = spec.get("end") or sdur
    dur = float(end) - start
    layout = spec.get("layout", "split")
    split_y = int(spec.get("split_y", 1300))
    end_s = float(spec.get("end_seconds", 2.5))

    tmp = tempfile.mkdtemp()
    ass = os.path.join(tmp, "texto.ass"); card = os.path.join(tmp, "cierre.png")
    tag = os.path.join(tmp, "tag.png")

    def crop_expr(box, tw, th):
        if box:
            x, y, w, h = box
            return f"crop={w}:{h}:{x}:{y},scale={tw}:{th}:force_original_aspect_ratio=increase,crop={tw}:{th}"
        return f"scale={tw}:{th}:force_original_aspect_ratio=increase,crop={tw}:{th}"

    def zoom_expr(target, tw, th):
        """Punch-in suave (rampa 0,15 s) en los tramos de spec['zooms'] para ese objetivo."""
        zs = [z for z in spec.get("zooms", []) if z[2] == target]
        if not zs:
            return ""
        terms = "+".join(
            f"between(t,{z_[0]},{z_[1]})*({z_[3]}-1)*min(1,min((t-{z_[0]}),({z_[1]}-t))/0.15)" for z_ in zs)
        z = f"(1+{terms})"
        # punto que queda fijo al hacer zoom (fracción del cuadro). En la cámara: la cara (cam_focus).
        # Cada zoom puede traer su propio foco como 5.º elemento: [ini, fin, "game", 1.4, [fx, fy]]
        dfx, dfy = spec.get("cam_focus", [0.5, 0.5]) if target == "cam" else (0.5, 0.5)
        fx, fy = str(dfx), str(dfy)
        for z_ in zs:
            if len(z_) > 4:
                fx = f"if(between(t,{z_[0]},{z_[1]}),{z_[4][0]},{fx})"
                fy = f"if(between(t,{z_[0]},{z_[1]}),{z_[4][1]},{fy})"
        return (f",scale=w='trunc({tw}*{z}/2)*2':h='trunc({th}*{z}/2)*2':eval=frame"
                f",crop={tw}:{th}:'(iw-{tw})*{fx}':'(ih-{th})*{fy}'")

    def fx_expr(tw, th):
        """Efectos sobre el juego: temblor (shake) y destello blanco (flash), solo en la pantalla del juego."""
        out = ""
        sh_ = spec.get("shake", [])      # [[ini, fin, px]]
        if sh_:
            m = int(max(s[2] for s in sh_)) + 2
            e = "+".join(f"between(t,{a},{b})*{px}" for a, b, px in sh_)
            out += (f",scale={tw + 2 * m}:{th + 2 * m}"
                    f",crop={tw}:{th}:'{m}+({e})*sin(t*83)':'{m}+({e})*cos(t*67)'")
        fl = spec.get("flash", [])       # [[ini, duración]]
        if fl:
            e = "+".join(f"between(t,{a},{a}+{d})*(1-(t-{a})/{d})" for a, d in fl)
            out += f",eq=brightness='min(0.7,0.7*({e}))':eval=frame"
        return out

    if layout == "split":
        if not spec.get("cam_crop"):
            sys.exit("layout split necesita cam_crop")
        cam_h = H - split_y
        top = spec.get("cam_pos", "bottom") == "top"
        gx = spec.get("game_x") or []   # [[ini, fin, x_px_del_original], ...]: corre el recorte del juego en esos tramos
        fc = spec.get("facecam")        # [x, y, w, h] de la facecam en el original: el juego NUNCA la muestra
        if (gx or fc) and not spec.get("game_crop"):
            cw = int(sh * W / split_y) // 2 * 2; cx = (sw - cw) // 2
            xmax = sw - cw
            if fc:
                xmax = min(xmax, int(fc[0]) - cw)   # el borde derecho del recorte termina antes de la facecam
                if xmax < 0:
                    sys.exit("La facecam queda dentro del recorte del juego: subí split_y o usá game_crop")
            clamp = lambda x: max(0, min(int(x), xmax))
            xe = str(clamp(cx))
            for a, b, x in reversed(gx):
                xe = f"if(between(t,{a},{b}),{clamp(x)},{xe})"
            gcrop = f"crop={cw}:{sh}:'{xe}':0,scale={W}:{split_y}"
        else:
            gcrop = crop_expr(spec.get('game_crop'), W, split_y)
        game = f"[g]{gcrop}{zoom_expr('game', W, split_y)}{fx_expr(W, split_y)}[gv];"
        if spec.get("cam_fit") == "width":
            # la cámara ocupa el ancho y queda pegada arriba del cuadro; abajo (lo que tapa Instagram) va fondo oscuro
            x_, y_, w_, h_ = spec["cam_crop"]
            camf = f"crop={w_}:{h_}:{x_}:{y_},scale={W}:-2,pad={W}:{cam_h}:0:0:color=0x10051F,crop={W}:{cam_h}:0:0"
        else:
            camf = crop_expr(spec['cam_crop'], W, cam_h)
        cam = f"[c]{camf}{zoom_expr('cam', W, cam_h)}[cv];"
        order = "[cv][gv]" if top else "[gv][cv]"
        ncz = len(spec.get("cam_zooms", []))
        extra = "".join(f"[cz{i}]" for i in range(ncz))
        vf = f"[0:v]split={2 + ncz}[g][c]{extra};{game}{cam}{order}vstack=2{zoom_expr('full', W, H)}[base]"
        if top:   # cámara arriba, juego abajo
            hook_y, sub_y = cam_h - 60, cam_h + int(split_y * 0.62)
            tag_xy = (30, 240)
            chat_center = (W // 2, cam_h + int(split_y * 0.35))
        else:     # cámara abajo
            hook_y, sub_y = 230, split_y
            tag_xy = (30, split_y + 24)
            chat_center = (W // 2, int(split_y * 0.55))
    elif layout == "cam":
        vf = f"[0:v]{crop_expr(spec.get('cam_crop'), W, H)}{zoom_expr('cam', W, H)}{zoom_expr('full', W, H)}[base]"
        hook_y, sub_y, tag_xy = 230, int(H * 0.62), (30, H - 140)
        chat_center = (W // 2, int(H * 0.45))
    else:
        vf = f"[0:v]{crop_expr(spec.get('game_crop'), W, H)}{zoom_expr('game', W, H)}{zoom_expr('full', W, H)}[base]"
        hook_y, sub_y, tag_xy = 230, int(H * 0.62), (30, H - 140)
        chat_center = (W // 2, int(H * 0.45))

    cnt = [0]
    def nxt():
        """Etiqueta nueva para la cadena de video: [base] -> [b1] -> [b2] ..."""
        cur = "base" if cnt[0] == 0 else f"b{cnt[0]}"
        cnt[0] += 1
        return cur, f"b{cnt[0]}"

    for a, b in spec.get("bw", []):
        i_, o_ = nxt(); vf += f";[{i_}]hue=s=0:enable='between(t,{a},{b})'[{o_}]"

    sub_y = int(spec.get("sub_y", sub_y))   # p. ej. split_y - 120: sobre el juego (oscuro), no sobre la pared clara de la cámara
    build_ass(spec, dur, hook_y, sub_y, ass)
    end_card(spec, fonts_dir, card)
    pill("AlitaaTV", find_font(fonts_dir, "Montserrat-ExtraBold.ttf"), spec.get("twitch_glyph"), 34).save(tag)

    inputs = ["-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", src,
              "-loop", "1", "-t", f"{dur:.3f}", "-i", tag,
              "-loop", "1", "-t", f"{dur:.3f}", "-i", card]
    n = 3
    fs = max(dur - end_s, 0)
    i_, o_ = nxt(); vf += f";[{i_}][1:v]overlay={tag_xy[0]}:{tag_xy[1]}:enable='lt(t,{fs:.2f})'[{o_}]"

    # cámara grande que sigue la cara: crece desde la unión y tapa parte del juego, con un push-in lento
    LH = int(spec.get("cam_zoom_h", 960)); SH = int(spec.get("cam_zoom_src_h", 330))
    SW = int(round(SH * W / LH)); push = float(spec.get("cam_zoom_push", 0.15)); y0 = int(spec.get("split_y", 1300))
    for i, (a, b, cx, cy) in enumerate(spec.get("cam_zooms", [])):
        x = min(max(int(cx - SW / 2), 0), sw - SW); y = min(max(int(cy + 20 - SH / 2), 0), sh - SH)
        z = f"(1+{push}*min(1,max(0,(t-{a})/({b}-{a}))))"
        bwz = "".join(f",hue=s=0:enable='between(t,{p},{q})'" for p, q in spec.get("bw", []))
        vf += (f";[cz{i}]crop={SW}:{SH}:{x}:{y},scale={W}:{LH}:flags=lanczos"
               f",scale=w='trunc({W}*{z}/2)*2':h='trunc({LH}*{z}/2)*2':eval=frame,crop={W}:{LH}:'(iw-{W})/2':'(ih-{LH})/2'"
               f",drawbox=x=0:y=0:w=iw:h=10:color=0x9146FF:t=fill{bwz}[czv{i}]")
        p_ = f"min(1,min((t-{a}),({b}-t))/0.18)"
        i_, o_ = nxt()
        vf += f";[{i_}][czv{i}]overlay=x=0:y='{H - LH}+({y0}-{H - LH})*(1-{p_})':eval=frame:enable='between(t,{a},{b})'[{o_}]"

    # mensajes del chat (entran con un pop corto)
    for i, (a, b, user, msg) in enumerate(spec.get("chat", [])):
        p = os.path.join(tmp, f"chat{i}.png"); bw_, bh_ = chat_bubble(user, msg, fonts_dir, p)
        inputs += ["-loop", "1", "-t", f"{dur:.3f}", "-i", p]
        x, y = chat_center[0] - bw_ // 2, chat_center[1] - bh_ // 2
        i_, o_ = nxt()
        vf += f";[{n}:v]format=rgba,fade=t=in:st={a}:d=0.15:alpha=1[ch{i}];[{i_}][ch{i}]overlay={x}:{y}:enable='between(t,{a},{b})'[{o_}]"
        n += 1

    # memes / imágenes
    for i, im in enumerate(spec.get("images", [])):
        a, b, path, pos, width = im[:5]
        pop = len(im) > 5 and im[5] == "pop"   # entrada con rebote + latido suave
        inputs += ["-loop", "1", "-t", f"{dur:.3f}", "-i", path]
        if pos == "center":
            xy = f"(W-w)/2:(H-h)/2"
        elif pos == "top":
            xy = f"(W-w)/2:{hook_y + 260}"
        else:
            xy = pos                      # "x:y" literal
        i_, o_ = nxt()
        if pop:
            k = f"(if(lt(t-{a},0.25),0.6+0.5*(t-{a})/0.25,if(lt(t-{a},0.4),1.1-0.1*(t-{a}-0.25)/0.15,1+0.04*sin((t-{a})*9))))"
            sc = f"scale=w='trunc({int(width)}*{k}/2)*2':h=-2:eval=frame"
        else:
            sc = f"scale={int(width)}:-1"
        vf += f";[{n}:v]format=rgba,{sc}[im{i}];[{i_}][im{i}]overlay={xy}:eval=frame:enable='between(t,{a},{b})'[{o_}]"
        n += 1

    font_esc = os.path.dirname(find_font(fonts_dir, "Montserrat-Black.ttf")).replace("\\", "/").replace(":", "\\:")
    last = f"b{cnt[0]}" if cnt[0] else "base"
    vf += (f";[{last}]ass='{ass}':fontsdir='{font_esc}'[t2]"
           f";[2:v]format=rgba,fade=t=in:st={fs:.2f}:d=0.35:alpha=1[cd]"
           f";[t2][cd]overlay=0:0:enable='gte(t,{fs:.2f})',fps=30,format=yuv420p[v]")
    vmax = int(max(1500, min(6000, 28 * 8 * 1000 / dur - 170)))

    # audio: voz/juego normalizado + efectos de sonido (con recorte opcional)
    af = f"[0:a]loudnorm=I=-14:TP=-1.5:LRA=11[main]"
    mix = ["[main]"]
    for i, fx in enumerate(spec.get("sfx", [])):
        t0, path, gain = fx[:3]
        d_ = float(fx[3]) if len(fx) > 3 and fx[3] else None; off = float(fx[4]) if len(fx) > 4 else 0.0
        inputs += ["-i", path]
        ms = int(float(t0) * 1000)
        trim = f"atrim={off}:{off + d_},asetpts=PTS-STARTPTS,afade=t=out:st={max(d_ - 0.25, 0)}:d=0.25," if d_ else (f"atrim=start={off},asetpts=PTS-STARTPTS," if off else "")
        af += f";[{n}:a]{trim}aresample=48000,aformat=channel_layouts=stereo,loudnorm=I=-16:TP=-2,volume={gain}dB,adelay={ms}|{ms}[fx{i}]"
        mix.append(f"[fx{i}]"); n += 1
    if len(mix) > 1:
        af += f";{''.join(mix)}amix=inputs={len(mix)}:duration=first:normalize=0,alimiter=limit=0.89[mx]"
    else:
        af += ";[main]anull[mx]"
    af += f";[mx]afade=t=out:st={max(dur-0.6,0):.2f}:d=0.6[a]"

    cmd = ["ffmpeg", "-y", "-v", "error", *inputs,
           "-filter_complex", vf + ";" + af, "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", str(spec.get("crf", 20)),
           # techo de bitrate para que el archivo quede por debajo de ~28 MB (límite de 30 MB al devolverlo a la PC)
           "-maxrate", f"{vmax}k", "-bufsize", f"{vmax * 2}k",
           "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", out]
    run(cmd)
    print(json.dumps({"output": out, "duracion": round(dur, 2), "layout": layout}))


if __name__ == "__main__":
    main()
