import pandas as pd
import streamlit as st
import requests
import datetime

@st.cache_data(ttl=1800)
def internetten_takim_verilerini_cek(lig_kodu):
    try:
        url = f"https://api.football-data.org/v4/competitions/{lig_kodu}/matches?status=FINISHED"
        headers = {}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get('matches', [])
    except:
        pass
    return []

@st.cache_data(ttl=600)
def canli_maclari_getir():
    try:
        bugun = datetime.datetime.now().strftime('%Y-%m-%d')
        url = f"https://api.football-data.org/v4/matches?dateFrom={bugun}&dateTo={bugun}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json().get('matches', [])
    except:
        pass
    return []

def otomatik_mac_analizi(maclar, ev_sahibi, deplasman):
    ev_maclari = [m for m in maclar if m['homeTeam']['name'] == ev_sahibi or m['awayTeam']['name'] == ev_sahibi][-5:]
    dep_maclari = [m for m in maclar if m['homeTeam']['name'] == deplasman or m['awayTeam']['name'] == deplasman][-5:]

    ev_atilan, ev_yenen = 0, 0
    for m in ev_maclari:
        if m['homeTeam']['name'] == ev_sahibi:
            ev_atilan += m['score']['fullTime']['home'] or 0
            ev_yenen += m['score']['fullTime']['away'] or 0
        else:
            ev_atilan += m['score']['fullTime']['away'] or 0
            ev_yenen += m['score']['fullTime']['home'] or 0

    dep_atilan, dep_yenen = 0, 0
    for m in dep_maclari:
        if m['homeTeam']['name'] == deplasman:
            dep_atilan += m['score']['fullTime']['home'] or 0
            dep_yenen += m['score']['fullTime']['away'] or 0
        else:
            dep_atilan += m['score']['fullTime']['away'] or 0
            dep_yenen += m['score']['fullTime']['home'] or 0

    ev_at_ort = (ev_atilan / len(ev_maclari)) if ev_maclari else 1.3
    ev_yen_ort = (ev_yenen / len(ev_maclari)) if ev_maclari else 1.0
    dep_at_ort = (dep_atilan / len(dep_maclari)) if dep_maclari else 1.2
    dep_yen_ort = (dep_yenen / len(dep_maclari)) if dep_maclari else 1.1

    ev_beklenen = (ev_at_ort + dep_yen_ort) / 2
    dep_beklenen = (dep_at_ort + ev_yen_ort) / 2

    ev_oran = max(15, min(75, round((ev_beklenen / (ev_beklenen + dep_beklenen + 0.1)) * 100)))
    dep_oran = max(15, min(75, round((dep_beklenen / (ev_beklenen + dep_beklenen + 0.1)) * 100)))
    beraberlik = max(10, 100 - (ev_oran + dep_oran))

    tahmini_ev_gol = round(ev_beklenen)
    tahmini_dep_gol = round(dep_beklenen)

    oruntuler = []
    if (ev_at_ort + dep_at_ort) > 2.7:
        oruntuler.append("🔥 **Yüksek Gol Eğilimi:** Takımların güncel son maçlarında maç başı gol ortalamaları yüksek (2.5 Üst potansiyeli).")
    else:
        oruntuler.append("🛡 **Düşük Tempo:** Son karşılaşmalarda skor üretimi kısıtlı seyrediyor.")

    if ev_yen_ort > 1.1 and dep_yen_ort > 1.1:
        oruntuler.append("⚡ **Savunma Zaafiyeti:** Her iki taraf da son maçlarında düzenli gol yiyor (KG Var güçlü aday).")

    return {
        "ev_gol_beklentisi": round(ev_beklenen, 2),
        "dep_gol_beklentisi": round(dep_beklenen, 2),
        "ev_oran": ev_oran,
        "dep_oran": dep_oran,
        "beraberlik_oran": beraberlik,
        "skor_tahmini": f"{tahmini_ev_gol} - {tahmini_dep_gol}",
        "oruntuler": oruntuler,
        "analiz_edilen_mac": max(len(ev_maclari), len(dep_maclari))
    }

