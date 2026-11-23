"""Učni model strojnega učenja: zaznava želja v slovenskem prostem besedilu.
Model temelji na označenih primerih, ne na jezikovnem modelu LLM.
Ocen modela ne uporabljamo kot dokaz o resnični ponudbi.
"""
from __future__ import annotations
from functools import lru_cache
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.pipeline import Pipeline

_EXAMPLES = [
    ("Iščem najnižjo ceno", ["cena"]),
    ("Naj bo čim ceneje", ["cena"]),
    ("Najbolj ugodne počitnice", ["cena"]),
    ("Ne želim porabiti veliko denarja", ["cena"]),
    ("Poceni hotel in let", ["cena"]),
    ("Zelo omejen proračun", ["cena"]),
    ("Pomembna mi je skupna cena", ["cena"]),
    ("Želim prihraniti", ["cena"]),
    ("Hotel tik ob plaži", ["plaža"]),
    ("Želim čim bližje morju", ["plaža"]),
    ("Naj bo kratek sprehod do plaže", ["plaža"]),
    ("Plaža naj bo blizu hotela", ["plaža"]),
    ("Rad bi pogled na morje", ["plaža"]),
    ("Obmorski hotel", ["plaža"]),
    ("Želim kopanje in plažo", ["plaža"]),
    ("Hotel naj bo ob obali", ["plaža"]),
    ("Rad imam vključen zajtrk", ["zajtrk"]),
    ("Hočem hotel z zajtrkom", ["zajtrk"]),
    ("Zjutraj bi jedel v hotelu", ["zajtrk"]),
    ("Zajtrk mora biti v ceni", ["zajtrk"]),
    ("Vključena naj bo jutranja prehrana", ["zajtrk"]),
    ("Pomembno mi je, da je zajtrk vključen", ["zajtrk"]),
    ("Zajtrk in kava v hotelu", ["zajtrk"]),
    ("Ne želim prestopanj na letalu", ["direktni_let"]),
    ("Obvezen direkten let", ["direktni_let"]),
    ("Let brez prestopanja", ["direktni_let"]),
    ("Želim neposredno povezavo", ["direktni_let"]),
    ("Naj bo čim manj prestopov", ["direktni_let"]),
    ("Raje imam direkten polet", ["direktni_let"]),
    ("Neposredni leti so mi pomembni", ["direktni_let"]),
    ("Želim miren hotel", ["mir"]),
    ("Naj bo tiho in mirno", ["mir"]),
    ("Brez zabav in nočnega življenja", ["mir"]),
    ("Želim sprostitev in mir", ["mir"]),
    ("Mirna lokacija stran od hrupa", ["mir"]),
    ("Naj bo mirna okolica", ["mir"]),
    ("Brezplačna odpoved rezervacije", ["odpoved"]),
    ("Pomembna je možnost odpovedi", ["odpoved"]),
    ("Želim fleksibilno odpoved", ["odpoved"]),
    ("Vračilo denarja ob odpovedi", ["odpoved"]),
    ("Rezervacija brez stroškov odpovedi", ["odpoved"]),
    ("Hotel z visoko oceno gostov", ["kakovost"]),
    ("Želim kakovosten hotel", ["kakovost"]),
    ("Naj bo vrhunska nastanitev", ["kakovost"]),
    ("Pomembne so odlične ocene", ["kakovost"]),
    ("Izberite najbolje ocenjeni hotel", ["kakovost"]),
    ("Želim mirno plažo in nizko ceno", ["plaža", "mir", "cena"]),
    ("Poceni hotel ob plaži z zajtrkom", ["cena", "plaža", "zajtrk"]),
    ("Direkten let in brezplačna odpoved", ["direktni_let", "odpoved"]),
    ("Zelo dober hotel ob morju", ["kakovost", "plaža"]),
]
# Uporabljamo samo enote iz zgornje učne zbirke; narekovaji so zgolj del besedila.
_LABELS = ["cena", "plaža", "zajtrk", "direktni_let", "mir", "odpoved", "kakovost"]

@lru_cache(maxsize=1)
def _trained():
    x = [txt.lower() for txt, _ in _EXAMPLES]
    y = [labels for _, labels in _EXAMPLES]
    mlb = MultiLabelBinarizer(classes=_LABELS)
    matrix = mlb.fit_transform(y)
    model = Pipeline([
        ("features", TfidfVectorizer(analyzer="char", ngram_range=(2, 5), min_df=1, sublinear_tf=True)),
        ("model", OneVsRestClassifier(LogisticRegression(max_iter=1200, class_weight="balanced", C=3.0))),
    ])
    model.fit(x, matrix)
    return model, mlb


def detect_preferences(text: str) -> dict[str, float]:
    """Vrne razred -> zaupanje. Združitev ML in jasnih ključnih besed."""
    clean = (text or "").lower().strip()
    if not clean:
        return {}
    model, mlb = _trained()
    scores = model.predict_proba([clean])[0]
    probabilities = {str(l): round(float(v), 2) for l, v in zip(mlb.classes_, scores)}
    patterns = {
        "cena": r"cen[aeoi]|pocen|ugodn|proračun|prihran|nizk.*(cen|stroš)",
        "plaža": r"plaž|ob morj|blizu morj|obal|kopanj",
        "zajtrk": r"zajtrk|zajtrkom|jutranj.*prehran",
        "direktni_let": r"direkt|neposred|brez prestop|manj prestop",
        "mir": r"mirn|tiho|sprostit|brez hrupa",
        "odpoved": r"odpoved|vračilo denarja|fleksibilno",
        "kakovost": r"kakovost|najboljš|odličn.*ocen|visoko ocen|vrhunsk",
    }
    found = {}
    for label, prob in probabilities.items():
        if re.search(patterns[label], clean):
            found[label] = max(prob, 0.92)
        elif prob >= 0.46:
            found[label] = prob
    return found
