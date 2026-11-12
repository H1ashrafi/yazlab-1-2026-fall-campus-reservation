# Kampüs Kaynak Rezervasyon Sistemi (Sürüm 3)

Kocaeli Üniversitesi, Yazılım Laboratuvarı I, Proje 1.
Sadece Python'un kendi kütüphaneleri kullanılıyor, ek kurulum gerekmiyor (Python 3.11 veya üstü).

## Çalıştırma

Komut satırı (gizli testler bu yolla çalışacak):

    calistir.bat baslangic.json komutlar.jsonl > sonuclar.jsonl
    ./calistir.sh baslangic.json komutlar.jsonl > sonuclar.jsonl

Masaüstü uygulaması:

    masaustu_uygulamasi.bat
    python masaustu_uygulamasi.py                          (açılışta başlangıç dosyası sorulur, önerilen
                                                            dosya ornek/baslangic_3_kasim.json: 3 Kasım 2026)
    python masaustu_uygulamasi.py ornek\baslangic.json     (dosya doğrudan verilir)

Kendi testlerimiz (PDF'teki örnek + 7 senaryo, toplam 148 satır):

    python testler\testleri_calistir.py

## Klasörler

    calistir.bat / .sh               komut satırı betikleri (adları PDF'te istendiği gibi)
    komut_satiri.py                  betiklerin çağırdığı dosya: dosyaları okur, sonuç satırlarını yazar
    masaustu_uygulamasi.py / .bat    masaüstü uygulaması (pencere, talep formu, tablolar, günlük)
    rezervasyon/kurallar.py          modülün kendisi, bütün kurallar burada (K1-K11)
    rezervasyon/kural_sabitleri.py   kurallardaki sabit sayılar (15, 30, 60 dk, bantlar, pik saatler)
    rezervasyon/zaman_islemleri.py   zaman yardımcıları (metin <-> zaman, kesişme, ortak dakika)
    arayuz/kaynak_takvimi.py         kaynak takvimi çizimi
    arayuz/renkler_ve_stiller.py     renkler, yazı tipi (Arial) ve ttk stilleri
    arayuz/turkce_metinler.py        hata kodlarının ve durumların Türkçe açıklamaları
    arayuz/logo/                     Kocaeli Üniversitesi logosu
    ornek/                           PDF'teki 19 komutluk örnek senaryo (baslangic.json) ve
                                     3 Kasım 2026'da başlayan deneme dosyası (baslangic_3_kasim.json)
    testler/testleri_calistir.py     kendi testlerimizi çalıştırır
    testler/senaryolar/              kendi test senaryolarımız
    TUM_KODLAR.txt                   bütün kodlar tek dosyada

## Yeni PDF'e göre yapılanlar

- `kullanici_ekle` ve `kaynak_ekle` komutları eklendi. Hata sırası ID_MEVCUT, TANIMSIZ_DEGER, GECERSIZ_DEGER.
  Eklenenler sadece bellekte tutuluyor, başlangıç dosyası değişmiyor.
- K5: türdeki kaynak sayısı talep anında sayılıyor, sonradan eklenen kaynak eklendiği andan itibaren sayılıyor.
- Örnek senaryo 19 komut oldu (u1, u2, YAZ-1, LAB-1 başlangıç dosyasında yok, ilk dört komut ekliyor).
- Arayüz: açılışta dosya seçimi, komut dosyası okuma / sonuç yazma yok, takvimde 15 dakikalık çizgiler,
  simüle saat çizgisi, IPTAL / GELMEDI ile çakışan yeni rezervasyon ayrı alt satırda, Türkçe hata açıklamaları,
  paket reddinde her kalemin kendi satırında sonucu, KESISME / HAZIRLIK_IHLALI sonrası bekleme önerisi,
  takvimden doğrudan giriş / çıkış / iptal, iptal için onay penceresi yok, yeni kullanıcı ve yeni kaynak pencereleri.
