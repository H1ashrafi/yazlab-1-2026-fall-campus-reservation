# Renkler, yazı tipleri (her yerde Arial) ve ttk stilleri.

import tkinter.font as tkfont
from tkinter import ttk

# tkfont.Font fontları oluşturuyor, tkfont.families yüklü fontları veriyor. ttk.Style stiller için.

# renkler
ZEMIN = "#F2F7F7"
YUZEY = "#FFFFFF"
YUZEY_ALT = "#F6FBFA"
KENAR = "#D6E6E4"
METIN = "#12302F"
METIN_SOLUK = "#557071"
BASLIK_ZEMIN = "#0E4D4A"
BASLIK_METIN = "#FFFFFF"
BASLIK_SOLUK = "#9FD9D3"
FIRUZE = "#1FB5AA"
FIRUZE_KOYU = "#0B7A74"
FIRUZE_ACIK = "#E3F5F3"
MERCAN = "#E8685E"
MERCAN_KOYU = "#A3322A"
MERCAN_ACIK = "#FDECEA"
KEHRIBAR = "#F2B544"
HAZIRLIK = "#8FD8D1"

# takvimdeki kutuların rengi: durum -> (dolgu, yazı rengi)
DURUM_RENKLERI = {
    "ONAYLI": ("#2BC4B8", "#08312E"),
    "KULLANIMDA": ("#2F6FD0", "#FFFFFF"),
    "TAMAMLANDI": ("#A9C6C3", "#12302F"),
    "IPTAL": ("#D5DCDC", "#3E5556"),
    "GELMEDI": ("#F4A29B", "#3A0B07"),
}

PIK = "#FFF1CC"     # pik saatlerin (10-16) takvimdeki açık sarı zemini
GIRIS = "#1A3A9C"   # erken / geç girişi gösteren koyu mavi noktalar

# tablolarda satır rengi: durum -> (zemin, yazı rengi)
SATIR_RENKLERI = {
    "ONAYLI": (FIRUZE_ACIK, METIN),
    "KULLANIMDA": ("#E4EEFB", METIN),
    "GELMEDI": (MERCAN_ACIK, MERCAN_KOYU),
    "IPTAL": (YUZEY, METIN_SOLUK),
    "RED": (MERCAN_ACIK, MERCAN_KOYU),
}

# boşluk ölçüleri (piksel)
XS = 3
S = 5
M = 8
L = 13
XL = 21

# Arial yoksa (Linux gibi) sıradakine geçiyoruz
YAZI_TIPLERI = ["Arial", "Helvetica", "Liberation Sans"]
SABIT_GENISLIK = ["Consolas", "Courier New"]

# oluşturulan fontlar burada duruyor, örnek: FONT["govde_kalin"]
FONT = {}


# listeden bilgisayarda yüklü olan ilk yazı tipi, hiçbiri yoksa Tk'nin varsayılanı
def ilk_bulunan(adaylar):
    yuklu = tkfont.families()
    for ad in adaylar:
        if ad in yuklu:
            return ad
    return "TkDefaultFont"


# Fontlar burada bir kere oluşturuluyor. Tk penceresi açılmadan çağrılırsa hata veriyor.
def fontlari_hazirla():
    aile = ilk_bulunan(YAZI_TIPLERI)
    mono = ilk_bulunan(SABIT_GENISLIK)
    FONT["kucuk"] = tkfont.Font(family=aile, size=9)
    FONT["kucuk_kalin"] = tkfont.Font(family=aile, size=9, weight="bold")
    FONT["govde"] = tkfont.Font(family=aile, size=10)
    FONT["govde_kalin"] = tkfont.Font(family=aile, size=10, weight="bold")
    FONT["baslik"] = tkfont.Font(family=aile, size=13, weight="bold")
    FONT["buyuk"] = tkfont.Font(family=aile, size=21, weight="bold")
    FONT["mono"] = tkfont.Font(family=mono, size=9)


