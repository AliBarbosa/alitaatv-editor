"""Detecta la cara en la zona de la facecam, 5 veces por segundo. Uso: seguir_cara.py video.mp4 x y w h salida.json"""
import cv2, sys, json, numpy as np
v, x, y, w, h, out = sys.argv[1], *map(int, sys.argv[2:6]), sys.argv[6]
cas = cv2.CascadeClassifier('/home/claude/models/haar_face.xml')
cap = cv2.VideoCapture(v); fps = cap.get(cv2.CAP_PROP_FPS); step = max(1, round(fps / 5))
res = []; i = 0
while True:
    ok, fr = cap.read()
    if not ok: break
    if i % step == 0:
        g = cv2.cvtColor(fr[y:y+h, x:x+w], cv2.COLOR_BGR2GRAY)
        f = cas.detectMultiScale(g, 1.1, 5, minSize=(50, 50))
        if len(f):
            fx, fy, fw, fh = max(f, key=lambda r: r[2]*r[3])
            res.append([round(i/fps, 2), int(x+fx+fw/2), int(y+fy+fh/2), int(fw)])
    i += 1
json.dump(res, open(out, 'w'))
print(len(res), "detecciones de", i//step)
if not res: sys.exit("No se detectó ninguna cara: revisá las coordenadas de la facecam")
a = np.array(res)
print("cx mediana", np.median(a[:,1]), "| cy mediana", np.median(a[:,2]), "| ancho cara", np.median(a[:,3]))
