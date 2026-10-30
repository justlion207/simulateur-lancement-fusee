"""
optimisation.py
Analyse de l'orbite atteinte, conseils chiffrés et recherche des valeurs exactes
(début/fin de bascule, masse initiale) permettant d'atteindre l'orbite visée.
"""
import math

from main import lancer_simulation

# ============================================================
# ANALYSE DE L'ORBITE & CONSEILS
# ============================================================
MU_TERRE = 3.986004418e14       # m^3/s^2
RAYON_TERRE = 6371000.0         # m
G0 = 9.80665                    # m/s^2
PERTES_ESTIMEES = 1800.0        # m/s (gravité + traînée, ordre de grandeur)
TOLERANCE_ORBITE = 0.10         # ±10 % autour de l'altitude cible


def fmt(x, unite=""):
    return f"{x:,.0f}".replace(",", " ") + (f" {unite}" if unite else "")


def orbite_finale(historique):
    """Estime l'orbite à partir du dernier point de la simulation."""
    dernier = historique[-1]
    alt, v = dernier["altitude"], dernier["vitesse"]
    v_r = 0.0
    if len(historique) > 1:
        dt_h = dernier["temps"] - historique[-2]["temps"]
        if dt_h > 0:
            v_r = (alt - historique[-2]["altitude"]) / dt_h

    r = RAYON_TERRE + alt
    energie = v ** 2 / 2 - MU_TERRE / r
    orb = {"alt": alt, "v": v, "energie": energie, "echappement": energie >= 0, "peri": None, "apo": None}
    if energie < 0:
        a = -MU_TERRE / (2 * energie)
        v_t = math.sqrt(max(v ** 2 - v_r ** 2, 0.0))
        p_orb = (r * v_t) ** 2 / MU_TERRE
        e = math.sqrt(max(0.0, 1 - p_orb / a))
        orb["peri"] = a * (1 - e) - RAYON_TERRE
        orb["apo"] = a * (1 + e) - RAYON_TERRE
    return orb


def cout_orbite(orb, h_cible):
    """0 = orbite parfaite. Somme des écarts relatifs² du périgée et de l'apogée."""
    if orb["echappement"]:
        return 1e5 * (1.0 + orb["energie"] / (MU_TERRE / (RAYON_TERRE + orb["alt"])))
    return ((orb["peri"] - h_cible) / h_cible) ** 2 + ((orb["apo"] - h_cible) / h_cible) ** 2


# ============================================================
# OPTIMISATION : TROUVER LES VALEURS EXACTES
# ============================================================
SEUIL_PRECISION = 0.01   # périgée et apogée à ±1 % de l'altitude cible
MAX_ESSAIS = 600


class _Arret(Exception):
    pass


