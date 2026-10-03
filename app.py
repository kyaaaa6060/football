import pandas as pd
import streamlit as st

# Veriyi bir kez okuyup hafızada tutarak paneli hızlandırıyoruz
@st.cache_data
def veri_yukle():
    try:
        xls = pd.ExcelFile('all-euro-data-2026-2027.xlsx')
        tum_ligler = []
        for sekme in xls.sheet_names:
            df_sekme = pd.read_excel(xls, sheet_name=sekme)
            tum_ligler.append(df_sekme)
        
        df = pd.concat(tum_ligler, ignore_index=True)
        # Boş takım isimleri varsa temizle
        df = df.dropna(subset=['HomeTeam', 'AwayTeam']) 
        return df
    except Exception as e:
        st.error(f"Veri yüklenirken hata oluştu: {e}")
        return pd.DataFrame()

def oranli_ham_veri_analizi(df, ev_sahibi, deplasman):
    ev_genel_son5 = df[(df['HomeTeam'] == ev_sahibi) | (df['AwayTeam'] == ev_sahibi)].tail(5)
    dep_genel_son5 = df[(df['HomeTeam'] == deplasman) | (df['AwayTeam'] == deplasman)].tail(5)
    ev_ic_saha = df[df['HomeTeam'] == ev_sahibi].tail(5)
    dep_dis_saha = df[df['AwayTeam'] == deplasman].tail(5)
    
    h2h = df[((df['HomeTeam'] == ev_sahibi) & (df['AwayTeam'] == deplasman)) | 
             ((df['HomeTeam'] == deplasman) & (df['AwayTeam'] == ev_sahibi))].tail(5)

    def istatistik_cikar(veri_seti, takim_adi):
        if veri_seti.empty:
            return {'Atilan_Ort': 0, 'Yenen_Ort': 0, 'Galibiyet_%': 0, 'Favoriyken_Kazanma_%': 'Veri Yok'}
        
        atilan_gol = veri_seti.apply(lambda x: x['FTHG'] if x['HomeTeam'] == takim_adi else x['FTAG'], axis=1).mean()
        yenen_gol = veri_seti.apply(lambda x: x['FTAG'] if x['HomeTeam'] == takim_adi else x['FTHG'], axis=1).mean()
        
        galibiyet_sayisi = veri_seti.apply(lambda x: 1 if (x['HomeTeam'] == takim_adi and x['FTHG'] > x['FTAG']) or 
                                                          (x['AwayTeam'] == takim_adi and x['FTAG'] > x['FTHG']) else 0, axis=1).sum()
        galibiyet_yuzdesi = (galibiyet_sayisi / len(veri_seti)) * 100
        
        favori_kazanma_yuzdesi = 'Oran Verisi Yok'
        if 'B365H' in veri_seti.columns and 'B365A' in veri_seti.columns:
            favori_mac_sayisi = 0
            favoriyken_kazanilan = 0
            
            for index, mac in veri_seti.iterrows():
                # Bet365 Oranlarına Göre Favori Çıkılan Maçların Analizi
                try:
                    b365h = float(mac['B365H'])
                    b365a = float(mac['B365A'])
                    
                    if mac['HomeTeam'] == takim_adi and b365h < b365a:
                        favori_mac_sayisi += 1
                        if mac['FTHG'] > mac['FTAG']: favoriyken_kazanilan += 1
                            
                    elif mac['AwayTeam'] == takim_adi and b365a < b365h:
                        favori_mac_sayisi += 1
                        if mac['FTAG'] > mac['FTHG']: favoriyken_kazanilan += 1
                except ValueError:
                    continue # Oran verisi eksikse veya sayı değilse atla
            
            if favori_mac_sayisi > 0:
                favori_kazanma_yuzdesi = round((favoriyken_kazanilan / favori_mac_sayisi) * 100, 2)
            else:
                favori_kazanma_yuzdesi = 'Favori Çıkmadı'

        return {
            'Atilan_Ort': round(atilan_gol, 2),
            'Yenen_Ort': round(yenen_gol, 2),
            'Galibiyet_%': round(galibiyet_yuzdesi, 2),
            'Favoriyken_Kazanma_%': favori_kazanma_yuzdesi
        }

    return {
        f'{ev_sahibi} Son 5 (Genel)': istatistik_cikar(ev_genel_son5, ev_sahibi),
        f'{deplasman} Son 5 (Genel)': istatistik_cikar(dep_genel_son5, deplasman),
        f'{ev_sahibi} İç Saha': istatistik_cikar(ev_ic_saha, ev_sahibi),
        f'{deplasman} Dış Saha': istatistik_cikar(dep_dis_saha, deplasman),
        'H2H (Ev Sahibi)': istatistik_cikar(h2h, ev_sahibi),
        'H2H (Deplasman)': istatistik_cikar(h2h, deplasman)
    }

# --- STREAMLIT ARAYÜZÜ ---
st.set_page_config(layout="wide", page_title="Avrupa Futbol Ham Veri Paneli")
st.title("Avrupa Ligleri: H2H ve Oran Odaklı Maç Analizi")

df = veri_yukle()

if not df.empty:
    takimlar = sorted(df['HomeTeam'].astype(str).unique())
    
    col1, col2 = st.columns(2)
    with col1:
        ev_sahibi = st.selectbox("Ev Sahibi Takım", takimlar)
    with col2:
        deplasman = st.selectbox("Deplasman Takım", takimlar, index=1 if len(takimlar) > 1 else 0)
        
    if st.button("Ham İstatistikleri Hesapla"):
        sonuclar = oranli_ham_veri_analizi(df, ev_sahibi, deplasman)
        
        st.markdown("---")
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("Form Durumu (Genel)")
            st.write(f"**{ev_sahibi} Son 5:**", sonuclar.get(f'{ev_sahibi} Son 5 (Genel)'))
            st.write(f"**{deplasman} Son 5:**", sonuclar.get(f'{deplasman} Son 5 (Genel)'))
            
            st.subheader("İç Saha / Dış Saha Formu")
            st.write(f"**{ev_sahibi} İç Saha:**", sonuclar.get(f'{ev_sahibi} İç Saha'))
            st.write(f"**{deplasman} Dış Saha:**", sonuclar.get(f'{deplasman} Dış Saha'))
            
        with c2:
            st.subheader("Aralarındaki Maçlar (H2H)")
            st.write("**Ev Sahibi Perspektifinden:**", sonuclar.get('H2H (Ev Sahibi)'))
            st.write("**Deplasman Perspektifinden:**", sonuclar.get('H2H (Deplasman)'))
else:
    st.warning("Veri seti boş veya yüklenemedi. Lütfen 'all-euro-data-2026-2027.xlsx' dosyasının dizinde olduğundan emin ol.")
