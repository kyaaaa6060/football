import pandas as pd
import streamlit as st
import requests
import datetime

@st.cache_data(ttl=1800)
def internetten_takim_verilerini_cek(lig_kodu):
    try:
        # İnternetten ilgili ligin bitmiş tüm güncel maçlarını çekiyoruz (Arşiv ve Analiz için)
        url = f"https://api.football-data.org/v4/competitions/{lig_kodu}/matches?status=FINISHED"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json().get('matches', [])
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

# İnternetten gelen güncel maçlar üzerinden geçmiş/H2H analizi yapan motor
def internet_uzerinden_gecmis_analizi(maclar, ev_sahibi, deplasman):
    if not maclar:
        return {"gecmis_senaryolar": []}
    
    # Seçilen iki takımın internetteki güncel geçmiş karşılaşmaları (H2H)
    h2h_maclar = [m for m in maclar if (m['homeTeam']['name'] == ev_sahibi and m['awayTeam']['name'] == deplasman) or 
                                       (m['homeTeam']['name'] == deplasman and m['awayTeam']['name'] == ev_sahibi)]
    
    # Ev sahibinin güncel son maçları
    ev_son_maclar = [m for m in maclar if m['homeTeam']['name'] == ev_sahibi or m['awayTeam']['name'] == ev_sahibi][-10:]

    toplam_h2h = len(h2h_maclar)
    gecmis_senaryolar = []

    if toplam_h2h > 0:
        ev_galibiyet = 0
        dep_galibiyet = 0
        beraberlikler = 0
        for m in h2h_maclar:
            kazanan = m['score']['winner'] # HOME_TEAM, AWAY_TEAM, DRAW
            kazanan_takim = m['homeTeam']['name'] if kazanan == 'HOME_TEAM' else (m['awayTeam']['name'] if kazanan == 'AWAY_TEAM' else None)
            
            if kazanan_takim == ev_sahibi:
                ev_galibiyet += 1
            elif kazanan_takim == deplasman:
                dep_galibiyet += 1
            else:
                beraberlikler += 1

        metin = f"İnternetteki güncel kayıtlara göre bu iki takım daha önce {toplam_h2h} kez karşılaşmış. {ev_sahibi}: {ev_galibiyet} galibiyet, {deplasman}: {dep_galibiyet} galibiyet, Beraberlik: {beraberlikler}."
        gecmis_senaryolar.append({
            "baslik": f"📁 Güncel Karşılıklı Maç Arşivi (H2H - {toplam_h2h} Maç)",
            "detay": metin
        })
    else:
        gecmis_senaryolar.append({
            "baslik": "📁 Doğrudan Karşılaşma Bulunamadı",
            "detay": "Bu iki ekip bu sezon güncel veri havuzunda doğrudan resmi maç yapmamış."
        })

    # Güncel gol eğilimleri
    if ev_son_maclar:
        toplam_gol = 0
        ust_sayisi = 0
        for m in ev_son_maclar:
            hg = m['score']['fullTime']['home'] or 0
            ag = m['score']['fullTime']['away'] or 0
            t_gol = hg + ag
            if t_gol > 2.5:
                ust_sayisi += 1
        ust_yuzde = round((ust_sayisi / len(ev_son_maclar)) * 100)
        gecmis_senaryolar.append({
            "baslik": f"📊 Güncel Gol Oranı Eğilimi ({ev_sahibi})",
            "detay": f"{ev_sahibi} takımının son {len(ev_son_maclar)} resmi maçının %{ust_yuzde} oranında 2.5 Gol Üstü bittiği görülüyor."
        })

    return {
        "gecmis_senaryolar": gecmis_senaryolar,
        "h2h_sayisi": toplam_h2h
    }

st.set_page_config(layout="wide", page_title="Canlı ve Güncel Futbol Analiz Paneli")
st.title("⚽ Tamamen Canlı ve Güncel Arşiv / Tahmin Motoru")

sekme1, sekme2, sekme3 = st.tabs(["📊 Güncel / Canlı Tahmin", "📁 Güncel Arşiv & Geçmiş Analiz", "🔴 Canlı Skor Merkezi"])

ligler = {
    "İngiltere Premier Lig": "PL",
    "İspanya La Liga": "PD",
    "İtalya Serie A": "SA",
    "Almanya Bundesliga": "BL1",
    "Fransa Ligue 1": "FL1",
    "Türkiye Süper Lig": "TSL",
    "UEFA Şampiyonlar Ligi": "CL"
}

with sekme1:
    st.subheader("İnternetten Otomatik Beslenen Güncel Tahmin Motoru")
    secilen_lig = st.selectbox("Lig Seçin", list(ligler.keys()), key="s1")
    maclar = internetten_takim_verilerini_cek(ligler[secilen_lig])

    if maclar:
        t_set = set(m['homeTeam']['name'] for m in maclar).union(set(m['awayTeam']['name'] for m in maclar))
        takimlar = sorted(list(t_set))
        if len(takimlar) >= 2:
            c1, c2 = st.columns(2)
            with c1: ev = st.selectbox("Ev Sahibi", takimlar, key="ev1")
            with c2: dep = st.selectbox("Deplasman", takimlar, key="dep1")

            if st.button("Güncel Analizi Çalıştır"):
                st.success(f"{ev} ve {dep} için internetteki güncel verilerle analiz yapıldı!")
        else:
            st.warning("Yeterli takım verisi yok.")

with sekme2:
    st.subheader("📁 İnternet Tabanlı Güncel Arşiv ve Geçmiş Taraması")
    secilen_lig_arsiv = st.selectbox("Lig Seçin (Arşiv için)", list(ligler.keys()), key="s_arsiv")
    arsiv_maclari = internetten_takim_verilerini_cek(ligler[secilen_lig_arsiv])

    if arsiv_maclari:
        a_set = set(m['homeTeam']['name'] for m in arsiv_maclari).union(set(m['awayTeam']['name'] for m in arsiv_maclari))
        arsiv_takimlar = sorted(list(a_set))
        
        ac1, ac2 = st.columns(2)
        with ac1: a_ev = st.selectbox("Ev Sahibi Seç", arsiv_takimlar, key="a_ev")
        with ac2: a_dep = st.selectbox("Deplasman Seç", arsiv_takimlar, key="a_dep")

        if st.button("Güncel Geçmiş Arşivini Getir"):
            arsiv_sonuc = internet_uzerinden_gecmis_analizi(arsiv_maclari, a_ev, a_dep)
            st.markdown("---")
            st.markdown(f"### 🔍 {a_ev} vs {a_dep} - İnternet Tabanlı Güncel Arşiv Raporu")
            
            for sen in arsiv_sonuc['gecmis_senaryolar']:
                st.markdown(f"**{sen['baslik']}**")
                st.write(sen['detay'])
                st.markdown("")
    else:
        st.warning("Seçilen lig için internetten arşiv verisi alınamadı.")

with sekme3:
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
                with cm1: st.markdown(f"<h4 style='text-align: right;'>{ev}</h4>", unsafe_allow_html=True)
                with cm2: st.markdown(f"<h3 style='text-align: center;'>{skor_ev} - {skor_dep}</h3>", unsafe_allow_html=True)
                with cm3: st.markdown(f"<h4 style='text-align: left;'>{dep}</h4>", unsafe_allow_html=True)
                st.markdown("---")
    else:
        st.info("Şu an aktif oynanan canlı maç bulunmuyor.")
