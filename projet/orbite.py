# -*- coding: utf-8 -*-
"""
Created on Tue Sep 29 09:29:56 2026

@author: tristan dupuis 
"""


# PROGRAMME 3 : ANALYSE DE LA MISE EN ORBITE

import math

from trajectoire import MU, R_TERRE


# Fonction 12 : Calculer la vitesse orbitale
def calculer_vitesse_orbitale(altitude):

    if altitude < 0:
        raise ValueError("Altitude négative.")

    vitesse = math.sqrt( MU / (R_TERRE + altitude) )

    return vitesse


# Fonction 13 : Vérifier l'altitude
def verifier_altitude(
    altitude,
    minimum=200000,
    maximum=800000):

    if minimum <= altitude <= maximum:
        return True

    return False


# Fonction 14 : Vérifier les conditions orbitales
def verifier_orbite(
    altitude,
    vitesse_tangentielle,
    vitesse_orbitale,
    vitesse_radiale=0.0,
    tolerance=0.05):

    condition_altitude = verifier_altitude(altitude)

    ecart_vitesse = abs(vitesse_tangentielle - vitesse_orbitale)

    condition_vitesse = (ecart_vitesse <= vitesse_orbitale * tolerance)

    condition_radiale = (abs(vitesse_radiale)
        <= vitesse_orbitale * tolerance)

    return (condition_altitude
        and condition_vitesse
        and condition_radiale)


# Fonction 15 : Calculer les paramètres orbitaux
def calculer_parametres_orbitaux(x, y, vx, vy):

    r = math.hypot(x, y)

    v2 = vx**2 + vy**2

    # Moment cinétique spécifique
    moment = x * vy - y * vx

    # Énergie mécanique spécifique
    energie = v2 / 2 - MU / r

    # Vecteur excentricité
    ex = (vy * moment) / MU - x / r

    ey = (-vx * moment) / MU - y / r

    excentricite = math.hypot(ex, ey)

    # Trajectoire non liée
    if energie >= 0:

        return {"liee": False,
            "excentricite": excentricite,
            "perigee": None,
            "apogee": None}

    # Demi-grand axe
    a = -MU / (2 * energie)

    # Périgée et apogée
    perigee = a * (1 - excentricite) - R_TERRE

    apogee = a * (1 + excentricite) - R_TERRE

    return {"liee": True,
        "excentricite": excentricite,
        "perigee": perigee,
        "apogee": apogee }
