# Masaüstü uygulaması. Çalıştırmak için masaustu_uygulamasi.bat ya da
# python masaustu_uygulamasi.py [baslangic.json]
#
# Ekrandaki her işlem bir komut sözlüğü olarak modüle (komut_calistir) gidiyor, sonucu
# gösteriyoruz. Arayüzde kural yok, yanlış bir talebi de gönderiyoruz, reddini modül veriyor.
# Komut dosyası okunmuyor, sonuç dosyası yazılmıyor, başlangıç dosyası değişmiyor (PDF Bölüm 7).

import ctypes
import json
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import timedelta

# ctypes sadece Windows ayarı için (SetProcessDpiAwareness ve SetCurrentProcessExplicitAppUserModelID,
# bkz. ekran_netligini_ac). json.dumps günlükteki JSON'u göstermek için. os.path dosya yolları için,
# sys.argv komut satırından gelen dosya için.
# tkinter ekranın kendisi: Tk, Frame, Label, Button, Canvas, Text, Menu, Toplevel, StringVar,
# PhotoImage (logo); ttk'den Combobox, Treeview, Notebook, Spinbox, Checkbutton, PanedWindow.
# filedialog.askopenfilename dosya seçtirmek, messagebox.showerror dosya okunamazsa uyarmak için.
# timedelta saati ilerletirken.

PROJE_KLASORU = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJE_KLASORU)

from rezervasyon import kural_sabitleri as S
from rezervasyon.kurallar import dosyadan_sistem_olustur
from rezervasyon.zaman_islemleri import metni_zamana_cevir, zamani_metne_cevir
from arayuz import renkler_ve_stiller as tema
from arayuz.turkce_metinler import HATALAR, DURUMLAR, OLAYLAR, KOMUTLAR, GUNLER
from arayuz.kaynak_takvimi import Takvim

ORNEK_KLASORU = os.path.join(PROJE_KLASORU, "ornek")
# uygulama açılırken önerilen dosya: sınav günü (3 Kasım 2026) başlayan örnek. PDF'teki 19 komutluk
# örnek senaryo ise ornek/baslangic.json, onu da aynı pencereden seçmek yeterli.
ORNEK_BASLANGIC = os.path.join(ORNEK_KLASORU, "baslangic_3_kasim.json")
LOGO_ICO = os.path.join(PROJE_KLASORU, "arayuz", "logo", "logo.ico")
LOGO_KUCUK = os.path.join(PROJE_KLASORU, "arayuz", "logo", "logo_kucuk.png")
PROGRAM_KIMLIGI = "KocaeliUniversitesi.KampusRezervasyon.YazLab1"
GUN_BICIMI = "%Y-%m-%d"

# bekleme kaydı önerisi sadece bu iki retten sonra çıkıyor (PDF Bölüm 7 madde 5 ve K9)
BEKLEME_ONERILEN_KODLAR = ("KESISME", "HAZIRLIK_IHLALI")

# alt çubuktaki kırmızı hata yazısı 10 saniye kalıyor, sonra çubuk bu yazıya dönüyor
HATA_SURESI_MS = 10000
HAZIR_YAZISI = "Hazır. Kullanıcı seçip talep oluşturabilirsiniz."

TAKVIM_IPUCU = ("Kutunun üstüne gelince ayrıntı görünür. Kutuya tıkla: seç. Boş yere tıkla: form dolar. "
                "Kaynak adına tıkla: o günü sorgula.")


# Windows'ta yazılar bulanık olmasın ve görev çubuğunda Python yerine bizim logo çıksın.
# Başka işletim sisteminde windll yok, hata verirse geçiyoruz.
def ekran_netligini_ac():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(PROGRAM_KIMLIGI)
    except (AttributeError, OSError):
        pass


# Kutudaki yazıyı int ya da float yapmaya çalışıyor, olmazsa yazıyı aynen bırakıyor.
# Yanlış değeri arayüz değil modül reddetsin diye (GECERSIZ_DEGER).
def sayiya_cevir(yazi):
    yazi = yazi.strip()
    try:
        return int(yazi)
    except ValueError:
        pass
    try:
        return float(yazi)
    except ValueError:
        return yazi


