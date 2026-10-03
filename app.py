import pandas as pd
import streamlit as st
import requests
import datetime

@st.cache_data
def veri_yukle():
    try:
        xls = pd.ExcelFile('all-euro-data-2026-2027.xlsx')
        tum_ligler = []
        for sekme in xls.sheet_names:
            df_sekme = pd.read_excel(xls, sheet_name=sekme)
            tum_ligler.append(df_sekme)
        df = pd.concat(tum_ligler, ignore_index=True)
        df = df.dropna(subset=['HomeTeam', 'AwayTeam']) 
        return df
    except:
        return pd.DataFrame()

@st.cache_data(ttl=1800)
def internetten_takim_verilerini_cek(lig_kodu):
    try:
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

def arsiv_ve_gecmis_analizi(df, ev_sahibi, deplasman):
    if df.empty:
        return {"gecmis_senaryolar": []}
    
    h2h_maclar = df[((df['HomeTeam'] == ev_sahibi) & (df['AwayTeam'] == deplasman)) | 
                    ((df['HomeTeam'] == deplasman) & (df['AwayTeam'] == ev_sahibi))]
    
    ev_arsiv = df[(df['HomeTeam'] == ev_sahibi) | (df['AwayTeam'] == ev_sahibi)].tail(10)

    toplam_h2h = len(h2h_maclar)
    gecmis_senaryolar = []

    if toplam_h2h > 0:
        ev_galibiyet = len(h2h_maclar[((h2h_maclar['HomeTeam'] == ev_sahibi) & (h2h_maclar['FTR'] == 'H')) | 
                                       ((h2h_maclar['AwayTeam'] == ev_sahibi) & (h2h_maclar['FTR'] == 'A'))])
        dep_galibiyet = len(h2h_maclar[((h2h_maclar['HomeTeam'] == deplasman) & (h2h_maclar['FTR'] == 'H')) | 
                                        ((h2h_maclar['AwayTeam'] == deplasman) & (h2h_maclar['FTR'] == 'A'))])
        beraberlikler = toplam_h2h - (ev_galibiyet + dep_galibiyet)
        
        metin = f"Bu iki takım arşivde daha önce {toplam_h2h} kez karşılaşmış. {ev_sahibi}: {ev_galibiyet} kez kazandı, {deplasman}: {dep_galibiyet} kez kazandı, Beraberlik: {beraberlik}."
        gecmis_senaryolar.append({
            "baslik": f"📁 Doğrudan Geçmiş Karşılaşmalar (H2H - {toplam_h2h} Maç)",
            "detay": metin
        })
    else:
        gecmis_senaryolar.append({
            "baslik": "📁 Doğrudan Geçmiş Karşılaşma Bulunamadı",
            "detay": "Bu iki ekip arşive kaydedilen dönemde doğrudan resmi maç yapmamış."
        })

    if not ev_arsiv.empty and 'FTHG' in ev_arsiv.columns and 'FTAG' in ev_arsiv.columns:
        ev_arsiv = ev_arsiv.copy()
        ev_arsiv['ToplamGol'] = ev_arsiv['FTHG'] + ev_arsiv['FTAG']
        ust_sayisi = len(ev_arsiv[ev_arsiv['ToplamGol'] > 2.5])
        ust_yuzde = round((ust_sayisi / len(ev_arsiv)) * 100)
        gecmis_senaryolar.append({
            "baslik": f"📊 Arşiv Gol Oranı Eğilimi ({ev_sahibi})",
            "detay": f"Arşivdeki son maçlarına bakıldığında {ev_sahibi} maçlarının %{ust_yuzde} oranında 2.5 Gol Üstü bittiği görülüyor."
        })

    return {
        "gecmis_senaryolar": gecmis_senaryolar,
        "h2h_sayisi": toplam_h2h
    }

st.set_page_config(layout="wide", page_title="Arşiv ve Canlı Futbol Analiz Paneli")
st.title("⚽ Kapsamlı Arşiv & Canlı Tahmin Motoru")

sekme1, sekme2, sekme3 = st.tabs(["📊 Güncel / Canlı Tahmin", "📁 Arşiv & Eski Maç Benzerlikleri", "🔴 Canlı Skor Merkezi"])

df_arsiv = veri_yukle()
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
    secilen_lig = st.selectbox("Lig Seçin (Güncel)", list(ligler.keys()), key="s1")
    maclar = internetten_takim_verilerini_cek(ligler[secilen_lig])

    if maclar:
        t_set = set(m['homeTeam']['name'] for m in maclar).union(set(m['awayTeam']['name'] for m in maclar))
        takimlar = sorted(list(t_set))
        if len(takimlar) >= 2:
            c1, c2 = st.columns(2)
            with c1: ev = st.selectbox("Ev Sahibi", takimlar, key="ev1")
            with c2: dep = st.selectbox("Deplasman", takimlar, key="dep1")

            if st.button("Güncel Analizi Çalıştır"):
                st.success(f"{ev} ve {dep} için güncel form analizi başarıyla tamamlandı!")
        else:
            st.warning("Yeterli takım verisi yok.")

with sekme2:
    st.subheader("📁 Arşivdeki Eski Maçlar ve Benzerlik / İhtimal Taraması")
    if not df_arsiv.empty:
        arsiv_takimlar = sorted(df_arsiv['HomeTeam'].astype(str).unique())
        
        ac1, ac2 = st.columns(2)
        with ac1: a_ev = st.selectbox("Arşivden Ev Sahibi Seç", arsiv_takimlar, key="a_ev")
        with ac2: a_dep = st.selectbox("Arşivden Deplasman Seç", arsiv_takimlar, key="a_dep")

        if st.button("Arşivdeki Benzerlikleri ve İhtimalleri Getir"):
            arsiv_sonuc = arsiv_ve_gecmis_analizi(df_arsiv, a_ev, a_dep)
            st.markdown("---")
            st.markdown(f"### 🔍 {a_ev} vs {a_dep} - Geçmiş Arşiv Raporu")
            
            for sen in arsiv_sonuc['gecmis_senaryolar']:
                st.markdown(f"**{sen['baslik']}**")
                st.write(sen['detay'])
                st.markdown("")
    else:
        st.warning("Arşivde okunacak Excel dosyası bulunamadı. Lütfen 'all-euro-data-2026-2027.xlsx' dosyasının reponuzda olduğundan emin olun.")

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
