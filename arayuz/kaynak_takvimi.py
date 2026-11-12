# Kaynak takvimi (PDF 7.2). Her kaynak bir satır, yatay eksen 08:00-22:00.
# Takvim hiçbir şeyi değiştirmiyor, modülün gun_takvimi'nden gelen kutuları çiziyor.

import tkinter as tk

from rezervasyon import kural_sabitleri as S
from rezervasyon.zaman_islemleri import gun_metnini_cevir, kesisiyor_mu
from arayuz import renkler_ve_stiller as tema
from arayuz.turkce_metinler import DURUMLAR

# Hepsi tk.Canvas üstüne çiziliyor (create_rectangle, create_line, create_text, create_polygon).
# find_withtag("current") farenin altındaki şekli veriyor, gettags onun etiketlerini.

ETIKET_GENISLIGI = 150   # soldaki kaynak adlarının genişliği
EKSEN_YUKSEKLIGI = 34    # üstteki saat yazılarının yüksekliği
EN_AZ_SERIT = 22         # bir şeridin (alt satırın) en az ve en çok yüksekliği
EN_COK_SERIT = 55
RAHAT_SATIR = 36         # satır bundan yüksekse kaynak adı iki satır yazılıyor

PASIF_DURUMLAR = (S.IPTAL, S.GELMEDI)


# Canvas'ta yuvarlak köşeli dikdörtgen yok. Köşe noktalarını verip smooth=True ile çokgen çiziyoruz.
# kesikli=True ise kenar kesik çizgi oluyor (IPTAL / GELMEDI kutuları).
def yuvarlak_kutu(tuval, x1, y1, x2, y2, yaricap, dolgu, cizgi, kalinlik, etiket, kesikli=False):
    r = min(yaricap, (x2 - x1) / 2, (y2 - y1) / 2)
    noktalar = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
                x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    if kesikli:
        return tuval.create_polygon(noktalar, smooth=True, fill=dolgu, outline=cizgi, width=kalinlik,
                                    dash=(4, 2), tags=(etiket,))
    return tuval.create_polygon(noktalar, smooth=True, fill=dolgu, outline=cizgi, width=kalinlik, tags=(etiket,))


# yazı sığmazsa sonunu kırpıp ... koyar
def sigdir(yazi, font, genislik):
    if font.measure(yazi) <= genislik:
        return yazi
    while len(yazi) > 1 and font.measure(yazi + "...") > genislik:
        yazi = yazi[:-1]
    return yazi + "..."


# IPTAL / GELMEDI bir rezervasyonla aynı saate yeni rezervasyon alınınca ikisi üst üste çizilmesin diye
# kutuları alt satırlara (şerit) dağıtıyoruz. Aktif olanlar birbiriyle çakışamaz, hepsi 0. şeride gider.
# Pasifler çakışmadıkları ilk şeride, yer yoksa yeni şeride. Her kutuya "serit" yazılıyor,
# şerit sayısı döner.
def serit_ata(kutular):
    sirali = []
    for kutu in kutular:
        if kutu["rezervasyon"]["durum"] not in PASIF_DURUMLAR:
            sirali.append(kutu)
    for kutu in kutular:
        if kutu["rezervasyon"]["durum"] in PASIF_DURUMLAR:
            sirali.append(kutu)

    seritler = []
    for kutu in sirali:
        yer = None
        for i in range(len(seritler)):
            bos = True
            for diger in seritler[i]:
                if kesisiyor_mu(kutu["baslangic"], kutu["bitis"], diger["baslangic"], diger["bitis"]):
                    bos = False
            if bos:
                yer = i
                break
        if yer is None:
            seritler.append([])
            yer = len(seritler) - 1
        seritler[yer].append(kutu)
        kutu["serit"] = yer
    return max(1, len(seritler))