class Uygulama:

    # Ana pencere. Boyutu ayarlıyor, açılışta başlangıç dosyasını soruyor ve ekranı kuruyor.
    # Dosya okunamazsa pencere kapanıyor. Formdaki değişkenlere trace_add bağlı, değer değişince
    # form_degisti çalışıp ücret yeniden hesaplanıyor.
    def __init__(self, kok):
        self.kok = kok
        try:
            self.kok.iconbitmap(default=LOGO_ICO)
        except tk.TclError:
            pass
        self.logo_resmi = None   # PhotoImage burada tutulmazsa Python siliyor ve logo kayboluyor
        self.sistem = None
        self.dosya_yolu = ""
        self.paket_kalemleri = []
        self.secili_rezervasyon = None
        self.teklif_komutu = None   # reddedilen ve bekleme kaydı önerilen son talep
        self.onizleme_etiketi = None
        self.bildirim_zamanlayici = None   # hatayı 10 saniye sonra silecek after'ın kimliği
        self.takvim_kalici = (TAKVIM_IPUCU, tema.METIN_SOLUK)

        # ekrandaki seçimleri tutan değişkenler; formdaki bir değer değişince fiyat önizlemesi yenileniyor
        self.kullanici_var = tk.StringVar()
        self.kaynak_var = tk.StringVar()
        self.gun_var = tk.StringVar()
        self.bas_var = tk.StringVar(value="10:00")
        self.bit_var = tk.StringVar(value="10:30")
        self.hedef_saat_var = tk.StringVar()
        self.takvim_gun_var = tk.StringVar()
        for degisken in (self.kullanici_var, self.kaynak_var, self.gun_var, self.bas_var, self.bit_var):
            degisken.trace_add("write", self.form_degisti)

        self.kok.minsize(1100, 640)
        ekran_g = self.kok.winfo_screenwidth()
        ekran_y = self.kok.winfo_screenheight()
        if ekran_g <= 1440 or ekran_y <= 860:
            try:
                self.kok.state("zoomed")
            except tk.TclError:
                pass
        else:
            genislik = int(ekran_g * 0.8)
            yukseklik = min(int(genislik / 1.6), ekran_y - 80)
            self.kok.geometry(f"{genislik}x{yukseklik}+{(ekran_g - genislik) // 2}+{(ekran_y - yukseklik) // 3}")

        # dosya seçilirken arkada boş pencere görünmesin
        self.kok.withdraw()
        yol = self.ilk_dosyayi_sec()
        if not yol or not self.sistemi_yukle(yol):
            self.kok.destroy()
            return
        self.kok.deiconify()
        self.arayuzu_kur()

    # Açılışta hangi dosya yüklensin (PDF 7.1): komut satırında verildiyse o, yoksa dosya seçme penceresi.
    # Pencere kapatılırsa örnek dosyayı açıyoruz ki program boş açılmasın. Dosya yolunu döner.
    def ilk_dosyayi_sec(self):
        if len(sys.argv) > 1:
            return sys.argv[1]
        yol = filedialog.askopenfilename(title="Başlangıç dosyasını seçin", initialdir=ORNEK_KLASORU,
                                         initialfile=os.path.basename(ORNEK_BASLANGIC),
                                         filetypes=[("JSON", "*.json"), ("Tüm dosyalar", "*.*")])
        if yol:
            return yol
        if os.path.exists(ORNEK_BASLANGIC):
            return ORNEK_BASLANGIC
        return ""

    # "u1 - Ayşe Kaya" -> "u1"
    def secili_id(self, degisken):
        return degisken.get().split(" - ")[0].strip()

    # listede görünen hali: "u1 - Ayşe Kaya"
    def kullanici_yazisi(self, kullanici_id):
        return kullanici_id + " - " + self.sistem.kullanicilar[kullanici_id].get("ad", "")

    # "YAZ-1 - 3B Yazıcı 1 (YAZICI)"
    def kaynak_yazisi(self, kaynak_id):
        kaynak = self.sistem.kaynaklar[kaynak_id]
        return kaynak_id + " - " + kaynak.get("ad", "") + " (" + kaynak["tur"] + ")"

    # üstteki gün: "Pzt 08.03.2027". Saatin kendisi soldaki beyaz kutuda yazıyor.
    def gun_yazisi(self, zaman):
        return GUNLER[zaman.weekday()] + " " + zaman.strftime("%d.%m.%Y")

    # 1.25 gibi kesirleri gereksiz sıfırlar olmadan yazmak için
    def sayi_yaz(self, sayi):
        return ("%.3f" % float(sayi)).rstrip("0").rstrip(".")

    # Gün listesindeki seçenekler: simüle günden geri_gun kadar geriden, en uzun ileri_gun'e kadar.
    # Sadece kolaylık için, kutuya elle başka bir gün de yazılabiliyor.
    def gun_secenekleri(self, geri_gun):
        en_uzun = 0
        for rol in self.sistem.roller.values():
            en_uzun = max(en_uzun, rol["ileri_gun"])
        liste = []
        for i in range(-geri_gun, en_uzun + 1):
            liste.append((self.sistem.saat + timedelta(days=i)).strftime(GUN_BICIMI))
        return liste

    # 08:00, 08:15 ... 22:00
    def saat_secenekleri(self):
        liste = []
        dakika = S.CALISMA_BASLANGIC_SAAT * 60
        while dakika <= S.CALISMA_BITIS_SAAT * 60:
            liste.append(f"{dakika // 60:02d}:{dakika % 60:02d}")
            dakika += S.ADIM_DK
        return liste

    # Dosyadan yeni sistem kuruyor. Yeni dosya seçilince her şey sıfırdan bu dosyaya göre kuruluyor.
    # Okunamazsa uyarı gösterip False, olursa True döner.
    def sistemi_yukle(self, yol):
        try:
            yeni = dosyadan_sistem_olustur(yol)
            if yeni.saat is None:
                raise ValueError("saat alanı YYYY-AA-GGTSS:DD biçiminde değil")
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as hata:
            messagebox.showerror("Hata", "Dosya okunamadı veya biçimi hatalı.\n\n" + str(hata))
            return False
        self.sistem = yeni
        self.dosya_yolu = yol
        self.paket_kalemleri = []
        self.secili_rezervasyon = None
        self.teklif_komutu = None
        self.takvim_kalici = (TAKVIM_IPUCU, tema.METIN_SOLUK)
        if len(yeni.kullanicilar) > 0:
            self.kullanici_var.set(self.kullanici_yazisi(list(yeni.kullanicilar)[0]))
        else:
            self.kullanici_var.set("")
        if len(yeni.kaynaklar) > 0:
            self.kaynak_var.set(self.kaynak_yazisi(list(yeni.kaynaklar)[0]))
        else:
            self.kaynak_var.set("")
        self.gun_var.set(yeni.saat.strftime(GUN_BICIMI))
        self.takvim_gun_var.set(yeni.saat.strftime(GUN_BICIMI))
        self.hedef_saat_var.set(zamani_metne_cevir(yeni.saat))
        return True

    # Bütün ekranı kurar. Yeni dosya açılınca da çağrılıyor, önce eski parçaları siliyor.
    def arayuzu_kur(self):
        for parca in self.kok.winfo_children():
            parca.destroy()
        tema.stilleri_kur(self.kok)
        self.kaynak_kutulari = []
        self.gun_kutulari = []
        self.kok.title("Kampüs Kaynak Rezervasyon - Kocaeli Üniversitesi - " + os.path.basename(self.dosya_yolu))

        self.menu_kur()
        self.ust_bant_kur()
        self.alt_cubuk_kur()

        self.govde = ttk.PanedWindow(self.kok, orient="horizontal")
        self.govde.pack(fill="both", expand=True, padx=tema.L, pady=(tema.L, tema.S))
        self.govde.add(self.sol_panel_kur(self.govde), weight=5)
        self.govde.add(self.sag_panel_kur(self.govde), weight=8)
        self.yenile()
        self.kok.after(150, self.bolmeleri_ayarla)

    # Sol panelin genişliği ve takvimin yüksekliği. Pencere ekrana çizilmeden winfo_width 1 döndüğü
    # için arayuzu_kur bunu after ile biraz sonra çağırıyor.
    def bolmeleri_ayarla(self):
        genislik = self.govde.winfo_width()
        if genislik > 100:
            self.govde.sashpos(0, int(genislik * 0.38))
        yukseklik = self.sag_bolme.winfo_height()
        if yukseklik > 100:
            gereken = 150 + 36 * (len(self.sistem.kaynaklar) + 1)
            hedef = min(max(yukseklik * 0.6, gereken), yukseklik * 0.75)
            self.sag_bolme.sashpos(0, int(hedef))

    # Dosya menüsü ve Ctrl+O / Ctrl+N / Ctrl+K
    def menu_kur(self):
        cubuk = tk.Menu(self.kok)
        dosya = tk.Menu(cubuk, tearoff=0)
        dosya.add_command(label="Başlangıç dosyası seç...", accelerator="Ctrl+O", command=self.baslangic_dosyasi_ac)
        dosya.add_command(label="Yeni kullanıcı ekle...", accelerator="Ctrl+N", command=self.kullanici_ekle_penceresi)
        dosya.add_command(label="Yeni kaynak ekle...", accelerator="Ctrl+K", command=self.kaynak_ekle_penceresi)
        dosya.add_separator()
        dosya.add_command(label="Kapat", command=self.kok.destroy)
        cubuk.add_cascade(label="Dosya", menu=dosya)
        self.kok.config(menu=cubuk)
        self.kok.bind_all("<Control-o>", lambda olay: self.baslangic_dosyasi_ac())
        self.kok.bind_all("<Control-n>", lambda olay: self.kullanici_ekle_penceresi())
        self.kok.bind_all("<Control-k>", lambda olay: self.kaynak_ekle_penceresi())

    # Koyu zeminde duran düz düğme. ttk düğmesi orada kötü göründüğü için tk.Button kullandık.
    def koyu_dugme(self, ust, yazi, komut):
        dugme = tk.Button(ust, text=yazi, command=komut, relief="flat", bd=0, cursor="hand2",
                          bg="#155F5B", fg=tema.BASLIK_METIN, activebackground=tema.FIRUZE_KOYU,
                          activeforeground="#FFFFFF", font=tema.FONT["kucuk_kalin"], padx=tema.M, pady=tema.XS)
        dugme.bind("<Enter>", lambda olay: dugme.configure(bg="#1C7A74"))
        dugme.bind("<Leave>", lambda olay: dugme.configure(bg="#155F5B"))
        return dugme

    # Üst bant: logo, başlık, saat ilerletme düğmeleri, başlangıç dosyası düğmesi ve simüle günün adı.
    # Simüle saat beyaz kutuda hep yazıyor (PDF 7.6), saat_degisti onu her ilerletmede güncelliyor.
    def ust_bant_kur(self):
        bant = tk.Frame(self.kok, bg=tema.BASLIK_ZEMIN)
        bant.pack(side="top", fill="x")
        ic = tk.Frame(bant, bg=tema.BASLIK_ZEMIN)
        ic.pack(fill="x", padx=tema.XL, pady=tema.S)

        # Kocaeli Üniversitesi logosu; dosya yoksa logosuz devam ediyoruz
        try:
            self.logo_resmi = tk.PhotoImage(file=LOGO_KUCUK)
            tk.Label(ic, image=self.logo_resmi, bg=tema.BASLIK_ZEMIN).pack(side="left", padx=(0, tema.M))
        except tk.TclError:
            self.logo_resmi = None
        tk.Label(ic, text="Kampüs Kaynak Rezervasyon", bg=tema.BASLIK_ZEMIN, fg=tema.BASLIK_METIN,
                 font=tema.FONT["baslik"]).pack(side="left")

        # side="right" ile sağdan sola diziliyor: gün, dosya düğmesi, saat kontrolleri
        self.gun_etiketi = tk.Label(ic, text="", bg=tema.BASLIK_ZEMIN, fg=tema.BASLIK_METIN, font=tema.FONT["baslik"])
        self.gun_etiketi.pack(side="right")
        self.koyu_dugme(ic, "Başlangıç Dosyası Seç", self.baslangic_dosyasi_ac).pack(side="right", padx=tema.L)

        kontrol = tk.Frame(ic, bg=tema.BASLIK_ZEMIN)
        kontrol.pack(side="right", padx=(0, tema.XL))
        for yazi, dakika in (("+15 dk", 15), ("+1 sa", 60), ("+1 gün", 1440)):
            dugme = self.koyu_dugme(kontrol, yazi, lambda dakika=dakika: self.saati_ilerlet_dakika(dakika))
            dugme.pack(side="left", padx=2)
        giris = ttk.Entry(kontrol, textvariable=self.hedef_saat_var, width=17, font=tema.FONT["govde"],
                          justify="center")
        giris.pack(side="left", padx=(tema.M, tema.XS), ipady=2)
        giris.bind("<Return>", lambda olay: self.saati_ilerlet_hedef())
        self.koyu_dugme(kontrol, "Git", self.saati_ilerlet_hedef).pack(side="left")

    # alt çubuk: son işlemin sonucu (başka dosya açmak Dosya menüsünde, Ctrl+O)
    def alt_cubuk_kur(self):
        if self.bildirim_zamanlayici is not None:
            self.kok.after_cancel(self.bildirim_zamanlayici)
            self.bildirim_zamanlayici = None
        self.bildirim = tk.Label(self.kok, text=HAZIR_YAZISI, anchor="w",
                                 justify="left", bg=tema.FIRUZE_ACIK, fg=tema.FIRUZE_KOYU,
                                 font=tema.FONT["govde_kalin"], padx=tema.XL, pady=tema.S)
        self.bildirim.pack(side="bottom", fill="x")

    # Sol taraf: kullanıcı kartı ve altında Tek Talep / Paket / Rezervasyonlarım sekmeleri.
    # Oturum açma yok, kullanıcı listeden seçiliyor (PDF 7.4).
    def sol_panel_kur(self, ust):
        panel = ttk.Frame(ust)

        kart = ttk.Frame(panel, style="Kart.TFrame", padding=tema.L)
        kart.pack(fill="x")
        satir = ttk.Frame(kart, style="Kart.TFrame")
        satir.pack(fill="x")
        ttk.Label(satir, text="Kullanıcı", style="Baslik.TLabel").pack(side="left")
        self.kullanici_kutusu = ttk.Combobox(satir, textvariable=self.kullanici_var, state="readonly", width=20,
                                             font=tema.FONT["govde_kalin"])
        self.kullanici_kutusu.pack(side="right")
        self.kullanici_kutusu.bind("<<ComboboxSelected>>", lambda olay: self.kullanici_secildi())
        ttk.Button(satir, text="+ Yeni", command=self.kullanici_ekle_penceresi).pack(side="right", padx=tema.S)
        ttk.Button(satir, text="Sorgula", command=self.kullanici_sorgula).pack(side="right")
        self.kullanici_bilgi = ttk.Label(kart, text="", style="Soluk.TLabel")
        self.kullanici_bilgi.pack(anchor="w", pady=(tema.XS, tema.M))
        gostergeler = ttk.Frame(kart, style="Kart.TFrame")
        gostergeler.pack(fill="x")
        self.bakiye_gostergesi = self.gosterge_kur(gostergeler, "BAKİYE")
        self.guven_gostergesi = self.gosterge_kur(gostergeler, "GÜVENİLİRLİK")

        self.sol_defter = ttk.Notebook(panel)
        self.sol_defter.pack(fill="both", expand=True, pady=(tema.L, 0))
        tek = ttk.Frame(self.sol_defter, style="Kart.TFrame", padding=tema.L)
        paket = ttk.Frame(self.sol_defter, style="Kart.TFrame", padding=tema.L)
        rezler = ttk.Frame(self.sol_defter, style="Kart.TFrame", padding=tema.L)
        self.sol_defter.add(tek, text="Tek Talep")
        self.sol_defter.add(paket, text="Paket")
        self.sol_defter.add(rezler, text="Rezervasyonlarım")
        self.tek_sekmesi_kur(tek)
        self.paket_sekmesi_kur(paket)
        self.rezervasyon_sekmesi_kur(rezler)
        return panel

    # Bakiye ve güvenilirlik için büyük sayılı kutu, altında doluluk çubuğu. Parçaları bir sözlükte
    # döndürüyoruz ki sonra değerlerini değiştirebilelim.
    def gosterge_kur(self, ust, baslik):
        kutu = tk.Frame(ust, bg=tema.FIRUZE_ACIK)
        kutu.pack(side="left", fill="both", expand=True, padx=(0, tema.M))
        ic = tk.Frame(kutu, bg=tema.FIRUZE_ACIK)
        ic.pack(fill="both", expand=True, padx=tema.L, pady=tema.S)
        satir = tk.Frame(ic, bg=tema.FIRUZE_ACIK)
        satir.pack(fill="x")
        tk.Label(satir, text=baslik, bg=tema.FIRUZE_ACIK, fg=tema.METIN_SOLUK,
                 font=tema.FONT["kucuk_kalin"]).pack(side="left", anchor="s", pady=(0, tema.S))
        birim = tk.Label(satir, text="", bg=tema.FIRUZE_ACIK, fg=tema.METIN_SOLUK, font=tema.FONT["kucuk"])
        birim.pack(side="right", anchor="s", pady=(0, tema.S))
        deger = tk.Label(satir, text="-", bg=tema.FIRUZE_ACIK, fg=tema.METIN, font=tema.FONT["buyuk"])
        deger.pack(side="right", padx=tema.XS)
        cubuk = tk.Canvas(ic, height=6, width=1, bg="#CBE8E4", highlightthickness=0)
        cubuk.pack(fill="x", pady=(tema.XS, 0))
        gosterge = {"deger": deger, "birim": birim, "cubuk": cubuk, "oran": 0.0, "renk": tema.FIRUZE}
        cubuk.bind("<Configure>", lambda olay: self.gostergeyi_ciz(gosterge))
        return gosterge

    # çubuğu orana göre doldur
    def gostergeyi_ciz(self, gosterge):
        cubuk = gosterge["cubuk"]
        cubuk.delete("all")
        dolu = cubuk.winfo_width() * max(0.0, min(1.0, gosterge["oran"]))
        cubuk.create_rectangle(0, 0, dolu, 6, fill=gosterge["renk"], width=0)

    # Kaynak, gün, başlangıç, bitiş. Saatler 15 dakikalık seçeneklerden seçiliyor ama elle de
    # yazılabiliyor; 13:10 gibi yanlış bir saati de modül reddetsin diye.
    # Tek Talep ve Paket sekmeleri aynı değişkenleri paylaşıyor.
    def form_kur(self, ust):
        satir1 = ttk.Frame(ust, style="Kart.TFrame")
        satir1.pack(fill="x")
        ttk.Label(satir1, text="Kaynak", style="Kart.TLabel", width=9).pack(side="left")
        kaynak_kutusu = ttk.Combobox(satir1, textvariable=self.kaynak_var, state="readonly",
                                     font=tema.FONT["govde_kalin"])
        kaynak_kutusu.pack(side="left", fill="x", expand=True)
        self.kaynak_kutulari.append(kaynak_kutusu)

        satir2 = ttk.Frame(ust, style="Kart.TFrame")
        satir2.pack(fill="x", pady=(tema.M, 0))
        ttk.Label(satir2, text="Gün", style="Kart.TLabel", width=9).pack(side="left")
        gun_kutusu = ttk.Combobox(satir2, textvariable=self.gun_var, width=11, justify="center", font=tema.FONT["govde"])
        gun_kutusu.pack(side="left")
        self.gun_kutulari.append(gun_kutusu)
        saatler = self.saat_secenekleri()
        ttk.Label(satir2, text="Başlangıç", style="Kart.TLabel").pack(side="left", padx=(tema.L, tema.XS))
        ttk.Combobox(satir2, textvariable=self.bas_var, values=saatler, width=6, justify="center",
                     font=tema.FONT["govde"]).pack(side="left")
        ttk.Label(satir2, text="Bitiş", style="Kart.TLabel").pack(side="left", padx=(tema.L, tema.XS))
        ttk.Combobox(satir2, textvariable=self.bit_var, values=saatler, width=6, justify="center",
                     font=tema.FONT["govde"]).pack(side="left")

    # sonuçların yazıldığı açık renkli kutu, genişliğe göre satır kaydırıyor
    def sonuc_kutusu(self, ust, ipucu, genisle=True):
        etiket = tk.Label(ust, text=ipucu, bg=tema.YUZEY_ALT, fg=tema.METIN_SOLUK, font=tema.FONT["govde"],
                          justify="left", anchor="nw", padx=tema.L, pady=tema.M)
        etiket.pack(fill="both", expand=genisle, pady=(tema.M, 0))
        etiket.bind("<Configure>", lambda olay: etiket.configure(wraplength=max(100, olay.width - 2 * tema.L)))
        return etiket

    # Tek Talep sekmesi: form, altında canlı ücret, düğmeler ve sonuç kutusu.
    # "Bu talep için bekleme kaydı aç" düğmesi başta gizli, gerekince çıkıyor.
    def tek_sekmesi_kur(self, ust):
        self.form_kur(ust)
        self.onizleme_etiketi = tk.Label(ust, text="", bg=tema.YUZEY, fg=tema.METIN, anchor="w", justify="left",
                                         font=tema.FONT["govde_kalin"])
        self.onizleme_etiketi.pack(fill="x", pady=(tema.M, 0))
        self.onizleme_etiketi.bind("<Configure>",
                                   lambda olay: self.onizleme_etiketi.configure(wraplength=max(100, olay.width)))
        dugmeler = ttk.Frame(ust, style="Kart.TFrame")
        dugmeler.pack(fill="x", pady=(tema.M, 0))
        ttk.Button(dugmeler, text="Fiyatı Gör", command=self.fiyat_gor).pack(side="left")
        ttk.Button(dugmeler, text="Rezervasyon Yap", style="Ana.TButton",
                   command=self.rezervasyon_yap).pack(side="left", padx=tema.M)
        ttk.Button(dugmeler, text="Bekleme Listesine Gir", command=self.beklemeye_gir).pack(side="left")
        # bu düğme sadece KESISME / HAZIRLIK_IHLALI reddinden sonra görünüyor
        self.teklif_dugmesi = ttk.Button(ust, text="Bu talep için bekleme kaydı aç", style="Ana.TButton",
                                         command=self.teklif_edilen_beklemeyi_ac)
        self.tek_sonuc = self.sonuc_kutusu(ust, "Formu doldurunca ücret yukarıda görünür. "
                                                "Fiyatı Gör ile dilim dilim hesabı görebilirsiniz.")

    # Paket sekmesi: aynı form, kalem ekle / sil / temizle, kalem tablosu ve gönder düğmesi.
    def paket_sekmesi_kur(self, ust):
        ttk.Label(ust, text=f"{S.PAKET_EN_AZ}-{S.PAKET_EN_COK} kalem, ya hepsi alınır ya hiçbiri.",
                  style="Soluk.TLabel").pack(anchor="w", pady=(0, tema.S))
        self.form_kur(ust)
        dugmeler = ttk.Frame(ust, style="Kart.TFrame")
        dugmeler.pack(fill="x", pady=tema.M)
        ttk.Button(dugmeler, text="+ Pakete Ekle", command=self.pakete_ekle).pack(side="left")
        ttk.Button(dugmeler, text="Kalemi Sil", command=self.kalemi_sil).pack(side="left", padx=tema.M)
        ttk.Button(dugmeler, text="Temizle", style="Tehlike.TButton", command=self.paketi_temizle).pack(side="left")
        alt = ttk.Frame(ust, style="Kart.TFrame")
        alt.pack(side="bottom", fill="x", pady=(tema.M, 0))
        ttk.Button(alt, text="Paketi Gönder", style="Ana.TButton", command=self.paketi_gonder).pack(side="right",
                                                                                                   anchor="n")
        self.paket_sonuc = self.sonuc_kutusu(alt, "Eklenen her kalemin ücreti tabloda görünür.", genisle=False)
        self.paket_sonuc.pack_configure(side="left", fill="x", expand=True, pady=0, padx=(0, tema.M))
        self.paket_tablosu = self.tablo_kur(ust, [("#", 22, False), ("Kaynak", 50, False), ("Gün", 38, False),
                                                  ("Saat", 74, False), ("Ücret / Sonuç", 170, True)], 3, True)

    # Seçili kullanıcının rezervasyonları ve bekleme kayıtları. Giriş / çıkış / iptal tablodan seçilen
    # rezervasyona yapılıyor, numara yazmak gerekmiyor (PDF 7.5).
    def rezervasyon_sekmesi_kur(self, ust):
        ust_satir = ttk.Frame(ust, style="Kart.TFrame")
        ust_satir.pack(fill="x", pady=(0, tema.S))
        ttk.Label(ust_satir, text="Rezervasyonlar", style="Baslik.TLabel").pack(side="left")
        ttk.Button(ust_satir, text="İptal Et", style="Tehlike.TButton",
                   command=lambda: self.eylem("iptal", "tablo")).pack(side="right")
        ttk.Button(ust_satir, text="Çıkış", command=lambda: self.eylem("cikis", "tablo")).pack(side="right", padx=tema.S)
        ttk.Button(ust_satir, text="Giriş", style="Ana.TButton",
                   command=lambda: self.eylem("giris", "tablo")).pack(side="right")
        self.rez_sonuc = self.sonuc_kutusu(ust, "Tablodan bir rezervasyon seçip işlem yapabilirsiniz.", genisle=False)
        self.rez_sonuc.pack_configure(pady=(0, tema.S))
        self.bek_tablosu = self.tablo_kur(ust, [("No", 28, False), ("Kaynak", 50, False), ("Gün", 38, False),
                                                ("Saat", 74, False), ("Sıra", 40, True)], 2, False, taraf="bottom")
        ttk.Label(ust, text="Bekleme kayıtları", style="Baslik.TLabel").pack(side="bottom", anchor="w",
                                                                           pady=(tema.M, tema.XS))
        self.rez_tablosu = self.tablo_kur(ust, [("No", 28, False), ("Kaynak", 50, False), ("Gün", 38, False),
                                                ("Saat", 74, False), ("Durum", 70, True), ("Ücret", 36, False),
                                                ("Paket", 34, False)], 4, True, tiklaninca=self.rezervasyon_secildi)

    # Izgara gibi tablo, her hücre ayrı bir kutu. Treeview hücre çizgisi çizemediği için Label kullandık:
    # Label'ların arasında 1 piksel boşluk kalınca arkadaki koyu zemin çizgi gibi görünüyor.
    # Kaydırabilmek için Label'lar bir Canvas'ın içindeki Frame'e konuyor.
    # sutunlar (başlık, genişlik, kalın mı) listesi. tiklaninca verilirse satıra tıklanınca o satırın
    # anahtarıyla çağrılıyor. Tablonun parçalarını bir sözlükte döner.
    def tablo_kur(self, ust, sutunlar, yukseklik, genisle, taraf="top", tiklaninca=None):
        cerceve = ttk.Frame(ust, style="Kart.TFrame")
        cerceve.pack(side=taraf, fill="both", expand=genisle)
        tuval = tk.Canvas(cerceve, bg=tema.YUZEY, highlightthickness=0, height=(yukseklik + 1) * 24,
                          yscrollincrement=24)
        kaydirma = ttk.Scrollbar(cerceve, orient="vertical", command=tuval.yview)
        tuval.configure(yscrollcommand=kaydirma.set)
        kaydirma.pack(side="right", fill="y")
        tuval.pack(side="left", fill="both", expand=True)
        ic = tk.Frame(tuval, bg=tema.KENAR)
        pencere = tuval.create_window(0, 0, window=ic, anchor="nw")
        ic.bind("<Configure>", lambda olay: tuval.configure(scrollregion=tuval.bbox("all")))
        tuval.bind("<Configure>", lambda olay: tuval.itemconfigure(pencere, width=olay.width))
        tablo = {"tuval": tuval, "ic": ic, "sutunlar": sutunlar, "tiklaninca": tiklaninca, "secili": None,
                 "kaydir": lambda olay: tuval.yview_scroll(-olay.delta // 120, "units")}
        tuval.bind("<MouseWheel>", tablo["kaydir"])
        self.tabloyu_doldur(tablo, [])
        return tablo

    # Tabloyu baştan doldurur. satirlar (anahtar, değerler, durum) üçlüleri; durum satırın rengini seçiyor
    # (tema.SATIR_RENKLERI), seçili satır turkuaz oluyor. Geniş sütunlarda uzun yazı alt satıra iniyor.
    # sona=True ise en alta kaydırıyor.
    def tabloyu_doldur(self, tablo, satirlar, sona=False):
        tablo["satirlar"] = satirlar
        for parca in tablo["ic"].winfo_children():
            parca.destroy()
        for j in range(len(tablo["sutunlar"])):
            baslik, genislik, kalin = tablo["sutunlar"][j]
            tablo["ic"].grid_columnconfigure(j, minsize=genislik, weight=1)
            tk.Label(tablo["ic"], text=baslik, bg=tema.FIRUZE_ACIK, font=tema.FONT["kucuk_kalin"], anchor="w",
                     padx=tema.S, pady=tema.XS).grid(row=0, column=j, sticky="nsew", padx=(0, 1), pady=(0, 1))
        for i in range(len(satirlar)):
            anahtar, degerler, durum = satirlar[i]
            zemin, yazi_rengi = tema.SATIR_RENKLERI.get(durum, (tema.YUZEY, tema.METIN))
            if anahtar == tablo["secili"]:
                zemin = tema.FIRUZE
            for j in range(len(degerler)):
                baslik, genislik, kalin = tablo["sutunlar"][j]
                hucre = tk.Label(tablo["ic"], text=degerler[j], bg=zemin, fg=yazi_rengi, anchor="w", justify="left",
                                 font=tema.FONT["govde_kalin" if kalin else "govde"],
                                 wraplength=genislik if genislik >= 150 else 0,
                                 padx=tema.S, pady=tema.XS)
                hucre.grid(row=i + 1, column=j, sticky="nsew", padx=(0, 1), pady=(0, 1))
                hucre.bind("<Button-1>", lambda olay, a=anahtar: self.satir_tiklandi(tablo, a))
                hucre.bind("<MouseWheel>", tablo["kaydir"])
        if sona:
            tablo["ic"].update_idletasks()
            tablo["tuval"].configure(scrollregion=tablo["tuval"].bbox("all"))
            tablo["tuval"].yview_moveto(1.0)

    # Satıra tıklanınca o satırı seçili yapar. Tablo tıklanan Label'ı silip yeniden çizeceği için
    # yeniden çizmeyi after_idle ile olay bittikten sonraya bırakıyoruz.
    def satir_tiklandi(self, tablo, anahtar):
        tablo["secili"] = anahtar
        if tablo["tiklaninca"] is not None:
            tablo["tiklaninca"](anahtar)
        self.kok.after_idle(lambda: self.tabloyu_doldur(tablo, tablo["satirlar"]))

    # Sağ taraf. Üstte takvim kartı: gün seçimi, + Kaynak, renk açıklaması, takvim ve altında seçili
    # rezervasyon satırı ile giriş / çıkış / iptal. Altta Saat Olayları ve Olay Günlüğü sekmeleri.
    def sag_panel_kur(self, ust):
        self.sag_bolme = ttk.PanedWindow(ust, orient="vertical")
        takvim_karti = ttk.Frame(self.sag_bolme, style="Kart.TFrame", padding=tema.L)
        alt = ttk.Frame(self.sag_bolme)
        self.sag_bolme.add(takvim_karti, weight=8)
        self.sag_bolme.add(alt, weight=5)

        ust_satir = ttk.Frame(takvim_karti, style="Kart.TFrame")
        ust_satir.pack(fill="x")
        ttk.Label(ust_satir, text="Kaynak Takvimi", style="Baslik.TLabel").pack(side="left")
        ttk.Button(ust_satir, text="+ Kaynak", command=self.kaynak_ekle_penceresi).pack(side="left", padx=tema.L)
        gezinti = ttk.Frame(ust_satir, style="Kart.TFrame")
        gezinti.pack(side="right")
        ttk.Button(gezinti, text="<", width=3, command=lambda: self.takvim_gun_kaydir(-1)).pack(side="left")
        self.takvim_gun_kutusu = ttk.Combobox(gezinti, textvariable=self.takvim_gun_var, width=11,
                                              justify="center", font=tema.FONT["govde"])
        self.takvim_gun_kutusu.pack(side="left", padx=tema.XS)
        self.takvim_gun_kutusu.bind("<<ComboboxSelected>>", lambda olay: self.takvim.ciz())
        self.takvim_gun_kutusu.bind("<Return>", lambda olay: self.takvim.ciz())
        ttk.Button(gezinti, text=">", width=3, command=lambda: self.takvim_gun_kaydir(1)).pack(side="left")
        ttk.Button(gezinti, text="Bugün", command=self.takvim_bugune).pack(side="left", padx=(tema.M, 0))

        self.lejant_kur(takvim_karti)
        # seçili rezervasyon satırı takvimin altında; önce bunu "bottom" ile koyuyoruz ki takvim kalan yeri alsın
        secim = ttk.Frame(takvim_karti, style="Kart.TFrame")
        secim.pack(side="bottom", fill="x", pady=(tema.S, 0))
        ttk.Button(secim, text="İptal Et", style="Tehlike.TButton",
                   command=lambda: self.eylem("iptal", "takvim")).pack(side="right")
        ttk.Button(secim, text="Çıkış", command=lambda: self.eylem("cikis", "takvim")).pack(side="right", padx=tema.S)
        ttk.Button(secim, text="Giriş", style="Ana.TButton",
                   command=lambda: self.eylem("giris", "takvim")).pack(side="right")
        self.takvim_bilgi = ttk.Label(secim, text=TAKVIM_IPUCU, style="Soluk.TLabel", anchor="w")
        self.takvim_bilgi.pack(side="left", fill="x", expand=True)
        self.takvim_bilgi.bind("<Configure>", lambda olay: self.takvim_bilgi.configure(wraplength=max(100, olay.width)))
        self.takvim = Takvim(takvim_karti, self)

        self.sag_defter = ttk.Notebook(alt)
        self.sag_defter.pack(fill="both", expand=True, pady=(tema.L, 0))
        olaylar = ttk.Frame(self.sag_defter, style="Kart.TFrame", padding=tema.M)
        gunluk = ttk.Frame(self.sag_defter, style="Kart.TFrame", padding=tema.M)
        self.sag_defter.add(olaylar, text="Saat Olayları")
        self.sag_defter.add(gunluk, text="Olay Günlüğü")
        self.olay_tablosu = self.tablo_kur(olaylar, [("#", 22, False), ("Zaman", 82, False), ("Olay", 100, True),
                                                     ("Rezervasyon", 76, False), ("Kullanıcı", 60, False),
                                                     ("Ayrıntı", 230, False)], 4, True)

        json_alani = ttk.Frame(gunluk, style="Kart.TFrame")
        json_alani.pack(side="right", fill="both", padx=(tema.M, 0))
        gunluk_tablo_alani = ttk.Frame(gunluk, style="Kart.TFrame")
        gunluk_tablo_alani.pack(side="left", fill="both", expand=True)
        self.gunluk_tablosu = self.tablo_kur(gunluk_tablo_alani, [("#", 22, False), ("Komut", 80, False),
                                                                  ("Durum", 54, True), ("Ayrıntı", 230, False)],
                                             4, True, tiklaninca=self.gunluk_secildi)
        self.json_kutusu = tk.Text(json_alani, width=34, height=6, font=tema.FONT["mono"], bg=tema.YUZEY_ALT,
                                   fg=tema.METIN, relief="flat", wrap="char", padx=tema.M, pady=tema.M)
        self.json_kutusu.pack(fill="both", expand=True)
        self.json_yaz("Bir satır seçin; komut ve modülün döndürdüğü sonuç JSON olarak burada görünür.")
        return self.sag_bolme

    # takvimdeki renklerin açıklaması
    def lejant_kur(self, ust):
        satir = ttk.Frame(ust, style="Kart.TFrame")
        satir.pack(fill="x", pady=(tema.S, 0))
        ogeler = []
        for durum in ("ONAYLI", "KULLANIMDA", "TAMAMLANDI", "GELMEDI", "IPTAL"):
            ogeler.append((tema.DURUM_RENKLERI[durum][0], "", DURUMLAR[durum]))
        ogeler.append((tema.KEHRIBAR, "gray50", "Bakım"))
        ogeler.append((tema.HAZIRLIK, "gray50", "Hazırlık"))
        ogeler.append((tema.PIK, "", "Pik saat"))
        ogeler.append((tema.GIRIS, "gray50", "Erken / geç giriş"))
        ogeler.append((tema.MERCAN, "", "Şimdi"))
        for renk, desen, ad in ogeler:
            kare = tk.Canvas(satir, width=13, height=13, bg=tema.YUZEY, highlightthickness=0)
            kare.create_rectangle(1, 1, 12, 12, fill=renk, outline=renk, stipple=desen)
            kare.pack(side="left", padx=(tema.S, tema.XS))
            ttk.Label(satir, text=ad, style="Soluk.TLabel").pack(side="left")

    # Durumu değiştiren her işlemden sonra (komut_gonder) çağrılıyor. Saat, listeler, panel, paket
    # tablosu, olaylar, günlük ve takvim kendiliğinden yenileniyor, kullanıcının bir şey yapmasına gerek yok.
    def yenile(self):
        if self.sistem is None:
            return
        self.gun_etiketi.configure(text=self.gun_yazisi(self.sistem.saat))
        kullanici_listesi = []
        for kullanici_id in self.sistem.kullanicilar:
            kullanici_listesi.append(self.kullanici_yazisi(kullanici_id))
        self.kullanici_kutusu["values"] = kullanici_listesi
        kaynak_listesi = []
        for kaynak_id in self.sistem.kaynaklar:
            kaynak_listesi.append(self.kaynak_yazisi(kaynak_id))
        for kutu in self.kaynak_kutulari:
            kutu["values"] = kaynak_listesi
        for kutu in self.gun_kutulari:
            kutu["values"] = self.gun_secenekleri(0)
        self.takvim_gun_kutusu["values"] = self.gun_secenekleri(7)
        self.kullanici_panelini_yenile()
        self.paket_tablosunu_yenile()
        self.olaylari_yenile()
        self.gunlugu_yenile()
        self.secili_bilgisini_yaz()
        self.onizleme_guncelle()
        self.takvim.ciz()

    # Seçili kullanıcının rolü, sertifikaları, bakiye ve güvenilirlik göstergeleri, rezervasyon ve
    # bekleme tabloları. Güvenilirlik 50'nin altına inerse gösterge kırmızı oluyor.
    def kullanici_panelini_yenile(self):
        kullanici_id = self.secili_id(self.kullanici_var)
        kullanici = self.sistem.kullanicilar.get(kullanici_id)
        if kullanici is None:
            self.kullanici_bilgi.configure(text="Kullanıcı yok. + Yeni ile ekleyebilirsiniz.")
            return
        sertifikalar = ", ".join(kullanici.get("sertifikalar", []))
        if sertifikalar == "":
            sertifikalar = "yok"
        self.kullanici_bilgi.configure(text=kullanici["rol"] + "   |   Sertifikalar: " + sertifikalar)

        kota = self.sistem.roller[kullanici["rol"]]["haftalik_kota"]
        self.bakiye_gostergesi["deger"].configure(text=str(kullanici["bakiye"]))
        self.bakiye_gostergesi["birim"].configure(text="/ " + str(kota) + " KP")
        if kota:
            self.bakiye_gostergesi["oran"] = kullanici["bakiye"] / kota
        else:
            self.bakiye_gostergesi["oran"] = 0
        self.gostergeyi_ciz(self.bakiye_gostergesi)

        # güvenilirlik 50'nin altındaysa kırmızı (ileri tarih 1 gün, paket yok)
        guv = kullanici["guvenilirlik"]
        self.guven_gostergesi["deger"].configure(text=str(guv))
        self.guven_gostergesi["birim"].configure(text="/ " + str(S.GUV_EN_COK))
        self.guven_gostergesi["oran"] = guv / S.GUV_EN_COK
        if guv < S.GUV_ESIK:
            self.guven_gostergesi["renk"] = tema.MERCAN
            self.guven_gostergesi["deger"].configure(fg=tema.MERCAN_KOYU)
        else:
            self.guven_gostergesi["renk"] = tema.FIRUZE
            self.guven_gostergesi["deger"].configure(fg=tema.METIN)
        self.gostergeyi_ciz(self.guven_gostergesi)

        satirlar = []
        for rez in self.sistem.kullanici_rezervasyonlari(kullanici_id):
            saatler = rez["baslangic"].strftime("%H:%M") + "-" + rez["bitis"].strftime("%H:%M")
            satirlar.append((rez["id"], [rez["id"], rez["kaynak"], rez["baslangic"].strftime("%d.%m"), saatler,
                                         DURUMLAR[rez["durum"]], rez["ucret"], rez["paket"] or ""], rez["durum"]))
        self.rez_tablosu["secili"] = self.secili_rezervasyon
        self.tabloyu_doldur(self.rez_tablosu, satirlar)

        satirlar = []
        for kayit, sira in self.sistem.kullanici_beklemeleri(kullanici_id):
            saatler = kayit["baslangic"].strftime("%H:%M") + "-" + kayit["bitis"].strftime("%H:%M")
            satirlar.append((kayit["id"], [kayit["id"], kayit["kaynak"], kayit["baslangic"].strftime("%d.%m"),
                                           saatler, sira], ""))
        self.tabloyu_doldur(self.bek_tablosu, satirlar)

    # Paket tablosu. Gönderilmemiş kalemlerin ücreti fiyat fonksiyonuyla o anki duruma göre hesaplanıp
    # altta tahmini toplam yazıyor (1. sürümdeki "Paket Fiyatı" düğmesinin yerine).
    # Paket gönderilip reddedildiyse her kalemin satırında modülün verdiği sonuç görünüyor.
    def paket_tablosunu_yenile(self):
        satirlar = []
        toplam = 0
        gecmeyen = 0
        gonderildi = False
        for i in range(len(self.paket_kalemleri)):
            kalem = self.paket_kalemleri[i]
            etiket = ""
            if "sonuc" in kalem:
                gonderildi = True
                yazi = kalem["sonuc"]
                if kalem["red"]:
                    etiket = "RED"
            else:
                komut = {"kullanici": self.secili_id(self.kullanici_var), "kaynak": kalem["kaynak"],
                         "baslangic": kalem["baslangic"], "bitis": kalem["bitis"]}
                onizleme = self.sistem.komut_fiyat(komut)
                if onizleme["durum"] == S.TAMAM:
                    yazi = str(onizleme["ucret"]) + " KP"
                    toplam += onizleme["ucret"]
                else:
                    yazi = "geçmez: " + onizleme["kod"]
                    etiket = "RED"
                    gecmeyen += 1
            gun = kalem["baslangic"][8:10] + "." + kalem["baslangic"][5:7]
            satirlar.append((i, [i + 1, kalem["kaynak"], gun, kalem["baslangic"][11:] + "-" + kalem["bitis"][11:],
                                 yazi], etiket))
        self.tabloyu_doldur(self.paket_tablosu, satirlar)

        # gönderilmeden önceki durumda alttaki kutuda tahmini toplamı gösteriyoruz
        if len(self.paket_kalemleri) > 0 and not gonderildi:
            yazi = str(len(self.paket_kalemleri)) + " kalem  |  tahmini toplam: " + str(toplam) + " KP"
            if gecmeyen > 0:
                yazi += "  |  " + str(gecmeyen) + " kalem şu an geçmiyor"
            self.kutuya_yaz(self.paket_sonuc, yazi, "notr")

    # Saat Olayları tablosu: sonuçların içindeki bütün olaylar (gelmedi, tamamlandı, haftalık
    # sıfırlama, otomatik atama).
    def olaylari_yenile(self):
        satirlar = []
        for kayit in self.sistem.gunluk:
            for olay in kayit["sonuc"].get("olaylar", []):
                zaman = olay["zaman"][8:10] + "." + olay["zaman"][5:7] + " " + olay["zaman"][11:]
                satirlar.append((len(satirlar), [len(satirlar) + 1, zaman, OLAYLAR.get(olay["tur"], olay["tur"]),
                                                 olay.get("rezervasyon", "-"), olay.get("kullanici", "-"),
                                                 self.olay_yazisi(olay)], olay["tur"]))
        self.tabloyu_doldur(self.olay_tablosu, satirlar, sona=True)

    # Olay günlüğü (PDF 7.7). Satırın anahtarı sonucun no değeri, gunluk_secildi onu kullanıyor.
    # Ayrıntı sütununda önce talebin kendisi (kim, hangi kaynak, ne zaman), sonra sonucu yazıyor.
    def gunlugu_yenile(self):
        satirlar = []
        for kayit in self.sistem.gunluk:
            sonuc = kayit["sonuc"]
            if sonuc["durum"] == S.RED:
                ayrinti = self.talep_yazisi(kayit["komut"]) + self.hata_yazisi(sonuc, kayit["komut"].get("kullanici"))
            else:
                ayrinti = self.talep_yazisi(kayit["komut"]) + self.ozet_yaz(kayit["komut"], sonuc)
            satirlar.append((sonuc["no"], [sonuc["no"], KOMUTLAR.get(sonuc["komut"], str(sonuc["komut"])),
                                           DURUMLAR[sonuc["durum"]], ayrinti], sonuc["durum"]))
        self.tabloyu_doldur(self.gunluk_tablosu, satirlar, sona=True)

    # Günlükte talebin kendisini kısaca yazar: "u1, YAZ-1, 08.03 11:00-13:00 -> " gibi.
    # Rezervasyona yapılan işlemlerde (giriş, iptal...) sadece rezervasyon numarası.
    def talep_yazisi(self, komut):
        if not isinstance(komut, dict):
            return ""
        if "baslangic" in komut and "bitis" in komut:
            bas = str(komut["baslangic"])
            return (str(komut.get("kullanici")) + ", " + str(komut.get("kaynak")) + ", " + bas[8:10] + "." +
                    bas[5:7] + " " + bas[11:] + "-" + str(komut["bitis"])[11:] + " -> ")
        if "rezervasyon" in komut:
            return str(komut["rezervasyon"]) + " -> "
        return ""

    # JSON kutusuna yaz. Kutu salt okunur, yazarken bir anlığına açıyoruz.
    def json_yaz(self, yazi):
        self.json_kutusu.configure(state="normal")
        self.json_kutusu.delete("1.0", "end")
        self.json_kutusu.insert("1.0", yazi)
        self.json_kutusu.configure(state="disabled")

    # Arayüzden modüle giden her komut buradan geçiyor. Saat değiştiyse takvim o güne geliyor, sonra
    # ekran yenileniyor ve sonuç alt çubukta gösteriliyor. Modülün sonucunu döner.
    def komut_gonder(self, komut):
        sonuc = self.sistem.komut_calistir(komut)
        if sonuc.get("komut") == "saat" and sonuc["durum"] == S.TAMAM:
            self.saat_degisti()
            self.sag_defter.select(0)
        self.yenile()
        self.bildir(komut, sonuc)
        return sonuc

    # saat ilerleyince takvim ve formdaki gün de yeni güne gelsin
    def saat_degisti(self):
        bugun = self.sistem.saat.strftime(GUN_BICIMI)
        self.takvim_gun_var.set(bugun)
        if self.gun_var.get() < bugun:
            self.gun_var.set(bugun)
        self.hedef_saat_var.set(zamani_metne_cevir(self.sistem.saat))

    # Bir olayın kısa Türkçe hali. Otomatik atamada bekleme -> rezervasyon, ücret ve bakiye yazıyor.
    def olay_yazisi(self, olay):
        if olay["tur"] == S.OTOMATIK_ATAMA:
            return (olay["bekleme"] + " -> " + olay["rezervasyon"] + " (" + olay["kullanici"] + ")  |  " +
                    str(olay["ucret"]) + " KP  |  bakiye " + str(olay["bakiye"]))
        if olay["tur"] == S.HAFTALIK_SIFIRLAMA:
            return "Bütün bakiyeler haftalık kotaya eşitlendi"
        return "güvenilirlik " + str(olay.get("guvenilirlik"))

    # iptal / çıkış sonrası otomatik atamalar tek yazıda, yoksa "otomatik atama yok"
    def atama_yazisi(self, olaylar):
        if len(olaylar) == 0:
            return "  |  otomatik atama yok"
        parcalar = []
        for olay in olaylar:
            parcalar.append(self.olay_yazisi(olay))
        return "  |  OTOMATIK_ATAMA: " + ";  ".join(parcalar)

    # TAMAM sonucunun kısa özeti. Her komutun sonucunda farklı alanlar olduğu için tek tek yazdık.
    # komut da lazım, çünkü kullanici_ekle ve kaynak_ekle sonucunda id yok.
    def ozet_yaz(self, komut, sonuc):
        ad = sonuc.get("komut")
        if ad == "rezervasyon":
            return (sonuc["rezervasyon_id"] + " oluşturuldu  |  ücret " + str(sonuc["ucret"]) +
                    " KP  |  yeni bakiye " + str(sonuc["bakiye"]) + " KP")
        if ad == "paket":
            ucretler = []
            for ucret in sonuc["ucretler"]:
                ucretler.append(str(ucret))
            return ("Paket " + sonuc["paket_id"] + ": " + ", ".join(sonuc["rezervasyonlar"]) + "  |  ücretler " +
                    ", ".join(ucretler) + "  |  toplam " + str(sonuc["toplam"]) + " KP  |  yeni bakiye " +
                    str(sonuc["bakiye"]) + " KP")
        if ad == "fiyat":
            return "Ücret: " + str(sonuc["ucret"]) + " KP"
        if ad == "iptal":
            return ("İptal edildi  |  iade " + str(sonuc["iade"]) + " KP  |  bakiye " + str(sonuc["bakiye"]) +
                    " KP  |  güvenilirlik " + str(sonuc["guvenilirlik"]) + self.atama_yazisi(sonuc["olaylar"]))
        if ad == "giris":
            return "Giriş yapıldı, yeni durum: " + DURUMLAR[sonuc["yeni_durum"]]
        if ad == "cikis":
            return ("Çıkış yapıldı, yeni durum: " + DURUMLAR[sonuc["yeni_durum"]] + "  |  güvenilirlik " +
                    str(sonuc["guvenilirlik"]) + self.atama_yazisi(sonuc["olaylar"]))
        if ad == "bekleme":
            return "Bekleme kaydı " + sonuc["bekleme_id"] + " açıldı  |  sıra " + str(sonuc["sira"])
        if ad == "saat":
            return "Saat ilerletildi  |  " + str(len(sonuc["olaylar"])) + " olay"
        if ad == "sorgu" and "rezervasyonlar" in sonuc:
            parcalar = []
            for rez in sonuc["rezervasyonlar"]:
                parcalar.append(rez["id"] + " " + DURUMLAR[rez["durum"]] + " " + str(rez["ucret"]))
            return (str(komut.get("id")) + ": bakiye " + str(sonuc["bakiye"]) + " KP  |  güvenilirlik " +
                    str(sonuc["guvenilirlik"]) + "  |  " + (", ".join(parcalar) or "rezervasyon yok"))
        if ad == "sorgu":
            parcalar = []
            for kutu in sonuc["doluluk"]:
                parca = kutu["baslangic"][11:] + "-" + kutu["bitis"][11:] + " "
                if kutu["tur"] == S.KUTU_BAKIM:
                    parca += "bakım"
                else:
                    parca += kutu["rezervasyon"]
                parcalar.append(parca)
            return (str(komut.get("id")) + " " + str(komut.get("gun")) + " doluluk: " +
                    (", ".join(parcalar) or "boş"))
        if ad == "kullanici_ekle":
            return str(komut.get("id")) + " kullanıcısı eklendi"
        if ad == "kaynak_ekle":
            return str(komut.get("id")) + " kaynağı eklendi"
        return "Tamam"

    # Sonucu alt çubuğa yazar: TAMAM ise özet, RED ise kod ve Türkçe açıklama.
    def bildir(self, komut, sonuc):
        ad = KOMUTLAR.get(sonuc.get("komut"), str(sonuc.get("komut")))
        if sonuc["durum"] == S.RED:
            self.bildir_yazi("RED  |  " + ad + "  |  " + self.hata_yazisi(sonuc), basarili=False)
        else:
            self.bildir_yazi("TAMAM  |  " + self.ozet_yaz(komut, sonuc), basarili=True)

    # Alt çubuğa yazı: başarılıysa yeşil, hataysa kırmızı üstüne siyah kalın yazı. Hata 10 saniye
    # kalıyor, sonra çubuk "Hazır" haline dönüyor; arada yeni bir sonuç gelirse o yazılıyor.
    def bildir_yazi(self, yazi, basarili):
        if self.bildirim_zamanlayici is not None:
            self.kok.after_cancel(self.bildirim_zamanlayici)
            self.bildirim_zamanlayici = None
        if basarili:
            self.bildirim.configure(text=yazi, bg=tema.FIRUZE_ACIK, fg=tema.FIRUZE_KOYU)
        else:
            self.bildirim.configure(text=yazi, bg=tema.MERCAN, fg="#000000")
            self.bildirim_zamanlayici = self.kok.after(HATA_SURESI_MS, self.bildirimi_sakinlestir)

    # 10 saniye dolunca alt çubuğu ilk haline getirir
    def bildirimi_sakinlestir(self):
        self.bildirim_zamanlayici = None
        self.bildirim.configure(text=HAZIR_YAZISI, bg=tema.FIRUZE_ACIK, fg=tema.FIRUZE_KOYU)

    # "KESISME: Bu aralıkta ..." gibi kod ve Türkçe açıklaması (açıklamalar arayuz/turkce_metinler.py'de).
    # İleri tarih hatasında kullanıcının kaç gün ilerisini alabildiğini de yazıyoruz; gün sayısı modülün
    # ileri_gun_siniri fonksiyonundan geliyor (rol ve güvenilirliğe göre). kullanici_id verilmezse seçili kullanıcı.
    def hata_yazisi(self, sonuc, kullanici_id=None):
        kod = sonuc.get("kod", "")
        yazi = kod + ": " + HATALAR.get(kod, kod)
        if kullanici_id is None:
            kullanici_id = self.secili_id(self.kullanici_var)
        kullanici = self.sistem.kullanicilar.get(kullanici_id)
        if kod == "ILERI_TARIH_SINIRI" and kullanici is not None:
            yazi += " Bu kullanıcı en fazla " + str(self.sistem.ileri_gun_siniri(kullanici)) + " gün sonrasını alabilir."
        return yazi

    # Sonuç kutusuna yazar. durum "tamam" ise yeşil, "red" ise kırmızı, başka bir şeyse gri.
    def kutuya_yaz(self, etiket, yazi, durum):
        if durum == "tamam":
            etiket.configure(text=yazi, bg=tema.FIRUZE_ACIK, fg=tema.METIN)
        elif durum == "red":
            etiket.configure(text=yazi, bg=tema.MERCAN_ACIK, fg=tema.MERCAN_KOYU)
        else:
            etiket.configure(text=yazi, bg=tema.YUZEY_ALT, fg=tema.METIN_SOLUK)

    # Formdaki değerlerden komut sözlüğü yapar. Ne yazıyorsa öyle gönderiyoruz, kontrol modülde.
    def talep_komutu(self, komut_adi):
        gun = self.gun_var.get().strip()
        return {
            "komut": komut_adi,
            "kullanici": self.secili_id(self.kullanici_var),
            "kaynak": self.secili_id(self.kaynak_var),
            "baslangic": gun + "T" + self.bas_var.get().strip(),
            "bitis": gun + "T" + self.bit_var.get().strip(),
        }

    # Form değişince eski bekleme önerisini kaldır, ücreti yeniden göster.
    # trace_add üç değer gönderiyor, kullanmıyoruz (*args).
    def form_degisti(self, *args):
        self.bekleme_teklifini_gizle()
        self.onizleme_guncelle()

    # Göndermeden önce ücreti gösteriyor (PDF 7.3). komut_fiyat'ı komut_calistir'dan geçirmeden
    # doğrudan çağırıyoruz, böylece günlüğe yazılmıyor. Yazılsaydı formdaki her değişiklikte günlüğe
    # bir satır düşer, örnek senaryodaki no değerleri kayardı.
    def onizleme_guncelle(self):
        if self.onizleme_etiketi is None or self.sistem is None:
            return
        sonuc = self.sistem.komut_fiyat(self.talep_komutu("fiyat"))
        if sonuc["durum"] == S.TAMAM:
            self.onizleme_etiketi.configure(text="Ücret: " + str(sonuc["ucret"]) + " KP", fg=tema.FIRUZE_KOYU)
        else:
            self.onizleme_etiketi.configure(text="Bu haliyle geçmez: " + self.hata_yazisi(sonuc), fg=tema.MERCAN_KOYU)

    # Ücretin dilim dilim nasıl çıktığı. Aynı bant ve çarpana düşen dilimleri birleştiriyoruz ki 8 satır
    # yerine 1-2 satır olsun. (satırlar, yuvarlanmamış toplam) döner.
    def fiyat_detayi(self, komut):
        bas = metni_zamana_cevir(komut["baslangic"])
        bit = metni_zamana_cevir(komut["bitis"])
        gruplar = []
        for dilim in self.sistem.ucret_dilimleri(komut["kaynak"], bas, bit):
            anahtar = (dilim["bant_baslangic"], dilim["bant_carpani"], dilim["pik_carpani"])
            if gruplar and gruplar[-1]["anahtar"] == anahtar:
                gruplar[-1]["adet"] += 1
                gruplar[-1]["tutar"] += dilim["tutar"]
            else:
                gruplar.append({"anahtar": anahtar, "dilim": dilim, "adet": 1, "tutar": dilim["tutar"]})
        satirlar = []
        toplam = 0
        for grup in gruplar:
            dilim = grup["dilim"]
            toplam += grup["tutar"]
            bant = dilim["bant_baslangic"].strftime("%H:%M") + "-" + dilim["bant_bitis"].strftime("%H:%M")
            satirlar.append(bant + " bandı: doluluk " + str(dilim["dolu_dk"]) + "/" + str(dilim["kapasite_dk"]) +
                            " dk, bant x" + self.sayi_yaz(dilim["bant_carpani"]) + ", pik x" +
                            self.sayi_yaz(dilim["pik_carpani"]) + ", " + str(grup["adet"]) + " dilim = " +
                            self.sayi_yaz(grup["tutar"]))
        return satirlar, self.sayi_yaz(toplam)

    # "Fiyatı Gör" düğmesi. Bu sefer fiyat komutu günlüğe yazılıyor, dilim hesabı da gösteriliyor.
    def fiyat_gor(self):
        komut = self.talep_komutu("fiyat")
        sonuc = self.komut_gonder(komut)
        if sonuc["durum"] == S.RED:
            self.kutuya_yaz(self.tek_sonuc, self.hata_yazisi(sonuc), "red")
            return
        satirlar, toplam = self.fiyat_detayi(komut)
        yazi = ("Ücret: " + str(sonuc["ucret"]) + " KP\n\n" + "\n".join(satirlar) + "\n" +
                "Toplam " + toplam + ", yuvarlanınca " + str(sonuc["ucret"]) + " KP")
        self.kutuya_yaz(self.tek_sonuc, yazi, "tamam")

    # "Rezervasyon Yap". Kabul edilirse numara, ücret ve yeni bakiye yazıyor. KESISME ya da
    # HAZIRLIK_IHLALI ile reddedilirse aynı talep için bekleme kaydı öneriliyor (PDF 7.5).
    def rezervasyon_yap(self):
        komut = self.talep_komutu("rezervasyon")
        sonuc = self.komut_gonder(komut)
        if sonuc["durum"] == S.RED:
            self.kutuya_yaz(self.tek_sonuc, self.hata_yazisi(sonuc), "red")
            if sonuc["kod"] in BEKLEME_ONERILEN_KODLAR:
                self.bekleme_teklifini_goster(komut)
        else:
            self.secili_rezervasyon = sonuc["rezervasyon_id"]
            self.kutuya_yaz(self.tek_sonuc, self.ozet_yaz(komut, sonuc), "tamam")
            self.secili_bilgisini_yaz()
            self.takvim.ciz()

    # reddedilen talebi saklayıp öneri düğmesini gösteriyor, kullanıcı tekrar bir şey girmiyor
    def bekleme_teklifini_goster(self, komut):
        self.teklif_komutu = dict(komut)
        self.teklif_dugmesi.configure(text="Bu talep için bekleme kaydı aç (" + komut["kaynak"] + " " +
                                           komut["baslangic"][11:] + "-" + komut["bitis"][11:] + ")")
        self.teklif_dugmesi.pack(fill="x", pady=(tema.M, 0), before=self.tek_sonuc)

    # öneri düğmesini sakla
    def bekleme_teklifini_gizle(self):
        self.teklif_komutu = None
        if getattr(self, "teklif_dugmesi", None) is not None and self.teklif_dugmesi.winfo_exists():
            self.teklif_dugmesi.pack_forget()

    # Öneriye basılınca saklanan talep bekleme komutu olarak gidiyor.
    def teklif_edilen_beklemeyi_ac(self):
        if self.teklif_komutu is None:
            return
        komut = dict(self.teklif_komutu)
        komut["komut"] = "bekleme"
        self.bekleme_teklifini_gizle()
        sonuc = self.komut_gonder(komut)
        if sonuc["durum"] == S.RED:
            self.kutuya_yaz(self.tek_sonuc, self.hata_yazisi(sonuc), "red")
        else:
            self.kutuya_yaz(self.tek_sonuc, self.ozet_yaz(komut, sonuc), "tamam")

    # "Bekleme Listesine Gir": formdaki aralık için doğrudan bekleme kaydı
    def beklemeye_gir(self):
        komut = self.talep_komutu("bekleme")
        sonuc = self.komut_gonder(komut)
        if sonuc["durum"] == S.RED:
            self.kutuya_yaz(self.tek_sonuc, self.hata_yazisi(sonuc), "red")
        else:
            self.kutuya_yaz(self.tek_sonuc, self.ozet_yaz(komut, sonuc), "tamam")

    # Formdaki aralığı pakete ekler, modüle henüz bir şey gitmiyor. Aynı kaynak ve aynı saatler
    # listede zaten varsa ikinci kez eklemiyor, "zaten seçildi" yazıyor.
    def pakete_ekle(self):
        komut = self.talep_komutu("kalem")
        for kalem in self.paket_kalemleri:
            if (kalem["kaynak"], kalem["baslangic"], kalem["bitis"]) == (komut["kaynak"], komut["baslangic"], komut["bitis"]):
                self.kutuya_yaz(self.paket_sonuc, "Bu kalem zaten seçildi: " + str(komut["kaynak"]) + " " +
                                komut["baslangic"][-5:] + "-" + komut["bitis"][-5:], "red")
                return
        self.paket_kalemleri.append({"kaynak": komut["kaynak"], "baslangic": komut["baslangic"],
                                     "bitis": komut["bitis"]})
        self.paket_sonuclarini_sil()

    # tabloda seçili kalemi paketten çıkar
    def kalemi_sil(self):
        secili = self.paket_tablosu["secili"]
        if secili is None or secili >= len(self.paket_kalemleri):
            self.kutuya_yaz(self.paket_sonuc, "Silmek için tablodan bir kalem seçin.", "red")
            return
        self.paket_kalemleri.pop(secili)
        self.paket_tablosu["secili"] = None
        self.paket_sonuclarini_sil()

    # hepsini sil
    def paketi_temizle(self):
        self.paket_kalemleri = []
        self.paket_sonuclarini_sil()

    # Kalemler değişince eski gönderim sonuçlarını unut, tablo yine önizleme göstersin.
    def paket_sonuclarini_sil(self):
        for kalem in self.paket_kalemleri:
            kalem.pop("sonuc", None)
            kalem.pop("red", None)
        if len(self.paket_kalemleri) == 0:
            self.kutuya_yaz(self.paket_sonuc, "Paket boş. Formu doldurup + Pakete Ekle ile kalem ekleyin.", "notr")
        self.paket_tablosunu_yenile()

    # Paketi gönderir. Kabul edilirse kalemler temizleniyor. Reddedilirse modülün kalemler listesi
    # her kalemin kendi satırına yazılıyor: geçen TAMAM, geçmeyen RED, kodu ve Türkçe sebebi (PDF 7.3).
    def paketi_gonder(self):
        kalemler = []
        for kalem in self.paket_kalemleri:
            kalemler.append({"kaynak": kalem["kaynak"], "baslangic": kalem["baslangic"], "bitis": kalem["bitis"]})
        komut = {"komut": "paket", "kullanici": self.secili_id(self.kullanici_var), "kalemler": kalemler}
        sonuc = self.komut_gonder(komut)
        if sonuc["durum"] == S.TAMAM:
            self.paket_kalemleri = []
            self.paket_tablosunu_yenile()
            self.kutuya_yaz(self.paket_sonuc, self.ozet_yaz(komut, sonuc), "tamam")
            return
        for kalem_sonucu in sonuc.get("kalemler", []):
            sira = kalem_sonucu["sira"]
            if sira < len(self.paket_kalemleri):
                if kalem_sonucu["durum"] == S.RED:
                    self.paket_kalemleri[sira]["sonuc"] = "RED " + self.hata_yazisi(kalem_sonucu)
                    self.paket_kalemleri[sira]["red"] = True
                else:
                    self.paket_kalemleri[sira]["sonuc"] = "TAMAM"
                    self.paket_kalemleri[sira]["red"] = False
        self.paket_tablosunu_yenile()
        yazi = "Paket alınmadı. " + self.hata_yazisi(sonuc)
        for kalem_sonucu in sonuc.get("kalemler", []):
            if kalem_sonucu["durum"] == S.RED:
                yazi += "\nKalem " + str(kalem_sonucu["sira"] + 1) + ": RED " + self.hata_yazisi(kalem_sonucu)
        self.kutuya_yaz(self.paket_sonuc, yazi, "red")

    # Seçili rezervasyona giriş, çıkış ya da iptal. komut_adi "giris" / "cikis" / "iptal",
    # yer "takvim" ya da "tablo". Onay penceresi yok. Sonuç (iade, bakiye, güvenilirlik,
    # otomatik atamalar) düğmeye basılan yerin hemen yanında görünüyor.
    def eylem(self, komut_adi, yer):
        if self.secili_rezervasyon is None:
            mesaj = "Önce bir rezervasyon seçin (takvimde kutuya ya da tabloda satıra tıklayın)."
            self.bildir_yazi(mesaj, basarili=False)
            if yer == "tablo":
                self.kutuya_yaz(self.rez_sonuc, mesaj, "red")
            else:
                self.takvim_kalici = (mesaj, tema.MERCAN_KOYU)
                self.takvim_bilgisi(None)
            return
        komut = {"komut": komut_adi, "rezervasyon": self.secili_rezervasyon}
        sonuc = self.komut_gonder(komut)
        if sonuc["durum"] == S.RED:
            yazi = self.secili_rezervasyon + "  |  " + self.hata_yazisi(sonuc)
            durum, renk = "red", tema.MERCAN_KOYU
        else:
            yazi = self.secili_rezervasyon + "  |  " + self.ozet_yaz(komut, sonuc)
            durum, renk = "tamam", tema.FIRUZE_KOYU
        if yer == "tablo":
            self.kutuya_yaz(self.rez_sonuc, yazi, durum)
        else:
            self.takvim_kalici = (yazi, renk)
            self.takvim_bilgisi(None)

    # +15 dk, +1 sa, +1 gün düğmeleri
    def saati_ilerlet_dakika(self, dakika):
        hedef = self.sistem.saat + timedelta(minutes=dakika)
        self.komut_gonder({"komut": "saat", "zaman": zamani_metne_cevir(hedef)})

    # Kutudaki zamana ilerlet. Geri bir saat yazılırsa modül SAAT_GERI veriyor.
    def saati_ilerlet_hedef(self):
        self.komut_gonder({"komut": "saat", "zaman": self.hedef_saat_var.get().strip()})

    # takvimde bir gün ileri ya da geri (adim +1 / -1)
    def takvim_gun_kaydir(self, adim):
        gun = metni_zamana_cevir(self.takvim_gun_var.get().strip() + "T00:00")
        if gun is None:
            gun = self.sistem.saat
        self.takvim_gun_var.set((gun + timedelta(days=adim)).strftime(GUN_BICIMI))
        self.takvim.ciz()

    # takvimi simüle saatin gününe getir
    def takvim_bugune(self):
        self.takvim_gun_var.set(self.sistem.saat.strftime(GUN_BICIMI))
        self.takvim.ciz()

    # Takvimin altındaki satır. yazi verilirse onu gösteriyor (fare bir şeyin üstünde), None ise
    # seçili rezervasyonu ya da son işlemin sonucunu.
    def takvim_bilgisi(self, yazi):
        if yazi is None:
            self.takvim_bilgi.configure(text=self.takvim_kalici[0], foreground=self.takvim_kalici[1])
        else:
            self.takvim_bilgi.configure(text=yazi, foreground=tema.METIN)

    # seçili rezervasyonun ayrıntısı takvimin altına
    def secili_bilgisini_yaz(self):
        rez = None
        if self.secili_rezervasyon is not None:
            rez = self.sistem.rezervasyonlar.get(self.secili_rezervasyon)
        if rez is None:
            self.takvim_kalici = (TAKVIM_IPUCU, tema.METIN_SOLUK)
        else:
            self.takvim_kalici = ("Seçili: " + self.takvim.rez_bilgisi(rez), tema.METIN)
        self.takvim_bilgisi(None)

    # Takvimde kutuya tıklanınca. 1. sürümdeki gibi kullanıcı rezervasyonun sahibine geçiyor ve
    # Rezervasyonlarım sekmesi açılıyor. Giriş / çıkış / iptal iki yerden de yapılabiliyor.
    def rezervasyonu_sec(self, rez_id):
        rez = self.sistem.rezervasyonlar.get(rez_id)
        if rez is None:
            return
        self.secili_rezervasyon = rez_id
        self.kullanici_var.set(self.kullanici_yazisi(rez["kullanici"]))
        self.sol_defter.select(2)
        self.secili_bilgisini_yaz()
        self.kullanici_secildi()
        self.takvim.ciz()

    # Takvimde boş yere tıklanınca formu o kaynak ve saatle doldurur (15 dakikaya yuvarlıyor, süre en kısa
    # süre olan 30 dakika).
    # Değer yazmak yerine seçmek için.
    def formu_doldur(self, kaynak_id, zaman):
        dakika = (zaman.minute // S.ADIM_DK) * S.ADIM_DK
        bas = zaman.replace(minute=dakika, second=0, microsecond=0)
        bit = min(bas + timedelta(minutes=S.EN_AZ_SURE_DK), bas.replace(hour=S.CALISMA_BITIS_SAAT, minute=0))
        self.kaynak_var.set(self.kaynak_yazisi(kaynak_id))
        self.gun_var.set(bas.strftime(GUN_BICIMI))
        self.bas_var.set(bas.strftime("%H:%M"))
        self.bit_var.set(bit.strftime("%H:%M"))
        self.sol_defter.select(0)
        self.kutuya_yaz(self.tek_sonuc, "Form takvimden dolduruldu. Ücret yukarıda.", "notr")

    # Sorgula düğmesi. Panel aynı bilgileri zaten gösteriyor; bu, örnek senaryodaki 19. işlemi (sorgu)
    # arayüzden de yapabilmek için.
    def kullanici_sorgula(self):
        self.komut_gonder({"komut": "sorgu", "tur": "kullanici", "id": self.secili_id(self.kullanici_var)})

    # takvimde kaynak adına tıklanınca o günün doluluğunu sorgular (sorgu kaynak)
    def kaynak_sorgula(self, kaynak_id):
        komut = {"komut": "sorgu", "tur": "kaynak", "id": kaynak_id, "gun": self.takvim_gun_var.get().strip()}
        sonuc = self.komut_gonder(komut)
        if sonuc["durum"] == S.RED:
            self.takvim_kalici = (self.hata_yazisi(sonuc), tema.MERCAN_KOYU)
        else:
            self.takvim_kalici = (self.ozet_yaz(komut, sonuc), tema.FIRUZE_KOYU)
        self.takvim_bilgisi(None)

    # listeden başka kullanıcı seçilince
    def kullanici_secildi(self):
        self.kullanici_panelini_yenile()
        self.paket_tablosunu_yenile()

    # tabloda satıra tıklanınca o rezervasyon seçili olsun (rez_id tıklanan satırın anahtarı)
    def rezervasyon_secildi(self, rez_id):
        self.secili_rezervasyon = rez_id
        self.secili_bilgisini_yaz()
        self.takvim.ciz()

    # Günlükte satıra tıklanınca o işlemin komutu ve sonucu, Bölüm 5'teki JSON satırı biçiminde.
    # no tıklanan satırın anahtarı, yani sonucun no değeri.
    def gunluk_secildi(self, no):
        kayit = self.sistem.gunluk[no - 1]
        komut_satiri = json.dumps(kayit["komut"], ensure_ascii=False, separators=(",", ":"))
        sonuc_satiri = json.dumps(kayit["sonuc"], ensure_ascii=False, separators=(",", ":"))
        self.json_yaz("Komut:\n" + komut_satiri + "\n\nSonuç:\n" + sonuc_satiri)

    # Çalışırken başka başlangıç dosyası seç. Seçilirse her şey o dosyaya göre baştan kuruluyor.
    def baslangic_dosyasi_ac(self):
        klasor = os.path.dirname(self.dosya_yolu) or ORNEK_KLASORU
        yol = filedialog.askopenfilename(title="Başlangıç dosyasını seçin", initialdir=klasor,
                                         filetypes=[("JSON", "*.json"), ("Tüm dosyalar", "*.*")])
        if not yol:
            return
        if self.sistemi_yukle(yol):
            self.arayuzu_kur()
            self.bildir_yazi(os.path.basename(yol) + " yüklendi, yeni oturum başladı.", basarili=True)

    # İki ekleme penceresinin ortak kısmı. grab_set yüzünden pencere açıkken ana pencereye
    # tıklanamıyor. (pencere, iç çerçeve) döner.
    def pencere_ac(self, baslik):
        pencere = tk.Toplevel(self.kok)
        pencere.title(baslik)
        pencere.configure(bg=tema.YUZEY)
        pencere.transient(self.kok)
        pencere.resizable(False, False)
        ic = ttk.Frame(pencere, style="Kart.TFrame", padding=tema.XL)
        ic.pack(fill="both", expand=True)
        ttk.Label(ic, text=baslik, style="Baslik.TLabel").grid(row=0, column=0, columnspan=2, sticky="w",
                                                               pady=(0, tema.L))
        return pencere, ic

    # Yeni Kullanıcı penceresi (PDF 7.8). Rol ve sertifikalar dosyadaki değerlerden seçiliyor,
    # bakiye seçilen rolün kotasıyla dolu geliyor.
    def kullanici_ekle_penceresi(self):
        self.kul_pencere, ic = self.pencere_ac("Yeni Kullanıcı")
        roller = list(self.sistem.roller)
        self.kul_id_var = tk.StringVar()
        self.kul_ad_var = tk.StringVar()
        self.kul_rol_var = tk.StringVar(value=roller[0] if roller else "")
        self.kul_bakiye_var = tk.StringVar()
        self.kul_guv_var = tk.StringVar(value="80")
        id_kutusu = ttk.Entry(ic, textvariable=self.kul_id_var, width=26, font=tema.FONT["govde"])
        ad_kutusu = ttk.Entry(ic, textvariable=self.kul_ad_var, width=26, font=tema.FONT["govde"])
        rol_kutusu = ttk.Combobox(ic, textvariable=self.kul_rol_var, values=roller, state="readonly", width=24,
                                  font=tema.FONT["govde"])
        rol_kutusu.bind("<<ComboboxSelected>>", lambda olay: self.rol_secildi())
        bakiye_kutusu = ttk.Spinbox(ic, textvariable=self.kul_bakiye_var, from_=0, to=100000, width=8,
                                    font=tema.FONT["govde"])
        guv_kutusu = ttk.Spinbox(ic, textvariable=self.kul_guv_var, from_=S.GUV_EN_AZ, to=S.GUV_EN_COK, width=8,
                                 font=tema.FONT["govde"])
        alanlar = [("Kimlik (id)", id_kutusu), ("Ad Soyad", ad_kutusu), ("Rol", rol_kutusu),
                   ("Bakiye (KP)", bakiye_kutusu), ("Güvenilirlik", guv_kutusu)]
        for satir_no in range(len(alanlar)):
            yazi, alan = alanlar[satir_no]
            ttk.Label(ic, text=yazi, style="Kart.TLabel").grid(row=satir_no + 1, column=0, sticky="w",
                                                              padx=tema.S, pady=tema.XS)
            alan.grid(row=satir_no + 1, column=1, sticky="w", padx=tema.S, pady=tema.XS)

        ttk.Label(ic, text="Sertifikalar", style="Kart.TLabel").grid(row=6, column=0, sticky="nw",
                                                                     padx=tema.S, pady=tema.XS)
        sertifika_cercevesi = ttk.Frame(ic, style="Kart.TFrame")
        sertifika_cercevesi.grid(row=6, column=1, sticky="w", padx=tema.S, pady=tema.XS)
        self.kul_sertifikalar = []
        for sertifika in self.sistem.tum_sertifikalar():
            secili_mi = tk.BooleanVar(value=False)
            ttk.Checkbutton(sertifika_cercevesi, text=sertifika, variable=secili_mi).pack(anchor="w")
            self.kul_sertifikalar.append((sertifika, secili_mi))

        self.kul_mesaj = ttk.Label(ic, text="Sadece bu oturumda tutulur, başlangıç dosyası değişmez.",
                                   style="Soluk.TLabel", wraplength=340)
        self.kul_mesaj.grid(row=7, column=0, columnspan=2, sticky="w", pady=(tema.M, 0))
        dugmeler = ttk.Frame(ic, style="Kart.TFrame")
        dugmeler.grid(row=8, column=0, columnspan=2, sticky="w", pady=(tema.L, 0))
        ttk.Button(dugmeler, text="Ekle", style="Ana.TButton", command=self.kullanici_ekle_onayla).pack(side="left")
        ttk.Button(dugmeler, text="Vazgeç", command=self.kul_pencere.destroy).pack(side="left", padx=tema.M)
        self.kul_pencere.bind("<Return>", lambda olay: self.kullanici_ekle_onayla())
        self.rol_secildi()
        self.kul_pencere.grab_set()
        id_kutusu.focus_set()

    # rol değişince bakiye kutusuna o rolün kotasını koy
    def rol_secildi(self):
        rol = self.sistem.roller.get(self.kul_rol_var.get())
        if rol is not None:
            self.kul_bakiye_var.set(str(rol["haftalik_kota"]))

    # kullanici_ekle komutunu gönderir. Reddedilirse kod ve açıklama pencerede kalıyor, kabul edilirse
    # pencere kapanıp yeni kullanıcı seçili hale geliyor.
    def kullanici_ekle_onayla(self):
        sertifikalar = []
        for sertifika, secili_mi in self.kul_sertifikalar:
            if secili_mi.get():
                sertifikalar.append(sertifika)
        komut = {
            "komut": "kullanici_ekle",
            "id": self.kul_id_var.get().strip(),
            "ad": self.kul_ad_var.get().strip(),
            "rol": self.kul_rol_var.get(),
            "sertifikalar": sertifikalar,
            "bakiye": sayiya_cevir(self.kul_bakiye_var.get()),
            "guvenilirlik": sayiya_cevir(self.kul_guv_var.get()),
        }
        sonuc = self.komut_gonder(komut)
        if sonuc["durum"] == S.RED:
            self.kul_mesaj.configure(text="RED  |  " + self.hata_yazisi(sonuc), style="Kart.TLabel",
                                     foreground=tema.MERCAN_KOYU)
            return
        self.kul_pencere.destroy()
        self.kullanici_var.set(self.kullanici_yazisi(komut["id"]))
        self.kullanici_panelini_yenile()

    # Yeni Kaynak penceresi (PDF 7.9). Tür listeden, izinli roller kutucuklardan seçiliyor,
    # hepsi işaretli geliyor.
    def kaynak_ekle_penceresi(self):
        self.kyn_pencere, ic = self.pencere_ac("Yeni Kaynak")
        turler = list(self.sistem.turler)
        self.kyn_id_var = tk.StringVar()
        self.kyn_ad_var = tk.StringVar()
        self.kyn_tur_var = tk.StringVar(value=turler[0] if turler else "")
        id_kutusu = ttk.Entry(ic, textvariable=self.kyn_id_var, width=26, font=tema.FONT["govde"])
        ad_kutusu = ttk.Entry(ic, textvariable=self.kyn_ad_var, width=26, font=tema.FONT["govde"])
        tur_kutusu = ttk.Combobox(ic, textvariable=self.kyn_tur_var, values=turler, state="readonly", width=24,
                                  font=tema.FONT["govde"])
        alanlar = [("Kimlik (id)", id_kutusu), ("Ad", ad_kutusu), ("Tür", tur_kutusu)]
        for satir_no in range(len(alanlar)):
            yazi, alan = alanlar[satir_no]
            ttk.Label(ic, text=yazi, style="Kart.TLabel").grid(row=satir_no + 1, column=0, sticky="w",
                                                              padx=tema.S, pady=tema.XS)
            alan.grid(row=satir_no + 1, column=1, sticky="w", padx=tema.S, pady=tema.XS)

        ttk.Label(ic, text="İzinli roller", style="Kart.TLabel").grid(row=4, column=0, sticky="nw",
                                                                      padx=tema.S, pady=tema.XS)
        rol_cercevesi = ttk.Frame(ic, style="Kart.TFrame")
        rol_cercevesi.grid(row=4, column=1, sticky="w", padx=tema.S, pady=tema.XS)
        self.kyn_roller = []
        for rol in self.sistem.roller:
            secili_mi = tk.BooleanVar(value=True)
            ttk.Checkbutton(rol_cercevesi, text=rol, variable=secili_mi).pack(anchor="w")
            self.kyn_roller.append((rol, secili_mi))

        self.kyn_mesaj = ttk.Label(ic, text="Sadece bu oturumda tutulur, başlangıç dosyası değişmez.",
                                   style="Soluk.TLabel", wraplength=340)
        self.kyn_mesaj.grid(row=5, column=0, columnspan=2, sticky="w", pady=(tema.M, 0))
        dugmeler = ttk.Frame(ic, style="Kart.TFrame")
        dugmeler.grid(row=6, column=0, columnspan=2, sticky="w", pady=(tema.L, 0))
        ttk.Button(dugmeler, text="Ekle", style="Ana.TButton", command=self.kaynak_ekle_onayla).pack(side="left")
        ttk.Button(dugmeler, text="Vazgeç", command=self.kyn_pencere.destroy).pack(side="left", padx=tema.M)
        self.kyn_pencere.bind("<Return>", lambda olay: self.kaynak_ekle_onayla())
        self.kyn_pencere.grab_set()
        id_kutusu.focus_set()

    # kaynak_ekle komutunu gönderir. Eklenen kaynak takvimde hemen görünüyor ve formda seçili oluyor.
    def kaynak_ekle_onayla(self):
        roller = []
        for rol, secili_mi in self.kyn_roller:
            if secili_mi.get():
                roller.append(rol)
        komut = {
            "komut": "kaynak_ekle",
            "id": self.kyn_id_var.get().strip(),
            "ad": self.kyn_ad_var.get().strip(),
            "tur": self.kyn_tur_var.get(),
            "izinli_roller": roller,
        }
        sonuc = self.komut_gonder(komut)
        if sonuc["durum"] == S.RED:
            self.kyn_mesaj.configure(text="RED  |  " + self.hata_yazisi(sonuc), style="Kart.TLabel",
                                     foreground=tema.MERCAN_KOYU)
            return
        self.kyn_pencere.destroy()
        self.kaynak_var.set(self.kaynak_yazisi(komut["id"]))


# programın başladığı yer
def main():
    ekran_netligini_ac()
    kok = tk.Tk()
    Uygulama(kok)
    kok.mainloop()


if __name__ == "__main__":
    main()
