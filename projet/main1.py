import os
import math
import time
import customtkinter as ctk
import numpy as np

from PIL import Image
from matplotlib.figure import Figure
from matplotlib.patches import Circle
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


# ============================================================
# CONFIGURATION GENERALE
# ============================================================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Durée totale de l'animation (en secondes) et cadence visée (en ms).
# L'animation est basée sur le temps réel : si la machine ralentit,
# des images sont sautées mais la durée reste la même (jamais de retard cumulé).
DUREE_ANIMATION_S = 4.8
INTERVALLE_FRAME_MS = 16

# Exagération verticale de l'altitude dans la vue de profil.
# Une orbite à 200 km est minuscule face à un rayon terrestre de 6371 km :
# on la dilate pour que la trajectoire reste lisible (1.0 = échelle réelle).
# Les cartes et les courbes affichent toujours les valeurs réelles.
ECHELLE_ALTITUDE = 4.0


# ============================================================
# GESTIONNAIRE DE BLITTING
# ============================================================

class GestionnaireBlit:
    """
    Redessine uniquement les éléments animés d'un canvas Matplotlib.

    Principe : le fond (Terre, axes, courbes...) est dessiné une seule fois
    puis mis en cache. À chaque image, on restaure ce cache, on redessine
    seulement les artistes "animés" (fusée, tracé parcouru, curseurs) et on
    envoie le résultat à l'écran avec canvas.blit(). C'est ce qui évite
    les freezes de Tkinter.
    """

    def __init__(self, canvas):
        self.canvas = canvas
        self.figure = canvas.figure
        self.artistes = []
        self.fond = None

        # Le cache est recapturé après chaque dessin complet
        # et invalidé si la fenêtre change de taille.
        self.canvas.mpl_connect("draw_event", self._sur_dessin)
        self.canvas.mpl_connect("resize_event", self._sur_redim)

    def ajouter(self, artiste):
        """Déclare un artiste comme animé (exclu du dessin de fond)."""
        artiste.set_animated(True)
        self.artistes.append(artiste)

    def vider(self):
        """Oublie tous les artistes animés (avant de reconstruire un graphique)."""
        self.artistes = []
        self.fond = None

    def invalider(self):
        """Force un redessin complet au prochain passage."""
        self.fond = None

    def _sur_redim(self, event=None):
        self.fond = None

    def _sur_dessin(self, event=None):
        # Fin d'un dessin complet : on mémorise le fond, puis on ajoute
        # les artistes animés par-dessus.
        self.fond = self.canvas.copy_from_bbox(self.figure.bbox)
        self._dessiner_artistes()

    def _dessiner_artistes(self):
        for artiste in self.artistes:
            self.figure.draw_artist(artiste)

    def actualiser(self):
        """Met à jour l'affichage des seuls artistes animés."""
        if self.fond is None:
            # Pas encore de fond en cache : un dessin complet le créera.
            self.canvas.draw_idle()
            return

        try:
            self.canvas.restore_region(self.fond)
            self._dessiner_artistes()
            self.canvas.blit(self.figure.bbox)
        except Exception:
            # Cache incohérent (ex. redimensionnement en cours) : on repart proprement.
            self.fond = None
            self.canvas.draw_idle()


# ============================================================
# APPLICATION
# ============================================================

