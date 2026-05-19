import pandas as pd

# Excel oku
df = pd.read_excel("fees.xlsx")

def kar_hesapla(platform, kategori, satis_fiyati, maliyet):

    # ilgili satırı bul
    veri = df[
        (df["platform"] == platform) &
        (df["kategori"] == kategori)
    ].iloc[0]

    komisyon = veri["komisyon"]
    kargo = veri["kargo"]

    # komisyon tutarı
    komisyon_tutari = satis_fiyati * (komisyon / 100)

    # net kar hesapla
    net_kar = satis_fiyati - maliyet - komisyon_tutari - kargo

    # BONUS MESAJLAR
    if net_kar < 0:
        return "ZARAR EDİYORSUN!"

    if net_kar > 300:
        return "ÇOK KARLI"
   

    return round(net_kar, 2)


# TEST
kar = kar_hesapla(
    platform="Trendyol",
    kategori="Elektronik",
    satis_fiyati=1500,
    maliyet=1000
)

print("Sonuç:", kar)