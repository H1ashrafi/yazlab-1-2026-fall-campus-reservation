# PDF'te kural olarak sabit yazılmış sayılar ve durum adları.
# Kota, ileri_gun, hazirlik_dk, temel_ucret gibi değerler burada değil, başlangıç dosyasından geliyor.

# K1: saatler 15 dakikalık adımlara oturmalı, ücret de 15 dakikalık dilimlerle hesaplanıyor (K5)
ADIM_DK = 15

# K1: rezervasyon aynı gün içinde 08:00 ile 22:00 arasında olmalı
CALISMA_BASLANGIC_SAAT = 8
CALISMA_BITIS_SAAT = 22

# K1: en kısa rezervasyon 30 dakika (en uzunu rolden geliyor: azami_sure_dk)
EN_AZ_SURE_DK = 30

# K4: aynı kişinin aynı kaynaktaki iki rezervasyonu arasında en az 60 dakika olmalı
ARDISIK_BOSLUK_DK = 60

# K5: gün iki saatlik bantlara bölünüyor (08-10, 10-12, ... 20-22)
BANT_DK = 120

# K5: 10:00-16:00 pik saat, enerji yoğun türlerde bu saatlerde çarpan 1,5
PIK_BASLANGIC_SAAT = 10
PIK_BITIS_SAAT = 16
PIK_CARPANI = 1.5

# K8: giriş başlangıçtan 10 dk önce açılıyor, 15 dk sonrasına kadar gelinmezse GELMEDI
GIRIS_ONCE_DK = 10
GELMEME_DK = 15

# K8 iade tablosu: 24 saat ve üstü tam iade, 2-24 saat arası yarı iade, 2 saatten az iade yok
TAM_IADE_SAAT = 24
YARIM_IADE_SAAT = 2
YARIM_IADE_YUZDE = 50

# K8 güvenilirlik değişimleri
GUV_GELMEDI = -15
GUV_GEC_IPTAL = -5
GUV_TAMAMLANDI = 2

# güvenilirlik her zaman 0 ile 100 arasında tutuluyor
GUV_EN_AZ = 0
GUV_EN_COK = 100

# güvenilirlik 50'nin altına düşerse ileri tarih sınırı 1 gün oluyor ve paket yapılamıyor
GUV_ESIK = 50
DUSUK_GUV_ILERI_GUN = 1

# K7: paket 2 ile 4 kalem arasında olmalı
PAKET_EN_AZ = 2
PAKET_EN_COK = 4

# Rezervasyonun alabileceği durumlar (PDF Bölüm 3'teki durum tablosu)
ONAYLI = "ONAYLI"
KULLANIMDA = "KULLANIMDA"
TAMAMLANDI = "TAMAMLANDI"
IPTAL = "IPTAL"
GELMEDI = "GELMEDI"

# K3 kesişme kontrolünde ve K5 doluluk hesabında sadece bu ikisi sayılıyor
AKTIF_DURUMLAR = (ONAYLI, KULLANIMDA)

# K3 hazırlık ve K4 art arda kullanım kontrolünde tamamlananlar da sayılıyor
HAZIRLIK_DURUMLARI = (ONAYLI, KULLANIMDA, TAMAMLANDI)

# sonuç satırlarındaki "durum" alanı
TAMAM = "TAMAM"
RED = "RED"

# saat komutunun ürettiği olay türlerinden ikisi (diğer ikisi TAMAMLANDI ve GELMEDI)
HAFTALIK_SIFIRLAMA = "HAFTALIK_SIFIRLAMA"
OTOMATIK_ATAMA = "OTOMATIK_ATAMA"

# takvimde çizilen kutuların türü (sorgu kaynak sonucundaki "tur" alanı da bunlar)
KUTU_REZERVASYON = "REZERVASYON"
KUTU_BAKIM = "BAKIM"
KUTU_HAZIRLIK = "HAZIRLIK"