class Application(ctk.CTk):

    def __init__(self):
        super().__init__()

        # ====================================================
        # FENETRE
        # ====================================================

        self.title("Simulation de lancement - IPSA")
        self.geometry("1550x900")
        self.minsize(1250, 750)

        self.configure(fg_color="#06111d")

        # ====================================================
        # CONSTANTES
        # ====================================================

        self.G = 6.67430e-11
        self.M_TERRE = 5.972e24
        self.R_TERRE = 6_371_000
        self.G0 = 9.81

        # ====================================================
        # VARIABLES D'ANIMATION
        # ====================================================

        self.animation_active = False
        self.indice_animation = 0
        self.after_id = None
        self.t_debut_animation = 0.0

        # Cache des textes des cartes (évite de reconfigurer un label inchangé)
        self._textes_cartes = {}

        # Emprise de la vue 2D (calculée à chaque analyse)
        self._vue = None

        # Arrêt propre à la fermeture de la fenêtre
        self.protocol("WM_DELETE_WINDOW", self.fermer)

        # ====================================================
        # GRILLE PRINCIPALE
        # ====================================================

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        self.grid_rowconfigure(0, weight=1)

        # ====================================================
        # PANNEAU GAUCHE
        # ====================================================

        self.creer_panneau_gauche()

        # ====================================================
        # PANNEAU DROIT
        # ====================================================

        self.frame_droit = ctk.CTkFrame(
            self,
            fg_color="transparent",
            corner_radius=0
        )

        self.frame_droit.grid(
            row=0,
            column=1,
            padx=(0, 15),
            pady=15,
            sticky="nsew"
        )

        self.frame_droit.grid_columnconfigure(0, weight=1)
        self.frame_droit.grid_rowconfigure(0, weight=3)
        self.frame_droit.grid_rowconfigure(1, weight=2)

        # Terre + trajectoire
        self.creer_zone_trajectoire()

        # Analyses temps réel
        self.creer_zone_analyses()

        # Première simulation
        self.lancer_analyse()

    # ========================================================
    # PANNEAU GAUCHE
    # ========================================================

    def creer_panneau_gauche(self):

        self.frame_gauche = ctk.CTkFrame(
            self,
            width=390,
            fg_color="#071a2b",
            corner_radius=18,
            border_width=1,
            border_color="#1478b8"
        )

        self.frame_gauche.grid(
            row=0,
            column=0,
            padx=15,
            pady=15,
            sticky="ns"
        )

        self.frame_gauche.grid_propagate(False)

        # ----------------------------------------------------
        # TITRE
        # ----------------------------------------------------

        frame_titre = ctk.CTkFrame(
            self.frame_gauche,
            fg_color="transparent"
        )

        frame_titre.pack(
            fill="x",
            padx=18,
            pady=(18, 10)
        )

        titre = ctk.CTkLabel(
            frame_titre,
            text="SIMULATION DE LANCEMENT",
            font=("Arial", 23, "bold"),
            text_color="#d8edff"
        )

        titre.pack(anchor="w")

        sous_titre = ctk.CTkLabel(
            frame_titre,
            text="Du décollage à la mise en orbite",
            font=("Arial", 14),
            text_color="#8eaac1"
        )

        sous_titre.pack(anchor="w")

        # ----------------------------------------------------
        # SCROLL
        # ----------------------------------------------------

        self.scroll = ctk.CTkScrollableFrame(
            self.frame_gauche,
            fg_color="transparent"
        )

        self.scroll.pack(
            fill="both",
            expand=True,
            padx=10
        )

        # ====================================================
        # DECOLLAGE
        # ====================================================

        frame_decollage = self.creer_section(
            "1   DÉCOLLAGE"
        )

        self.entry_masse_vide = self.creer_entree(
            frame_decollage,
            "Masse à vide (kg)",
            "120000"
        )

        self.entry_carburant = self.creer_entree(
            frame_decollage,
            "Carburant (kg)",
            "430000"
        )

        self.entry_charge = self.creer_entree(
            frame_decollage,
            "Charge utile (kg)",
            "15000"
        )

        self.entry_poussee = self.creer_entree(
            frame_decollage,
            "Poussée / moteur (N)",
            "1000000"
        )

        self.entry_moteurs = self.creer_entree(
            frame_decollage,
            "Nombre de moteurs",
            "7"
        )

        self.label_masse_totale = self.creer_resultat(
            frame_decollage,
            "Masse totale",
            "--"
        )

        self.label_twr = self.creer_resultat(
            frame_decollage,
            "TWR",
            "--"
        )

        self.label_decollage_ok = self.creer_resultat(
            frame_decollage,
            "Vérification",
            "--"
        )

        # ====================================================
        # CROISIERE
        # ====================================================

        frame_croisiere = self.creer_section(
            "2   CROISIÈRE / ASCENSION"
        )

        self.entry_combustion = self.creer_entree(
            frame_croisiere,
            "Durée combustion (s)",
            "500"
        )

        self.entry_cd = self.creer_entree(
            frame_croisiere,
            "Coefficient de traînée",
            "0.30"
        )

        self.entry_diametre = self.creer_entree(
            frame_croisiere,
            "Diamètre fusée (m)",
            "5"
        )

        self.entry_angle = self.creer_entree(
            frame_croisiere,
            "Inclinaison trajectoire (°)",
            "12"
        )

        self.label_debit = self.creer_resultat(
            frame_croisiere,
            "Débit carburant",
            "--"
        )

        self.label_croisiere_ok = self.creer_resultat(
            frame_croisiere,
            "Vérification",
            "--"
        )

        # ====================================================
        # ORBITE
        # ====================================================

        frame_orbite = self.creer_section(
            "3   MISE EN ORBITE"
        )

        self.entry_altitude_orbite = self.creer_entree(
            frame_orbite,
            "Altitude cible (km)",
            "200"
        )

        self.entry_inclinaison = self.creer_entree(
            frame_orbite,
            "Inclinaison orbitale (°)",
            "15"
        )

        self.label_vitesse_orbite = self.creer_resultat(
            frame_orbite,
            "Vitesse orbitale",
            "--"
        )

        self.label_orbite_ok = self.creer_resultat(
            frame_orbite,
            "Vérification",
            "--"
        )

        # ====================================================
        # BOUTONS
        # ====================================================

        self.bouton_lancer = ctk.CTkButton(
            self.frame_gauche,
            text="▶   LANCER LA SIMULATION",
            height=45,
            font=("Arial", 15, "bold"),
            fg_color="#0785dc",
            hover_color="#0ca2ff",
            command=self.demarrer_animation
        )

        self.bouton_lancer.pack(
            fill="x",
            padx=18,
            pady=(12, 5)
        )

        self.bouton_reset = ctk.CTkButton(
            self.frame_gauche,
            text="↻   RÉINITIALISER",
            height=40,
            fg_color="#19334a",
            hover_color="#254b68",
            command=self.reinitialiser
        )

        self.bouton_reset.pack(
            fill="x",
            padx=18,
            pady=5
        )

        # ====================================================
        # LOGO IPSA
        # ====================================================

        self.creer_logo_ipsa()

    # ========================================================
    # LOGO
    # ========================================================

    def creer_logo_ipsa(self):

        frame_logo = ctk.CTkFrame(
            self.frame_gauche,
            fg_color="transparent"
        )

        frame_logo.pack(
            fill="x",
            padx=20,
            pady=(8, 15)
        )

        chemin = "ipsa_logo.png"

        if os.path.exists(chemin):

            image = Image.open(chemin)

            logo = ctk.CTkImage(
                light_image=image,
                dark_image=image,
                size=(130, 55)
            )

            label = ctk.CTkLabel(
                frame_logo,
                text="",
                image=logo
            )

        else:

            label = ctk.CTkLabel(
                frame_logo,
                text="IPSA ✦",
                font=("Arial", 34, "bold"),
                text_color="white"
            )

        label.pack(side="left")

        texte = ctk.CTkLabel(
            frame_logo,
            text="ÉCOLE D'INGÉNIEURS\nDE L'AIR ET DE L'ESPACE",
            font=("Arial", 9),
            justify="left",
            text_color="#8ba4b8"
        )

        texte.pack(
            side="left",
            padx=15
        )

    # ========================================================
    # CREER SECTION
    # ========================================================

    def creer_section(self, titre):

        frame = ctk.CTkFrame(
            self.scroll,
            fg_color="#082238",
            corner_radius=15,
            border_width=1,
            border_color="#087bc2"
        )

        frame.pack(
            fill="x",
            padx=2,
            pady=7
        )

        label = ctk.CTkLabel(
            frame,
            text=titre,
            font=("Arial", 15, "bold"),
            text_color="#e4f2ff"
        )

        label.pack(
            anchor="w",
            padx=15,
            pady=(11, 8)
        )

        return frame

    # ========================================================
    # ENTREE
    # ========================================================

    def creer_entree(self, parent, texte, valeur):

        ligne = ctk.CTkFrame(
            parent,
            fg_color="transparent"
        )

        ligne.pack(
            fill="x",
            padx=13,
            pady=3
        )

        label = ctk.CTkLabel(
            ligne,
            text=texte,
            font=("Arial", 12),
            anchor="w"
        )

        label.pack(
            side="left",
            fill="x",
            expand=True
        )

        entree = ctk.CTkEntry(
            ligne,
            width=145,
            height=28,
            fg_color="#071521",
            border_color="#31536d"
        )

        entree.insert(0, valeur)

        entree.pack(side="right")

        return entree

    # ========================================================
    # RESULTAT
    # ========================================================

    def creer_resultat(self, parent, texte, valeur):

        ligne = ctk.CTkFrame(
            parent,
            fg_color="transparent"
        )

        ligne.pack(
            fill="x",
            padx=13,
            pady=3
        )

        label = ctk.CTkLabel(
            ligne,
            text=f"{texte} :",
            font=("Arial", 12)
        )

        label.pack(side="left")

        valeur_label = ctk.CTkLabel(
            ligne,
            text=valeur,
            font=("Arial", 12, "bold"),
            text_color="#68f09a"
        )

        valeur_label.pack(side="right")

        return valeur_label

    # ========================================================
    # ZONE TERRE
    # ========================================================

    def creer_zone_trajectoire(self):

        self.frame_trajectoire = ctk.CTkFrame(
            self.frame_droit,
            fg_color="#020912",
            corner_radius=18,
            border_width=1,
            border_color="#126ba4"
        )

        self.frame_trajectoire.grid(
            row=0,
            column=0,
            sticky="nsew",
            pady=(0, 10)
        )

        # Figure Matplotlib "pure" (sans pyplot) : pas de fenêtre
        # fantôme ni d'état global, idéal pour l'intégration dans Tkinter.
        self.figure_2d = Figure(
            figsize=(10, 6),
            facecolor="#020912"
        )

        self.figure_2d.subplots_adjust(
            left=0.01,
            right=0.99,
            bottom=0.01,
            top=0.93
        )

        self.ax2d = self.figure_2d.add_subplot(111)

        self.ax2d.set_facecolor("#020912")
        self.ax2d.set_axis_off()

        # Les limites sont calculées à la main (repère orthonormé) :
        # on désactive l'autoscale pour qu'elles ne bougent jamais.
        self.ax2d.set_autoscale_on(False)

        self.canvas2d = FigureCanvasTkAgg(
            self.figure_2d,
            master=self.frame_trajectoire
        )

        self.canvas2d.get_tk_widget().pack(
            fill="both",
            expand=True,
            padx=5,
            pady=5
        )

        self.canvas2d.mpl_connect(
            "button_press_event",
            self.clic_trajectoire
        )

        # Recalcule la vue si la fenêtre est redimensionnée
        self.canvas2d.mpl_connect(
            "resize_event",
            self._sur_redim_trajectoire
        )

        self.blit_trajectoire = GestionnaireBlit(
            self.canvas2d
        )

        self.creer_elements_graphiques()

    # ========================================================
    # ELEMENTS GRAPHIQUES 2D (créés UNE seule fois)
    # ========================================================

    def creer_elements_graphiques(self):

        ax = self.ax2d

        R = self.R_TERRE / 1000

        # ----------------------------------------------------
        # TITRE
        # ----------------------------------------------------

        ax.set_title(
            "TRAJECTOIRE INTERACTIVE : DÉCOLLAGE → ORBITE",
            color="white",
            fontsize=12
        )

        # ----------------------------------------------------
        # ETOILES (en coordonnées de l'axe : indépendantes du zoom)
        # ----------------------------------------------------

        rng = np.random.default_rng(7)

        ax.scatter(
            rng.random(170),
            rng.random(170),
            s=rng.uniform(0.6, 3.2, 170),
            color="white",
            alpha=0.55,
            linewidths=0,
            transform=ax.transAxes,
            zorder=0
        )

        # ----------------------------------------------------
        # ATMOSPHERE (halos concentriques très transparents)
        # ----------------------------------------------------

        for altitude_halo, alpha in [
            (110, 0.035),
            (75, 0.05),
            (45, 0.07),
            (20, 0.10)
        ]:

            ax.add_patch(
                Circle(
                    (0, 0),
                    R + altitude_halo * ECHELLE_ALTITUDE,
                    facecolor="#23aaff",
                    edgecolor="none",
                    alpha=alpha,
                    zorder=1
                )
            )

        # ----------------------------------------------------
        # TERRE (disque plein + liseré lumineux à l'horizon)
        # ----------------------------------------------------

        ax.add_patch(
            Circle(
                (0, 0),
                R,
                facecolor="#0c4c83",
                edgecolor="none",
                zorder=2
            )
        )

        ax.add_patch(
            Circle(
                (0, 0),
                R,
                fill=False,
                edgecolor="#3db4ff",
                linewidth=1.6,
                alpha=0.85,
                zorder=3
            )
        )

        # ----------------------------------------------------
        # ELEMENTS FIXES DONT LES DONNEES CHANGENT A CHAQUE ANALYSE
        # ----------------------------------------------------

        # Orbite cible
        (self.ligne_orbite,) = ax.plot(
            [],
            [],
            linestyle="--",
            linewidth=1.2,
            color="#1faaff",
            alpha=0.7,
            zorder=4
        )

        # Trajectoire complète (fantôme)
        (self.ligne_trajectoire,) = ax.plot(
            [],
            [],
            linewidth=3,
            color="#ff8500",
            alpha=0.28,
            solid_capstyle="round",
            zorder=5
        )

        # Site de lancement
        (self.point_depart,) = ax.plot(
            [],
            [],
            marker="o",
            markersize=5,
            color="white",
            linestyle="none",
            zorder=6
        )

        # ----------------------------------------------------
        # ELEMENTS ANIMES (mis à jour par set_data / set_offsets)
        # ----------------------------------------------------

        # Portion de trajectoire déjà parcourue
        (self.trace_parcourue,) = ax.plot(
            [],
            [],
            linewidth=3,
            color="#ff8500",
            solid_capstyle="round",
            zorder=7
        )

        # Halo lumineux derrière la fusée
        self.halo_fusee = ax.scatter(
            [0],
            [R],
            s=420,
            marker="o",
            color="#52ff8c",
            alpha=0.22,
            linewidths=0,
            zorder=8
        )

        # Marqueur de la fusée
        self.marqueur_fusee = ax.scatter(
            [0],
            [R],
            s=100,
            marker="^",
            color="#52ff8c",
            zorder=9
        )

        for artiste in (
            self.trace_parcourue,
            self.halo_fusee,
            self.marqueur_fusee
        ):
            self.blit_trajectoire.ajouter(artiste)

    # ========================================================
    # VUE 2D
    # ========================================================

    def _ajuster_vue(self):
        """
        Cadre la vue sur la trajectoire et l'arc terrestre en gardant
        un repère orthonormé (la Terre reste un vrai cercle) quelle que soit
        la forme de la fenêtre.
        """

        if self._vue is None:
            return

        bbox = self.ax2d.bbox

        if bbox.width < 2 or bbox.height < 2:
            return

        xmin, xmax, ymin, ymax = self._vue

        largeur = xmax - xmin
        hauteur = ymax - ymin

        # Marges : un peu d'espace autour, davantage sous l'arc pour voir la Terre
        xmin -= 0.06 * largeur
        xmax += 0.06 * largeur
        ymin -= 0.30 * hauteur
        ymax += 0.10 * hauteur

        largeur = xmax - xmin
        hauteur = ymax - ymin

        ratio_ecran = bbox.width / bbox.height

        if largeur / hauteur < ratio_ecran:

            # Trop étroit : on élargit horizontalement
            nouvelle_largeur = hauteur * ratio_ecran
            centre = 0.5 * (xmin + xmax)

            xmin = centre - nouvelle_largeur / 2
            xmax = centre + nouvelle_largeur / 2

        else:

            # Trop large : on agrandit verticalement
            nouvelle_hauteur = largeur / ratio_ecran
            centre = 0.5 * (ymin + ymax)

            ymin = centre - nouvelle_hauteur / 2
            ymax = centre + nouvelle_hauteur / 2

        self.ax2d.set_xlim(xmin, xmax)
        self.ax2d.set_ylim(ymin, ymax)

    def _sur_redim_trajectoire(self, event=None):
        self._ajuster_vue()

    # ========================================================
    # ZONE ANALYSES
    # ========================================================

    def creer_zone_analyses(self):

        self.frame_analyses = ctk.CTkFrame(
            self.frame_droit,
            fg_color="#06192a",
            corner_radius=18,
            border_width=1,
            border_color="#126ba4"
        )

        self.frame_analyses.grid(
            row=1,
            column=0,
            sticky="nsew"
        )

        titre = ctk.CTkLabel(
            self.frame_analyses,
            text="⌁   ANALYSES EN TEMPS RÉEL",
            font=("Arial", 16, "bold")
        )

        titre.pack(
            anchor="w",
            padx=18,
            pady=(10, 5)
        )

        # ----------------------------------------------------
        # CARTES
        # ----------------------------------------------------

        self.frame_cartes = ctk.CTkFrame(
            self.frame_analyses,
            fg_color="transparent"
        )

        self.frame_cartes.pack(
            fill="x",
            padx=12,
            pady=5
        )

        for i in range(6):
            self.frame_cartes.grid_columnconfigure(
                i,
                weight=1
            )

        self.card_temps = self.creer_carte(
            0,
            "Temps depuis décollage",
            "--"
        )

        self.card_altitude = self.creer_carte(
            1,
            "Altitude",
            "--"
        )

        self.card_vitesse = self.creer_carte(
            2,
            "Vitesse",
            "--"
        )

        self.card_masse = self.creer_carte(
            3,
            "Masse actuelle",
            "--"
        )

        self.card_carburant = self.creer_carte(
            4,
            "Carburant restant",
            "--"
        )

        self.card_phase = self.creer_carte(
            5,
            "Phase de vol",
            "--"
        )

        # ----------------------------------------------------
        # FIGURE DES COURBES
        # ----------------------------------------------------

        self.figure_stats = Figure(
            figsize=(10, 2.7),
            facecolor="#06192a"
        )

        (
            self.ax_altitude,
            self.ax_vitesse,
            self.ax_masse
        ) = self.figure_stats.subplots(
            1,
            3
        )

        self.canvas_stats = FigureCanvasTkAgg(
            self.figure_stats,
            master=self.frame_analyses
        )

        self.canvas_stats.get_tk_widget().pack(
            fill="both",
            expand=True,
            padx=10,
            pady=(0, 8)
        )

        # Blitting des curseurs : évite de retracer les 3 courbes à chaque image
        self.blit_stats = GestionnaireBlit(
            self.canvas_stats
        )

    # ========================================================
    # CARTE
    # ========================================================

    def creer_carte(self, colonne, titre, valeur):

        frame = ctk.CTkFrame(
            self.frame_cartes,
            fg_color="#071f32",
            border_width=1,
            border_color="#174e72",
            corner_radius=10
        )

        frame.grid(
            row=0,
            column=colonne,
            padx=4,
            sticky="ew"
        )

        label = ctk.CTkLabel(
            frame,
            text=titre,
            font=("Arial", 10),
            text_color="#b4cbdc"
        )

        label.pack(
            pady=(7, 0)
        )

        valeur_label = ctk.CTkLabel(
            frame,
            text=valeur,
            font=("Arial", 17, "bold")
        )

        valeur_label.pack(
            pady=(2, 7)
        )

        return valeur_label

    # ========================================================
    # CALCUL GENERAL
    # ========================================================

    def lancer_analyse(self):

        try:

            masse_vide = float(
                self.entry_masse_vide.get()
            )

            carburant = float(
                self.entry_carburant.get()
            )

            charge = float(
                self.entry_charge.get()
            )

            poussee_moteur = float(
                self.entry_poussee.get()
            )

            moteurs = int(
                self.entry_moteurs.get()
            )

            combustion = float(
                self.entry_combustion.get()
            )

            altitude_cible = float(
                self.entry_altitude_orbite.get()
            )

            inclinaison = float(
                self.entry_inclinaison.get()
            )

        except ValueError:
            return

        # Évite une division par zéro (durée de combustion nulle ou négative)
        if combustion <= 0:
            return

        # ----------------------------------------------------
        # DECOLLAGE
        # ----------------------------------------------------

        masse_totale = (
            masse_vide
            + carburant
            + charge
        )

        poussee_totale = (
            poussee_moteur
            * moteurs
        )

        twr = poussee_totale / (
            masse_totale
            * self.G0
        )

        self.label_masse_totale.configure(
            text=f"{masse_totale:,.0f} kg"
        )

        self.label_twr.configure(
            text=f"{twr:.2f}"
        )

        if twr > 1:

            self.label_decollage_ok.configure(
                text="● OK",
                text_color="#68f09a"
            )

        else:

            self.label_decollage_ok.configure(
                text="✖ Impossible",
                text_color="#ff6464"
            )

        # ----------------------------------------------------
        # CARBURANT
        # ----------------------------------------------------

        debit = carburant / combustion

        self.label_debit.configure(
            text=f"{debit:,.0f} kg/s"
        )

        self.label_croisiere_ok.configure(
            text="● OK"
        )

        # ----------------------------------------------------
        # VITESSE ORBITALE
        # ----------------------------------------------------

        altitude_m = altitude_cible * 1000

        vitesse_orbitale = math.sqrt(
            self.G
            * self.M_TERRE
            /
            (
                self.R_TERRE
                + altitude_m
            )
        )

        self.label_vitesse_orbite.configure(
            text=f"{vitesse_orbitale:,.0f} m/s"
        )

        self.label_orbite_ok.configure(
            text="● Cible définie"
        )

        # ----------------------------------------------------
        # DONNEES SIMULATION
        # ----------------------------------------------------

        self.generer_trajectoire(
            masse_totale,
            masse_vide + charge,
            carburant,
            combustion,
            altitude_cible,
            vitesse_orbitale,
            inclinaison
        )

        self.dessiner_terre()

        self.preparer_graphiques()

        self.afficher_etat(0)

    # ========================================================
    # TRAJECTOIRE
    # ========================================================

    def generer_trajectoire(
        self,
        masse_initiale,
        masse_finale,
        carburant_initial,
        duree,
        altitude_orbite,
        vitesse_orbitale,
        inclinaison_deg
    ):

        self.temps = np.linspace(
            0,
            duree,
            1200
        )

        p = self.temps / duree

        # Altitude progressive
        self.altitude = (
            altitude_orbite
            * (
                1 - np.exp(-4.5 * p)
            )
            /
            (
                1 - np.exp(-4.5)
            )
        )

        # Vitesse progressive
        self.vitesse = (
            vitesse_orbitale
            * np.sin(
                p * np.pi / 2
            ) ** 1.35
        )

        # Masse
        self.masse = (
            masse_initiale
            - (
                masse_initiale
                - masse_finale
            )
            * p
        )

        self.carburant = (
            carburant_initial
            * (1 - p)
        )

        # ----------------------------------------------------
        # COORDONNEES 2D (VUE DE PROFIL)
        # ----------------------------------------------------
        # Repère centré sur la Terre :
        #   x = distance horizontale le long de l'arc (vers la droite)
        #   y = distance verticale (le site de lancement est en haut, x = 0)
        # La composante z de l'ancienne vue 3D (hors du plan de profil)
        # n'est plus utilisée, donc l'inclinaison orbitale n'influe plus
        # sur le tracé ; elle reste utilisée dans l'interface.

        R = self.R_TERRE / 1000

        # Rayon d'affichage (altitude dilatée par ECHELLE_ALTITUDE)
        rayon = (
            R
            + self.altitude * ECHELLE_ALTITUDE
        )

        angle_autour_terre = (
            np.radians(38)
            * p ** 1.45
        )

        self.angle_max = float(
            angle_autour_terre[-1]
        )

        self.x = (
            rayon
            * np.sin(
                angle_autour_terre
            )
        )

        self.y = (
            rayon
            * np.cos(
                angle_autour_terre
            )
        )

    # ========================================================
    # TERRE 2D (mise à jour des données, sans rien recréer)
    # ========================================================

    def dessiner_terre(self):

        R = self.R_TERRE / 1000

        altitude_orbite = self.altitude[-1]

        rayon_orbite = (
            R
            + altitude_orbite * ECHELLE_ALTITUDE
        )

        # ----------------------------------------------------
        # ORBITE CIBLE
        # ----------------------------------------------------

        theta = np.linspace(
            0,
            2 * np.pi,
            720
        )

        self.ligne_orbite.set_data(
            rayon_orbite * np.sin(theta),
            rayon_orbite * np.cos(theta)
        )

        # ----------------------------------------------------
        # TRAJECTOIRE COMPLETE + SITE DE LANCEMENT
        # ----------------------------------------------------

        self.ligne_trajectoire.set_data(
            self.x,
            self.y
        )

        self.point_depart.set_data(
            [self.x[0]],
            [self.y[0]]
        )

        # ----------------------------------------------------
        # EMPRISE DE LA VUE : arc terrestre + orbite autour de la trajectoire
        # ----------------------------------------------------

        angles = np.linspace(
            -np.radians(7),
            self.angle_max + np.radians(12),
            120
        )

        xs = np.concatenate((
            R * np.sin(angles),
            rayon_orbite * np.sin(angles)
        ))

        ys = np.concatenate((
            R * np.cos(angles),
            rayon_orbite * np.cos(angles)
        ))

        self._vue = (
            xs.min(),
            xs.max(),
            ys.min(),
            ys.max()
        )

        self._ajuster_vue()

        # Un seul redessin complet : le fond sera remis en cache
        self.blit_trajectoire.invalider()
        self.canvas2d.draw_idle()

    # ========================================================
    # GRAPHIQUES
    # ========================================================

    def preparer_graphiques(self):

        for ax in [
            self.ax_altitude,
            self.ax_vitesse,
            self.ax_masse
        ]:

            ax.clear()

            ax.set_facecolor(
                "#06192a"
            )

            ax.tick_params(
                colors="#adc2d2",
                labelsize=8
            )

            for spine in ax.spines.values():
                spine.set_color(
                    "#183b53"
                )

            ax.grid(
                alpha=0.15
            )

        # ----------------------------------------------------

        self.ax_altitude.set_title(
            "Altitude (km)",
            color="white",
            fontsize=9
        )

        self.ax_vitesse.set_title(
            "Vitesse (m/s)",
            color="white",
            fontsize=9
        )

        self.ax_masse.set_title(
            "Masse (kg)",
            color="white",
            fontsize=9
        )

        self.ax_altitude.plot(
            self.temps,
            self.altitude,
            color="#ff8500"
        )

        self.ax_vitesse.plot(
            self.temps,
            self.vitesse,
            color="#38aaff"
        )

        self.ax_masse.plot(
            self.temps,
            self.masse,
            color="#65e69a"
        )

        # Curseurs
        self.ligne_altitude = self.ax_altitude.axvline(
            0,
            color="white",
            linestyle="--",
            alpha=0.7
        )

        self.ligne_vitesse = self.ax_vitesse.axvline(
            0,
            color="white",
            linestyle="--",
            alpha=0.7
        )

        self.ligne_masse = self.ax_masse.axvline(
            0,
            color="white",
            linestyle="--",
            alpha=0.7
        )

        self.figure_stats.tight_layout()

        # Les curseurs deviennent les seuls éléments animés de ce canvas
        self.blit_stats.vider()

        for curseur in (
            self.ligne_altitude,
            self.ligne_vitesse,
            self.ligne_masse
        ):
            self.blit_stats.ajouter(curseur)

        self.canvas_stats.draw_idle()

    # ========================================================
    # CLIC SUR TRAJECTOIRE
    # ========================================================

    def clic_trajectoire(self, event):

        if event.x is None or event.y is None:
            return

        if not hasattr(self, "x"):
            return

        # Coordonnées 2D -> pixels écran (simple transformation, sans projection 3D)
        points = self.ax2d.transData.transform(
            np.column_stack(
                (
                    self.x,
                    self.y
                )
            )
        )

        distances = np.hypot(
            points[:, 0] - event.x,
            points[:, 1] - event.y
        )

        indice = int(
            np.argmin(distances)
        )

        if distances[indice] < 35:

            self.arreter_animation()

            self.afficher_etat(
                indice
            )

    # ========================================================
    # OUTIL : MAJ D'UN LABEL SEULEMENT SI LE TEXTE CHANGE
    # ========================================================

    def maj_carte(self, label, texte):

        if self._textes_cartes.get(label) != texte:

            self._textes_cartes[label] = texte

            label.configure(
                text=texte
            )

    # ========================================================
    # AFFICHER ETAT
    # ========================================================

    def afficher_etat(self, indice):

        t = self.temps[indice]
        altitude = self.altitude[indice]
        vitesse = self.vitesse[indice]
        masse = self.masse[indice]
        carburant = self.carburant[indice]

        progression = (
            indice
            / (
                len(self.temps) - 1
            )
        )

        if progression < 0.08:
            phase = "Décollage"

        elif progression < 0.78:
            phase = "Ascension"

        else:
            phase = "Mise en orbite"

        # ----------------------------------------------------
        # CARTES
        # ----------------------------------------------------

        self.maj_carte(
            self.card_temps,
            f"{t:.1f} s"
        )

        self.maj_carte(
            self.card_altitude,
            f"{altitude:.1f} km"
        )

        self.maj_carte(
            self.card_vitesse,
            f"{vitesse:,.0f} m/s"
        )

        self.maj_carte(
            self.card_masse,
            f"{masse:,.0f} kg"
        )

        self.maj_carte(
            self.card_carburant,
            f"{carburant:,.0f} kg"
        )

        self.maj_carte(
            self.card_phase,
            phase
        )

        # ----------------------------------------------------
        # FUSEE + TRACE PARCOURUE (mise à jour des données uniquement)
        # ----------------------------------------------------

        position = [
            [
                self.x[indice],
                self.y[indice]
            ]
        ]

        self.marqueur_fusee.set_offsets(
            position
        )

        self.halo_fusee.set_offsets(
            position
        )

        self.trace_parcourue.set_data(
            self.x[:indice + 1],
            self.y[:indice + 1]
        )

        # ----------------------------------------------------
        # CURSEURS GRAPHIQUES
        # ----------------------------------------------------

        self.ligne_altitude.set_xdata(
            [t, t]
        )

        self.ligne_vitesse.set_xdata(
            [t, t]
        )

        self.ligne_masse.set_xdata(
            [t, t]
        )

        # ----------------------------------------------------
        # AFFICHAGE : blitting (redessin des seuls éléments animés)
        # ----------------------------------------------------

        self.blit_trajectoire.actualiser()
        self.blit_stats.actualiser()

    # ========================================================
    # ANIMATION
    # ========================================================

    def arreter_animation(self):

        self.animation_active = False

        if self.after_id is not None:

            try:
                self.after_cancel(
                    self.after_id
                )
            except Exception:
                pass

            self.after_id = None

    def demarrer_animation(self):

        # Empêche deux boucles d'animation simultanées
        self.arreter_animation()

        self.lancer_analyse()

        self.animation_active = True
        self.indice_animation = -1

        # Le chronomètre démarre APRÈS le calcul et le redessin initial
        self.t_debut_animation = time.perf_counter()

        self.animer()

    def animer(self):

        self.after_id = None

        if not self.animation_active:
            return

        dernier = len(self.temps) - 1

        # Indice déduit du temps réel écoulé : durée constante,
        # même si certaines images sont sautées.
        fraction = min(
            (time.perf_counter() - self.t_debut_animation)
            / DUREE_ANIMATION_S,
            1.0
        )

        indice = int(
            round(fraction * dernier)
        )

        if indice != self.indice_animation:

            self.indice_animation = indice

            self.afficher_etat(
                indice
            )

        if fraction >= 1.0:

            self.animation_active = False
            return

        self.after_id = self.after(
            INTERVALLE_FRAME_MS,
            self.animer
        )

    # ========================================================
    # RESET
    # ========================================================

    def reinitialiser(self):

        self.arreter_animation()

        self.lancer_analyse()

        self.afficher_etat(0)

    # ========================================================
    # FERMETURE
    # ========================================================

    def fermer(self):

        self.arreter_animation()

        self.quit()
        self.destroy()


# ============================================================
# DEMARRAGE
# ============================================================

if __name__ == "__main__":

    app = Application()
    app.mainloop()