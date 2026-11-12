# Rezervasyon modülü, kuralların hepsi burada.
# Arayüzden bağımsız: komut_satiri.py de masaustu_uygulamasi.py de aynı RezervasyonSistemi'ni
# kullanıyor, yani iki yolda da aynı kurallar çalışıyor. Her komut komut_calistir'dan giriyor.
# Veriler sadece bellekte, başlangıç dosyasına hiçbir şey yazılmıyor.
#
# Hangi kural nerede (sınavda lazım olur):
# K1-K4 ve K10 sırası dogrula'da, K5 ucret_dilimleri'nde, K6 rezervasyon_ekle / iade_ekle'de,
# K7 komut_paket'te, K8 komut_giris / cikis / iptal ve ani_isle'de, K9 komut_bekleme ve
# bekleme_tara'da, K11 saati_ilerlet ve ani_isle'de. Yeni PDF'teki ekleme komutları en altta.

import json
from datetime import timedelta
from fractions import Fraction

from rezervasyon import kural_sabitleri as S
from rezervasyon.zaman_islemleri import (dakika_farki, gun_metnini_cevir, kesisiyor_mu,
                                         metni_zamana_cevir, ortak_dakika, sonraki_pazartesi,
                                         zamani_metne_cevir)

# json: sadece json.load, başlangıç dosyasını okumak için.
# timedelta: saate dakika / gün eklemek için.
# Fraction: ücret kesirli çıkıyor (0,25 x 1,75 x 1,5 gibi). float ile küçük hatalar olabiliyor
# ve "tam 0,5 ise yukarı" kuralı bozulabiliyordu, Fraction'da hesap tam.
# kural_sabitleri ve zaman_islemleri bizim dosyalarımız.


# Sayıyı Fraction yapar. str'den geçirince 1.5 tam olarak 3/2 oluyor, float hatası kalmıyor.
def kesir(sayi):
    return Fraction(str(sayi))


# K5'teki yuvarlama: 0,5 ekleyip int() alınca 2,5 -> 3, 2,4 -> 2 oluyor.
# int() aşağı kırpıyor ama ücret hiç eksi olmadığı için sorun çıkmıyor. Fraction alır, int verir.
def yuvarla(deger):
    return int(deger + Fraction(1, 2))


# {"durum": "RED", "kod": kod} döner, her yerde aynı sözlüğü yazmamak için
def red(kod):
    return {"durum": S.RED, "kod": kod}


# sort için anahtar: kaydın baslangic değeri
def baslangica_gore(kayit):
    return kayit["baslangic"]


# sort anahtarı, önce başlangıç sonra rezervasyon numarası (sorgu kullanici böyle sıralanıyor)
def baslangic_ve_numara(rez):
    return (rez["baslangic"], rez["no"])


# Dosya yolunu alır, JSON'u okuyup RezervasyonSistemi nesnesi döner. Dosya yoksa ya da bozuksa
# hata fırlatıyor, onu çağıran taraf (komut_satiri.py, arayüz) kendisi yakalıyor.
def dosyadan_sistem_olustur(dosya_yolu):
    with open(dosya_yolu, "r", encoding="utf-8-sig") as dosya:
        veri = json.load(dosya)
    return RezervasyonSistemi(veri)