st.set_page_config(layout="wide", page_title="Otomatik Canlı Futbol Analiz Paneli")
st.title("⚽ Tamamen Otomatik Canlı Analiz ve Skor Motoru")

sekme1, sekme2 = st.tabs(["📊 Akıllı Maç Tahmin Motoru", "🔴 Canlı Skor Merkezi"])

ligler = {
    "İngiltere Premier Lig": "PL",
    "İspanya La Liga": "PD",
    "İtalya Serie A": "SA",
    "Almanya Bundesliga": "BL1",
    "Fransa Ligue 1": "FL1",
    "Türkiye Süper Lig (Global Takip)": "CL"
}

with sekme1:
    st.subheader("İnternetten Otomatik Beslenen Tahmin Paneli")
    secilen_lig_adi = st.selectbox("Lig Seçin", list(ligler.keys()))
    lig_kodu = ligler[secilen_lig_adi]

    with st.spinner("Güncel takım verileri internetten çekiliyor..."):
        maclar = internetten_takim_verilerini_cek(lig_kodu)

    if maclar:
        takimlar_set = set()
        for m in maclar:
            takimlar_set.add(m['homeTeam']['name'])
            takimlar_set.add(m['awayTeam']['name'])
        takimlar = sorted(list(takimlar_set))

        if len(takimlar) >= 2:
            col1, col2 = st.columns(2)
            with col1:
                ev_sahibi = st.selectbox("Ev Sahibi Takım", takimlar, index=0)
            with col2:
                deplasman = st.selectbox("Deplasman Takım", takimlar, index=1 if len(takimlar) > 1 else 0)

            if st.button("Canlı Verilerle Analiz Et"):
                sonuc = otomatik_mac_analizi(maclar, ev_sahibi, deplasman)
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
                    st.write(f"* Ev Sahibi Gol Beklentisi (Güncel xG): **{sonuc['ev_gol_beklentisi']}**")
                    st.write(f"* Deplasman Gol Beklentisi (Güncel xG): **{sonuc['dep_gol_beklentisi']}**")
                with c2:
                    st.subheader("📊 Otomatik Algoritma Trendleri")
                    # Düzeltilen kısım (hata veren := kaldırıldı)
                    for t in sonuc['oruntuler']:
                        st.write(t)
                    st.write(f"* **Veri Kaynağı:** Son {sonuc['analiz_edilen_mac']} resmi maç taranarak hesaplandı.")
        else:
            st.warning("Bu lig için yeterli takım verisi yüklenemedi.")
    else:
        st.info("Seçilen lig için internet üzerinden güncel maç verisi alınamadı. Lütfen daha sonra tekrar deneyin.")

with sekme2:
    st.subheader("Günün Canlı Maç Takip Ekranı")
    if st.button("🔄 Canlı Skorları Yenile"):
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

            durum_etiketi = "🔴 CANLI" if durum == "IN_PLAY" else ("✅ BİTTİ" if durum == "FINISHED" else "⏳ BAŞLAMADI")

            with st.container():
                st.info(f"**{lig}** | Durum: **{durum_etiketi}**")
                cm1, cm2, cm3 = st.columns([3, 2, 3])
                with cm1:
                    st.markdown(f"<h4 style='text-align: right;'>{ev}</h4>", unsafe_allow_html=True)
                with cm2:
                    st.markdown(f"<h3 style='text-align: center;'>{skor_ev} - {skor_dep}</h3>", unsafe_allow_html=True)
                with cm3:
                    st.markdown(f"<h4 style='text-align: left;'>{dep}</h4>", unsafe_allow_html=True)
                st.markdown("---")
    else:
        st.info("Şu an aktif oynanan canlı maç bulunmuyor.")
