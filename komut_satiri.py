# Komut satırı girişi, gizli testler bununla çalışacak:
#     calistir.bat baslangic.json komutlar.jsonl > sonuclar.jsonl

import json
import sys

from rezervasyon.kurallar import dosyadan_sistem_olustur

# json.loads satırı sözlüğe, json.dumps sonucu tek satıra çeviriyor.
# sys.stdout.reconfigure: çıktı UTF-8 olsun ve Windows'ta satır sonları \r\n olmasın.


# İki dosya adını sys.argv'den alıyor. Her dolu satır modüle gidiyor, sonuç tek satır JSON olarak
# ekrana basılıyor. Bozuk JSON satırı boş sözlük olarak gidiyor ki yine de bir sonuç satırı çıksın.
# Parametre sayısı yanlışsa 1, değilse 0 döner.
def main():
    if len(sys.argv) != 3:
        print("Kullanim: calistir.bat baslangic.json komutlar.jsonl > sonuclar.jsonl", file=sys.stderr)
        return 1

    sistem = dosyadan_sistem_olustur(sys.argv[1])
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")

    with open(sys.argv[2], "r", encoding="utf-8-sig") as dosya:
        for satir in dosya:
            satir = satir.strip()
            if satir == "":
                continue
            try:
                komut = json.loads(satir)
            except json.JSONDecodeError:
                komut = {}
            sonuc = sistem.komut_calistir(komut)
            # separators ile boşluksuz yazıyoruz, PDF'teki örnek satırlar da böyle
            print(json.dumps(sonuc, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
