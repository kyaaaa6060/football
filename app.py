import pandas as pd
import streamlit as st
import requests
import datetime

@st.cache_data
def veri_yukle():
    try:
        # Excel verilerini ana analiz motoru için yüklüyoruz
        xls = pd.ExcelFile('all-euro-data-2026-2027.xlsx')
        tum_ligler = []
        for sekme in xls.sheet_names:
            df_sekme = pd.read_excel(xls, sheet_name=sekme)
            tum_ligler.append(df_sekme)
        df = pd.concat(tum_ligler, ignore_index=True)
        df = df.dropna(subset=['HomeTeam', 'AwayTeam']) 
        return df
    except Exception as e:
        st.error(f"Veri yüklenirken hata oluştu: {e}")
        return pd.DataFrame()

# İnternetten güncel ve canlı maç skorlarını çeken fonksiyon
def canli_maclari_getir():
    try:
        bugun = datetime.datetime.now().strftime('%Y-%m-%d')
        # Ücretsiz futbol veri servisinden günün maçlarını çekiyoruz
        url = f"https://api.football-data.org/v4/matches?dateFrom={bugun}&dateTo={bugun}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json().get('matches', [])
    except:
        pass
    return []

def detayli_mac_analizi(df, ev_sahibi, deplasman):
    ev_ic = df[df['HomeTeam'] == ev_sahibi].tail(5)
    dep_dis = df[df['AwayTeam'] == deplasman].tail(5)
    h2h = df[((df['HomeTeam'] == ev_sahibi) & (df['AwayTeam'] == deplasman)) | 
             ((df['HomeTeam'] == deplasman) & (df['AwayTeam'] == ev_sahibi))].tail(5)

    ev_atilan_ort = ev_ic.apply(lambda x: x['FTHG'] if x['HomeTeam'] == ev_sahibi else x['FTAG'], axis=1).mean()
    ev_yenen_ort = ev_ic.apply(lambda x: x['FTAG'] if x['HomeTeam'] == ev_sahibi else x['FTHG'], axis=1).mean()
    dep_atilan_ort = dep_dis.apply(lambda x: x['FTAG'] if x['AwayTeam'] == deplasman else x['FTHG'], axis=1).mean()
    dep_yenen_ort = dep_dis.apply(lambda x: x['FTAG'] if x['AwayTeam'] == deplasman else x['FTHG'], axis=1).mean()

    if pd.isna(ev_atilan_ort): ev_atilan_ort = 1.2
    if pd.isna(ev_yenen_ort): ev_yenen_ort = 1.0
    if pd.isna(dep_atilan_ort): dep_atilan_ort = 1.1
    if pd.isna(dep_yenen_ort): dep_yenen_ort = 1.2

    ev_beklenen_gol = (ev_atilan_ort + dep_yenen_ort) / 2
    dep_beklenen_gol = (dep_atilan_ort + ev_yenen_ort) / 2

    ev_kazanma_ihtimali = max(10, min(80, round((ev_beklenen_gol / (ev_beklenen_gol + dep_beklenen_gol + 0.1)) * 100)))
    dep_kazanma_ihtimali = max(10, min(80, round((dep_beklenen_gol / (ev_beklenen_gol + dep_beklenen_gol + 0.1)) * 100)))
    beraberlik_ihtimali = max(10, 100 - (ev_kazanma_ihtimali + dep_kazanma_ihtimali))

    tahmini_ev_gol = round(ev_beklenen_gol)
    tahmini_dep_gol = round(dep_beklenen_gol)

    oruntuler = []
    if (ev_atilan_ort + dep_atilan_ort) > 2.8:
        oruntuler.append("🔥 **Yüksek Gol Eğilimi:** Son maçlarındaki gol ortalamaları 2.5 ÜST seçeneğini destekliyor.")
    else:
        oruntuler.append("🛡️ **Düşük Tempo / Kısıtlı Skor:** Takımların son maçlarında maç başı gol ortalamaları 2.5 Alt sınırında seyrediyor.")

    if ev_yenen_ort > 1.0 and dep_yenen_ort > 1.0:
        oruntuler.append("⚡ **Defansif Zaafiyet:** Her iki takım da düzenli olarak gol yiyor (KG Var potansiyeli yüksek).")

    favori_durumu = "Oran Verisi Bulunamadı"
    if not h2h.empty and 'B365H' in h2h.columns:
        son_oran_ev = h2h.iloc[-1]['B365H']
        son_oran_dep = h2h.iloc[-1]['B365A']
        if not pd.isna(son_oran_ev) and not pd.isna(son_oran_dep):
            if son_oran_ev < son_oran_dep:
                favori_durumu = f"{ev_sahibi} (H2H Oranlarına Göre Favori)"
            else:
                favori_durumu = f"{deplasman} (H2H Oranlarına Göre Favori)"

    return {
        "ev_gol_beklentisi": round(ev_beklenen_gol, 2),
        "dep_gol_beklentisi": round(dep_beklenen_gol, 2),
        "ev_oran": ev_kazanma_ihtimali,
        "dep_oran": dep_kazanma_ihtimali,
        "beraberlik_oran": beraberlik_ihtimali,
        "skor_tahmini": f"{tahmini_ev_gol} - {tahmini_dep_gol}",
        "oruntuler": oruntuler,
        "h2h_favori": favori_durumu,
        "h2h_mac_sayisi": len(h2h)
    }

