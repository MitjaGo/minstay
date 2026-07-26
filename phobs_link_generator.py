"""
Generator linkov za Phobs rezervacijski sistem (book.sava-hotels-resorts.com)
==============================================================================

Za izbrano obdobje (npr. 1.8.–7.8.) in izbrane dolžine bivanja (2, 3, 4 noči)
generira vse možne kombinacije checkin/checkout datumov ter sestavi direktne
linke do razpoložljivosti za izbrani hotel.

Zagon:
    pip install -r requirements.txt
    streamlit run phobs_link_generator.py
"""

from datetime import date, timedelta
from urllib.parse import urlencode

import pandas as pd
import streamlit as st

BASE_URL = "https://book.sava-hotels-resorts.com/book.php"

st.set_page_config(page_title="Phobs – generator linkov", page_icon="🔗", layout="wide")
st.title("🔗 Phobs – generator linkov za razpoložljivost")
st.caption("book.sava-hotels-resorts.com – generira linke za izbrano obdobje in dolžino bivanja")

HOTELI = {
    "Grand Hotel Bernardin": "514",
    "Hotel Histrion": "513",
    "Hotel Salinera": "520",
    "Depandanse San Simon": "526",
    "Hotel Mirta": "524",
    "Hotel Haliaetum": "517",
}

with st.sidebar:
    st.header("Nastavitve hotela")
    companyid = st.text_input("companyid", value="205")

    st.markdown("**Izberi hotele**")
    col_a, col_b = st.columns(2)
    izberi_vse = col_a.button("✅ Izberi vse", use_container_width=True)
    pocisti_vse = col_b.button("❌ Počisti vse", use_container_width=True)

    if izberi_vse:
        st.session_state["izbrani_hoteli"] = list(HOTELI.keys())
    if pocisti_vse:
        st.session_state["izbrani_hoteli"] = []
    if "izbrani_hoteli" not in st.session_state:
        st.session_state["izbrani_hoteli"] = list(HOTELI.keys())  # privzeto vsi

    izbrani_seznam = []
    for ime in HOTELI:
        default_checked = ime in st.session_state["izbrani_hoteli"]
        checked = st.checkbox(f"{ime}  (ID: {HOTELI[ime]})", value=default_checked, key=f"cb_{ime}")
        if checked:
            izbrani_seznam.append(ime)
    st.session_state["izbrani_hoteli"] = izbrani_seznam

    with st.expander("➕ Dodaj hotel z ročnim ID-jem"):
        rocno_ime = st.text_input("Ime hotela (poljubno)", value="")
        rocno_id = st.text_input("hotelid", value="")
        if rocno_ime and rocno_id:
            HOTELI[rocno_ime] = rocno_id
            izbrani_seznam.append(rocno_ime)

    ibelang = st.selectbox("Jezik (ibelang)", ["si", "en", "de", "it", "hr"], index=0)
    crcid = st.text_input(
        "crcid (neobvezno – kampanjska koda)",
        value="",
        help="V primeru URL-ja, ki si ga poslal, je bila prisotna vrednost "
             "'c48e0a785371c58d454ca30cee293622'. Ni nujna za delovanje linka, "
             "pusti prazno, če je ne potrebuješ.",
    )

    st.divider()
    st.header("Termin in dolžina bivanja")

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Od (prihod najzgodneje)", value=date(2026, 8, 1))
    with col2:
        end_date = st.date_input("Do (odhod najkasneje)", value=date(2026, 8, 7))

    nights_options = st.multiselect(
        "Dolžina bivanja (noči)",
        options=[1, 2, 3, 4, 5, 6, 7, 10, 14],
        default=[2, 3, 4],
    )

    zazeni = st.button("🔗 Generiraj linke", type="primary", use_container_width=True)

if end_date <= start_date:
    st.error("Datum 'Do' mora biti kasnejši od datuma 'Od'.")
    st.stop()

if not nights_options:
    st.info("Izberi vsaj eno dolžino bivanja (noči) v levem meniju.")
    st.stop()


def sestavi_link(hotelid: str, checkin: date, checkout: date) -> str:
    params = {
        "page": "availability",
        "companyid": companyid,
        "hotelid": hotelid,
        "checkin": checkin.isoformat(),
        "checkout": checkout.isoformat(),
        "ibelang": ibelang,
    }
    if crcid.strip():
        params["crcid"] = crcid.strip()
    return f"{BASE_URL}?{urlencode(params)}"


if not izbrani_seznam:
    st.info("Izberi vsaj en hotel v levem meniju (kljukica poleg imena).")
    st.stop()

if zazeni or True:  # generiraj tudi ob prvem nalaganju, da uporabnik takoj vidi primer
    vrstice = []
    for ime_hotela in izbrani_seznam:
        hid = HOTELI[ime_hotela]
        for nights in sorted(nights_options):
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

    st.subheader(f"Generirani termini ({len(df)}) za {len(izbrani_seznam)} hotel(ov)")

    for ime_hotela in izbrani_seznam:
        st.markdown(f"## 🏨 {ime_hotela}")
        podmnozica_hotel = df[df["Hotel"] == ime_hotela]
        for nights in sorted(nights_options):
            podmnozica = podmnozica_hotel[podmnozica_hotel["Noči"] == nights]
            if podmnozica.empty:
                continue
            st.markdown(f"**{nights} noči** ({len(podmnozica)} terminov)")
            for _, vrstica in podmnozica.iterrows():
                st.markdown(
                    f"- {vrstica['Prihod']} → {vrstica['Odhod']} &nbsp; "
                    f"<a href='{vrstica['Link']}' target='_blank' rel='noopener noreferrer'>"
                    f"Odpri razpoložljivost ↗</a>",
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
        file_name=f"phobs_linki_{start_date}_{end_date}.csv",
        mime="text/csv",
    )
