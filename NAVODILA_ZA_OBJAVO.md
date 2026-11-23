# TravelAI – objava naprednejše Python aplikacije

Ta paket vsebuje celoten delujoč Streamlit prototip z modelom strojnega učenja.

## 1. GitHub
1. Odpri https://github.com/new
2. Repository name: `travelai`
3. Izberi `Public`, po želji označi `Add a README file`, klikni `Create repository`.
4. Naloži vse datoteke iz te mape, tako da bosta `app.py` in `requirements.txt` v KORENU repozitorija ter mapa `data/` pod njima.
   Lahko tudi samo ustvariš repozitorij in ChatGPT-ju sporočiš, da je pripravljen, da bo poskusil naložiti datoteke prek povezanega GitHuba.

## 2. Streamlit Community Cloud
1. Odpri https://share.streamlit.io/
2. Prijavi se z GitHubom.
3. Izberi `Create app` / `Deploy an app`.
4. Repozitorij: `noelfortuna100-ship-it/travelai`
5. Branch: `main`
6. Main file path: `app.py`
7. Klikni `Deploy`.

Streamlit bo iz requirements.txt namestil odvisnosti in objavil aplikacijo na novem naslovu *.streamlit.app.

## 3. Kaj je res in kaj ne
- Leti, hoteli, termini in cene v prototipu so IZMIŠLJENI.
- Aplikacija ne izvaja dejanskih rezervacij.
- `ai.py` vsebuje učni model TF-IDF + logistična regresija za prepoznavanje slovenskih želja, ne LLM.
- Po želji je mogoče dodati generativni LLM preko varno shranjenega API ključa. Ključa ne objavljaj v GitHubu.
- Datoteka `app.py` je prava spletna aplikacija. Statični HTML z Netlify ni ista implementacija.

## 4. Lokalni zagon
    pip install -r requirements.txt
    streamlit run app.py

## 5. Testni primer
- Odhodna letališča: Trst, Benetke, Ljubljana
- Datum: 1. 7. 2027
- Osebi: 2
- Nočitve: 7
- Proračun: 1200 €
- Hotel: najmanj 4★
- Proste želje: "Želim hotel blizu plaže in čim nižjo skupno ceno"

Repozitorij ob objavi nastavi kot javen, če želiš javno demonstracijo.