# --- STREAMLIT ARAYÜZÜ ---
st.set_page_config(layout="wide", page_title="Futbol Analiz ve Canlı Skor Paneli")
st.title("⚽ Gelişmiş Futbol Analiz ve Canlı Skor Paneli")

# Sekmeler (Analiz ve Canlı Skorlar)
sekme1, sekme2 = st.tabs(["📊 Derinlemesine Maç Analizi", "🔴 Canlı Maçlar ve Skorlar"])

df = veri_yukle()

with sekme1:
    st.subheader("İstatistiksel Tahmin ve Örüntü Motoru")
    if not df.empty:
        takimlar = sorted(df['HomeTeam'].astype(str).unique())
        
        col1, col2 = st.columns(2)
        with col1:
            ev_sahibi = st.selectbox("Ev Sahibi Takım", takimlar, index=0, key="ev_key")
        with col2:
            deplasman = st.selectbox("Deplasman Takım", takimlar, index=1 if len(takimlar) > 1 else 0, key="dep_key")
            
        if st.button("Analiz Et ve Tahminleri Üret"):
            sonuc = detayli_mac_analizi(df, ev_sahibi, deplasman)
            st.markdown("---")
            
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric(label=f"{ev_sahibi} Kazanma İhtimali", value=f"%{sonuc['ev_oran']}")
            with m2:
                st.metric(label="Beraberlik İhtimali", value=f"%{sonuc['beraberlik_oran']}")
            with m3:
                st.metric(label=f"{deplasman} Kazanma İhtimali", value=f"%{sonuc['dep_oran']}")
                
            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("🎯 Tahmini Maç Skoru")
                st.markdown(f"### **{ev_sahibi} {sonuc['skor_tahmini']} {deplasman}**")
                st.write(f"* Ev Sahibi Gol Beklentisi (xG): **{sonuc['ev_gol_beklentisi']}**")
                st.write(f"* Deplasman Gol Beklentisi (xG): **{sonuc['dep_gol_beklentisi']}**")
            with c2:
                st.subheader("📊 Algoritma Örüntüleri ve Trendler")
                for t in sonuc['oruntuler']:
                    st.write(t)
                st.write(f"* **H2H Tarihsel Piyasası:** {sonuc['h2h_favori']} ({sonuc['h2h_mac_sayisi']} maç)")
    else:
        st.warning("Veri yüklenemedi.")

with sekme2:
    st.subheader("Günün Canlı Maç Akışı")
    if st.button("🔄 Skorları Güncelle"):
        st.rerun()
        
    canli_maclar = canli_maclari_getir()
    
    if canli_maclar:
        for mac in canli_maclar:
            ev = mac['homeTeam']['name']
            dep = mac['awayTeam']['name']
            durum = mac['status']
            skor_ev = mac['score']['fullTime']['home']
            skor_dep = mac['score']['fullTime']['away']
            lig = mac['competition']['name']
            
            durum_metni = "🔴 CANLI" if durum == "IN_PLAY" else ("✅ BİTTİ" if durum == "FINISHED" else "⏳ BAŞLAMADI")
            
            with st.container():
                st.info(f"**{lig}** | Durum: **{durum_metni}**")
                cm1, cm2, cm3 = st.columns([3, 2, 3])
                with cm1:
                    st.markdown(f"<h4 style='text-align: right;'>{ev}</h4>", unsafe_allow_html=True)
                with cm2:
                    st.markdown(f"<h3 style='text-align: center;'>{skor_ev} - {skor_dep}</h3>", unsafe_allow_html=True)
                with cm3:
                    st.markdown(f"<h4 style='text-align: left;'>{dep}</h4>", unsafe_allow_html=True)
                st.markdown("---")
    else:
        st.info("Bugün için aktif canlı maç verisi bulunamadı veya maç saatini bekliyor.")