class RezervasyonSistemi:

    # baslangic_verisi json.load'dan gelen sözlük. Türler, roller, kaynaklar, bakımlar, kullanıcılar
    # ve saat hep buradan okunuyor, koda sabit yazılmıyor. Yani dosyada kota ya da hazırlık süresi
    # değişirse program kod değişmeden yeni değerle çalışıyor (PDF Bölüm 7, demoda bakılacak).
    def __init__(self, baslangic_verisi):
        self.saat = metni_zamana_cevir(baslangic_verisi["saat"])
        self.turler = baslangic_verisi["kaynak_turleri"]
        self.roller = baslangic_verisi["roller"]

        # kaynak ve kullanıcıları id ile hızlı bulmak için sözlükte tutuyoruz
        self.kaynaklar = {}
        for kaynak in baslangic_verisi.get("kaynaklar", []):
            self.kaynaklar[kaynak["id"]] = kaynak

        self.bakimlar = []
        for bakim in baslangic_verisi.get("bakim_pencereleri", []):
            self.bakimlar.append({
                "kaynak": bakim["kaynak"],
                "baslangic": metni_zamana_cevir(bakim["baslangic"]),
                "bitis": metni_zamana_cevir(bakim["bitis"]),
            })

        # dict() ile kopyalıyoruz, bakiye değişince dosyadan gelen sözlük bozulmasın
        self.kullanicilar = {}
        for kullanici in baslangic_verisi.get("kullanicilar", []):
            self.kullanicilar[kullanici["id"]] = dict(kullanici)

        self.rezervasyonlar = {}
        self.beklemeler = {}

        # r1, r2 / b1, b2 / p1, p2 numaraları ve sonuçtaki "no" alanı için sayaçlar
        self.rez_sayac = 0
        self.bek_sayac = 0
        self.paket_sayac = 0
        self.komut_sayac = 0

        # her komut ve sonucu buraya ekleniyor, arayüzdeki olay günlüğü bunu gösteriyor
        self.gunluk = []

    # Her komut buradan giriyor. komut bir sözlük, "komut" alanına bakıp ilgili fonksiyona
    # yolluyoruz. Dönen cevaba no ve komut alanlarını ekleyip günlüğe de yazıyoruz.
    # Alan eksik ya da tipi yanlışsa program çökmesin diye hatayı yakalayıp GECERSIZ_KOMUT veriyoruz.
    # komut_satiri.py, arayüz ve testler hep bunu çağırıyor.
    def komut_calistir(self, komut):
        self.komut_sayac += 1

        komut_adi = None
        if isinstance(komut, dict):
            komut_adi = komut.get("komut")

        try:
            if komut_adi == "saat":
                govde = self.komut_saat(komut)
            elif komut_adi == "rezervasyon":
                govde = self.komut_rezervasyon(komut)
            elif komut_adi == "paket":
                govde = self.komut_paket(komut)
            elif komut_adi == "fiyat":
                govde = self.komut_fiyat(komut)
            elif komut_adi == "iptal":
                govde = self.komut_iptal(komut)
            elif komut_adi == "giris":
                govde = self.komut_giris(komut)
            elif komut_adi == "cikis":
                govde = self.komut_cikis(komut)
            elif komut_adi == "bekleme":
                govde = self.komut_bekleme(komut)
            elif komut_adi == "sorgu":
                govde = self.komut_sorgu(komut)
            elif komut_adi == "kullanici_ekle":
                govde = self.komut_kullanici_ekle(komut)
            elif komut_adi == "kaynak_ekle":
                govde = self.komut_kaynak_ekle(komut)
            else:
                govde = red("GECERSIZ_KOMUT")
        except (KeyError, TypeError, ValueError, AttributeError):
            govde = red("GECERSIZ_KOMUT")

        sonuc = {"no": self.komut_sayac, "komut": komut_adi}
        sonuc.update(govde)
        self.gunluk.append({"komut": komut, "sonuc": sonuc})
        return sonuc


    # Kaç gün ilerisi için rezervasyon yapılabilir: normalde rolün ileri_gun değeri,
    # güvenilirlik 50'nin altındaysa 1 gün.
    def ileri_gun_siniri(self, kullanici):
        if kullanici["guvenilirlik"] < S.GUV_ESIK:
            return S.DUSUK_GUV_ILERI_GUN
        return self.roller[kullanici["rol"]]["ileri_gun"]

    # K10'daki 13 adımlık kontrol. İlk tutmayan adımın kodunu döndürür, gerisine bakmaz.
    # Dönüş (hata_kodu, ucret): her şey tamamsa hata_kodu None. Ücret ancak 13. adıma gelindiyse
    # hesaplanıyor, daha önce takıldıysa None.
    # bakiye_bak=False olunca bakiye bakılmıyor (fiyat, paket kalemi, bekleme).
    # cakisma_bak=False sadece bekleme komutunun ilk turunda, KESISME / HAZIRLIK dışında
    # bir sorun var mı diye bakmak için.
    def dogrula(self, kullanici_id, kaynak_id, bas, bit, bakiye_bak=True, cakisma_bak=True):
        kullanici = self.kullanicilar.get(kullanici_id)
        kaynak = self.kaynaklar.get(kaynak_id)

        # 1. BULUNAMADI
        if kullanici is None or kaynak is None:
            return "BULUNAMADI", None

        # 2. ZAMAN_ADIMI_HATASI: :00 :15 :30 :45 dışı veya bitiş başlangıçtan önce
        if bas is None or bit is None:
            return "ZAMAN_ADIMI_HATASI", None
        if bas.minute % S.ADIM_DK != 0 or bit.minute % S.ADIM_DK != 0 or bit <= bas:
            return "ZAMAN_ADIMI_HATASI", None

        # 3. GECMIS_ZAMAN
        if bas < self.saat:
            return "GECMIS_ZAMAN", None

        # 4. CALISMA_SAATI_DISI: aynı günün 08:00-22:00 arası (gün aşarsa bitiş 22:00'ı geçer)
        acilis = bas.replace(hour=S.CALISMA_BASLANGIC_SAAT, minute=0)
        kapanis = bas.replace(hour=S.CALISMA_BITIS_SAAT, minute=0)
        if bas < acilis or bit > kapanis:
            return "CALISMA_SAATI_DISI", None

        # 5. SURE_SINIRI: en az 30 dk, en çok rolün azami_sure_dk değeri
        rol = self.roller[kullanici["rol"]]
        sure = dakika_farki(bas, bit)
        if sure < S.EN_AZ_SURE_DK or sure > rol["azami_sure_dk"]:
            return "SURE_SINIRI", None

        # 6. ILERI_TARIH_SINIRI: başlangıç, simüle saat + ileri_gun x 24 saati geçemez
        sinir = self.saat + timedelta(days=self.ileri_gun_siniri(kullanici))
        if bas > sinir:
            return "ILERI_TARIH_SINIRI", None

        # 7. ROL_IZNI_YOK
        if kullanici["rol"] not in kaynak["izinli_roller"]:
            return "ROL_IZNI_YOK", None

        # 8. SERTIFIKA_YOK
        tur = self.turler[kaynak["tur"]]
        gereken_sertifika = tur.get("sertifika")
        if gereken_sertifika and gereken_sertifika not in kullanici.get("sertifikalar", []):
            return "SERTIFIKA_YOK", None

        # 9. BAKIM (K2): bakımdan sonra hazırlık süresi yok, sadece kesişmeye bakıyoruz
        for bakim in self.bakimlar:
            if bakim["kaynak"] == kaynak_id:
                if kesisiyor_mu(bas, bit, bakim["baslangic"], bakim["bitis"]):
                    return "BAKIM", None

        if cakisma_bak:
            # 10. KESISME (K3): sadece ONAYLI ve KULLANIMDA rezervasyonlarla
            for rez in self.rezervasyonlar.values():
                if rez["kaynak"] == kaynak_id and rez["durum"] in S.AKTIF_DURUMLAR:
                    if kesisiyor_mu(bas, bit, rez["baslangic"], rez["bitis"]):
                        return "KESISME", None

            # 11. HAZIRLIK_IHLALI (K3): b < e' + h ve e + h > b'. TAMAMLANDI da sayılıyor
            hazirlik = timedelta(minutes=tur["hazirlik_dk"])
            for rez in self.rezervasyonlar.values():
                if rez["kaynak"] == kaynak_id and rez["durum"] in S.HAZIRLIK_DURUMLARI:
                    if bas < rez["bitis"] + hazirlik and bit + hazirlik > rez["baslangic"]:
                        return "HAZIRLIK_IHLALI", None

        # 12. ARDISIK_KULLANIM (K4): aynı kişi, aynı kaynak, arada 60 dk'dan az boşluk
        bosluk = timedelta(minutes=S.ARDISIK_BOSLUK_DK)
        for rez in self.rezervasyonlar.values():
            if rez["kaynak"] == kaynak_id and rez["kullanici"] == kullanici_id:
                if rez["durum"] in S.HAZIRLIK_DURUMLARI:
                    if bas < rez["bitis"] + bosluk and bit + bosluk > rez["baslangic"]:
                        return "ARDISIK_KULLANIM", None

        # 13. BAKIYE_YETERSIZ (K6)
        ucret = self.ucret_hesapla(kaynak_id, bas, bit)
        if bakiye_bak and ucret > kullanici["bakiye"]:
            return "BAKIYE_YETERSIZ", ucret

        return None, ucret


    # Verilen saat hangi 2 saatlik banda düşüyor (08-10, 10-12 ...)? Bandın başını ve sonunu döner.
    def bant_bul(self, zaman):
        acilis = zaman.replace(hour=S.CALISMA_BASLANGIC_SAAT, minute=0)
        kacinci = dakika_farki(acilis, zaman) // S.BANT_DK
        bant_bas = acilis + timedelta(minutes=kacinci * S.BANT_DK)
        bant_bit = bant_bas + timedelta(minutes=S.BANT_DK)
        return bant_bas, bant_bit

    # Bir türün o banttaki dolu dakikası. O türdeki bütün kaynaklara bakıyoruz, sadece ONAYLI ve
    # KULLANIMDA sayılıyor. Talebin kendisi henüz eklenmediği için zaten sayılmıyor.
    def dolu_dakika(self, tur_adi, bant_bas, bant_bit):
        toplam = 0
        for rez in self.rezervasyonlar.values():
            if rez["durum"] in S.AKTIF_DURUMLAR:
                if self.kaynaklar[rez["kaynak"]]["tur"] == tur_adi:
                    toplam += ortak_dakika(rez["baslangic"], rez["bitis"], bant_bas, bant_bit)
        return toplam

    # Ücretin asıl hesaplandığı yer (K5). Talep 15 dakikalık dilimlere bölünüyor:
    #   dilim = temel_ucret x 0,25 x bant çarpanı x pik çarpanı
    #   bant çarpanı = 1 + 0,25 x taban(4 x doluluk), doluluk = dolu dk / (kaynak sayısı x 120)
    # Kaynak sayısı talep anında sayılıyor, kaynak_ekle ile gelen kaynak hemen hesaba giriyor.
    # Her dilim için bir sözlük olan liste döner. Arayüz de "Fiyatı Gör"de bunu dilim dilim
    # gösteriyor.
    def ucret_dilimleri(self, kaynak_id, bas, bit):
        tur_adi = self.kaynaklar[kaynak_id]["tur"]
        tur = self.turler[tur_adi]

        kaynak_sayisi = 0
        for kaynak in self.kaynaklar.values():
            if kaynak["tur"] == tur_adi:
                kaynak_sayisi += 1
        kapasite = kaynak_sayisi * S.BANT_DK

        # 15 dakikalık bir dilimin çarpansız fiyatı (saatlik ücretin dörtte biri)
        dilim_temel = kesir(tur["temel_ucret"]) * Fraction(S.ADIM_DK, 60)

        dilimler = []
        an = bas
        while an < bit:
            bant_bas, bant_bit = self.bant_bul(an)
            dolu = self.dolu_dakika(tur_adi, bant_bas, bant_bit)

            # taban(4 x dolu / kapasite) tam sayı bölmesiyle aynı şey; doluluk 1'i geçse de en çok 2,00
            kademe = (4 * dolu) // kapasite
            if kademe > 4:
                kademe = 4
            bant_carpani = 1 + Fraction(kademe, 4)

            pik_carpani = Fraction(1)
            if tur["enerji_yogun"] and S.PIK_BASLANGIC_SAAT <= an.hour < S.PIK_BITIS_SAAT:
                pik_carpani = kesir(S.PIK_CARPANI)

            dilimler.append({
                "baslangic": an,
                "bant_baslangic": bant_bas,
                "bant_bitis": bant_bit,
                "dolu_dk": dolu,
                "kapasite_dk": kapasite,
                "bant_carpani": bant_carpani,
                "pik_carpani": pik_carpani,
                "tutar": dilim_temel * bant_carpani * pik_carpani,
            })
            an = an + timedelta(minutes=S.ADIM_DK)
        return dilimler

    # dilimleri toplayıp yuvarlar, ücret (int)
    def ucret_hesapla(self, kaynak_id, bas, bit):
        toplam = Fraction(0)
        for dilim in self.ucret_dilimleri(kaynak_id, bas, bit):
            toplam += dilim["tutar"]
        return yuvarla(toplam)


    # Yeni rezervasyonu ONAYLI olarak kaydeder, ücreti hemen bakiyeden düşer.
    # paket_id paketten geliyorsa dolu, yoksa None. Oluşan rezervasyon sözlüğünü döner.
    def rezervasyon_ekle(self, kullanici_id, kaynak_id, bas, bit, ucret, paket_id=None):
        self.rez_sayac += 1
        rez = {
            "id": "r" + str(self.rez_sayac),
            "no": self.rez_sayac,
            "kullanici": kullanici_id,
            "kaynak": kaynak_id,
            "baslangic": bas,
            "bitis": bit,
            "ucret": ucret,
            "durum": S.ONAYLI,
            "paket": paket_id,
        }
        self.rezervasyonlar[rez["id"]] = rez
        self.kullanicilar[kullanici_id]["bakiye"] -= ucret
        return rez

    # güvenilirliğe fark ekler ama 0-100 dışına çıkarmaz
    def guvenilirlik_degistir(self, kullanici, fark):
        yeni = kullanici["guvenilirlik"] + fark
        if yeni < S.GUV_EN_AZ:
            yeni = S.GUV_EN_AZ
        if yeni > S.GUV_EN_COK:
            yeni = S.GUV_EN_COK
        kullanici["guvenilirlik"] = yeni

    # İadeyi bakiyeye ekler. Bakiye kotayı geçemiyor, fazlası yanıyor (K6). Gerçekten eklenen
    # miktarı döndürüyoruz, çünkü sonuçtaki "iade" alanı o.
    def iade_ekle(self, kullanici, miktar):
        kota = self.roller[kullanici["rol"]]["haftalik_kota"]
        bos_yer = kota - kullanici["bakiye"]
        if bos_yer < 0:
            bos_yer = 0
        eklenen = min(miktar, bos_yer)
        kullanici["bakiye"] += eklenen
        return eklenen


    # Bekleme sırası için sort anahtarı: (-güvenilirlik, kayıt saati, numara). Eksi koyunca yüksek
    # güvenilirlik öne geçiyor. Numara int olduğu için b2, b10'dan önce geliyor.
    def bekleme_onceligi(self, kayit):
        guv = self.kullanicilar[kayit["kullanici"]]["guvenilirlik"]
        return (-guv, kayit["kayit_saati"], kayit["no"])

    # bir kaynağın bekleme kayıtları, öncelik sırasıyla
    def bekleme_sirasi(self, kaynak_id):
        liste = []
        for kayit in self.beklemeler.values():
            if kayit["kaynak"] == kaynak_id:
                liste.append(kayit)
        liste.sort(key=self.bekleme_onceligi)
        return liste

    # Başlangıcı saatin gerisinde kalmış bekleme kayıtlarını siler (K9'un son maddesi).
    def eski_beklemeleri_sil(self):
        silinecekler = []
        for kayit in self.beklemeler.values():
            if kayit["baslangic"] < self.saat:
                silinecekler.append(kayit["id"])
        for bekleme_id in silinecekler:
            del self.beklemeler[bekleme_id]

    # Yer boşalınca (iptal, gelmeme, çıkış) o kaynağın bekleme listesini baştan sona dolaşır.
    # Her kayıt o anki saat ve bakiyeyle dogrula'dan geçiyor. Geçen rezervasyona dönüşüyor, geçemeyen
    # listede kalıyor. OTOMATIK_ATAMA olaylarının listesini döner, atama yoksa boş liste.
    def bekleme_tara(self, kaynak_id):
        self.eski_beklemeleri_sil()
        olaylar = []
        for kayit in self.bekleme_sirasi(kaynak_id):
            hata, ucret = self.dogrula(kayit["kullanici"], kaynak_id, kayit["baslangic"], kayit["bitis"])
            if hata is not None:
                continue
            rez = self.rezervasyon_ekle(kayit["kullanici"], kaynak_id, kayit["baslangic"], kayit["bitis"], ucret)
            del self.beklemeler[kayit["id"]]
            olaylar.append({
                "zaman": zamani_metne_cevir(self.saat),
                "tur": S.OTOMATIK_ATAMA,
                "bekleme": kayit["id"],
                "rezervasyon": rez["id"],
                "kullanici": kayit["kullanici"],
                "ucret": ucret,
                "bakiye": self.kullanicilar[kayit["kullanici"]]["bakiye"],
            })
        return olaylar


    # Şimdiden sonra, hedefe kadar (hedef dahil) ilk olay ne zaman? Adaylar: sonraki Pazartesi 00:00,
    # kullanımdakilerin bitişi, onaylıların başlangıç + 15 dk'sı. Aralıkta hiç yoksa None.
    def sonraki_olay_ani(self, hedef):
        adaylar = [sonraki_pazartesi(self.saat)]
        for rez in self.rezervasyonlar.values():
            if rez["durum"] == S.KULLANIMDA:
                adaylar.append(rez["bitis"])
            elif rez["durum"] == S.ONAYLI:
                adaylar.append(rez["baslangic"] + timedelta(minutes=S.GELMEME_DK))
        en_erken = None
        for an in adaylar:
            if self.saat < an <= hedef:
                if en_erken is None or an < en_erken:
                    en_erken = an
        return en_erken

    # Aynı andaki olaylar K11'deki sırayla işleniyor:
    #   1) Pazartesi 00:00 ise haftalık sıfırlama
    #   2) bitişi gelen KULLANIMDA -> TAMAMLANDI, güvenilirlik +2
    #   3) 15 dk içinde gelinmeyen ONAYLI -> GELMEDI, güvenilirlik -15
    #   4) boşalan kaynaklar için bekleme taraması
    # Sözlük r1, r2 diye sırayla dolduğu için döngü zaten numara sırasıyla gidiyor. Olay listesi döner.
    def ani_isle(self, an):
        olaylar = []
        zaman_metni = zamani_metne_cevir(an)

        if an.weekday() == 0 and an.hour == 0 and an.minute == 0:
            for kullanici in self.kullanicilar.values():
                kullanici["bakiye"] = self.roller[kullanici["rol"]]["haftalik_kota"]
            olaylar.append({"zaman": zaman_metni, "tur": S.HAFTALIK_SIFIRLAMA})

        for rez in self.rezervasyonlar.values():
            if rez["durum"] == S.KULLANIMDA and rez["bitis"] == an:
                rez["durum"] = S.TAMAMLANDI
                kullanici = self.kullanicilar[rez["kullanici"]]
                self.guvenilirlik_degistir(kullanici, S.GUV_TAMAMLANDI)
                olaylar.append({
                    "zaman": zaman_metni,
                    "tur": S.TAMAMLANDI,
                    "rezervasyon": rez["id"],
                    "kullanici": kullanici["id"],
                    "guvenilirlik": kullanici["guvenilirlik"],
                })

        bosalan_kaynaklar = []
        for rez in self.rezervasyonlar.values():
            if rez["durum"] == S.ONAYLI:
                if rez["baslangic"] + timedelta(minutes=S.GELMEME_DK) == an:
                    rez["durum"] = S.GELMEDI
                    kullanici = self.kullanicilar[rez["kullanici"]]
                    self.guvenilirlik_degistir(kullanici, S.GUV_GELMEDI)
                    olaylar.append({
                        "zaman": zaman_metni,
                        "tur": S.GELMEDI,
                        "rezervasyon": rez["id"],
                        "kullanici": kullanici["id"],
                        "guvenilirlik": kullanici["guvenilirlik"],
                    })
                    if rez["kaynak"] not in bosalan_kaynaklar:
                        bosalan_kaynaklar.append(rez["kaynak"])

        for kaynak_id in bosalan_kaynaklar:
            olaylar += self.bekleme_tara(kaynak_id)
        return olaylar

    # Saati olaydan olaya atlatarak hedefe getiriyoruz. Her seferinde saat önce olayın anına alınıyor,
    # yoksa o andaki bekleme taraması yanlış saatle yapılırdı.
    def saati_ilerlet(self, hedef):
        olaylar = []
        while True:
            an = self.sonraki_olay_ani(hedef)
            if an is None:
                break
            self.saat = an
            olaylar += self.ani_isle(an)
        self.saat = hedef
        self.eski_beklemeleri_sil()
        return olaylar


    # {"komut":"saat","zaman":...} -> o ana kadarki olaylar. Geriye gitmek SAAT_GERI.
    def komut_saat(self, komut):
        hedef = metni_zamana_cevir(komut.get("zaman"))
        if hedef is None:
            return red("GECERSIZ_KOMUT")
        if hedef < self.saat:
            return red("SAAT_GERI")
        olaylar = self.saati_ilerlet(hedef)
        return {"durum": S.TAMAM, "olaylar": olaylar}

    # kaynak, baslangic ve bitis alanlarını okur, saatleri datetime'a çevirir (bozuksa None).
    # Rezervasyon, fiyat, bekleme ve paket kalemlerinde alanlar aynı olduğu için ortak.
    def talep_oku(self, veri):
        kaynak_id = veri.get("kaynak")
        bas = metni_zamana_cevir(veri.get("baslangic"))
        bit = metni_zamana_cevir(veri.get("bitis"))
        return kaynak_id, bas, bit

    # kontrollerden geçerse rezervasyonu oluşturur: rezervasyon_id, ucret, bakiye
    def komut_rezervasyon(self, komut):
        kullanici_id = komut.get("kullanici")
        kaynak_id, bas, bit = self.talep_oku(komut)
        hata, ucret = self.dogrula(kullanici_id, kaynak_id, bas, bit)
        if hata is not None:
            return red(hata)
        rez = self.rezervasyon_ekle(kullanici_id, kaynak_id, bas, bit, ucret)
        return {
            "durum": S.TAMAM,
            "rezervasyon_id": rez["id"],
            "ucret": ucret,
            "bakiye": self.kullanicilar[kullanici_id]["bakiye"],
        }

    # Bakiye hariç bütün kontroller, sonra ücret. Hiçbir şeyi değiştirmiyor.
    # Arayüz formdaki canlı ücret için bunu günlüğe yazmadan doğrudan çağırıyor.
    def komut_fiyat(self, komut):
        kullanici_id = komut.get("kullanici")
        kaynak_id, bas, bit = self.talep_oku(komut)
        hata, ucret = self.dogrula(kullanici_id, kaynak_id, bas, bit, bakiye_bak=False)
        if hata is not None:
            return red(hata)
        return {"durum": S.TAMAM, "ucret": ucret}

    # Paketin kendi kalemleri aynı kaynakta birbirine çakışıyor mu (K7, 5. adım)? Kesişme, hazırlık
    # ve 60 dk kuralına bakıyoruz. Kalemler aynı kişinin olduğu için aslında 60 dk kuralı hepsini kapsıyor.
    def paket_ici_cakisma_var_mi(self, kalemler):
        for i in range(len(kalemler)):
            for j in range(i + 1, len(kalemler)):
                a = kalemler[i]
                b = kalemler[j]
                if a["kaynak"] != b["kaynak"]:
                    continue
                tur = self.turler[self.kaynaklar[a["kaynak"]]["tur"]]
                hazirlik = timedelta(minutes=tur["hazirlik_dk"])
                bosluk = timedelta(minutes=S.ARDISIK_BOSLUK_DK)
                if kesisiyor_mu(a["baslangic"], a["bitis"], b["baslangic"], b["bitis"]):
                    return True
                if a["baslangic"] < b["bitis"] + hazirlik and a["bitis"] + hazirlik > b["baslangic"]:
                    return True
                if a["baslangic"] < b["bitis"] + bosluk and a["bitis"] + bosluk > b["baslangic"]:
                    return True
        return False

    # Paket (K7), ya hepsi ya hiçbiri. Sıra: BULUNAMADI, PAKET_BOYUTU, GUVENILIRLIK_DUSUK, PAKET_RED,
    # PAKET_ICI_KESISME, BAKIYE_YETERSIZ. Kalemler paketten önceki duruma göre doğrulanıyor, birbirinin
    # doluluğunu etkilemiyorlar. Rezervasyonlar en sonda topluca ekleniyor.
    # Red olursa "kalemler" listesinde her kalemin sırası, durumu ve varsa kodu var.
    def komut_paket(self, komut):
        kullanici_id = komut.get("kullanici")
        kullanici = self.kullanicilar.get(kullanici_id)
        kalemler = komut.get("kalemler")

        if kullanici is None:
            return {"durum": S.RED, "kod": "BULUNAMADI", "kalemler": []}

        if not isinstance(kalemler, list) or len(kalemler) < S.PAKET_EN_AZ or len(kalemler) > S.PAKET_EN_COK:
            return {"durum": S.RED, "kod": "PAKET_BOYUTU", "kalemler": []}

        if kullanici["guvenilirlik"] < S.GUV_ESIK:
            return {"durum": S.RED, "kod": "GUVENILIRLIK_DUSUK", "kalemler": []}

        kalem_sonuclari = []
        hazir_kalemler = []
        hatali_var = False
        for sira in range(len(kalemler)):
            kaynak_id, bas, bit = self.talep_oku(kalemler[sira])
            hata, ucret = self.dogrula(kullanici_id, kaynak_id, bas, bit, bakiye_bak=False)
            if hata is None:
                kalem_sonuclari.append({"sira": sira, "durum": S.TAMAM})
            else:
                kalem_sonuclari.append({"sira": sira, "durum": S.RED, "kod": hata})
                hatali_var = True
            hazir_kalemler.append({"kaynak": kaynak_id, "baslangic": bas, "bitis": bit, "ucret": ucret})

        if hatali_var:
            return {"durum": S.RED, "kod": "PAKET_RED", "kalemler": kalem_sonuclari}

        if self.paket_ici_cakisma_var_mi(hazir_kalemler):
            return {"durum": S.RED, "kod": "PAKET_ICI_KESISME", "kalemler": kalem_sonuclari}

        toplam = 0
        for kalem in hazir_kalemler:
            toplam += kalem["ucret"]
        if toplam > kullanici["bakiye"]:
            return {"durum": S.RED, "kod": "BAKIYE_YETERSIZ", "kalemler": kalem_sonuclari}

        self.paket_sayac += 1
        paket_id = "p" + str(self.paket_sayac)
        rez_idleri = []
        ucretler = []
        for kalem in hazir_kalemler:
            rez = self.rezervasyon_ekle(kullanici_id, kalem["kaynak"], kalem["baslangic"], kalem["bitis"],
                                        kalem["ucret"], paket_id)
            rez_idleri.append(rez["id"])
            ucretler.append(rez["ucret"])
        return {
            "durum": S.TAMAM,
            "paket_id": paket_id,
            "rezervasyonlar": rez_idleri,
            "ucretler": ucretler,
            "toplam": toplam,
            "bakiye": kullanici["bakiye"],
        }

    # Giriş: ONAYLI -> KULLANIMDA. Başlangıçtan 10 dk önce ile 15 dk sonra arasında yapılabilir.
    def komut_giris(self, komut):
        rez = self.rezervasyonlar.get(komut.get("rezervasyon"))
        if rez is None:
            return red("BULUNAMADI")
        if rez["durum"] != S.ONAYLI:
            return red("DURUM_HATASI")
        pencere_bas = rez["baslangic"] - timedelta(minutes=S.GIRIS_ONCE_DK)
        pencere_bit = rez["baslangic"] + timedelta(minutes=S.GELMEME_DK)
        if self.saat < pencere_bas or self.saat > pencere_bit:
            return red("GIRIS_PENCERESI_DISI")
        rez["durum"] = S.KULLANIMDA
        rez["giris"] = self.saat   # sonuca yazılmıyor, takvim erken / geç girişi göstermek için kullanıyor
        return {"durum": S.TAMAM, "yeni_durum": S.KULLANIMDA}

    # Çıkış: KULLANIMDA -> TAMAMLANDI. Erken çıkılırsa bitiş şimdiki saate çekiliyor, iade yok,
    # güvenilirlik de değişmiyor. Boşalan kısım için bekleme listesine bakılıyor.
    def komut_cikis(self, komut):
        rez = self.rezervasyonlar.get(komut.get("rezervasyon"))
        if rez is None:
            return red("BULUNAMADI")
        if rez["durum"] != S.KULLANIMDA:
            return red("DURUM_HATASI")
        rez["bitis"] = max(self.saat, rez["baslangic"])
        rez["durum"] = S.TAMAMLANDI
        kullanici = self.kullanicilar[rez["kullanici"]]
        olaylar = self.bekleme_tara(rez["kaynak"])
        return {
            "durum": S.TAMAM,
            "yeni_durum": S.TAMAMLANDI,
            "guvenilirlik": kullanici["guvenilirlik"],
            "olaylar": olaylar,
        }

    # İptal (K8). Başlangıca 24 saat ve fazlası varsa iadenin hepsi, 2-24 saat arası yarısı (aşağı
    # yuvarlanıyor), 2 saatten az kaldıysa iade yok ve güvenilirlik -5.
    # iade, bakiye, guvenilirlik ve otomatik atama olaylarını döner.
    def komut_iptal(self, komut):
        rez = self.rezervasyonlar.get(komut.get("rezervasyon"))
        if rez is None:
            return red("BULUNAMADI")
        if rez["durum"] != S.ONAYLI:
            return red("DURUM_HATASI")
        kullanici = self.kullanicilar[rez["kullanici"]]
        kalan = rez["baslangic"] - self.saat
        if kalan >= timedelta(hours=S.TAM_IADE_SAAT):
            iade = rez["ucret"]
        elif kalan >= timedelta(hours=S.YARIM_IADE_SAAT):
            iade = rez["ucret"] * S.YARIM_IADE_YUZDE // 100
        else:
            iade = 0
            self.guvenilirlik_degistir(kullanici, S.GUV_GEC_IPTAL)
        eklenen = self.iade_ekle(kullanici, iade)
        rez["durum"] = S.IPTAL
        olaylar = self.bekleme_tara(rez["kaynak"])
        return {
            "durum": S.TAMAM,
            "iade": eklenen,
            "bakiye": kullanici["bakiye"],
            "guvenilirlik": kullanici["guvenilirlik"],
            "olaylar": olaylar,
        }

    # Bekleme kaydı (K9). İki kere doğruluyoruz: önce çakışmaya bakmadan (başka bir sebeple geçersizse
    # o kod dönüyor), sonra bakarak (hata çıkmazsa yer zaten boştur, BEKLEME_GEREKSIZ).
    # İkisinden de geçerse kayıt açılıyor, bakiyeye bakılmıyor. bekleme_id ve sira döner.
    def komut_bekleme(self, komut):
        kullanici_id = komut.get("kullanici")
        kaynak_id, bas, bit = self.talep_oku(komut)

        hata, ucret = self.dogrula(kullanici_id, kaynak_id, bas, bit, bakiye_bak=False, cakisma_bak=False)
        if hata is not None:
            return red(hata)

        hata, ucret = self.dogrula(kullanici_id, kaynak_id, bas, bit, bakiye_bak=False)
        if hata is None:
            return red("BEKLEME_GEREKSIZ")

        self.bek_sayac += 1
        kayit = {
            "id": "b" + str(self.bek_sayac),
            "no": self.bek_sayac,
            "kullanici": kullanici_id,
            "kaynak": kaynak_id,
            "baslangic": bas,
            "bitis": bit,
            "kayit_saati": self.saat,
        }
        self.beklemeler[kayit["id"]] = kayit
        sira = self.bekleme_sirasi(kaynak_id).index(kayit) + 1
        return {"durum": S.TAMAM, "bekleme_id": kayit["id"], "sira": sira}

    # sorgu kullanici -> bakiye, güvenilirlik ve bütün rezervasyonları
    # sorgu kaynak -> o günün ONAYLI / KULLANIMDA rezervasyonları ve bakımları (gun yoksa bugün)
    def komut_sorgu(self, komut):
        tur = komut.get("tur")

        if tur == "kullanici":
            kullanici = self.kullanicilar.get(komut.get("id"))
            if kullanici is None:
                return red("BULUNAMADI")
            liste = []
            for rez in self.kullanici_rezervasyonlari(kullanici["id"]):
                liste.append({
                    "id": rez["id"],
                    "kaynak": rez["kaynak"],
                    "baslangic": zamani_metne_cevir(rez["baslangic"]),
                    "bitis": zamani_metne_cevir(rez["bitis"]),
                    "durum": rez["durum"],
                    "ucret": rez["ucret"],
                })
            return {
                "durum": S.TAMAM,
                "bakiye": kullanici["bakiye"],
                "guvenilirlik": kullanici["guvenilirlik"],
                "rezervasyonlar": liste,
            }

        if tur == "kaynak":
            kaynak = self.kaynaklar.get(komut.get("id"))
            if kaynak is None:
                return red("BULUNAMADI")
            if komut.get("gun") is None:
                gun_bas = self.saat.replace(hour=0, minute=0)
            else:
                gun_bas = gun_metnini_cevir(komut.get("gun"))
                if gun_bas is None:
                    return red("GECERSIZ_KOMUT")
            gun_bit = gun_bas + timedelta(days=1)

            liste = []
            for bakim in self.bakimlar:
                if bakim["kaynak"] == kaynak["id"]:
                    if kesisiyor_mu(bakim["baslangic"], bakim["bitis"], gun_bas, gun_bit):
                        liste.append({
                            "baslangic": zamani_metne_cevir(bakim["baslangic"]),
                            "bitis": zamani_metne_cevir(bakim["bitis"]),
                            "tur": S.KUTU_BAKIM,
                        })
            for rez in self.rezervasyonlar.values():
                if rez["kaynak"] == kaynak["id"] and rez["durum"] in S.AKTIF_DURUMLAR:
                    if kesisiyor_mu(rez["baslangic"], rez["bitis"], gun_bas, gun_bit):
                        liste.append({
                            "baslangic": zamani_metne_cevir(rez["baslangic"]),
                            "bitis": zamani_metne_cevir(rez["bitis"]),
                            "tur": S.KUTU_REZERVASYON,
                            "rezervasyon": rez["id"],
                        })
            liste.sort(key=baslangica_gore)
            return {"durum": S.TAMAM, "doluluk": liste}

        return red("GECERSIZ_KOMUT")

    # Yeni PDF'teki kullanici_ekle. Sıra: ID_MEVCUT, TANIMSIZ_DEGER (rol dosyada yok), GECERSIZ_DEGER
    # (bakiye 0'dan küçük ya da kotadan büyük, güvenilirlik 0-100 arası tam sayı değil).
    # Python'da True da int sayıldığı için type() ile bakıyoruz. id hiç yoksa alan eksik demek,
    # GECERSIZ_KOMUT. Kullanıcı sadece bellekte tutuluyor, dosyaya yazılmıyor.
    def komut_kullanici_ekle(self, komut):
        yeni_id = komut.get("id")
        if not isinstance(yeni_id, str) or yeni_id.strip() == "":
            return red("GECERSIZ_KOMUT")
        rol = komut.get("rol")
        bakiye = komut.get("bakiye")
        guvenilirlik = komut.get("guvenilirlik")

        if yeni_id in self.kullanicilar:
            return red("ID_MEVCUT")

        if rol not in self.roller:
            return red("TANIMSIZ_DEGER")

        kota = self.roller[rol]["haftalik_kota"]
        if type(bakiye) not in (int, float) or bakiye < 0 or bakiye > kota:
            return red("GECERSIZ_DEGER")
        if type(guvenilirlik) != int or guvenilirlik < S.GUV_EN_AZ or guvenilirlik > S.GUV_EN_COK:
            return red("GECERSIZ_DEGER")

        self.kullanicilar[yeni_id] = {
            "id": yeni_id,
            "ad": komut.get("ad", ""),
            "rol": rol,
            "sertifikalar": list(komut.get("sertifikalar", [])),
            "bakiye": bakiye,
            "guvenilirlik": guvenilirlik,
        }
        return {"durum": S.TAMAM}

    # kaynak_ekle: önce ID_MEVCUT, sonra tür ya da izinli rollerden biri tanımlı değilse TANIMSIZ_DEGER.
    # Eklenen kaynak o andan sonra ücret hesabındaki kaynak sayısına giriyor.
    def komut_kaynak_ekle(self, komut):
        yeni_id = komut.get("id")
        if not isinstance(yeni_id, str) or yeni_id.strip() == "":
            return red("GECERSIZ_KOMUT")
        izinli_roller = komut.get("izinli_roller", [])

        if yeni_id in self.kaynaklar:
            return red("ID_MEVCUT")

        if komut.get("tur") not in self.turler:
            return red("TANIMSIZ_DEGER")
        for rol in izinli_roller:
            if rol not in self.roller:
                return red("TANIMSIZ_DEGER")

        self.kaynaklar[yeni_id] = {
            "id": yeni_id,
            "ad": komut.get("ad", ""),
            "tur": komut["tur"],
            "izinli_roller": list(izinli_roller),
        }
        return {"durum": S.TAMAM}

    # Aşağıdakiler durumu değiştirmiyor, arayüz ekrana çizerken kullanıyor.

    # kullanıcının bütün rezervasyonları, başlangıç sonra numara sırasıyla
    def kullanici_rezervasyonlari(self, kullanici_id):
        liste = []
        for rez in self.rezervasyonlar.values():
            if rez["kullanici"] == kullanici_id:
                liste.append(rez)
        liste.sort(key=baslangic_ve_numara)
        return liste

    # Kullanıcının bekleme kayıtları, her biri (kayıt, sıra) şeklinde. Arayüzdeki panel için.
    def kullanici_beklemeleri(self, kullanici_id):
        sonuc = []
        for kayit in self.beklemeler.values():
            if kayit["kullanici"] == kullanici_id:
                sira = self.bekleme_sirasi(kayit["kaynak"]).index(kayit) + 1
                sonuc.append((kayit, sira))
        return sonuc

    # Takvimin çizeceği kutular: {kaynak_id: [kutu, ...]}. Bakım, rezervasyon (IPTAL ve GELMEDI dahil)
    # ve hazırlık kutuları var. gun_bas o günün 00:00'ı.
    def gun_takvimi(self, gun_bas):
        gun_bit = gun_bas + timedelta(days=1)
        takvim = {}
        for kaynak_id in self.kaynaklar:
            takvim[kaynak_id] = []

        for bakim in self.bakimlar:
            if bakim["kaynak"] in takvim:
                if kesisiyor_mu(bakim["baslangic"], bakim["bitis"], gun_bas, gun_bit):
                    takvim[bakim["kaynak"]].append({
                        "tur": S.KUTU_BAKIM,
                        "baslangic": bakim["baslangic"],
                        "bitis": bakim["bitis"],
                    })

        for rez in self.rezervasyonlar.values():
            if rez["kaynak"] not in takvim:
                continue
            if rez["baslangic"].date() != gun_bas.date():
                continue
            takvim[rez["kaynak"]].append({
                "tur": S.KUTU_REZERVASYON,
                "baslangic": rez["baslangic"],
                "bitis": rez["bitis"],
                "rezervasyon": rez,
            })
            hazirlik_dk = self.turler[self.kaynaklar[rez["kaynak"]]["tur"]]["hazirlik_dk"]
            if rez["durum"] in S.HAZIRLIK_DURUMLARI and hazirlik_dk > 0:
                takvim[rez["kaynak"]].append({
                    "tur": S.KUTU_HAZIRLIK,
                    "baslangic": rez["bitis"],
                    "bitis": rez["bitis"] + timedelta(minutes=hazirlik_dk),
                    "rezervasyon": rez,
                })
        return takvim

    # dosyada geçen sertifika adları (yeni üye penceresindeki seçenekler için), sıralı liste
    def tum_sertifikalar(self):
        liste = []
        for tur in self.turler.values():
            if tur.get("sertifika") and tur["sertifika"] not in liste:
                liste.append(tur["sertifika"])
        for kullanici in self.kullanicilar.values():
            for sertifika in kullanici.get("sertifikalar", []):
                if sertifika not in liste:
                    liste.append(sertifika)
        liste.sort()
        return liste
