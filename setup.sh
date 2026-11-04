#!/usr/bin/env bash
# Prepara el entorno para editar shorts de AlitaaTV. Uso: bash setup.sh
# Deja: scripts en $BASE/scripts, modelo de Whisper en $BASE/models/whisper-small-int8,
# clasificador de caras en $BASE/models/haar_face.xml y fuentes en $BASE/fonts_all.
set -euo pipefail
BASE="${ALITAA_BASE:-/home/claude}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL="$BASE/models/whisper-small-int8"
SHA="ca732cb1379efc49417d028465f543d83a39de2c61f3027678de103dc404ce73"
mkdir -p "$BASE/scripts" "$BASE/models" "$BASE/fonts_all"

echo "1/6 Paquetes de Python"
pip install -q --break-system-packages faster-whisper opencv-python-headless fonttools pillow numpy playwright

echo "2/6 Scripts"
cp "$REPO"/scripts/*.py "$BASE/scripts/"

echo "3/6 Fuentes"
cp "$REPO"/fonts/*.ttf "$BASE/fonts_all/"

echo "4/6 Clasificador de caras"
[ -s "$BASE/models/haar_face.xml" ] || curl -fsSL -o "$BASE/models/haar_face.xml" \
  https://raw.githubusercontent.com/opencv/opencv/4.x/data/haarcascades/haarcascade_frontalface_default.xml

echo "5/6 Modelo de Whisper (small int8, desde npm: el CDN de Hugging Face está bloqueado)"
if [ -s "$MODEL/model.bin" ] && echo "$SHA  $MODEL/model.bin" | sha256sum -c --quiet 2>/dev/null; then
  echo "   ya estaba"
else
  T="$(mktemp -d)"; mkdir -p "$MODEL"
  for p in 0 1 2 3; do
    (cd "$T" && npm pack -q "@skillninja/shortmovie-telop-model-p$p" >/dev/null)
    mkdir -p "$T/p$p" && tar -xzf "$T"/skillninja-shortmovie-telop-model-p$p-*.tgz -C "$T/p$p"
  done
  cat $(for p in 0 1 2 3; do find "$T/p$p" -name "model.bin.part$p"; done) > "$MODEL/model.bin"
  for f in config.json preprocessor_config.json tokenizer.json vocabulary.json; do
    find "$T" -name "$f" -exec cp {} "$MODEL/" \; -quit
  done
  echo "$SHA  $MODEL/model.bin" | sha256sum -c --quiet || { echo "ERROR: el modelo no coincide con el sha256"; exit 1; }
  rm -rf "$T"
fi

echo "6/6 Pricedown (para el carrusel de eventos; se baja aparte, no se guarda en el repo)"
PD_SHA="07a781257f720802c9ac544a0ed048cc6e6ce2294f81f49301e1846adf2ea186"
if ! { [ -s "$BASE/fonts_all/Pricedown.ttf" ] && echo "$PD_SHA  $BASE/fonts_all/Pricedown.ttf" | sha256sum -c --quiet 2>/dev/null; }; then
  curl -fsSL -o "$BASE/fonts_all/Pricedown.ttf" \
    https://raw.githubusercontent.com/conykevin/Pricedown/3ac84cc/pricedown.ttf || echo "   AVISO: no se pudo bajar Pricedown"
  echo "$PD_SHA  $BASE/fonts_all/Pricedown.ttf" | sha256sum -c --quiet 2>/dev/null || { echo "   AVISO: Pricedown no coincide con el sha256, lo borro"; rm -f "$BASE/fonts_all/Pricedown.ttf"; }
fi
command -v google-chrome >/dev/null || command -v chromium >/dev/null || echo "   AVISO: no hay Chrome/Chromium: carrusel_evento.py no va a poder generar las imágenes"

echo "Listo. Editor: python3 -I $BASE/scripts/editar_short.py spec.json  ·  fonts_dir: $BASE/fonts_all  ·  Carrusel: python3 -I $BASE/scripts/carrusel_evento.py spec.json"
