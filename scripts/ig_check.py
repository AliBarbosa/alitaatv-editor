"""Chequeo de zonas seguras de Instagram Reels sobre un short 1080x1920.
Uso: python3 ig_check.py video.mp4 salida_dir [t1 t2 ...]
Zonas tapadas por la interfaz (aprox., celular 9:16):
  arriba 0-220 (título Reels / cámara), abajo 1540-1920 (usuario, caption, audio),
  derecha x>960 entre y 900-1700 (botones me gusta/comentar/compartir).
Además, la vista de la grilla del perfil recorta a 3:4 centrado (y 240-1680).
Detecta la cara (Haar) en cada cuadro y avisa si queda dentro de una zona tapada."""
import sys, os, subprocess, cv2
v, out = sys.argv[1], sys.argv[2]; ts = [float(x) for x in sys.argv[3:]]
os.makedirs(out, exist_ok=True)
casc = cv2.CascadeClassifier(os.environ.get('HAAR', '/home/claude/models/haar_face.xml'))
SAFE_TOP, SAFE_BOT, RX, RY0, RY1 = 220, 1540, 960, 900, 1700
rep = []
for t in ts:
    p = f"{out}/f_{t:05.2f}.png"
    subprocess.run(["ffmpeg","-v","error","-y","-ss",str(t),"-i",v,"-frames:v","1",p])
    im = cv2.imread(p); g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    fs = casc.detectMultiScale(g, 1.1, 6, minSize=(120,120))
    ov = im.copy()
    cv2.rectangle(ov,(0,0),(1080,SAFE_TOP),(0,0,255),-1)
    cv2.rectangle(ov,(0,SAFE_BOT),(1080,1920),(0,0,255),-1)
    cv2.rectangle(ov,(RX,RY0),(1080,RY1),(0,0,255),-1)
    im2 = cv2.addWeighted(ov,0.35,im,0.65,0)
    cv2.line(im2,(0,240),(1080,240),(0,255,255),3); cv2.line(im2,(0,1680),(1080,1680),(0,255,255),3)
    msgs=[]
    for (x,y,w,h) in fs:
        # la detección va de la frente al mentón; la vincha suma ~35 % arriba
        top, bot = int(y-0.35*h), int(y+h*1.05)
        cv2.rectangle(im2,(x,top),(x+w,bot),(0,255,0),4)
        if bot > SAFE_BOT: msgs.append(f"cara cortada abajo ({bot}>{SAFE_BOT})")
        if top < SAFE_TOP: msgs.append("cara cortada arriba")
        if x+w > RX and bot > RY0 and top < RY1: msgs.append("cara bajo los botones")
    if len(fs)==0: msgs.append("sin cara detectada")
    cv2.imwrite(p, cv2.resize(im2,(360,640)))
    rep.append((t, [(int(x),int(y),int(w),int(h)) for x,y,w,h in fs], msgs or ["OK"]))
for r in rep: print(r)
