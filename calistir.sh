#!/bin/sh
# Kullanim: ./calistir.sh baslangic.json komutlar.jsonl > sonuclar.jsonl
# DIZIN bu betigin bulundugu klasor. Once python3 deneniyor (gercekten calisiyor mu diye
# bos bir komutla bakiyoruz, Windows'taki sahte python3 kisayolu yuzunden), olmazsa python.
DIZIN="$(cd "$(dirname "$0")" && pwd)"
if python3 -c "" >/dev/null 2>&1; then
    exec python3 "$DIZIN/komut_satiri.py" "$@"
else
    exec python "$DIZIN/komut_satiri.py" "$@"
fi
