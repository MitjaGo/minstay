"""
Generator linkov za Phobs rezervacijski sistem (book.sava-hotels-resorts.com)
==============================================================================

Izbereš OBDOBJE (npr. 1.8.–7.8.) in dolžino/-e bivanja (2, 3, 4 noči ali
poljubno) - aplikacija za vsak izbran hotel in vsako izbrano dolžino bivanja
generira VSE možne kombinacije prihod/odhod znotraj tega obdobja ter sestavi
direktne linke do razpoložljivosti.

Zagon:
    pip install -r requirements.txt
    streamlit run phobs_link_generator.py
"""

from datetime import date, timedelta
from urllib.parse import urlencode

import pandas as pd
import streamlit as st

BASE_URL = "https://book.sava-hotels-resorts.com/book.php"
COMPANY_ID = "205"  # fiksen za vse Bernardin hotele

HOTELI = {
    "Grand Hotel Bernardin": "514",
    "Hotel Histrion": "513",
    "Hotel Salinera": "520",
    "Depandanse San Simon": "526",
    "Hotel Mirta": "524",
    "Hotel Haliaetum": "517",
}

st.set_page_config(page_title="Phobs – generator linkov", page_icon="🔗", layout="wide")
st.title("🔗 Bernardin hoteli – generator linkov za razpoložljivost")
st.caption("book.sava-hotels-resorts.com  ·  companyid je fiksno 205")

# --------------------------------------------------------------------------- #
# Sidebar – izbira hotelov in splošne nastavitve
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("🏨 Izberi hotele")
    col_a, col_b = st.columns(2)
    izberi_vse = col_a.button("✅ Vse", use_container_width=True)
    pocisti_vse = col_b.button("❌ Nobenega", use_container_width=True)

    if izberi_vse:
        st.session_state["izbrani_hoteli"] = list(HOTELI.keys())
    if pocisti_vse:
        st.session_state["izbrani_hoteli"] = []
    if "izbrani_hoteli" not in st.session_state:
        st.session_state["izbrani_hoteli"] = list(HOTELI.keys())  # privzeto vsi

    izbrani_seznam = []
    for ime in HOTELI:
        checked = st.checkbox(
            f"{ime}  (ID: {HOTELI[ime]})",
            value=ime in st.session_state["izbrani_hoteli"],
            key=f"cb_{ime}",
        )
        if checked:
            izbrani_seznam.append(ime)
    st.session_state["izbrani_hoteli"] = izbrani_seznam

    with st.expander("➕ Dodaj hotel z ročnim ID-jem"):
        rocno_ime = st.text_input("Ime hotela (poljubno)", value="")
        rocno_id = st.text_input("hotelid", value="")
        if rocno_ime and rocno_id:
            HOTELI[rocno_ime] = rocno_id
            izbrani_seznam.append(rocno_ime)

    st.divider()
    st.header("⚙️ Ostale nastavitve")
    ibelang = st.selectbox("Jezik (ibelang)", ["si", "en", "de", "it", "hr"], index=0)
    crcid = st.text_input(
        "crcid (neobvezno – kampanjska koda)",
        value="",
        help="Ni nujna za delovanje linka, pusti prazno, če je ne potrebuješ.",
    )

# --------------------------------------------------------------------------- #
# Glavno območje – obdobje + dolžina bivanja (min stay)
# --------------------------------------------------------------------------- #
st.subheader("📅 Obdobje")
col_od, col_do = st.columns(2)
with col_od:
    start_date = st.date_input("Od (prihod najzgodneje)", value=date(2026, 8, 1))
with col_do:
    end_date = st.date_input("Do (odhod najkasneje)", value=date(2026, 8, 7))

st.subheader("🌙 Dolžina bivanja (min. stay)")
col1, col2, col3, col4 = st.columns(4)
n2 = col1.checkbox("2 noči", value=True)
n3 = col2.checkbox("3 noči", value=False)
n4 = col3.checkbox("4 noči", value=False)
custom_on = col4.checkbox("Drugo:", value=False)
custom_nights = col4.number_input(
    "Št. noči", min_value=1, max_value=30, value=5, label_visibility="collapsed", disabled=not custom_on
)

nights_options = []
if n2:
    nights_options.append(2)
if n3:
    nights_options.append(3)
if n4:
    nights_options.append(4)
if custom_on:
    nights_options.append(int(custom_nights))

zazeni = st.button("🔗 Generiraj linke", type="primary")

if end_date <= start_date:
    st.error("Datum 'Do' mora biti kasnejši od datuma 'Od'.")
    st.stop()

if not izbrani_seznam:
    st.info("Izberi vsaj en hotel v levem meniju.")
    st.stop()

if not nights_options:
    st.info("Izberi vsaj eno dolžino bivanja (2, 3, 4 noči ali 'Drugo').")
    st.stop()


def sestavi_link(hotelid: str, checkin: date, checkout: date) -> str:
    params = {
        "page": "availability",
        "companyid": COMPANY_ID,
        "hotelid": hotelid,
        "checkin": checkin.isoformat(),
        "checkout": checkout.isoformat(),
        "ibelang": ibelang,
    }
    if crcid.strip():
        params["crcid"] = crcid.strip()
    return f"{BASE_URL}?{urlencode(params)}"


# --------------------------------------------------------------------------- #
# Generiranje: za vsak hotel x vsako dolžino bivanja x vsak možen datum
# prihoda znotraj izbranega obdobja
# --------------------------------------------------------------------------- #
vrstice = []
for ime_hotela in izbrani_seznam:
    hid = HOTELI[ime_hotela]
    for nights in sorted(set(nights_options)):
        checkin = start_date
        while True:
            checkout = checkin + timedelta(days=nights)
            if checkout > end_date:
                break
            vrstice.append({
                "Hotel": ime_hotela,
                "Noči": nights,
                "Prihod": checkin.isoformat(),
                "Odhod": checkout.isoformat(),
                "Link": sestavi_link(hid, checkin, checkout),
            })
            checkin += timedelta(days=1)

if not vrstice:
    st.warning(
        "V izbranem obdobju ni mogoče umestiti nobene od izbranih dolžin bivanja. "
        "Podaljšaj obdobje 'Od–Do' ali izberi krajše bivanje."
    )
    st.stop()

df = pd.DataFrame(vrstice)

st.divider()
st.subheader(f"Generirani termini ({len(df)}) za {len(izbrani_seznam)} hotel(ov)")

for ime_hotela in izbrani_seznam:
    st.markdown(f"## 🏨 {ime_hotela}")
    podmnozica_hotel = df[df["Hotel"] == ime_hotela]
    for nights in sorted(set(nights_options)):
        podmnozica = podmnozica_hotel[podmnozica_hotel["Noči"] == nights]
        if podmnozica.empty:
            continue
        st.markdown(f"**{nights} noči** ({len(podmnozica)} terminov)")
        for _, vrstica in podmnozica.iterrows():
            st.markdown(
                f"- {vrstica['Prihod']} → {vrstica['Odhod']} &nbsp; "
                f"<a href='{vrstica['Link']}' target='_blank' rel='noopener noreferrer'>Odpri razpoložljivost ↗</a>",
                unsafe_allow_html=True,
            )

st.divider()
st.subheader("Vsi linki (tabela)")
st.dataframe(df, use_container_width=True, column_config={
    "Link": st.column_config.LinkColumn("Link", display_text="Odpri →")
})

csv = df.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Prenesi seznam linkov (CSV)",
    data=csv,
    file_name=f"bernardin_linki_{start_date}_{end_date}.csv",
    mime="text/csv",
)
