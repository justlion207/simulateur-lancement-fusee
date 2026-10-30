"""Point d'entrée du projet : python main.py."""
import matplotlib.pyplot as plt

from decollage import (calculer_poids, calculer_poussee,
                       verifier_decollage, calculer_acceleration)
from trajectoire import simuler_lancement
from orbite import (calculer_vitesse_orbitale, verifier_altitude,
                    verifier_orbite, calculer_parametres_orbitaux)
from graphique import (afficher_altitude, afficher_vitesse, afficher_masse,
                       afficher_trajectoire, afficher_bilan)
import parametres as p


def saisir_parametres():
    """Retourne les paramètres du scénario, regroupés dans parametres.py."""
    return dict(
        masse=p.MASSE_INITIALE, masse_vide=p.MASSE_VIDE,
        poussee=p.POUSSEE_TOTALE, consommation=p.CONSOMMATION,
        duree=p.DUREE_SIMULATION, dt=p.DT, cd=p.CD, surface=p.SURFACE,
        debut_bascule=p.DEBUT_BASCULE, fin_bascule=p.FIN_BASCULE,
        altitude_cible=p.ALTITUDE_CIBLE
    )


def lancer_simulation(parametres=None, afficher_graphiques=True):
    """Calcule le décollage, la trajectoire, les critères orbitaux et le bilan."""
    cfg = saisir_parametres() if parametres is None else parametres
    poids = calculer_poids(cfg["masse"])
    # Un moteur équivalent représente la poussée totale de l'ensemble.
    poussee = calculer_poussee(1, cfg["poussee"])
    decolle = verifier_decollage(poussee, poids)
    acceleration = calculer_acceleration(poussee, poids, cfg["masse"])
    print(f"Poids initial : {poids:,.0f} N")
    print(f"Poussée totale : {poussee:,.0f} N")
    print(f"Décollage possible : {'oui' if decolle else 'non'}")
    print(f"Accélération initiale : {acceleration:.2f} m/s²")
    if not decolle:
        print("Simulation interrompue : poussée initiale insuffisante.")
        return None

    historique = simuler_lancement(
        masse=cfg["masse"], poussee=poussee,
        consommation=cfg["consommation"], masse_vide=cfg["masse_vide"],
        duree=cfg["duree"], dt=cfg["dt"], cd=cfg["cd"],
        surface=cfg["surface"], debut_bascule=cfg["debut_bascule"],
        fin_bascule=cfg["fin_bascule"]
    )
    final = historique[-1]
    vitesse_orbitale = calculer_vitesse_orbitale(final["altitude"])
    altitude_ok = verifier_altitude(final["altitude"])
    orbite_simplifiee = verifier_orbite(
        final["altitude"], final["vitesse_tangentielle"],
        vitesse_orbitale, final["vitesse_radiale"],
        tolerance=p.TOLERANCE_VITESSE
    )
    elements = calculer_parametres_orbitaux(
        final["x"], final["y"], final["vx"], final["vy"]
    )
    bilan = afficher_bilan(historique, elements)
    bilan["Altitude dans la plage 200–800 km"] = altitude_ok
    bilan["Conditions orbitales simplifiées"] = orbite_simplifiee
    bilan["Altitude cible (km)"] = cfg["altitude_cible"] / 1000
    bilan["Altitude cible atteinte"] = final["altitude"] >= cfg["altitude_cible"]
    bilan["Vitesse circulaire locale (m/s)"] = round(vitesse_orbitale, 2)
    print("\nBILAN FINAL")
    for nom, valeur in bilan.items():
        print(f"{nom} : {valeur}")

    if afficher_graphiques:
        temps = [point["temps"] for point in historique]
        afficher_altitude(temps, [point["altitude"] for point in historique])
        afficher_vitesse(temps, [point["vitesse"] for point in historique])
        afficher_masse(temps, [point["masse"] for point in historique])
        afficher_trajectoire(
            [point["x"] for point in historique],
            [point["y"] for point in historique]
        )
        plt.show()
    return {"historique": historique, "bilan": bilan,
            "parametres_orbitaux": elements}


def main():
    lancer_simulation()


if __name__ == "__main__":
    main()