def _nelder_mead(f, x0, pas, iterations):
    n = len(x0)
    pts = [list(x0)] + [[x0[j] + (pas[j] if j == i else 0.0) for j in range(n)] for i in range(n)]
    vals = [f(x) for x in pts]
    for _ in range(iterations):
        ordre = sorted(range(n + 1), key=lambda i: vals[i])
        pts = [pts[i] for i in ordre]
        vals = [vals[i] for i in ordre]
        if vals[-1] - vals[0] < 1e-10:
            break
        centre = [sum(pts[i][j] for i in range(n)) / n for j in range(n)]

        def point(c):
            return [centre[j] + c * (pts[-1][j] - centre[j]) for j in range(n)]

        xr = point(-1.0)
        fr = f(xr)
        if fr < vals[0]:
            xe = point(-2.0)
            fe = f(xe)
            pts[-1], vals[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < vals[-2]:
            pts[-1], vals[-1] = xr, fr
        else:
            xc = point(0.5) if fr >= vals[-1] else point(-0.5)
            fc = f(xc)
            if fc < min(fr, vals[-1]):
                pts[-1], vals[-1] = xc, fc
            else:
                for i in range(1, n + 1):
                    pts[i] = [pts[0][j] + 0.5 * (pts[i][j] - pts[0][j]) for j in range(n)]
                    vals[i] = f(pts[i])
    return pts[0], vals[0]


def optimiser_parametres(params, progression=None, annule=None, max_essais=MAX_ESSAIS):
    """
    Relance la simulation de nombreuses fois pour trouver les valeurs exactes qui
    amènent la fusée sur l'orbite visée.
      Étape 1 : début et fin de bascule uniquement.
      Étape 2 : si insuffisant, on ajuste aussi la masse initiale (quantité d'ergols).
    Retourne {"modif", "orbite", "cout", "succes", "precis", "essais", "annule"} ou None.
    """
    h = params["altitude_cible"]
    m0, mv = params["masse"], params["masse_vide"]
    seuil = 2 * SEUIL_PRECISION ** 2
    etat = {"essais": 0, "cout": float("inf"), "modif": None, "orbite": None}

    def simuler(modif):
        p2 = dict(params)
        p2.update(modif)
        try:
            res = lancer_simulation(parametres=p2, afficher_graphiques=False)
        except Exception:
            return 1e3, None
        if not res or not res.get("historique"):
            return 1e3, None
        orb = orbite_finale(res["historique"])
        return cout_orbite(orb, h), orb

    def evaluer(modif):
        d, fi = modif["debut_bascule"], modif["fin_bascule"]
        if d < 0 or fi < d + 1 or fi > params["duree"] or modif.get("masse", m0) <= mv * 1.02:
            return 1e3
        if annule and annule():
            raise _Arret()
        etat["essais"] += 1
        cout, orb = simuler(modif)
        if cout < etat["cout"]:
            etat.update(cout=cout, modif=dict(modif), orbite=orb)
        if progression:
            progression(etat["essais"], max_essais, etat["cout"])
        if etat["cout"] <= seuil or etat["essais"] >= max_essais:
            raise _Arret()
        return cout

    def f2(x):
        return evaluer({"debut_bascule": x[0], "fin_bascule": x[1]})

    def f3(x):
        return evaluer({"debut_bascule": x[0], "fin_bascule": x[1], "masse": x[2]})

    d0, f0 = params["debut_bascule"], params["fin_bascule"]
    try:
        # Étape 1 : balayage de la bascule, puis affinage
        grille = []
        for d in sorted({d0, 5.0, 10.0, 15.0, 25.0, 40.0}):
            for fi in sorted({f0, 100.0, 150.0, 200.0, 250.0, 300.0, 400.0}):
                grille.append((evaluer({"debut_bascule": d, "fin_bascule": fi}), d, fi))
        grille.sort()
        _, d, fi = grille[0]
        _nelder_mead(f2, [d, fi], [3.0, 15.0], 25)

        # Étape 2 : on ajuste aussi la masse initiale
        base = dict(etat["modif"]) if etat["modif"] else {"debut_bascule": d0, "fin_bascule": f0}
        # Masse initiale « théorique » donnant le Δv nécessaire (équation de Tsiolkovsky)
        candidats = [m0 * k for k in (0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.35)]
        if params["consommation"] > 0:
            v_eff = params["poussee"] / params["consommation"]
            v_circ = math.sqrt(MU_TERRE / (RAYON_TERRE + h))
            m_theo = mv * math.exp((v_circ + PERTES_ESTIMEES) / v_eff)
            candidats += [m_theo * k for k in (0.92, 1.0, 1.08)]
        meilleur_m, meilleur_c = m0, float("inf")
        for m_test in candidats:
            c = evaluer({**base, "masse": m_test})
            if c < meilleur_c:
                meilleur_m, meilleur_c = m_test, c
        depart = [base["debut_bascule"], base["fin_bascule"], meilleur_m]
        echelle, meilleur_avant = 1.0, float("inf")
        while True:  # redémarrages avec un pas de plus en plus fin, jusqu'à la fin du budget
            depart, cout_nm = _nelder_mead(f3, depart, [3.0 * echelle, 15.0 * echelle, 0.03 * m0 * echelle], 40)
            if cout_nm > meilleur_avant * 0.9:
                echelle *= 0.4
                if echelle < 0.01:
                    break
            meilleur_avant = min(meilleur_avant, cout_nm)
    except _Arret:
        pass

    if etat["modif"] is None:
        return None

    # Arrondi des valeurs + vérification par simulation
    base = {k: (round(v) if k == "masse" else round(v, 2)) for k, v in etat["modif"].items()}
    essais_arrondi = [base]
    if "masse" in base:  # l'optimum peut se trouver sur un « bord » : on teste les masses voisines
        essais_arrondi += [{**base, "masse": base["masse"] + dm} for dm in (-5, -2, -1, 1, 2, 5)]
    modif, cout, orb = None, float("inf"), None
    for cand in essais_arrondi:
        c, o = simuler(cand)
        if o is not None and c < cout:
            modif, cout, orb = cand, c, o
    if orb is None:
        return None

    return {
        "modif": modif, "orbite": orb, "cout": cout,
        "succes": cout <= 2 * TOLERANCE_ORBITE ** 2,
        "precis": cout <= seuil,
        "essais": etat["essais"],
        "annule": bool(annule and annule()),
    }


def analyser_orbite(params, historique):
    """
    Compare l'état final de la fusée à l'orbite visée.
    Retourne {"atteinte": bool, "lignes": [...], "conseils": [...]}.
    L'orbite est estimée à partir de l'altitude, de la vitesse et de la vitesse
    radiale du dernier point de la simulation.
    """
    h_cible = params["altitude_cible"]
    m0, mv = params["masse"], params["masse_vide"]
    poussee, mdot = params["poussee"], params["consommation"]
    tol = TOLERANCE_ORBITE
    lignes, conseils = [], []

    # --- État final et orbite estimée ---
    orb = orbite_finale(historique)
    alt, v = orb["alt"], orb["v"]
    echappement, peri, apo = orb["echappement"], orb["peri"], orb["apo"]

    v_circ = math.sqrt(MU_TERRE / (RAYON_TERRE + h_cible))
    atteinte = (
        not echappement
        and abs(peri - h_cible) <= tol * h_cible
        and abs(apo - h_cible) <= tol * h_cible
    )

    # --- Données de la fusée ---
    twr = poussee / (m0 * G0)
    t_comb = (m0 - mv) / mdot if mdot > 0 else float("inf")
    v_eff = poussee / mdot if mdot > 0 else 0.0
    dv_ideal = v_eff * math.log(m0 / mv) if v_eff > 0 else 0.0
    dv_requis = v_circ + PERTES_ESTIMEES

    lignes.append(f"Altitude finale : {fmt(alt / 1000, 'km')} (cible : {fmt(h_cible / 1000, 'km')})")
    lignes.append(f"Vitesse finale : {fmt(v, 'm/s')} (vitesse circulaire à la cible : {fmt(v_circ, 'm/s')})")
    if echappement:
        lignes.append("Orbite estimée : trajectoire d'échappement")
    else:
        lignes.append(f"Orbite estimée : périgée {fmt(peri / 1000, 'km')} / apogée {fmt(apo / 1000, 'km')}")
    lignes.append(f"Rapport poussée/poids au décollage : {twr:.2f}")
    lignes.append(f"Δv idéal de la fusée : {fmt(dv_ideal, 'm/s')} (≈ {fmt(dv_requis, 'm/s')} nécessaires)")

    if atteinte:
        return {"atteinte": True, "lignes": lignes, "conseils": []}

    # --- Conseils ---
    if twr < 1.2:
        conseils.append(
            f"Poussée/poids trop faible au décollage ({twr:.2f}). Augmente la poussée "
            f"(≥ {fmt(1.3 * m0 * G0, 'N')}) ou réduis la masse initiale."
        )

    if params["duree"] < t_comb:
        conseils.append(
            f"La durée de simulation ({fmt(params['duree'], 's')}) est plus courte que le temps de "
            f"combustion ({fmt(t_comb, 's')}) : augmente-la."
        )
    if params["fin_bascule"] > t_comb:
        conseils.append(
            f"La bascule se termine ({fmt(params['fin_bascule'], 's')}) après l'extinction du moteur "
            f"(≈ {fmt(t_comb, 's')}) : réduis la fin de bascule."
        )

    deficit = v_eff > 0 and dv_ideal < dv_requis
    if deficit:
        ratio = math.exp(dv_requis / v_eff)
        v_eff_req = dv_requis / math.log(m0 / mv)
        conseils.append(
            f"Δv insuffisant ({fmt(dv_ideal)} m/s pour ≈ {fmt(dv_requis)} m/s). Pistes : "
            f"masse à vide ≤ {fmt(m0 / ratio, 'kg')} (actuellement {fmt(mv, 'kg')}), "
            f"ou masse initiale ≥ {fmt(mv * ratio, 'kg')}, "
            f"ou consommation ≤ {fmt(poussee / v_eff_req, 'kg/s')}, "
            f"ou poussée ≥ {fmt(v_eff_req * mdot, 'N')}."
        )
    elif not echappement:
        bas, haut = h_cible * (1 - tol), h_cible * (1 + tol)
        if apo < bas:
            conseils.append(
                f"Apogée trop bas ({fmt(apo / 1000, 'km')}) : manque d'énergie ou trop de traînée. "
                "Réduis le coefficient de traînée, augmente la poussée ou la durée de combustion."
            )
        elif peri < bas and apo > haut:
            conseils.append(
                f"Trajectoire trop verticale (périgée {fmt(peri / 1000, 'km')}, apogée {fmt(apo / 1000, 'km')}) : "
                "avance le début de bascule et/ou raccourcis la durée de bascule pour gagner de la vitesse horizontale."
            )
        elif peri < bas:
            conseils.append(
                f"Orbite trop elliptique (périgée {fmt(peri / 1000, 'km')}) : vitesse horizontale insuffisante. "
                "Incline la fusée plus tôt (début de bascule plus petit) ou de façon plus franche (fin de bascule plus proche du début)."
            )
        elif peri > haut:
            conseils.append(
                f"Orbite trop haute (périgée {fmt(peri / 1000, 'km')}) : trop d'énergie. "
                "Réduis la poussée ou la masse d'ergols, ou relève l'altitude cible."
            )
        else:
            conseils.append(
                f"Apogée trop haut ({fmt(apo / 1000, 'km')}) : léger excès d'énergie. "
                "Réduis un peu la poussée ou la masse initiale."
            )
    if echappement:
        conseils.append(
            "Vitesse excessive (trajectoire d'échappement) : réduis la poussée ou la masse d'ergols "
            "(masse initiale), ou relève l'altitude cible."
        )

    if params["cd"] > 0.5:
        conseils.append(f"Coefficient de traînée élevé ({params['cd']}) : une valeur de 0.2 à 0.4 est plus réaliste pour une fusée.")
    if params["dt"] > 1:
        conseils.append(f"Pas de temps élevé ({params['dt']} s) : descends à 0.5 s ou moins pour plus de précision.")

    if not conseils:
        conseils.append("Ajuste progressivement le début et la fin de bascule par pas de 5 à 10 s et relance.")

    return {"atteinte": False, "lignes": lignes, "conseils": conseils}