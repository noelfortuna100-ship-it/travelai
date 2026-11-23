"""Poslovna logika TravelAI: deterministične cene, filtri in večkriterijska ocena.
Vsi podatki v priloženih CSV so izmišljeni. Ta modul ne izvaja rezervacij.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from math import ceil
from typing import Iterable
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data"

@dataclass(frozen=True)
class SearchParams:
    airports: tuple[str, ...] = ("TRS", "VCE", "LJU")
    departure: date = date(2027, 7, 1)
    nights: int = 7
    travellers: int = 2
    budget: float = 1200.0
    min_stars: int = 4
    flexibility_days: int = 0
    max_beach_m: int | None = None
    breakfast_only: bool = False
    free_cancellation_only: bool = False
    direct_only: bool = False
    destinations: tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.airports:
            raise ValueError("Izberi vsaj eno odhodno letališče.")
        if not (1 <= self.travellers <= 4):
            raise ValueError("Prototip podpira od 1 do 4 potnike.")
        if not (1 <= self.nights <= 28):
            raise ValueError("Število nočitev mora biti med 1 in 28.")
        if self.budget <= 0:
            raise ValueError("Proračun mora biti pozitiven.")
        if self.min_stars not in {3, 4, 5}:
            raise ValueError("Kategorija hotela mora biti 3, 4 ali 5 zvezdic.")
        if self.flexibility_days not in {0, 1, 2, 3}:
            raise ValueError("Dovoljena prilagodljivost je največ 3 dni.")


def load_data(path: Path = DATA_DIR) -> dict[str, pd.DataFrame]:
    tables = {}
    for table in ("airports", "destinations", "flights", "hotels"):
        tables[table] = pd.read_csv(path / f"{table}.csv")
    return tables


def preference_weights(detected: Iterable[str] = ()) -> dict[str, float]:
    """Prilagodi uteži iz prepoznanih tekstovnih želja; normalizacija na 1."""
    weights = {"price": 0.45, "rating": 0.20, "beach": 0.15, "flight": 0.10, "cancellation": 0.10}
    prefs = set(detected)
    if "cena" in prefs: weights["price"] += 0.18
    if "plaža" in prefs: weights["beach"] += 0.21
    if "direktni_let" in prefs: weights["flight"] += 0.18
    if "odpoved" in prefs: weights["cancellation"] += 0.18
    if "kakovost" in prefs: weights["rating"] += 0.17
    total = sum(weights.values())
    return {k: v / total for k, v in weights.items()}


def _score(row: pd.Series, budget: float, weights: dict[str, float], detected: Iterable[str]) -> float:
    price = min(1.0, max(0, 1 - float(row["total_cost"]) / (budget * 1.45)))
    rating = min(1.0, max(0, float(row["rating"]) / 10))
    beach = min(1.0, max(0, 1 - float(row["beach_distance_m"]) / 2500))
    flight = 1.0 if int(row["direct"]) else 0.35
    cancellation = 1.0 if int(row["free_cancellation"]) else 0.2
    qualities = dict(price=price, rating=rating, beach=beach, flight=flight, cancellation=cancellation)
    score = 100 * sum(weights[k] * qualities[k] for k in weights)
    if "zajtrk" in detected and not int(row["breakfast"]):
        score -= 9
    if "mir" in detected and "mirna" not in str(row["description"]):
        score -= 7
    if float(row["total_cost"]) > budget:
        score -= 12
    return round(max(0.0, min(100.0, score)), 1)


def find_packages(tables: dict[str, pd.DataFrame], params: SearchParams, detected: Iterable[str] = ()) -> pd.DataFrame:
    params.validate()
    flights = tables["flights"].copy()
    hotels = tables["hotels"].copy()
    flights["departure_date"] = pd.to_datetime(flights["departure_date"]).dt.date
    flights["return_date"] = pd.to_datetime(flights["return_date"]).dt.date
    flights = flights[flights["origin"].isin(params.airports)]
    flights = flights[flights["departure_date"].map(lambda d: abs((d-params.departure).days) <= params.flexibility_days)]
    flights = flights[flights.apply(lambda r: (r["return_date"]-r["departure_date"]).days == params.nights, axis=1)]
    if params.destinations:
        flights = flights[flights["destination_code"].isin(params.destinations)]
    if params.direct_only:
        flights = flights[flights["direct"] == 1]
    hotels = hotels[hotels["stars"] >= params.min_stars]
    if params.max_beach_m is not None:
        hotels = hotels[hotels["beach_distance_m"] <= params.max_beach_m]
    if params.breakfast_only:
        hotels = hotels[hotels["breakfast"] == 1]
    if params.free_cancellation_only:
        hotels = hotels[hotels["free_cancellation"] == 1]
    joined = flights.merge(hotels, on="destination_code", how="inner")
    if joined.empty:
        return joined
    airports = tables["airports"][ ["code", "city", "ground_access_cost"] ].rename(columns={"code":"origin", "city":"origin_city"})
    joined = joined.merge(airports, on="origin", how="left", validate="many_to_one")
    dests = tables["destinations"][ ["code", "destination", "country"] ].rename(columns={"code":"destination_code"})
    joined = joined.merge(dests, on="destination_code", how="left", validate="many_to_one")
    rooms = ceil(params.travellers / 2)
    joined["flight_cost"] = joined["fare_return_per_person"] * params.travellers
    joined["baggage_cost"] = joined["baggage_per_person"] * params.travellers
    joined["hotel_cost"] = (joined["nightly_rate_per_room"] * params.nights + joined["stay_fees_per_room"]) * rooms
    joined["local_cost"] = joined["local_transfer_cost"]
    joined["access_cost"] = joined["ground_access_cost"]
    joined["total_cost"] = joined[["flight_cost", "baggage_cost", "hotel_cost", "local_cost", "access_cost"]].sum(axis=1).round(2)
    joined["budget_difference"] = (params.budget - joined["total_cost"]).round(2)
    joined["within_budget"] = joined["total_cost"] <= params.budget
    weights = preference_weights(detected)
    joined["score"] = joined.apply(lambda row: _score(row, params.budget, weights, detected), axis=1)
    joined = joined.sort_values(by=["within_budget", "score", "total_cost"], ascending=[False, False, True]).reset_index(drop=True)
    return joined


def explain_offer(row: pd.Series, params: SearchParams) -> str:
    """Deterministična obrazložitev brez izmišljanja dejstev."""
    if row["within_budget"]:
        budget_text = f"je {int(row['budget_difference'])} € pod proračunom"
    else:
        budget_text = f"presega proračun za {int(-row['budget_difference'])} €"
    direct = "direkten let" if int(row["direct"]) else "let s prestopanjem"
    breakfast = "zajtrk je vključen" if int(row["breakfast"]) else "zajtrk ni vključen"
    return (
        f"Kombinacija {row['destination']} iz letališča {row['origin_city']} {budget_text}. "
        f"Hotel ima {int(row['stars'])} zvezdic in oceno {float(row['rating']):.1f}/10, "
        f"od plaže je oddaljen {int(row['beach_distance_m'])} m. "
        f"Predviden je {direct}; {breakfast}. "
        "Cene in urniki so izmišljeni demonstracijski podatki."
    )


def cost_breakdown(row: pd.Series) -> pd.DataFrame:
    return pd.DataFrame([
        {"Postavka": "Povratni leti", "EUR": row["flight_cost"]},
        {"Postavka": "Hotel", "EUR": row["hotel_cost"]},
        {"Postavka": "Prtljaga", "EUR": row["baggage_cost"]},
        {"Postavka": "Pot do odhodnega letališča", "EUR": row["access_cost"]},
        {"Postavka": "Transfer na destinaciji", "EUR": row["local_cost"]},
    ])
