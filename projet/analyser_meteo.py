import datetime
import random

import requests
from meteo import recuperer_previsions_api , evaluer_jour , formater_bulletin
def analyser_meteo(date_str, lieu):
    """
    Analyse la météo pour une date et un lieu.
    Retourne (go, bulletin, nouvelle_date_str, bulletin_nouvelle_date).
    - Si GO : nouvelle_date_str = None.
    - Si NO GO : cherche automatiquement le prochain jour GO.
    Lève ValueError si la date est invalide ou passée.
    """
    try:
        date_obj = datetime.datetime.strptime(date_str, "%d/%m/%Y").date()
    except ValueError:
        raise ValueError("Le format de la date doit être JJ/MM/AAAA (ex : 15/08/2026).")

    if date_obj < datetime.date.today():
        raise ValueError("La date de lancement ne peut pas être antérieure à aujourd'hui.")

    try:
        previsions = recuperer_previsions_api(lieu)
    except Exception:
        previsions = None  # pas de réseau : on bascule sur l'estimation simulée

    meteo = evaluer_jour(date_obj, lieu, previsions)
    bulletin = formater_bulletin(lieu, date_obj, meteo)

    if meteo["go"]:
        return True, bulletin + "✅ STATUT : GO (Autorisation accordée)", None, None

    bulletin += "❌ STATUT : NO GO (Lancement annulé)"

    # Recherche de la prochaine fenêtre de tir favorable
    jour = date_obj + datetime.timedelta(days=1)
    for _ in range(366):
        m = evaluer_jour(jour, lieu, previsions)
        if m["go"]:
            return False, bulletin, jour.strftime("%d/%m/%Y"), formater_bulletin(lieu, jour, m)
        jour += datetime.timedelta(days=1)

    return False, bulletin, None, None