import sys, json, wave, numpy as np
from faster_whisper import WhisperModel
# uso: python3 transcribir.py audio.wav salida.json   (wav mono 16 kHz: ffmpeg -i video -ac 1 -ar 16000 audio.wav)
# se le pasa el audio como array: con la versión de av instalada, pasarle el archivo falla
m = WhisperModel('/home/claude/models/whisper-small-int8', device='cpu', compute_type='int8')
wv = wave.open(sys.argv[1]); a = np.frombuffer(wv.readframes(wv.getnframes()), np.int16).astype(np.float32) / 32768
segs, info = m.transcribe(a, language='es', word_timestamps=True, vad_filter=True, beam_size=5)
out = []
for s in segs:
    print(f"[{s.start:6.2f}-{s.end:6.2f}] {s.text}")
    out.append({"start": s.start, "end": s.end, "text": s.text,
                "words": [{"w": w.word, "s": w.start, "e": w.end, "p": w.probability} for w in s.words]})
json.dump(out, open(sys.argv[2], 'w'), ensure_ascii=False, indent=1)
