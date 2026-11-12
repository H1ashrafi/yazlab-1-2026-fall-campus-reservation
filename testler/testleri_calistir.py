# Kendi test senaryolarımız. python testler/testleri_calistir.py ile çalışıyor.
# Her klasörde baslangic.json, komutlar.jsonl, beklenen.jsonl var.

import json
import os
import sys

# os ile klasörleri buluyoruz, sys.path'e proje klasörünü ekliyoruz ki rezervasyon paketi bulunsun.

TEST_KLASORU = os.path.dirname(os.path.abspath(__file__))
PROJE_KOKU = os.path.dirname(TEST_KLASORU)
sys.path.insert(0, PROJE_KOKU)

from rezervasyon.kurallar import dosyadan_sistem_olustur


# Beklenen ile üretilen sonucu alan alan karşılaştırır, iç içe yapılarda kendini tekrar çağırıyor.
# Fazla alan sorun değil (PDF öyle diyor), eksik ya da farklı olan her şey listeye yazılıyor.
def farklari_bul(beklenen, uretilen, yol):
    farklar = []
    if isinstance(beklenen, dict):
        if not isinstance(uretilen, dict):
            return [yol + ": sozluk bekleniyordu"]
        for anahtar in beklenen:
            if anahtar not in uretilen:
                farklar.append(yol + "." + anahtar + ": EKSIK ALAN")
            else:
                farklar += farklari_bul(beklenen[anahtar], uretilen[anahtar], yol + "." + anahtar)
    elif isinstance(beklenen, list):
        if not isinstance(uretilen, list) or len(beklenen) != len(uretilen):
            return [yol + ": liste farkli, beklenen " + json.dumps(beklenen, ensure_ascii=False) +
                    " uretilen " + json.dumps(uretilen, ensure_ascii=False)]
        for i in range(len(beklenen)):
            farklar += farklari_bul(beklenen[i], uretilen[i], yol + "[" + str(i) + "]")
    elif beklenen != uretilen:
        farklar.append(yol + ": beklenen " + repr(beklenen) + " uretilen " + repr(uretilen))
    return farklar


# .jsonl dosyasını satır satır okuyup sözlük listesi yapar
def satirlari_oku(dosya_yolu):
    satirlar = []
    with open(dosya_yolu, "r", encoding="utf-8-sig") as dosya:
        for satir in dosya:
            if satir.strip() != "":
                satirlar.append(json.loads(satir))
    return satirlar


# Bir klasörü çalıştırır, (geçen satır, toplam satır, hata mesajları) döner.
def senaryo_calistir(klasor):
    sistem = dosyadan_sistem_olustur(os.path.join(klasor, "baslangic.json"))
    komutlar = satirlari_oku(os.path.join(klasor, "komutlar.jsonl"))
    beklenenler = satirlari_oku(os.path.join(klasor, "beklenen.jsonl"))
    gecen = 0
    mesajlar = []
    for komut, beklenen in zip(komutlar, beklenenler):
        uretilen = sistem.komut_calistir(komut)
        farklar = farklari_bul(beklenen, uretilen, "satir " + str(beklenen.get("no")))
        if len(farklar) == 0:
            gecen += 1
        else:
            mesajlar += farklar
    if len(komutlar) != len(beklenenler):
        mesajlar.append("komut sayisi (" + str(len(komutlar)) + ") ile beklenen satir sayisi (" +
                        str(len(beklenenler)) + ") farkli")
    return gecen, len(beklenenler), mesajlar


# önce ornek klasörü, sonra senaryolar; hepsi geçerse 0 döner
def main():
    klasorler = [os.path.join(PROJE_KOKU, "ornek")]
    senaryo_dizini = os.path.join(TEST_KLASORU, "senaryolar")
    for ad in sorted(os.listdir(senaryo_dizini)):
        tam_yol = os.path.join(senaryo_dizini, ad)
        if os.path.isdir(tam_yol):
            klasorler.append(tam_yol)

    toplam_gecen = 0
    toplam_satir = 0
    for klasor in klasorler:
        gecen, toplam, mesajlar = senaryo_calistir(klasor)
        toplam_gecen += gecen
        toplam_satir += toplam
        if len(mesajlar) == 0:
            durum = "GECTI"
        else:
            durum = "KALDI"
        ad = os.path.basename(klasor)
        print(f"{ad:34} {gecen:3}/{toplam:<3} {durum}")
        for mesaj in mesajlar:
            print("    - " + mesaj)
    print("-" * 46)
    print(f"{'TOPLAM':34} {toplam_gecen:3}/{toplam_satir:<3}")
    if toplam_gecen == toplam_satir:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
