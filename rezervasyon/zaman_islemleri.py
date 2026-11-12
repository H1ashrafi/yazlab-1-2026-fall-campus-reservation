# Zaman yardımcıları. PDF'te zaman "2027-03-08T11:00" biçiminde, aralıklarda başlangıç dahil
# bitiş hariç.

from datetime import datetime, timedelta

# strptime yazıdan zamana, strftime zamandan yazıya çeviriyor. timedelta gün eklemek için.

ZAMAN_BICIMI = "%Y-%m-%dT%H:%M"
GUN_BICIMI = "%Y-%m-%d"


# "2027-03-08T11:00" gibi bir yazıyı datetime'a çevirir. Yazı değilse ya da biçim tutmuyorsa
# None döner, hata fırlatmaz. Komutlardaki bütün saatler buradan geçiyor.
def metni_zamana_cevir(metin):
    if not isinstance(metin, str):
        return None
    try:
        return datetime.strptime(metin, ZAMAN_BICIMI)
    except ValueError:
        return None


# tersi: datetime -> "2027-03-08T11:00" (sonuç satırlarına yazarken)
def zamani_metne_cevir(zaman):
    return zaman.strftime(ZAMAN_BICIMI)


# Sadece gün kısmı ("2027-03-08") için. Saati 00:00 olan bir datetime verir, bozuksa None.
# sorgu kaynak komutu ve takvim kullanıyor.
def gun_metnini_cevir(metin):
    if not isinstance(metin, str):
        return None
    try:
        return datetime.strptime(metin, GUN_BICIMI)
    except ValueError:
        return None


# bas ile bit arası kaç dakika (int). bit daha erkense eksi çıkar.
def dakika_farki(bas, bit):
    return int((bit - bas).total_seconds() // 60)


# İki aralık çakışıyor mu? Bitiş hariç sayıldığı için 10:00'da biten ile 10:00'da başlayan
# çakışmıyor. PDF'teki b < e' ve e > b' şartının aynısı, True / False döner.
def kesisiyor_mu(b1, e1, b2, e2):
    return b1 < e2 and e1 > b2


# İki aralığın üst üste gelen kısmı kaç dakika, hiç yoksa 0. Doluluk hesabında bir rezervasyonun
# bir banda kaç dakikasının düştüğünü bulmak için (dolu_dakika).
def ortak_dakika(b1, e1, b2, e2):
    bas = max(b1, b2)
    bit = min(e1, e2)
    if bit <= bas:
        return 0
    return dakika_farki(bas, bit)


# Verilen andan sonraki ilk Pazartesi 00:00, haftalık kota sıfırlaması için (K6).
# Zaten Pazartesi 00:00'daysak bir sonraki haftayı veriyor, çünkü o an işlenmiş oluyor.
def sonraki_pazartesi(zaman):
    kac_gun = 7 - zaman.weekday()
    gece_yarisi = zaman.replace(hour=0, minute=0, second=0, microsecond=0)
    return gece_yarisi + timedelta(days=kac_gun)