# ttk stilleri. clam temasını seçtik, Windows'un kendi teması arka plan rengini değiştirmeye izin vermiyor.
def stilleri_kur(kok):
    fontlari_hazirla()
    stil = ttk.Style(kok)
    stil.theme_use("clam")

    stil.configure(".", background=ZEMIN, foreground=METIN, font=FONT["govde"],
                   bordercolor=KENAR, lightcolor=YUZEY, darkcolor=KENAR, focuscolor=FIRUZE)

    stil.configure("TFrame", background=ZEMIN)
    stil.configure("Kart.TFrame", background=YUZEY)
    stil.configure("TLabel", background=ZEMIN, foreground=METIN)
    stil.configure("Kart.TLabel", background=YUZEY, foreground=METIN, font=FONT["govde_kalin"])
    stil.configure("Soluk.TLabel", background=YUZEY, foreground=METIN_SOLUK, font=FONT["kucuk"])
    stil.configure("Baslik.TLabel", background=YUZEY, foreground=METIN, font=FONT["baslik"])
    stil.configure("TCheckbutton", background=YUZEY, foreground=METIN, font=FONT["govde"])

    stil.configure("TButton", padding=(M, XS + 1), background=YUZEY, foreground=FIRUZE_KOYU,
                   bordercolor=KENAR, relief="flat", font=FONT["govde_kalin"])
    stil.map("TButton", background=[("pressed", "#CDEDEA"), ("active", FIRUZE_ACIK)])
    stil.configure("Ana.TButton", background=FIRUZE_KOYU, foreground="#FFFFFF", bordercolor=FIRUZE_KOYU)
    stil.map("Ana.TButton", background=[("pressed", "#07524E"), ("active", "#09625D")])
    stil.configure("Tehlike.TButton", foreground=MERCAN_KOYU)
    stil.map("Tehlike.TButton", background=[("pressed", "#F9D5D1"), ("active", MERCAN_ACIK)])

    satir = FONT["govde"].metrics("linespace") + L
    stil.configure("Treeview", background=YUZEY, fieldbackground=YUZEY, foreground=METIN,
                   rowheight=satir, bordercolor=KENAR, borderwidth=0, font=FONT["govde"])
    stil.configure("Treeview.Heading", background=FIRUZE_ACIK, foreground=METIN,
                   font=FONT["kucuk_kalin"], relief="flat", padding=(S, S))
    stil.map("Treeview.Heading", background=[("active", "#CDEDEA")])
    stil.map("Treeview", background=[("selected", FIRUZE)], foreground=[("selected", "#06302C")])

    stil.configure("TNotebook", background=ZEMIN, borderwidth=0, tabmargins=(0, 0, 0, 0))
    stil.configure("TNotebook.Tab", padding=(L, S), background="#E1ECEB", foreground=METIN_SOLUK,
                   font=FONT["govde_kalin"], borderwidth=0)
    stil.map("TNotebook.Tab", background=[("selected", YUZEY)], foreground=[("selected", FIRUZE_KOYU)])

    stil.configure("TCombobox", fieldbackground=YUZEY, background=YUZEY, arrowcolor=FIRUZE_KOYU, padding=(S, XS))
    stil.map("TCombobox", fieldbackground=[("readonly", YUZEY)], selectbackground=[("readonly", YUZEY)],
             selectforeground=[("readonly", METIN)])
    stil.configure("Vertical.TScrollbar", background="#E1ECEB", troughcolor=YUZEY, arrowcolor=FIRUZE_KOYU,
                   bordercolor=YUZEY)
    stil.configure("TPanedwindow", background=ZEMIN)

    # açılır listelerin içi de Arial olsun
    kok.option_add("*TCombobox*Listbox.font", FONT["govde"])
    kok.option_add("*TCombobox*Listbox.selectBackground", FIRUZE)
    kok.configure(background=ZEMIN)
