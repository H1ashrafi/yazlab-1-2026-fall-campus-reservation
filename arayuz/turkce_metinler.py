# Ekranda görünen Türkçe yazılar. Modül sadece kodu veriyor ("KESISME" gibi),
# Türkçe açıklamasını arayüz buradan alıyor.

# hata kodu -> Türkçe açıklama
HATALAR = {
    "BULUNAMADI": "Kullanıcı, kaynak veya rezervasyon bulunamadı.",
    "ZAMAN_ADIMI_HATASI": "Saatler 15 dakikalık adımlara oturmalı (:00, :15, :30, :45) ve bitiş başlangıçtan sonra olmalı.",
    "GECMIS_ZAMAN": "Başlangıç, simüle saatten önce olamaz.",
    "CALISMA_SAATI_DISI": "Rezervasyon aynı gün içinde, 08:00 ile 22:00 arasında kalmalı.",
    "SURE_SINIRI": "Süre en az 30 dakika, en fazla rolün azami süresi kadar olabilir.",
    "ILERI_TARIH_SINIRI": "Bu kadar ileri bir gün alınamaz. Sınır rolün ileri_gun değeri (güvenilirlik 50'nin altındaysa 1 gün).",
    "ROL_IZNI_YOK": "Kullanıcının rolü bu kaynağı rezerve edemez.",
    "SERTIFIKA_YOK": "Bu kaynak türü için gereken sertifika kullanıcıda yok.",
    "BAKIM": "İstenen aralık bir bakım penceresiyle çakışıyor.",
    "KESISME": "Bu aralıkta kaynağın onaylı veya kullanımdaki başka bir rezervasyonu var.",
    "HAZIRLIK_IHLALI": "Kaynağın hazırlık (soğuma / havalandırma) süresine denk geliyor.",
    "ARDISIK_KULLANIM": "Aynı kişinin aynı kaynaktaki iki rezervasyonu arasında en az 60 dakika olmalı.",
    "BAKIYE_YETERSIZ": "Bakiye (KP) ücreti karşılamıyor.",
    "PAKET_BOYUTU": "Paket en az 2, en fazla 4 kalem olmalı.",
    "GUVENILIRLIK_DUSUK": "Güvenilirliği 50'nin altında olan kullanıcı paket yapamaz.",
    "PAKET_RED": "Paketteki kalemlerden en az biri kontrolden geçemedi.",
    "PAKET_ICI_KESISME": "Paketteki aynı kaynağa ait kalemler çakışıyor (kesişme, hazırlık ya da 60 dakika kuralı).",
    "DURUM_HATASI": "Rezervasyon bu işlem için uygun durumda değil.",
    "GIRIS_PENCERESI_DISI": "Giriş sadece başlangıçtan 10 dk önce ile 15 dk sonrası arasında yapılabilir.",
    "BEKLEME_GEREKSIZ": "Bu aralık zaten boş, doğrudan rezervasyon yapılabilir.",
    "SAAT_GERI": "Simüle saat geri alınamaz.",
    "GECERSIZ_KOMUT": "Komut tanınmadı ya da alanları eksik / hatalı.",
    "ID_MEVCUT": "Bu kimlikle (id) kayıtlı biri ya da bir kaynak zaten var.",
    "TANIMSIZ_DEGER": "Rol, tür veya izinli rollerden biri başlangıç dosyasında tanımlı değil.",
    "GECERSIZ_DEGER": "Bakiye 0 ile rolün haftalık kotası arasında, güvenilirlik 0-100 arası tam sayı olmalı.",
}

# rezervasyon durumu ve sonuç durumu -> ekranda görünen ad
DURUMLAR = {
    "ONAYLI": "Onaylı",
    "KULLANIMDA": "Kullanımda",
    "TAMAMLANDI": "Tamamlandı",
    "IPTAL": "İptal",
    "GELMEDI": "Gelmedi",
    "TAMAM": "TAMAM",
    "RED": "RED",
}

# saat komutunun ürettiği olay türleri
OLAYLAR = {
    "HAFTALIK_SIFIRLAMA": "Haftalık sıfırlama",
    "TAMAMLANDI": "Tamamlandı",
    "GELMEDI": "Gelmedi",
    "OTOMATIK_ATAMA": "Otomatik atama",
}

# komut adı -> günlükte görünen ad
KOMUTLAR = {
    "saat": "Saat",
    "rezervasyon": "Rezervasyon",
    "paket": "Paket",
    "fiyat": "Fiyat",
    "iptal": "İptal",
    "giris": "Giriş",
    "cikis": "Çıkış",
    "bekleme": "Bekleme",
    "sorgu": "Sorgu",
    "kullanici_ekle": "Kullanıcı ekle",
    "kaynak_ekle": "Kaynak ekle",
}

# kısa gün adları, datetime.weekday() 0=Pazartesi ... 6=Pazar
GUNLER = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
