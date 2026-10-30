# -*- coding: utf-8 -*-
"""
Created on Tue Sep 29 09:30:33 2026

@author: tristan dupuis 
"""


# PROGRAMME 4 : AFFICHAGE DES GRAPHIQUES

import matplotlib.pyplot as plt

from trajectoire import R_TERRE


# Fonction 16 : Créer un graphique
def creer_graphique(temps, valeurs, titre, unite):

    fig, ax = plt.subplots()

    ax.plot(temps, valeurs)

    ax.set_xlabel("Temps (s)")
    ax.set_ylabel(unite)
    ax.set_title(titre)

    ax.grid(True)

    fig.tight_layout()

    return fig


# Fonction 17 : Afficher l'altitude
def afficher_altitude(temps, altitudes):

    altitudes_km = [h / 1000 for h in altitudes]

    return creer_graphique(temps, altitudes_km, "Evolution de l'altitude", "Altitude (km)")


# Fonction 18 : Afficher la vitesse
def afficher_vitesse(temps, vitesses):

    return creer_graphique( temps,vitesses,"Evolution de la vitesse", "Vitesse (m/s)" )


# Fonction 19 : Afficher la masse
def afficher_masse(temps, masses):

    return creer_graphique(temps,masses,"Evolution de la masse","Masse (kg)" )


# Fonction 20 : Afficher la trajectoire


def afficher_trajectoire(x, y):

    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    from matplotlib.lines import Line2D
    from trajectoire import R_TERRE

    # Conversion en kilomètres
    x = [valeur / 1000 for valeur in x]
    y = [valeur / 1000 for valeur in y]
    rayon = R_TERRE / 1000

    # Deux graphiques côte à côte
    fig, (ax1, ax2) = plt.subplots(
        1, 2,
        figsize=(12, 5),
        gridspec_kw={"width_ratios": [1, 1.2]}
    )

    fig.patch.set_facecolor("#111827")

    for ax in (ax1, ax2):

        ax.set_facecolor("#111827")

        # Terre bleue, sans continents
        terre = Circle(
            (0, 0),
            rayon,
            facecolor="#1769AA",
            edgecolor="#70CCFF",
            linewidth=2,
            zorder=1
        )
        ax.add_patch(terre)

        # Trajectoire lumineuse
        ax.plot(
            x, y,
            color="#FFD54F",
            linewidth=7,
            alpha=0.15,
            zorder=3
        )

        ax.plot(
            x, y,
            color="#FFD54F",
            linewidth=2.8,
            zorder=4
        )

        # Départ
        ax.scatter(
            x[0], y[0],
            color="#4ADE80",
            edgecolor="white",
            s=65,
            zorder=5
        )

        # Fin de simulation
        ax.scatter(
            x[-1], y[-1],
            color="#FB7185",
            edgecolor="white",
            s=65,
            zorder=5
        )

        ax.set_aspect("equal", adjustable="box")
        ax.grid(True, color="white", alpha=0.12, linestyle="--")
        ax.tick_params(colors="white")

        ax.set_xlabel("X (km)", color="white")
        ax.set_ylabel("Y (km)", color="white")

        for bord in ax.spines.values():
            bord.set_color("#475569")

    # GRAPHIQUE 1 : Terre complète
    limite = max(
        rayon * 1.12,
        max(abs(valeur) for valeur in x) * 1.08,
        max(abs(valeur) for valeur in y) * 1.08
    )

    ax1.set_xlim(-limite, limite)
    ax1.set_ylim(-limite, limite)
    ax1.set_title("Vue générale", color="white", fontweight="bold")

    # GRAPHIQUE 2 : zoom sur la trajectoire
    marge = max(
        150,
        0.12 * max(max(x) - min(x), max(y) - min(y))
    )

    ax2.set_xlim(min(x) - marge, max(x) + marge)
    ax2.set_ylim(min(y) - marge, max(y) + marge)
    ax2.set_title(
        "Zoom sur la trajectoire",
        color="white",
        fontweight="bold"
    )

    # Légende commune
    legende = [
        Line2D([0], [0], color="#FFD54F", linewidth=3,
               label="Trajectoire"),
        Line2D([0], [0], marker="o", linestyle="None",
               markerfacecolor="#4ADE80", markeredgecolor="white",
               label="Départ"),
        Line2D([0], [0], marker="o", linestyle="None",
               markerfacecolor="#FB7185", markeredgecolor="white",
               label="Fin de simulation")
    ]

    fig.legend(
        handles=legende,
        loc="lower center",
        ncol=3,
        frameon=False,
        labelcolor="white"
    )

    fig.subplots_adjust(
        left=0.08,
        right=0.97,
        top=0.88,
        bottom=0.19,
        wspace=0.35
    )

    return fig


# Fonction 21 : Afficher le bilan final
def afficher_bilan(historique, parametres):

    dernier = historique[-1]

    perigee = parametres["perigee"]
    apogee = parametres["apogee"]

    # Vérification de l'orbite cible
    reussite = ( parametres["liee"]
        and perigee is not None
        and perigee >= 200000
        and apogee <= 800000 )

    bilan = {

        "Altitude finale (km)":
            round(dernier["altitude"] / 1000, 2),

        "Vitesse finale (m/s)":
            round(dernier["vitesse"], 2),

        "Carburant restant (kg)":
            round(dernier["carburant"], 2),

        "Périgée (km)":
            None if perigee is None
            else round(perigee / 1000, 2),

        "Apogée (km)":
            None if apogee is None
            else round(apogee / 1000, 2),

        "Orbite cible théorique":
            "Atteinte" if reussite else "Non atteinte"

    }

    return bilan
