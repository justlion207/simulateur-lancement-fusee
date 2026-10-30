"""
verification.py
Lecture, vérification et conversion des paramètres de la fusée saisis dans l'interface.
Aucune dépendance à l'interface graphique.
"""
import math


def convertir_nombre(texte, nom):
    """Convertit un texte saisi en nombre fini (virgule ou point acceptés)."""
    try:
        valeur = float(str(texte).strip().replace(",", "."))
    except ValueError:
        raise ValueError(f"Le paramètre « {nom} » doit être un nombre.")
    if not math.isfinite(valeur):
        raise ValueError(f"Le paramètre « {nom} » doit être un nombre fini.")
    return valeur


def verifier_et_convertir(valeurs):
    """
    Vérifie la cohérence des paramètres puis les convertit pour la simulation.
    Entrée  : dict de nombres (altitude_cible en km, diametre en m) + éventuellement lieu/date.
    Sortie  : nouveau dict (altitude_cible en m, "surface" à la place de "diametre").
    Lève ValueError avec un message lisible si un paramètre est incohérent.
    """
    v = dict(valeurs)

    if not v["masse"] > v["masse_vide"] > 0:
        raise ValueError(
            "La masse initiale doit être supérieure à la masse à vide, qui doit être positive."
        )
    if v["poussee"] < 0:
        raise ValueError("La poussée ne peut pas être négative.")
    if v["consommation"] < 0:
        raise ValueError("La consommation ne peut pas être négative.")
    if v["diametre"] <= 0:
        raise ValueError("Le diamètre doit être strictement positif.")
    if v["cd"] < 0:
        raise ValueError("Le coefficient de traînée doit être positif ou nul.")
    if v["dt"] <= 0 or v["duree"] <= 0:
        raise ValueError("La durée et le pas de temps doivent être positifs.")
    if v["altitude_cible"] <= 0:
        raise ValueError("L'altitude cible doit être positive.")
    if v["debut_bascule"] < 0 or v["fin_bascule"] <= v["debut_bascule"]:
        raise ValueError("Les temps de bascule doivent être positifs et croissants.")
    if v["duree"] / v["dt"] > 200000:
        raise ValueError("Trop de pas de calcul : augmentez le pas de temps.")

    # Conversions : km -> m, diamètre -> surface frontale
    v["altitude_cible"] *= 1000
    v["surface"] = math.pi * (v["diametre"] / 2) ** 2
    del v["diametre"]

    return v