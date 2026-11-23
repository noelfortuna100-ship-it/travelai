"""TravelAI: delujoč demonstracijski prototip za IT podporo menedžmentu.
ZA UČNE NAMENE. Vse letalske povezave, hoteli, urniki in cene so izmišljeni.
"""
from __future__ import annotations
from datetime import date, timedelta
from html import escape
import os
import pandas as pd
import streamlit as st

from ai import detect_preferences
from engine import SearchParams, cost_breakdown, explain_offer, find_packages, load_data, preference_weights

st.set_page_config(
    page_title="TravelAI | Pametno načrtovanje počitnic",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
:root { --a: #155d86; --b: #0c2e44; --muted:#64748b; }
.block-container { max-width: 1280px; padding-top: 1.8rem; padding-bottom:3rem; }
[data-testid="stSidebar"] { background-color: #f4f8fb; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { line-height: 1.4; }
h1,h2,h3 { letter-spacing:-.025em; }
.travel-hero { border-radius:20px; padding:28px 35px; background:linear-gradient(115deg, #0c334d 0%, #146f93 65%,#39a7b2 100%); color:#fff; margin-bottom:1rem; }
.travel-hero .kicker { opacity:.85; font-weight:600; font-size:.78rem; letter-spacing:.12em; }
.travel-hero h1 { color:#fff; font-weight:800; margin:0.3rem 0 .5rem 0; font-size:2.75rem; }
.travel-hero p { color:#e2f7fc; margin:0; max-width:760px; font-size:1rem; }
.meta-chip { display:inline-block; border:1px solid #cbdfe6; border-radius:40px; padding:5px 11px; color:#22536c; background:#eef8fb; font-size:.78rem; margin:2px 6px 3px 0; }
.demo-info { background:#fff8ea; border:1px solid #e7cda6; padding:10px 15px; border-radius:12px; color:#8a521e; font-size:.87rem; margin:1rem 0; }
.card-number { font-weight:750; font-size:1.35rem; }
.muted-note { color:#6b7280; font-size:.85rem; }
.small-label { font-size:.75rem; color:#557488; letter-spacing:.04em; font-weight:650; text-transform:uppercase; }
@media (max-width:760px){.travel-hero{padding:23px 20px}.travel-hero h1{font-size:2rem}}
</style>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def get_data():
    return load_data()

tables = get_data()
airports = tables["airports"]
destinations = tables["destinations"]
label_airports = {f"{row.city} ({row.code})": str(row.code) for row in airports.itertuples()}
label_dest = {f"{row.destination}, {row.country}": str(row.code) for row in destinations.itertuples()}

st.markdown("""
<div class="travel-hero">
  <div class="kicker">PAMETNI ISKALNIK POČITNIC · ŠTUDIJSKI PROTOTIP</div>
  <h1>🌊 TravelAI</h1>
  <p>Primerjaj <strong>celotne stroške</strong> potovanja iz Trsta, Benetk in Ljubljane. Učni model umetne inteligence razume tvoje želje in razvrsti ustrezne ponudbe.</p>
</div>
""", unsafe_allow_html=True)
st.markdown('<div class="demo-info">⚠️ <strong>DEMO PODATKI:</strong> vse cene, imena hotelov in letalske povezave so izmišljene. Aplikacija ne preverja razpoložljivosti in ne omogoča rezervacij.</div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ✈️ Nastavitve iskanja")
    st.caption("Izberi kriterije in klikni **Poišči potovanja**.")
    with st.form("travel_search_form"):
        selected_airport_labels = st.multiselect(
            "Odhodna letališča",
            options=list(label_airports),
            default=list(label_airports),
        )
        d = st.date_input("Okvirni datum odhoda", value=date(2027, 7, 1), min_value=date(2026, 11, 23), max_value=date(2029, 12, 31))
        flexibility = st.slider("Fleksibilnost (± dni)", min_value=0, max_value=3, value=0)
        left, right = st.columns(2)
        with left:
            travellers = st.number_input("Osebe", min_value=1, max_value=4, value=2, step=1)
        with right:
            nights = st.selectbox("Nočitve", options=[3, 5, 7, 10, 14], index=2)
        budget = st.number_input("Skupni proračun (€)", min_value=100, max_value=25000, value=1200, step=50)
        stars = st.selectbox("Najmanj zvezdic", options=[3, 4, 5], index=1, format_func=lambda x: "★"*x)
        selected_dest_labels = st.multiselect("Destinacije (prazno = vse)", options=list(label_dest), default=[])
        with st.expander("Dodatni pogoji", expanded=False):
            max_beach = st.selectbox("Največja oddaljenost od plaže", [None, 250, 500, 1000, 2000], format_func=lambda x: "Brez omejitve" if x is None else f"{x} m")
            breakfast = st.checkbox("Zajtrk vključen")
            free_cancel = st.checkbox("Brezplačna odpoved")
            direct_only = st.checkbox("Samo direktni leti")
        wish = st.text_area("Opiši želje umetni inteligenci", value="Želim na morje, hotel blizu plaže in čim nižjo skupno ceno.", height=95)
        submitted = st.form_submit_button("🔎 Poišči potovanja", use_container_width=True, type="primary")

if submitted or "search_values" not in st.session_state:
    st.session_state["search_values"] = {
        "airports": tuple(label_airports[label] for label in selected_airport_labels),
        "departure": d,
        "nights": int(nights),
        "travellers": int(travellers),
        "budget": float(budget),
        "min_stars": int(stars),
        "flexibility_days": int(flexibility),
        "max_beach_m": max_beach,
        "breakfast_only": breakfast,
        "free_cancellation_only": free_cancel,
        "direct_only": direct_only,
        "destinations": tuple(label_dest[label] for label in selected_dest_labels),
    }
    st.session_state["wish"] = wish
    # Resetiramo nastavitve vrstnega reda samo pri novem iskanju.

try:
    params = SearchParams(**st.session_state["search_values"])
    prefs = detect_preferences(st.session_state.get("wish", ""))
    results = find_packages(tables, params, prefs.keys())
except ValueError as err:
    st.error(str(err))
    st.stop()

valid = results[results["within_budget"]].copy() if "within_budget" in results.columns else pd.DataFrame()
invalid = results[~results["within_budget"]].copy() if "within_budget" in results.columns else pd.DataFrame()

st.markdown("### Rezultati iskanja")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Kombinacije v proračunu", str(len(valid)))
c2.metric("Najnižja skupna cena", (f"{valid['total_cost'].min():,.0f} €" if len(valid) else "—"))
c3.metric("Hotel", f"{params.min_stars}★ ali več")
c4.metric("Potniki / nočitve", f"{params.travellers} / {params.nights}")

st.caption(f"Preverjeni testni odhodi: {params.departure.strftime('%d. %m. %Y')} ± {params.flexibility_days} dni · proračun {params.budget:,.0f} € za vse potnike skupaj.")

main_tab, table_tab, map_tab, ai_tab, about_tab = st.tabs(["🏖️ Ponudbe", "📊 Primerjava", "🗺️ Zemljevid", "🧠 Vloga umetne inteligence", "ℹ️ O projektu"])

with main_tab:
    if valid.empty:
        st.warning("Po izbranih pogojih v testni zbirki ni kombinacije znotraj proračuna.")
        if not invalid.empty:
            nearest = invalid.sort_values("total_cost").iloc[0]
            st.info(f"Najbližja ponudba je {nearest['destination']} za {nearest['total_cost']:.0f} €. Proračun bi morali povečati za {(-nearest['budget_difference']):.0f} € ali sprostiti pogoje.")
        st.caption("Poskusi datum ±3 dni, manj zvezdic ali višji proračun.")
    else:
        st.markdown("**Kako razvrstim rezultate?**")
        sorting = st.radio("Vrstni red", ["AI ustreznost", "Najnižja cena", "Najbližje plaži", "Najboljša ocena hotela"], horizontal=True, label_visibility="collapsed")
        if sorting == "Najnižja cena": valid = valid.sort_values("total_cost")
        elif sorting == "Najbližje plaži": valid = valid.sort_values("beach_distance_m")
        elif sorting == "Najboljša ocena hotela": valid = valid.sort_values("rating", ascending=False)
        else: valid = valid.sort_values("score", ascending=False)
        for i, (_, row) in enumerate(valid.head(10).iterrows(), 1):
            with st.container(border=True):
                a, b = st.columns([3.2, 1.15])
                with a:
                    st.markdown(f"#### {i}. {escape(str(row['destination']))}, {escape(str(row['country']))}")
                    st.caption(f"✈️ {row['origin_city']} ({row['origin']}) → {row['destination_code']}  ·  {row['departure_date'].strftime('%d. %m. %Y')}–{row['return_date'].strftime('%d. %m. %Y')}  ·  {'Direktni let' if int(row['direct']) else 'S prestopanjem'}")
                    st.markdown(f"**🏨 {escape(str(row['hotel_name']))}** · {int(row['stars'])}★ · ocena {float(row['rating']):.1f}/10")
                    st.caption(f"🏖️ Plaža {int(row['beach_distance_m'])} m · {'Zajtrk vključen' if int(row['breakfast']) else 'Brez zajtrka'} · {'Brezplačna odpoved' if int(row['free_cancellation']) else 'Odpoved po pogojih hotela'}")
                with b:
                    st.metric("Skupaj za vse", f"{row['total_cost']:,.0f} €", f"{row['budget_difference']:,.0f} € pod mejo", delta_color="normal")
                    st.caption(f"Ujemanje kriterijev: {row['score']:.1f}/100")
                    st.progress(int(row['score']))
                st.write(explain_offer(row, params))
                with st.expander("Poglej vseh 5 stroškov in opis hotela"):
                    details = cost_breakdown(row)
                    st.dataframe(details, hide_index=True, use_container_width=True)
                    st.markdown(f"**Skupaj:** {row['total_cost']:.2f} €")
                    st.caption(str(row['description']))
        if len(valid) > 10:
            st.caption(f"Prikazanih je prvih 10 od {len(valid)} ponudb znotraj proračuna. Vse so v zavihku Primerjava.")

    if not invalid.empty:
        with st.expander(f"Alternativne ponudbe nad proračunom ({len(invalid)})"):
            for _, row in invalid.sort_values("total_cost").head(5).iterrows():
                st.write(f"• **{row['destination']} · {row['hotel_name']}** — {row['total_cost']:.0f} € (prekoračitev {-row['budget_difference']:.0f} €)")

with table_tab:
    if results.empty:
        st.info("Za te pogoje v zbirki ni kombinacij. Spremeni filter datumov ali število nočitev.")
    else:
        cols = ["destination", "origin_city", "departure_date", "hotel_name", "stars", "rating", "beach_distance_m", "flight_cost", "hotel_cost", "baggage_cost", "access_cost", "local_cost", "total_cost", "score", "within_budget"]
        readable = results[cols].rename(columns={
            "destination": "Destinacija", "origin_city": "Odhod", "departure_date": "Datum odhoda", "hotel_name": "Hotel",
            "stars": "Zvezdice", "rating": "Ocena", "beach_distance_m": "Do plaže (m)", "flight_cost": "Let (€)", "hotel_cost": "Hotel (€)",
            "baggage_cost": "Prtljaga (€)", "access_cost": "Do letališča (€)", "local_cost": "Lokalni transfer (€)",
            "total_cost": "Skupaj (€)", "score": "AI ocena", "within_budget": "V proračunu",
        })
        st.dataframe(readable, hide_index=True, use_container_width=True)
        st.download_button("⬇️ Prenesi primerjavo v CSV", data=readable.to_csv(index=False).encode("utf-8-sig"), file_name="travelai_ponudbe_demo.csv", mime="text/csv", use_container_width=False)
        st.markdown("#### Najugodnejše kombinacije")
        chart = results.sort_values("total_cost").head(10).copy()
        chart["Ponudba"] = chart["destination"] + " / " + chart["origin"] + " / " + chart["hotel_id"]
        st.bar_chart(chart.set_index("Ponudba")["total_cost"], horizontal=True, x_label="Skupna cena (€)")

with map_tab:
    st.write("Lokacije hotelov znotraj proračuna – testne koordinate v realnih obmorskih krajih, hoteli so izmišljeni.")
    if valid.empty:
        st.info("Noben rezultat znotraj proračuna za prikaz.")
    else:
        points = valid[["lat", "lon", "hotel_name", "destination", "total_cost"]].drop_duplicates("hotel_name")
        st.map(points, latitude="lat", longitude="lon", size=110)
        st.dataframe(points.rename(columns={"hotel_name":"Hotel", "destination":"Destinacija", "total_cost":"Skupna cena (€)", "lat":"Širina", "lon":"Dolžina"}), hide_index=True)

with ai_tab:
    st.markdown("#### Kaj tu res počne umetna inteligenca?")
    st.markdown("Aplikacija uporablja **učni model strojnega učenja**: iz slovenskih primerov stavkov se nauči prepoznavati želje, zapisane v naravnem jeziku. Za klasifikacijo uporablja TF-IDF znakovne značilnice in logistično regresijo. Ključne besede dopolnjujejo model. Nato programski algoritem s preverljivimi pravili izračuna cene in razvrsti ponudbe.")
    st.markdown("**Tvoj opis želja:**")
    st.info(st.session_state.get("wish") or "(Ni podanih dodatnih želja)")
    if prefs:
        st.markdown("**Prepoznane želje (učne ocene zaupanja):**")
        for label, confidence in sorted(prefs.items(), key=lambda x: -x[1]):
            st.markdown(f"<span class='meta-chip'>{escape(label.replace('_',' '))} · {confidence:.0%}</span>", unsafe_allow_html=True)
    else:
        st.caption("Model ni z zadostno gotovostjo zaznal nobene posebne želje; uporabljen je osnovni model ocenjevanja.")
    st.markdown("**Uteži pri razvrščanju:**")
    names = {"price":"Cena", "rating":"Ocena hotela", "beach":"Bližina plaže", "flight":"Direktnost leta", "cancellation":"Odpoved"}
    pw = preference_weights(prefs.keys())
    for key, val in pw.items():
        st.write(f"{names[key]}: **{val:.0%}**")
        st.progress(val)
    st.markdown("**Zakaj to ni samo navaden filter?** Model klasificira prosto besedilo in spreminja pomembnost kriterijev. Cena in primernost datumov sta še vedno matematično izračunani, kar preprečuje napačno seštevanje s strani AI.")
    st.warning("Omejitev: majhen model, treniran na učnih primerih, lahko napačno razume želje in ne preverja resničnih ponudb. Rezultat je pomoč pri odločitvi, ne zagotovilo.")
    if os.getenv("OPENAI_API_KEY") and not valid.empty:
        st.markdown("#### Dodatna obrazložitev z LLM (opcijsko)")
        if st.button("✨ Ustvari dodatno obrazložitev prve ponudbe"):
            best = valid.sort_values("score", ascending=False).iloc[0]
            try:
                from openai import OpenAI
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                factual = {
                    "destinacija": str(best["destination"]),
                    "odhod": str(best["origin_city"]),
                    "datum": str(best["departure_date"]),
                    "hotel": str(best["hotel_name"]),
                    "hotel_zvezdice": int(best["stars"]),
                    "oddaljenost_plaza_m": int(best["beach_distance_m"]),
                    "skupna_cena_eur": float(best["total_cost"]),
                    "proracun_eur": params.budget,
                    "direkten_let": bool(best["direct"]),
                }
                answer = client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    temperature=0.2,
                    messages=[
                        {"role":"system", "content":"Si slovenski asistent za primerjavo IZMIŠLJENIH DEMONSTRACIJSKIH počitniških ponudb. Pojasni prednosti in omejitve največ 120 besed. NE izmišljaj podatkov in ne trdi, da so cene ali leti realni."},
                        {"role":"user", "content":f"Uporabnik: {st.session_state.get('wish','')}\nDovoljena dejstva: {factual}"},
                    ],
                )
                st.success(answer.choices[0].message.content)
            except Exception:
                st.error("Zunanje generiranje trenutno ni uspelo. Preveri ključ, dostop in model; osnovna aplikacija deluje brez LLM.")
    else:
        st.caption("Če želiš dodati generativni AI, nastavi okoljsko spremenljivko OPENAI_API_KEY. Brez nje osnovni model strojnega učenja deluje lokalno.")

with about_tab:
    st.markdown("#### O prototipu za predmet IT podpora menedžmentu")
    st.write("**Problem:** iskanje letov, hotelov in dodatnih stroškov na več portalih zahteva veliko časa; uporabnik pogosto vidi samo delno ceno.")
    st.write("**Rešitev:** prototip iz testnih podatkov združi povratne lete, nastanitve in stroške, preveri obvezne pogoje ter prikaže večkriterijsko oceno.")
    st.write("**Podatkovni model:** flights.csv, hotels.csv, airports.csv, destinations.csv; avtomatsko sestavljene kombinacije predstavljajo tabelo TravelPackages.")
    st.write("**Tehnologija:** Python, Streamlit, pandas, scikit-learn; po želji zunanji jezikovni model.")
    st.write("**Prednosti:** preglednost skupnih cen, hitra primerjava, prosti opis želja, izvoz v CSV.")
    st.write("**Slabosti:** testni namesto živih cen; majhna učna zbirka za NLP; ni preverjanja razpoložljivosti, realnih voznih redov ali rezervacij; cene transferjev so ocene v testnih podatkih.")
    st.write("**Nadgradnje:** dovoljeni API-ji letov in hotelov, dejanske rezervacije, personalizacija, sledenje cenam, primerjava datumske fleksibilnosti.")
    st.caption("Različica 1.0 · november 2026 · demonstracijski projekt")
