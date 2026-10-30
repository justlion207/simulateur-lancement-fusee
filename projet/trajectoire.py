# -*- coding: utf-8 -*-
"""
Created on Tue Sep 29 09:29:32 2026

@author: tristan dupuis 
"""


# PROGRAMME 2 : SIMULATION DE LA TRAJECTOIRE

import math

# Constantes physiques
MU = 3.986004418e14
R_TERRE = 6371000.0
RHO0 = 1.225
HAUTEUR_ECHELLE = 8500.0


# Fonction 5 : Calculer la densité atmosphérique
def calculer_densite_air(altitude):

    densite = RHO0 * math.exp(
        -max(0.0, altitude) / HAUTEUR_ECHELLE
    )

    return densite


# Fonction 6 : Calculer la traînée
def calculer_trainee(densite, vitesse,
                     coefficient, surface):

    trainee = (
        0.5 * densite * coefficient
        * surface * vitesse**2
    )

    return trainee


# Fonction 7 : Calculer la gravité
def calculer_gravite(altitude):

    gravite = MU / (
        R_TERRE + max(0.0, altitude)
    )**2

    return gravite


# Fonction 8 : Calculer la nouvelle masse
def calculer_masse(masse, consommation,
                   dt, masse_vide):

    nouvelle_masse = masse - consommation * dt

    return max(masse_vide, nouvelle_masse)


# Fonction 9 : Calculer la vitesse
def calculer_vitesse(vitesse, acceleration, dt):

    nouvelle_vitesse = vitesse + acceleration * dt

    return nouvelle_vitesse


# Fonction 10 : Calculer l'altitude
def calculer_altitude(altitude, vitesse, dt):

    nouvelle_altitude = altitude + vitesse * dt

    return nouvelle_altitude


# Fonction 11 : Simuler le lancement
def simuler_lancement(
    masse,
    poussee,
    consommation,
    masse_vide,
    duree=900,
    dt=0.5,
    cd=0.3,
    surface=10.0,
    debut_bascule=15.0,
    fin_bascule=240.0
):

    if not (masse > masse_vide > 0):
        raise ValueError("Masses invalides.")

    if poussee < 0 or consommation < 0:
        raise ValueError("Poussée ou consommation invalide.")

    if dt <= 0 or duree <= 0:
        raise ValueError("Durée ou pas de temps invalide.")

    if cd < 0 or surface < 0:
        raise ValueError("Paramètres aérodynamiques invalides.")

    if fin_bascule <= debut_bascule:
        raise ValueError("Période de bascule invalide.")

    # Position initiale
    x = R_TERRE
    y = 0.0

    # Vitesse initiale
    vx = 0.0
    vy = 0.0

    # Carburant disponible
    carburant = masse - masse_vide

    # Liste contenant les résultats
    historique = []

    for i in range(int(duree / dt) + 1):

        temps = i * dt

        # Distance au centre de la Terre
        r = math.hypot(x, y)

        # Altitude
        altitude = max(0.0, r - R_TERRE)

        # Direction radiale
        ux = x / r
        uy = y / r

        # Direction tangentielle
        tx = -uy
        ty = ux

        # Composantes de la vitesse
        vitesse_radiale = vx * ux + vy * uy

        vitesse_tangentielle = vx * tx + vy * ty

        vitesse = math.hypot(vx, vy)

        # Enregistrement des données
        historique.append({

            "temps": temps,
            "altitude": altitude,
            "vitesse": vitesse,
            "vitesse_radiale": vitesse_radiale,
            "vitesse_tangentielle": vitesse_tangentielle,
            "masse": masse,
            "carburant": carburant,
            "x": x,
            "y": y,
            "vx": vx,
            "vy": vy

        })

        if i == int(duree / dt):
            break

        # Gestion du carburant
        if consommation > 0:

            fraction = min(
                1.0,
                carburant / (consommation * dt)
            )

        else:

            fraction = 1.0 if carburant > 0 else 0.0

        # Poussée effective
        if carburant > 0:

            poussee_effective = poussee * fraction

        else:

            poussee_effective = 0.0

        # Masse consommée
        dm = min(carburant, consommation * dt)

        masse_moyenne = masse - dm / 2

        # Orientation progressive de la fusée
        progression = max(
            0.0,
            min(
                1.0,
                (temps - debut_bascule)
                / (fin_bascule - debut_bascule)
            )
        )

        angle = progression * math.pi / 2

        px = math.cos(angle) * ux + math.sin(angle) * tx
        py = math.cos(angle) * uy + math.sin(angle) * ty

        # Calcul de la résistance de l'air
        densite = calculer_densite_air(altitude)

        trainee = calculer_trainee(
            densite,
            vitesse,
            cd,
            surface
        )

        # Direction de la traînée
        if vitesse > 0:

            dx = -trainee * vx / vitesse
            dy = -trainee * vy / vitesse

        else:

            dx = 0.0
            dy = 0.0

        # Calcul de la gravité
        gravite = calculer_gravite(altitude)

        # Accélérations
        ax = (
            (poussee_effective * px + dx)
            / masse_moyenne
            - gravite * ux
        )

        ay = (
            (poussee_effective * py + dy)
            / masse_moyenne
            - gravite * uy
        )

        # Mise à jour des vitesses
        vx = calculer_vitesse(vx, ax, dt)
        vy = calculer_vitesse(vy, ay, dt)

        # Mise à jour de la position
        x += vx * dt
        y += vy * dt

        # Mise à jour de la masse
        masse = calculer_masse(
            masse,
            consommation,
            dt,
            masse_vide
        )

        carburant = max(0.0, carburant - dm)

        # Arrêt si la fusée rencontre le sol
        if math.hypot(x, y) < R_TERRE:
            break

    return historique