class Takvim:

    # ust: içine konacağı çerçeve. uygulama: masaustu_uygulamasi.py'deki Uygulama nesnesi, sistem ve seçili
    # rezervasyon oradan okunuyor, tıklamalar da oraya bildiriliyor.
    def __init__(self, ust, uygulama):
        self.uyg = uygulama
        self.tuval = tk.Canvas(ust, bg=tema.YUZEY, highlightthickness=0, height=EKSEN_YUKSEKLIGI + 6 * EN_AZ_SERIT)
        self.tuval.pack(fill="both", expand=True, pady=(tema.M, 0))
        self.tuval.bind("<Configure>", self.boyut_degisti)
        self.tuval.bind("<Motion>", self.fare_hareketi)
        self.tuval.bind("<Leave>", self.fare_cikti)
        self.tuval.bind("<Button-1>", self.tiklandi)
        self.sol = 0
        self.sag = 0
        self.acilis = None
        self.kapanis = None
        self.satirlar = []   # (kaynak_id, y0, y1) her satırın dikey yeri
        self.bilgiler = {}   # şekil etiketi -> fare üstüne gelince gösterilecek yazı

    # pencere büyüyüp küçülünce yeniden çiz
    def boyut_degisti(self, olay):
        self.ciz()

    # zaman -> x pikseli. 08:00 öncesi ve 22:00 sonrası kenara yapışıyor.
    def x_bul(self, zaman):
        toplam = (self.kapanis - self.acilis).total_seconds()
        oran = (zaman - self.acilis).total_seconds() / toplam
        oran = max(0.0, min(1.0, oran))
        return self.sol + oran * (self.sag - self.sol)

    # x_bul'un tersi, tıklanan yerin saati
    def zaman_bul(self, x):
        oran = (x - self.sol) / (self.sag - self.sol)
        return self.acilis + (self.kapanis - self.acilis) * oran

    # kutunun sol ve sağ x değeri
    def aralik(self, kutu):
        return self.x_bul(kutu["baslangic"]), self.x_bul(kutu["bitis"])

    # Fare kutunun üstüne gelince alttaki satırda görünen yazı: numara, kullanıcı, kaynak, saat,
    # durum, ücret ve varsa paket. PDF bunların takvimden görülebilmesini istiyor.
    def rez_bilgisi(self, rez):
        kullanici = self.uyg.sistem.kullanicilar.get(rez["kullanici"], {})
        saatler = rez["baslangic"].strftime("%d.%m %H:%M") + "-" + rez["bitis"].strftime("%H:%M")
        parcalar = [rez["id"], kullanici.get("ad", "") + " (" + rez["kullanici"] + ")", rez["kaynak"],
                    saatler, DURUMLAR.get(rez["durum"], rez["durum"]), str(rez["ucret"]) + " KP"]
        if rez["paket"]:
            parcalar.append("paket " + rez["paket"])
        if rez.get("giris"):
            parcalar.append("giriş " + rez["giris"].strftime("%H:%M"))
        return "  |  ".join(parcalar)

    # Takvimi baştan çizer. Önce her kaynağın kaç şeride ihtiyacı olduğunu buluyoruz, sonra yüksekliği
    # şerit sayısına göre paylaştırıyoruz; alt satırı olan kaynak biraz daha uzun oluyor.
    # Arayüzde durum her değiştiğinde (yenile) ve gün değişince çağrılıyor.
    def ciz(self):
        t = self.tuval
        sistem = self.uyg.sistem
        t.delete("all")
        self.bilgiler = {}
        self.satirlar = []
        genislik = t.winfo_width()
        yukseklik = t.winfo_height()
        if sistem is None or genislik < 200:
            return
        gun = gun_metnini_cevir(self.uyg.takvim_gun_var.get().strip())
        if gun is None:
            t.create_text(genislik / 2, yukseklik / 2, text="Gün YYYY-AA-GG biçiminde olmalı.",
                          fill=tema.MERCAN_KOYU, font=tema.FONT["govde"])
            return

        self.acilis = gun.replace(hour=S.CALISMA_BASLANGIC_SAAT, minute=0)
        self.kapanis = gun.replace(hour=S.CALISMA_BITIS_SAAT, minute=0)
        self.sol = ETIKET_GENISLIGI + tema.M
        self.sag = genislik - tema.L

        # her kaynağın şerit sayısı (IPTAL / GELMEDI ile çakışan yeni rezervasyon varsa 2 veya daha fazla)
        takvim = sistem.gun_takvimi(gun)
        kaynaklar = list(sistem.kaynaklar.values())
        serit_sayilari = {}
        toplam_serit = 0
        for kaynak in kaynaklar:
            rez_kutulari = []
            for kutu in takvim[kaynak["id"]]:
                if kutu["tur"] == S.KUTU_REZERVASYON:
                    rez_kutulari.append(kutu)
            serit_sayilari[kaynak["id"]] = serit_ata(rez_kutulari)
            toplam_serit += serit_sayilari[kaynak["id"]]

        # bir şeridin yüksekliği: alanı şerit sayısına bölüyoruz ama çok ince ya da çok kalın olmasın
        serit_yuk = (yukseklik - EKSEN_YUKSEKLIGI - tema.S) / max(1, toplam_serit)
        serit_yuk = max(EN_AZ_SERIT, min(EN_COK_SERIT, serit_yuk))
        alt = EKSEN_YUKSEKLIGI + serit_yuk * toplam_serit

        self.satirlari_ciz(kaynaklar, serit_sayilari, serit_yuk, genislik)
        self.izgara_ciz(gun, alt)
        self.simdiyi_ciz(gun, alt)
        for kaynak_id, y0, y1 in self.satirlar:
            self.kutulari_ciz(kaynak_id, takvim[kaynak_id], y0, y1, serit_yuk)
        # gri alan kutuların arkasında kalsın ama kırmızı çizgi en üstte görünsün
        t.tag_raise("simdi")

    # Kaynak satırlarının zemini ve soldaki adları. Her satırın y aralığını self.satirlar'a ekliyoruz,
    # tıklamada hangi satıra basıldığını oradan buluyoruz.
    def satirlari_ciz(self, kaynaklar, serit_sayilari, serit_yuk, genislik):
        t = self.tuval
        y0 = EKSEN_YUKSEKLIGI
        for i in range(len(kaynaklar)):
            kaynak = kaynaklar[i]
            satir_yuk = serit_yuk * serit_sayilari[kaynak["id"]]
            y1 = y0 + satir_yuk
            if i % 2 == 0:
                renk = tema.YUZEY
            else:
                renk = tema.YUZEY_ALT
            t.create_rectangle(0, y0, genislik, y1, fill=renk, width=0)
            etiket = "kyn_" + kaynak["id"]
            if satir_yuk >= RAHAT_SATIR:
                t.create_text(tema.M, y0 + satir_yuk / 2 - 8, text=kaynak["id"], anchor="w",
                              font=tema.FONT["govde_kalin"], fill=tema.METIN, tags=(etiket,))
                alt_yazi = sigdir(kaynak.get("ad", "") + " - " + kaynak["tur"], tema.FONT["kucuk"],
                                  ETIKET_GENISLIGI - tema.L)
                t.create_text(tema.M, y0 + satir_yuk / 2 + 9, text=alt_yazi, anchor="w",
                              font=tema.FONT["kucuk"], fill=tema.METIN_SOLUK, tags=(etiket,))
            else:
                t.create_text(tema.M, y0 + satir_yuk / 2, text=kaynak["id"] + "  " + kaynak["tur"],
                              anchor="w", font=tema.FONT["kucuk_kalin"], fill=tema.METIN, tags=(etiket,))
            self.bilgiler[etiket] = (kaynak["id"] + "  |  " + kaynak.get("ad", "") + "  |  " + kaynak["tur"] +
                                     "  |  izinli: " + ", ".join(kaynak.get("izinli_roller", [])) +
                                     "  |  tıkla: bu günü sorgula")
            self.satirlar.append((kaynak["id"], y0, y1))
            y0 = y1

    # Üstteki saatler ve dikey çizgiler: 15 dakikada bir ince, saat başı biraz koyu, bant sınırı en koyu.
    # Pik saatler (10-16) bütün satırların arkasında açık sarı zemin. Her saat yazılıyor; ekran darsa
    # "08:00" yerine kısaca "08".
    def izgara_ciz(self, gun, alt):
        t = self.tuval
        pik_a = self.x_bul(gun.replace(hour=S.PIK_BASLANGIC_SAAT))
        pik_b = self.x_bul(gun.replace(hour=S.PIK_BITIS_SAAT))
        t.create_rectangle(pik_a, EKSEN_YUKSEKLIGI, pik_b, alt, fill=tema.PIK, width=0)

        saat_sayisi = S.CALISMA_BITIS_SAAT - S.CALISMA_BASLANGIC_SAAT
        dar = (self.sag - self.sol) / saat_sayisi < 42

        dakika = 0
        while dakika <= saat_sayisi * 60:
            an = self.acilis.replace(hour=S.CALISMA_BASLANGIC_SAAT + dakika // 60, minute=dakika % 60)
            x = self.x_bul(an)
            if dakika % S.BANT_DK == 0:
                renk = "#A9CBC6"
            elif dakika % 60 == 0:
                renk = "#C9DEDB"
            else:
                renk = "#EAF2F1"
            t.create_line(x, EKSEN_YUKSEKLIGI, x, alt, fill=renk)
            if dakika % 60 == 0:
                yazi = f"{an.hour:02d}" if dar else f"{an.hour:02d}:00"
                t.create_text(x, EKSEN_YUKSEKLIGI / 2 - 3, text=yazi, font=tema.FONT["kucuk"], fill=tema.METIN_SOLUK)
            dakika += S.ADIM_DK

    # Bir kaynağın kutuları. Bakım ve hazırlık önce çiziliyor ki rezervasyonların arkasında kalsın.
    # Rezervasyon kendi şeridine çiziliyor, içine ne kadar yazı sığıyorsa o kadar yazıyoruz.
    def kutulari_ciz(self, kaynak_id, kutular, y0, y1, serit_yuk):
        t = self.tuval
        rez_kutulari = []
        for kutu in kutular:
            if kutu["tur"] == S.KUTU_BAKIM:
                x1, x2 = self.aralik(kutu)
                etiket = "bak_" + kaynak_id + "_" + str(len(self.bilgiler))
                t.create_rectangle(x1, y0 + 3, x2, y1 - 3, fill=tema.KEHRIBAR, outline="#C98F1E",
                                   stipple="gray50", tags=(etiket,))
                if x2 - x1 > 54:
                    t.create_text((x1 + x2) / 2, (y0 + y1) / 2, text="Bakım", font=tema.FONT["kucuk_kalin"],
                                  fill="#5A3A00", tags=(etiket,))
                saatler = kutu["baslangic"].strftime("%d.%m %H:%M") + " - " + kutu["bitis"].strftime("%d.%m %H:%M")
                self.bilgiler[etiket] = "Bakım  |  " + kaynak_id + "  |  " + saatler
            elif kutu["tur"] == S.KUTU_HAZIRLIK:
                x1, x2 = self.aralik(kutu)
                etiket = "haz_" + kaynak_id + "_" + str(len(self.bilgiler))
                t.create_rectangle(x1, y0 + 6, x2, y1 - 6, fill=tema.HAZIRLIK, outline="",
                                   stipple="gray50", tags=(etiket,))
                dakika = int((kutu["bitis"] - kutu["baslangic"]).total_seconds() // 60)
                self.bilgiler[etiket] = ("Hazırlık süresi  |  " + str(dakika) + " dk  |  " +
                                         kutu["rezervasyon"]["id"] + " sonrası")
            else:
                rez_kutulari.append(kutu)

        for kutu in rez_kutulari:
            rez = kutu["rezervasyon"]
            x1, x2 = self.aralik(kutu)
            if x2 - x1 < 2:
                continue
            ust = y0 + kutu["serit"] * serit_yuk
            alt = ust + serit_yuk
            dolgu, yazi_rengi = tema.DURUM_RENKLERI[rez["durum"]]
            pasif = rez["durum"] in PASIF_DURUMLAR
            etiket = "rez_" + rez["id"]
            if rez["id"] == self.uyg.secili_rezervasyon:
                cizgi, kalinlik = tema.METIN, 2
            elif pasif:
                cizgi, kalinlik = yazi_rengi, 1
            else:
                cizgi, kalinlik = dolgu, 1
            yuvarlak_kutu(t, x1 + 1, ust + 3, x2 - 1, alt - 3, 7, dolgu, cizgi, kalinlik, etiket, kesikli=pasif)

            # kutuya sığan en uzun yazıyı koyuyoruz
            if pasif:
                uzun = rez["id"] + " " + DURUMLAR[rez["durum"]]
            else:
                uzun = rez["id"] + " " + rez["kullanici"]
            if tema.FONT["kucuk_kalin"].measure(uzun) < x2 - x1 - 10:
                yazi = uzun
            elif tema.FONT["kucuk_kalin"].measure(rez["id"]) < x2 - x1 - 6:
                yazi = rez["id"]
            else:
                yazi = ""
            if yazi and alt - ust >= 14:
                t.create_text((x1 + x2) / 2, (ust + alt) / 2, text=yazi, fill=yazi_rengi,
                              font=tema.FONT["kucuk_kalin"], tags=(etiket,))
            # giriş başlangıçtan önce (erken) ya da sonra (geç) yapıldıysa arası koyu mavi noktalı çizgi
            giris = rez.get("giris")
            if giris is not None and giris != rez["baslangic"]:
                a = self.x_bul(min(giris, rez["baslangic"]))
                b = self.x_bul(max(giris, rez["baslangic"]))
                t.create_line(a, alt - 5, b, alt - 5, fill=tema.GIRIS, width=3, dash=(2, 3), tags=(etiket,))
            self.bilgiler[etiket] = self.rez_bilgisi(rez)

    # Simüle saatin yeri: o ana kadarki kısım gri, şimdi kırmızı çizgi ve üstünde saat. Gösterilen gün
    # tamamen geçmişse hepsi gri. Çizgiye "simdi" etiketi veriyoruz, ciz en sonda onu öne alıyor.
    def simdiyi_ciz(self, gun, alt):
        t = self.tuval
        simdi = self.uyg.sistem.saat
        if simdi.date() > gun.date():
            t.create_rectangle(self.sol, EKSEN_YUKSEKLIGI, self.sag, alt, fill="#9AA9A8", stipple="gray12", width=0)
            return
        if simdi.date() < gun.date() or simdi <= self.acilis:
            return
        x = self.x_bul(simdi)
        t.create_rectangle(self.sol, EKSEN_YUKSEKLIGI, x, alt, fill="#9AA9A8", stipple="gray12", width=0)
        if simdi <= self.kapanis:
            t.create_line(x, EKSEN_YUKSEKLIGI - 4, x, alt, fill=tema.MERCAN, width=2, tags=("simdi",))
            yazi = simdi.strftime("%H:%M")
            yari = tema.FONT["kucuk_kalin"].measure(yazi) / 2 + 4
            t.create_rectangle(x - yari, 3, x + yari, EKSEN_YUKSEKLIGI - 10, fill=tema.MERCAN, outline="",
                               tags=("simdi",))
            t.create_text(x, (EKSEN_YUKSEKLIGI - 7) / 2, text=yazi, fill="#FFFFFF", font=tema.FONT["kucuk_kalin"],
                          tags=("simdi",))

    # Farenin altındaki şeklin bilgisini alttaki satıra yazar, rezervasyon kutusuysa el imleci.
    def fare_hareketi(self, olay):
        bilgi = None
        tiklanabilir = False
        for oge in self.tuval.find_withtag("current"):
            for etiket in self.tuval.gettags(oge):
                if etiket in self.bilgiler:
                    bilgi = self.bilgiler[etiket]
                    tiklanabilir = etiket.startswith("rez_")
        # boş bir yerdeyse farenin olduğu saati (15 dakikaya yuvarlı) ve düştüğü bandı yaz
        if bilgi is None and self.acilis is not None and self.sol <= olay.x <= self.sag:
            for kaynak_id, y0, y1 in self.satirlar:
                if y0 <= olay.y < y1:
                    an = self.zaman_bul(olay.x)
                    an = an.replace(minute=an.minute // S.ADIM_DK * S.ADIM_DK, second=0, microsecond=0)
                    bant_bas, bant_bit = self.uyg.sistem.bant_bul(an)
                    bilgi = (kaynak_id + "  |  " + an.strftime("%H:%M") + "  |  bant " + bant_bas.strftime("%H:%M") +
                             "-" + bant_bit.strftime("%H:%M") + "  |  tıklayınca form bu saatle dolar")
        if tiklanabilir:
            self.tuval.configure(cursor="hand2")
        else:
            self.tuval.configure(cursor="")
        self.uyg.takvim_bilgisi(bilgi)

    # fare takvimden çıkınca bilgi satırı eski haline dönsün
    def fare_cikti(self, olay):
        self.uyg.takvim_bilgisi(None)

    # Kutuya tıklandıysa rezervasyonu seç, kaynak adına tıklandıysa o günü sorgula,
    # boş yere tıklandıysa formu o kaynak ve saatle doldur.
    def tiklandi(self, olay):
        for oge in self.tuval.find_withtag("current"):
            for etiket in self.tuval.gettags(oge):
                if etiket.startswith("rez_"):
                    self.uyg.rezervasyonu_sec(etiket[4:])
                    return
                if etiket.startswith("kyn_"):
                    self.uyg.kaynak_sorgula(etiket[4:])
                    return
        if self.acilis is None or not (self.sol <= olay.x <= self.sag):
            return
        for kaynak_id, y0, y1 in self.satirlar:
            if y0 <= olay.y < y1:
                self.uyg.formu_doldur(kaynak_id, self.zaman_bul(olay.x))
                return
