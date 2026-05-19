import streamlit as st
import pandas as pd
from google import genai
from PIL import Image
from dotenv import load_dotenv
import os

# --- AYARLAR & TEMA ---
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

st.set_page_config(page_title="SnapShop AI | Akıllı Satış Asistanı", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { background-color: #4CAF50; color: white; border-radius: 20px; width: 100%; }
    .reportview-container .main .block-container { padding-top: 2rem; }
    h1 { color: #1E3A8A; font-family: 'Helvetica Neue', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

def reset_state():
    """Kullanıcı yeni bir değer girdiğinde analiz sonuçlarını sıfırlar."""
    if 'analiz_yapildi' in st.session_state:
        st.session_state.analiz_yapildi = False

# --- VERİ OKUMA ---
@st.cache_data
def veri_oku():
    try:
        df = pd.read_excel("fees.xlsx")
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception as e:
        st.error(f"⚠️ Hata: 'fees.xlsx' dosyası okunamadı. Lütfen dosyanın var olduğundan ve bozuk olmadığından emin olun.\n\nDetay: {e}")
        st.stop()

fees = veri_oku()

if not API_KEY:
    st.error(".env dosyasında GEMINI_API_KEY bulunamadı.")
    st.stop()

client = genai.Client(api_key=API_KEY)

def kar_hesapla(maliyet, satis_fiyati, komisyon_yuzde, kargo):
    komisyon_tutari = satis_fiyati * (komisyon_yuzde / 100)
    net_kar = satis_fiyati - maliyet - komisyon_tutari - kargo
    kar_marji = (net_kar / satis_fiyati) * 100 if satis_fiyati > 0 else 0
    return komisyon_tutari, net_kar, kar_marji

def onerilen_fiyat_hesapla(maliyet, komisyon_yuzde, kargo):
    # Sistem otomatik makul kâr hedefi koyuyor
    # Düşük maliyetli ürünlerde daha yüksek, yüksek maliyetli ürünlerde daha dengeli kâr payı
    if maliyet <= 250:
        hedef_kar_orani = 0.45
    elif maliyet <= 1000:
        hedef_kar_orani = 0.30
    else:
        hedef_kar_orani = 0.20

    hedef_kar = maliyet * hedef_kar_orani
    oran = 1 - (komisyon_yuzde / 100)

    if oran <= 0:
        return 0, hedef_kar_orani

    onerilen_fiyat = (maliyet + kargo + hedef_kar) / oran
    return onerilen_fiyat, hedef_kar_orani

# --- HEADER ---
col_logo, col_text = st.columns([1, 4])
with col_text:
    st.title("📸 SnapShop AI")
    st.subheader("Ürünü Fotoğrafla, Saniyeler İçinde İlanın Hazır Olsun!")

# --- SOL PANEL ---
with st.sidebar:
    st.header("🛠️ İşlem Merkezi")

    yuklenen_dosya = st.file_uploader(
        "Ürün Fotoğrafı Yükle",
        type=["jpg", "jpeg", "png"],
        on_change=reset_state
    )

    platform = st.selectbox("Platform Seç", fees["platform"].unique(), on_change=reset_state)

    kategori_listesi = fees[fees["platform"] == platform]["kategori"].unique()
    kategori = st.selectbox("Kategori Seç", kategori_listesi, on_change=reset_state)

    secilen_satir = fees[
        (fees["platform"] == platform) &
        (fees["kategori"] == kategori)
    ].iloc[0]

    komisyon_yuzde = float(secilen_satir["komisyon"])
    kargo = float(secilen_satir["kargo"])

    st.info(f"Komisyon: %{komisyon_yuzde} | Kargo: {kargo:.2f} ₺")

    maliyet = st.number_input(
        "Ürün Maliyeti (₺)",
        min_value=0.0,
        value=0.0,
        step=10.0,
        on_change=reset_state
    )

    st.write("---")
    analiz_butonu = st.button("🚀 ANALİZ ET VE HESAPLA")

# --- ANA EKRAN ---
if yuklenen_dosya is not None:
    image = Image.open(yuklenen_dosya)

    if analiz_butonu:
        with st.spinner("Yapay Zeka ve Finans Verileri Hazırlanıyor..."):
            prompt = f"""
            Bu ürünü e-ticaret satıcısı için analiz et.
            Platform: {platform}
            Kategori: {kategori}

            Cevabı kısa, net ve satış odaklı ver.

            Şu formatta yaz:
            Başlık: ...
            Açıklama: ...
            Hedef Kitle: ...
            Anahtar Kelimeler: ...
            Satış Önerisi: ...
            """

            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[prompt, image]
                )
                ilan_metni = response.text
            except Exception as e:
                ilan_metni = f"""
Başlık: Şık ve Kullanışlı Ürün - Temiz Durumda
Açıklama: Günlük kullanıma uygun, temiz ve kullanışlı bir üründür.
Hedef Kitle: Uygun fiyatlı ve kaliteli ürün arayan kullanıcılar.
Anahtar Kelimeler: uygun fiyat, temiz ürün, ikinci el, kaliteli ürün
Satış Önerisi: Ürün açıklamasında kondisyon ve kullanım durumunu net belirtin.
"""
                st.warning(f"Gemini bağlantısında hata oluştu, demo ilan metni gösteriliyor. Hata detayı: {e}")

            onerilen_fiyat, hedef_kar_orani = onerilen_fiyat_hesapla(
                maliyet,
                komisyon_yuzde,
                kargo
            )

            komisyon_tutari, net_kar, kar_marji = kar_hesapla(
                maliyet,
                onerilen_fiyat,
                komisyon_yuzde,
                kargo
            )
            
            # Sonuçları session_state'e kaydet
            st.session_state.ilan_metni = ilan_metni
            st.session_state.onerilen_fiyat = onerilen_fiyat
            st.session_state.hedef_kar_orani = hedef_kar_orani
            st.session_state.komisyon_tutari = komisyon_tutari
            st.session_state.net_kar = net_kar
            st.session_state.kar_marji = kar_marji
            st.session_state.analiz_yapildi = True

            st.balloons()

    if st.session_state.get('analiz_yapildi', False):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🤖 AI Analiz Sonucu")
            st.success("Yapay zeka ürün analizini başarıyla tamamladı!")
            st.info(st.session_state.ilan_metni)

        with col2:
            st.markdown("### 💰 Finansal Analiz")

            st.metric(
                label="Önerilen Satış Fiyatı",
                value=f"{st.session_state.onerilen_fiyat:.2f} ₺",
                delta=f"%{st.session_state.hedef_kar_orani * 100:.0f} otomatik kâr hedefi"
            )

            st.metric(
                label="Tahmini Net Kâr",
                value=f"{st.session_state.net_kar:.2f} ₺",
                delta=f"%{st.session_state.kar_marji:.1f} kâr marjı"
            )

            st.write("**Gider Detayları:**")
            st.json({
                "Platform": platform,
                "Kategori": kategori,
                "Maliyet": round(maliyet, 2),
                "Komisyon Oranı": f"%{komisyon_yuzde}",
                "Komisyon Tutarı": round(st.session_state.komisyon_tutari, 2),
                "Kargo": round(kargo, 2),
                "Önerilen Satış Fiyatı": round(st.session_state.onerilen_fiyat, 2),
                "Tahmini Net Kar": round(st.session_state.net_kar, 2)
            })

            if st.session_state.net_kar > 0:
                st.success("✅ Bu fiyatla satış kârlı görünüyor.")
            elif st.session_state.net_kar == 0:
                st.warning("⚠️ Bu satış başa baş noktasında.")
            else:
                st.error("🚨 DİKKAT: Bu fiyata satarsan zarar ediyorsun.")

        st.markdown("---")
        st.markdown("### 📋 Kopyalanabilir İlan Metni")
        st.code(st.session_state.ilan_metni, language="markdown")

        st.markdown("### 🛒 İlanı Oluştur")
        
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            st.link_button(
                "Trendyol Satıcı Paneline Git",
                "https://partner.trendyol.com/",
                use_container_width=True
            )

        with btn_col2:
            st.link_button(
                "Hepsiburada Satıcı Paneline Git",
                "https://merchant.hepsiburada.com/",
                use_container_width=True
            )

    else:
        st.image(image, caption="Analiz için hazır!", width=400)

else:
    st.info("👋 Başlamak için sol menüden bir ürün fotoğrafı yükleyin.")