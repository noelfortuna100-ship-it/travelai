"""Ustvari ponovljivo izmišljeno zbirko za projekt TravelAI.
OPOZORILO: vse ponudbe, hoteli, urniki in cene so TESTNI, ne dejanski.
"""
from __future__ import annotations
import csv
from datetime import date, timedelta
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parent / "data"
ROOT.mkdir(exist_ok=True)
rng = random.Random(202711)

AIRPORTS = [
    ("TRS", "Trst", 50),
    ("VCE", "Benetke", 80),
    ("LJU", "Ljubljana", 60),
]
DESTINATIONS = [
    ("MLA", "Malta", "Malta", 35.8992, 14.5141, 45),
    ("CFU", "Krf", "Grčija", 39.6243, 19.9217, 55),
    ("HER", "Kreta", "Grčija", 35.3387, 25.1442, 60),
    ("PMO", "Sicilija (Palermo)", "Italija", 38.1157, 13.3615, 35),
    ("CAG", "Sardinija (Cagliari)", "Italija", 39.2238, 9.1217, 48),
    ("ALC", "Alicante", "Španija", 38.3452, -0.4810, 38),
    ("DBV", "Dubrovnik", "Hrvaška", 42.6507, 18.0944, 40),
    ("ZAD", "Zadar", "Hrvaška", 44.1194, 15.2314, 25),
    ("SPU", "Split", "Hrvaška", 43.5081, 16.4402, 30),
    ("BRI", "Bari", "Italija", 41.1171, 16.8719, 34),
    ("RHO", "Rodos", "Grčija", 36.4341, 28.2176, 62),
    ("PMI", "Majorka", "Španija", 39.5696, 2.6502, 50),
]

with (ROOT / "airports.csv").open("w", newline="", encoding="utf-8") as f:
    out = csv.writer(f); out.writerow(["code", "city", "ground_access_cost"])
    out.writerows(AIRPORTS)
with (ROOT / "destinations.csv").open("w", newline="", encoding="utf-8") as f:
    out = csv.writer(f); out.writerow(["code", "destination", "country", "lat", "lon", "default_transfer_cost"])
    out.writerows(DESTINATIONS)

flights = []
base_date = date(2027, 7, 1)
for di, (code, name, _, _, _, transfer) in enumerate(DESTINATIONS):
    for ai, (origin, _, _) in enumerate(AIRPORTS):
        shift = ((di * 2 + ai * 3) % 7) - 3
        if (code, origin) in (("MLA", "TRS"), ("CFU", "VCE"), ("HER", "LJU")):
            shift = 0
        if di in (3, 6, 8) and origin == "VCE":
            shift = 0
        depart = base_date + timedelta(days=shift)
        fare = 125 + 17 * di + 12 * ai + rng.randint(-22, 18)
        baggage = 38 + (di % 4) * 3
        direct = ((di + ai) % 3 != 1)
        duration = round(1.2 + (di % 5) * 0.35 + (0 if direct else 2.1), 1)
        if code == "MLA" and origin == "TRS":
            fare, baggage, direct = 130, 37.5, True
        if code == "CFU" and origin == "VCE":
            fare, baggage, direct = 170, 35, True
        if code == "HER" and origin == "LJU":
            fare, baggage, direct = 195, 40, False
        flights.append([
            f"F{len(flights)+1:03d}", origin, code, str(depart),
            str(depart + timedelta(days=7)), fare, baggage, int(direct), duration,
            f"Demo prevoznik {1 + (di+ai)%3}", transfer,
        ])
# Dodamo še druge trajanja, da izbirnik 3 / 5 / 7 / 10 / 14 nočitev res deluje.
original_week_flights = list(flights)
for nights in (3, 5, 10, 14):
    for base in original_week_flights:
        row = list(base)
        row[0] = f"F{len(flights)+1:03d}"
        row[4] = str(date.fromisoformat(row[3]) + timedelta(days=nights))
        # Splošen testni cenik: večje trajanje dopusta nekoliko spremeni letalsko tarifo.
        row[5] = round(float(row[5]) + (nights - 7) * 1.5, 2)
        flights.append(row)

with (ROOT / "flights.csv").open("w", newline="", encoding="utf-8") as f:
    out = csv.writer(f)
    out.writerow(["flight_id", "origin", "destination_code", "departure_date", "return_date", "fare_return_per_person", "baggage_per_person", "direct", "duration_hours", "airline", "local_transfer_cost"])
    out.writerows(flights)

hotels = []
adjectives = ["Mirni", "Modri", "Sončni", "Obalni", "Jadranski", "Zeleni", "Morski"]
for di, (code, destination, _, lat, lon, _) in enumerate(DESTINATIONS):
    for hi in range(3):
        stars = [3, 4, 5][hi]
        beach_m = [850, 250 + (di%4)*120, 100 + (di%3)*40][hi]
        rating = round([7.7, 8.6, 9.1][hi] + (di%3)*0.1, 1)
        nightly = [58, 83+di*2, 135+di*3][hi]
        fees = [15, 20, 35][hi]
        breakfast = (hi != 0)
        cancellation = (hi != 0 and di%2 == 0)
        if code == "MLA" and hi == 1:
            nightly, fees, beach_m = 90, 20, 1100
        if code == "CFU" and hi == 1:
            nightly, fees, beach_m = 84, 12, 250
        if code == "HER" and hi == 1:
            nightly, fees = 100, 0
        friendly = "mirna lokacija" if di%2 == 0 else "živahno letovišče"
        desc = (f"{stars}-zvezdični hotel ob morju v kraju {destination}. "
                f"Do plaže je približno {beach_m} metrov, {friendly}. "
                f"{'Zajtrk je vključen.' if breakfast else 'Zajtrk ni vključen.'} "
                f"{'Možnost brezplačne odpovedi.' if cancellation else 'Brezplačna odpoved ni vključena.'} "
                f"Primeren za poletni oddih, kopanje in sprostitev.")
        hotels.append([
            f"H{len(hotels)+1:03d}", code, f"{adjectives[(di+hi)%len(adjectives)]} zaliv {destination} {stars}★",
            stars, rating, beach_m, int(breakfast), int(cancellation), nightly, fees,
            desc, round(lat+(hi-1)*0.008, 5), round(lon+(hi-1)*0.008, 5), 2,
        ])
with (ROOT / "hotels.csv").open("w", newline="", encoding="utf-8") as f:
    out = csv.writer(f)
    out.writerow(["hotel_id", "destination_code", "hotel_name", "stars", "rating", "beach_distance_m", "breakfast", "free_cancellation", "nightly_rate_per_room", "stay_fees_per_room", "description", "lat", "lon", "capacity_per_room"])
    out.writerows(hotels)

print(f"Ustvarjeno: {len(flights)} testnih letov in {len(hotels)} izmišljenih hotelov")
