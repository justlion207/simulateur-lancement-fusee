"""
meteo.py
Vérification météo du lancement : prévisions réelles (Open-Meteo), estimation simulée
au-delà de la fenêtre de prévisions, décision GO / NO GO et recherche de la prochaine
date favorable. Aucune dépendance à l'interface graphique.
"""
import datetime
import random

import requests

from analyser_meteo import analyser_meteo

# ============================================================
# MÉTÉO (logique métier)
# ============================================================
COORDONNEES = {
    "Kourou (Guyane)": (5.1597, -52.6502),
    "Cap Canaveral (Floride)": (28.3922, -80.6077),
    "Baïkonour (Kazakhstan)": (45.9646, 63.3052),
    "Vandenberg (Californie)": (34.7420, -120.5724),
}
SEUIL_VENT_KMH = 50.0
DIRECTIONS_VENT = ["Nord", "Sud", "Est", "Ouest", "Nord-Est", "Nord-Ouest", "Sud-Est", "Sud-Ouest"]


def recuperer_previsions_api(lieu):
    """Retourne {date_iso: {temp, vent, precip, code}} sur ~16 jours (Open-Meteo)."""
    lat, lon = COORDONNEES.get(lieu, COORDONNEES["Kourou (Guyane)"])
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&daily=temperature_2m_max,windspeed_10m_max,precipitation_sum,weathercode"
        "&timezone=auto&forecast_days=16"
    )
    reponse = requests.get(url, timeout=10)
    reponse.raise_for_status()
    d = reponse.json()["daily"]
    previsions = {}
    for i, jour in enumerate(d["time"]):
        previsions[jour] = {
            "temp": d["temperature_2m_max"][i],
            "vent": d["windspeed_10m_max"][i] or 0,
            "precip": d["precipitation_sum"][i] or 0,
            "code": d["weathercode"][i] or 0,
        }
    return previsions


def libelle_ciel(code):
    if code <= 3:
        return "Clair à nuageux"
    if code <= 49:
        return "Brume/Brouillard"
    if code <= 69:
        return "Pluie"
    return "Orage / Fortes précipitations"


def meteo_simulee(date_obj, lieu):
    """Météo déterministe (même date + même lieu = même météo) quand l'API ne couvre pas la date."""
    rng = random.Random(f"{date_obj.isoformat()}-{lieu}")
    go = rng.choice([True, False])
    direction = rng.choice(DIRECTIONS_VENT)
    if go:
        return {
            "go": True, "temp": rng.randint(15, 32), "vent": rng.randint(0, 45), "precip": 0,
            "ciel": rng.choice(["Ensoleillé", "Ciel dégagé", "Légèrement nuageux", "Belles éclaircies"]),
            "direction": direction, "source": "Estimation simulée (hors fenêtre de prévisions)",
        }
    return {
        "go": False, "temp": rng.randint(5, 38), "vent": rng.randint(55, 110), "precip": rng.randint(5, 60),
        "ciel": rng.choice(["Fortement orageux", "Tempête", "Pluies intenses", "Couverture nuageuse épaisse"]),
        "direction": direction, "source": "Estimation simulée (hors fenêtre de prévisions)",
    }


def evaluer_jour(date_obj, lieu, previsions):
    """Évalue la météo d'un jour : API si disponible, sinon simulation."""
    iso = date_obj.strftime("%Y-%m-%d")
    if previsions and iso in previsions:
        j = previsions[iso]
        return {
            "go": j["vent"] <= SEUIL_VENT_KMH and j["code"] < 50,
            "temp": j["temp"], "vent": j["vent"], "precip": j["precip"],
            "ciel": libelle_ciel(j["code"]), "direction": None,
            "source": "Prévisions Open-Meteo",
        }
    return meteo_simulee(date_obj, lieu)


def formater_bulletin(lieu, date_obj, m):
    texte = f"Bulletin Météo : {lieu}\n"
    texte += f"Date : {date_obj.strftime('%d/%m/%Y')}\n" + "-" * 30 + "\n"
    texte += f"☁️ Ciel : {m['ciel']}\n"
    texte += f"🌡️ Température : {m['temp']} °C\n"
    texte += f"💨 Vent : {m['vent']} km/h (max autorisé : {SEUIL_VENT_KMH:.0f} km/h)\n"
    if m["direction"]:
        texte += f"🧭 Direction du vent : {m['direction']}\n"
    texte += f"🌧️ Pluie : {m['precip']} mm\n"
    texte += f"ℹ️ Source : {m['source']}\n\n"
    return texte


