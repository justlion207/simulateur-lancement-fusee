try:
    import pyi_splash
except ImportError:
    pyi_splash = None
from PIL import Image
import sys
import os
import math
import numbers
import threading
import gc

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd

import parametres as p
from main import lancer_simulation
from optimisation import analyser_orbite, optimiser_parametres, MAX_ESSAIS, fmt
from meteo import COORDONNEES, analyser_meteo
from verification import convertir_nombre, verifier_et_convertir
from graphique import (
    afficher_altitude,
    afficher_vitesse,
    afficher_masse,
    afficher_trajectoire
)

# ============================================================
# CONFIGURATION GENERALE & OUTILS
# ============================================================
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


def chemin_ressource(chemin_relatif):
    """Trouve les ressources que ce soit en Python ou compilé en .exe"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, chemin_relatif)


# Couleurs des champs
COULEUR_CHAMP_NORMAL = {"fg_color": "#FFFFFF", "border_color": "#D1D5DB"}
COULEUR_CHAMP_ERREUR = {"fg_color": "#FEE2E2", "border_color": "#EF4444"}

# Styles pastel de la zone météo
STYLES_METEO = {
    "neutre": {"fg_color": "#F1F5F9", "text_color": "#475569", "border_color": "#CBD5E1"},
    "go":     {"fg_color": "#D1E7DD", "text_color": "#0F5132", "border_color": "#BADBCC"},
    "nogo":   {"fg_color": "#F8D7DA", "text_color": "#842029", "border_color": "#F5C2C7"},
    "alerte": {"fg_color": "#FFF3CD", "text_color": "#856404", "border_color": "#FFEEBA"},
}

# ============================================================
# CLASSE PRINCIPALE (CONTRÔLEUR ET NAVIGATION)
# ============================================================
class InterfaceFusee(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("IPSA - Simulation Orbitale")
        self.geometry("1450x850")
        self.minsize(1200, 750)

        try:
            self.iconbitmap(chemin_ressource("icone.ico"))
        except Exception:
            pass

        # Variables partagées
        self.donnees_simulation = None
        self.texte_meteo_rapport = ""
        self.parametres_simulation = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # 1. Menu latéral
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color="#F3F4F6")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(4, weight=1)

        try:
  
            image_logo = Image.open(chemin_ressource("logo.png"))
            largeur = 75                                   # largeur voulue dans la sidebar
            hauteur = int(largeur * image_logo.height / image_logo.width)   # garde les proportions
            self.logo = ctk.CTkImage(light_image=image_logo, size=(largeur, hauteur))
            ctk.CTkLabel(self.sidebar, image=self.logo, text="").grid(row=0, column=0, padx=20, pady=(30, 30))
        except Exception:
            # Si l'image est introuvable, on garde le texte
            ctk.CTkLabel(
                self.sidebar, text="IPSA\nSPACE",
                font=ctk.CTkFont(size=24, weight="bold"), text_color="#1E3A8A"
            ).grid(row=0, column=0, padx=20, pady=(30, 30))

        self.boutons_nav = {}
        entrees = [
            ("PageAccueil", "🏠 Accueil", 1),
            ("PageParametres", "⚙️ Paramètres & Vol", 2),
            ("PageResultats", "📊 Résultats & Bilan", 3),
        ]
        for nom_page, texte, ligne in entrees:
            bouton = ctk.CTkButton(
                self.sidebar, text=texte, fg_color="transparent", text_color="black",
                hover_color="#E5E7EB", anchor="w", font=ctk.CTkFont(size=15),
                command=lambda n=nom_page: self.afficher_page(n)
            )
            bouton.grid(row=ligne, column=0, pady=5, padx=20, sticky="ew")
            self.boutons_nav[nom_page] = bouton

        # 2. Zone de contenu
        self.conteneur_pages = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=0)
        self.conteneur_pages.grid(row=0, column=1, sticky="nsew")
        self.conteneur_pages.grid_rowconfigure(0, weight=1)
        self.conteneur_pages.grid_columnconfigure(0, weight=1)

        self.pages = {}
        for PageClass in (PageAccueil, PageParametres, PageResultats):
            page = PageClass(parent=self.conteneur_pages, controleur=self)
            self.pages[PageClass.__name__] = page
            page.grid(row=0, column=0, sticky="nsew")

        self.afficher_page("PageAccueil")

        self.protocol("WM_DELETE_WINDOW", self.fermer)

        try:
            if pyi_splash:
                pyi_splash.close()
        except Exception:
            pass

    def afficher_page(self, nom_page):
        for nom, bouton in self.boutons_nav.items():
            bouton.configure(fg_color="#D1DBE8" if nom == nom_page else "transparent")
        self.pages[nom_page].tkraise()

    def fermer(self):
        page = self.pages.get("PageResultats")
        if page is not None:
            page.annuler = True
            thread = getattr(page, "thread_opt", None)
            if thread is not None and thread.is_alive():
                thread.join(timeout=15)  # le calcul s'arrête dès la fin de la simulation en cours
        gc.enable()
        plt.close("all")
        self.destroy()


# ============================================================
# PAGE 1 : ACCUEIL
# ============================================================
class PageAccueil(ctk.CTkFrame):
    def __init__(self, parent, controleur):
        super().__init__(parent, fg_color="transparent")
        self.controleur = controleur

        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="Bienvenue dans le centre de contrôle",
            font=ctk.CTkFont(size=36, weight="bold"), text_color="#1F2937"
        ).grid(row=1, column=0, pady=(0, 10))

        ctk.CTkLabel(
            self, text="Préparez vos paramètres, vérifiez la météo et analysez l'orbite.",
            font=ctk.CTkFont(size=18), text_color="#6B7280"
        ).grid(row=2, column=0, pady=(0, 50))

        ctk.CTkButton(
            self, text="NOUVELLE SIMULATION", height=50, width=250, corner_radius=25,
            fg_color="#3B82F6", hover_color="#2563EB", font=ctk.CTkFont(size=16, weight="bold"),
            command=lambda: controleur.afficher_page("PageParametres")
        ).grid(row=3, column=0)


# ============================================================
# PAGE 2 : PARAMÈTRES & MÉTÉO
# ============================================================
class PageParametres(ctk.CTkFrame):
    def __init__(self, parent, controleur):
        super().__init__(parent, fg_color="transparent")
        self.controleur = controleur
        self.champs = {}
        self.meteo_validee = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self, text="Configuration du Lancement",
            font=ctk.CTkFont(size=28, weight="bold"), text_color="#111827"
        ).grid(row=0, column=0, columnspan=2, pady=(30, 20))

        # --- PANNEAU GAUCHE : TECHNIQUE ---
        cadre_tech = ctk.CTkFrame(
            self, fg_color="#F9FAFB", border_width=1, border_color="#E5E7EB", corner_radius=10
        )
        cadre_tech.grid(row=1, column=0, sticky="nsew", padx=30, pady=10)

        ctk.CTkLabel(
            cadre_tech, text="Paramètres de la fusée",
            font=ctk.CTkFont(size=18, weight="bold"), text_color="#374151"
        ).pack(pady=(10, 20))

        self.parametres_interface = [
            ("masse", "Masse initiale (kg)", p.MASSE_INITIALE),
            ("masse_vide", "Masse à vide (kg)", p.MASSE_VIDE),
            ("poussee", "Poussée totale (N)", p.POUSSEE_TOTALE),
            ("consommation", "Consommation (kg/s)", p.CONSOMMATION),
            ("diametre", "Diamètre de la fusée (m)", p.DIAMETRE),
            ("cd", "Coefficient de traînée", p.CD),
            ("duree", "Durée de simulation (s)", p.DUREE_SIMULATION),
            ("dt", "Pas de temps (s)", p.DT),
            ("debut_bascule", "Début de bascule (s)", p.DEBUT_BASCULE),
            ("fin_bascule", "Fin de bascule (s)", p.FIN_BASCULE),
            ("altitude_cible", "Altitude cible (km)", p.ALTITUDE_CIBLE / 1000),
        ]
        self.noms_parametres = {cle: nom for cle, nom, _ in self.parametres_interface}

        grille = ctk.CTkFrame(cadre_tech, fg_color="transparent")
        grille.pack(fill="x", padx=20)
        grille.grid_columnconfigure((0, 1), weight=1, uniform="colonnes")

        for i, (cle, nom, valeur) in enumerate(self.parametres_interface):
            cellule = ctk.CTkFrame(grille, fg_color="transparent")
            cellule.grid(row=i // 2, column=i % 2, sticky="ew", padx=8, pady=6)
            ctk.CTkLabel(cellule, text=nom, anchor="w", text_color="#4B5563").pack(fill="x")
            champ = ctk.CTkEntry(cellule, height=34, text_color="black", **COULEUR_CHAMP_NORMAL)
            champ.insert(0, str(valeur))
            champ.pack(fill="x")
            self.champs[cle] = champ

        cadre_boutons_tech = ctk.CTkFrame(cadre_tech, fg_color="transparent")
        cadre_boutons_tech.pack(fill="x", pady=20, padx=20)
        ctk.CTkButton(
            cadre_boutons_tech, text="Importer Excel", fg_color="#10B981", hover_color="#059669",
            command=self.importer_excel
        ).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(
            cadre_boutons_tech, text="Réinitialiser", fg_color="#9CA3AF", hover_color="#6B7280",
            command=self.reinitialiser
        ).pack(side="right", expand=True, padx=5)

        # --- PANNEAU DROIT : MÉTÉO ---
        cadre_meteo = ctk.CTkFrame(
            self, fg_color="#F9FAFB", border_width=1, border_color="#E5E7EB", corner_radius=10
        )
        cadre_meteo.grid(row=1, column=1, sticky="nsew", padx=30, pady=10)

        ctk.CTkLabel(
            cadre_meteo, text="Météorologie & Environnement",
            font=ctk.CTkFont(size=18, weight="bold"), text_color="#374151"
        ).pack(pady=(10, 20))

        # Le bouton de décollage est packé en premier pour rester toujours visible en bas
        self.bouton_lancer = ctk.CTkButton(
            cadre_meteo, text="DÉCOLLAGE", height=60, corner_radius=30,
            fg_color="#EF4444", hover_color="#B91C1C", font=ctk.CTkFont(size=18, weight="bold"),
            command=self.valider_et_simuler
        )
        self.bouton_lancer.pack(side="bottom", fill="x", padx=40, pady=30)

        self.champ_lieu = ctk.CTkComboBox(
            cadre_meteo, height=40, fg_color="#FFFFFF", border_color="#D1D5DB", text_color="black",
            dropdown_fg_color="#FFFFFF", dropdown_text_color="black",
            values=list(COORDONNEES.keys())
        )
        self.champ_lieu.set("Kourou (Guyane)")
        self.champ_lieu.pack(fill="x", padx=30, pady=10)

        self.champ_date = ctk.CTkEntry(
            cadre_meteo, height=40, placeholder_text="Date (JJ/MM/AAAA) — ex : 15/08/2026",
            text_color="black", **COULEUR_CHAMP_NORMAL
        )
        self.champ_date.pack(fill="x", padx=30, pady=10)

        ctk.CTkButton(
            cadre_meteo, text="Vérifier la Météo", fg_color="#3B82F6", hover_color="#2563EB",
            height=40, command=self.tester_meteo
        ).pack(pady=15, fill="x", padx=30)

        self.zone_meteo = ctk.CTkTextbox(
            cadre_meteo, height=200, font=ctk.CTkFont(size=14, weight="bold"), border_width=2
        )
        self.zone_meteo.pack(fill="both", expand=True, padx=30, pady=10)
        self.afficher_meteo("En attente des données météorologiques...", "neutre")

    # ========================================================
    # OUTILS D'AFFICHAGE
    # ========================================================
    def afficher_meteo(self, texte, style):
        self.zone_meteo.configure(state="normal", **STYLES_METEO[style])
        self.zone_meteo.delete("1.0", "end")
        self.zone_meteo.insert("1.0", texte)
        self.zone_meteo.configure(state="disabled")

    # ========================================================
    # RÉCUPÉRATION ET VALIDATION DES PARAMÈTRES
    # ========================================================
    def saisir_parametres(self):
        valeurs = {
            cle: convertir_nombre(champ.get(), self.noms_parametres.get(cle, cle))
            for cle, champ in self.champs.items()
        }
        valeurs["lieu"] = self.champ_lieu.get()
        valeurs["date"] = self.champ_date.get().strip()
        return verifier_et_convertir(valeurs)

    # ========================================================
    # MÉTÉO
    # ========================================================
    def tester_meteo(self):
        """Bouton « Vérifier la Météo » : affiche le bulletin et propose une nouvelle date si NO GO."""
        date_str = self.champ_date.get().strip()
        lieu = self.champ_lieu.get()

        if not date_str:
            self.afficher_meteo("⚠️ Attention : veuillez entrer une date (JJ/MM/AAAA).", "alerte")
            self.meteo_validee = False
            return False

        self.afficher_meteo("⏳ Récupération des données météo...", "neutre")
        self.update_idletasks()

        try:
            go, bulletin, nouvelle_date, _ = analyser_meteo(date_str, lieu)
        except ValueError as e:
            self.afficher_meteo(f"⚠️ ERREUR\n\n{e}", "alerte")
            self.meteo_validee = False
            return False

        if go:
            self.afficher_meteo(bulletin, "go")
            self.controleur.texte_meteo_rapport = bulletin
            self.meteo_validee = True
        else:
            suite = (
                f"\n\n📅 Prochaine fenêtre de tir favorable : {nouvelle_date}"
                if nouvelle_date else "\n\nAucune fenêtre favorable trouvée."
            )
            self.afficher_meteo(bulletin + suite, "nogo")
            self.meteo_validee = False

        return self.meteo_validee

    def verifier_meteo_avant_lancement(self, parametres):
        """
        Lancée automatiquement avec la simulation.
        Retourne le texte du bulletin à inclure dans le rapport,
        ou None si le lancement est annulé.
        """
        date_str = parametres.get("date", "")
        lieu = parametres.get("lieu", "")

        if not date_str:
            self.afficher_meteo("ℹ️ Aucune date renseignée : la météo n'a pas été vérifiée.", "alerte")
            return "Météo non vérifiée (aucune date renseignée)."

        self.afficher_meteo("⏳ Récupération des données météo...", "neutre")
        self.update_idletasks()

        go, bulletin, nouvelle_date, bulletin_nouvelle = analyser_meteo(date_str, lieu)

        if go:
            self.afficher_meteo(bulletin, "go")
            self.meteo_validee = True
            return bulletin

        # NO GO : proposition de report
        self.afficher_meteo(bulletin, "nogo")
        self.meteo_validee = False

        if not nouvelle_date:
            messagebox.showerror(
                "Lancement Interdit",
                bulletin + "\n\nAucune fenêtre de tir favorable n'a été trouvée."
            )
            return None

        question = (
            f"{bulletin}\n\n----------------------------------\n\n"
            f"Une nouvelle fenêtre de tir optimale a été trouvée le : {nouvelle_date}.\n\n"
            "Voulez-vous reprogrammer le lancement à cette date et simuler la trajectoire ?"
        )
        if not messagebox.askyesno("ALERTE : Conditions Météo Défavorables", question):
            self.afficher_meteo(bulletin + "\n\n🚫 Lancement annulé par l'utilisateur.", "nogo")
            return None

        # Report accepté : mise à jour de la date et du bulletin
        self.champ_date.delete(0, "end")
        self.champ_date.insert(0, nouvelle_date)
        parametres["date"] = nouvelle_date
        self.afficher_meteo(bulletin_nouvelle + "✅ STATUT : GO (Lancement reprogrammé)", "go")
        self.meteo_validee = True
        return bulletin_nouvelle + "✅ STATUT : GO (Lancement reprogrammé)"

    # ========================================================
    # LANCEMENT DE LA SIMULATION
    # ========================================================
    def valider_et_simuler(self):
        try:
            parametres = self.saisir_parametres()
        except ValueError as erreur:
            messagebox.showerror("Erreur de paramètres", str(erreur))
            return

        try:
            rapport_meteo = self.verifier_meteo_avant_lancement(parametres)
        except ValueError as erreur:
            self.afficher_meteo(f"⚠️ ERREUR\n\n{erreur}", "alerte")
            messagebox.showerror("Erreur météo", str(erreur))
            return

        if rapport_meteo is None:
            self.controleur.donnees_simulation = None
            return

        try:
            self.bouton_lancer.configure(state="disabled", text="SIMULATION EN COURS...")
            self.update_idletasks()

            resultat = lancer_simulation(parametres=parametres, afficher_graphiques=False)
        except Exception as erreur:
            messagebox.showerror("Erreur de simulation", str(erreur))
            return
        finally:
            self.bouton_lancer.configure(state="normal", text="DÉCOLLAGE")

        if resultat is None:
            self.controleur.donnees_simulation = None
            messagebox.showerror("Décollage impossible", "La poussée est insuffisante pour le décollage.")
            return

        self.controleur.donnees_simulation = resultat
        self.controleur.parametres_simulation = parametres
        self.controleur.texte_meteo_rapport = rapport_meteo
        self.controleur.pages["PageResultats"].afficher_resultats()
        self.controleur.afficher_page("PageResultats")

    # ========================================================
    # IMPORT EXCEL
    # ========================================================
    def importer_excel(self):
        fichier = filedialog.askopenfilename(
            title="Sélectionner un fichier Excel",
            filetypes=[("Fichiers Excel", "*.xlsx *.xls")]
        )
        if not fichier:
            return

        try:
            df = pd.read_excel(fichier)

            # Ordre important : "masse_vide" avant "masse", "dt" avant "duree"
            mots_cles = {
                "masse_vide": ["vide", "masse à vide", "masse a vide"],
                "masse": ["initiale", "masse", "départ"],
                "poussee": ["poussée", "poussee", "force"],
                "consommation": ["consommation", "débit", "debit"],
                "diametre": ["diamètre", "diametre"],
                "cd": ["cd", "traînée", "trainee", "coefficient"],
                "dt": ["dt", "pas de temps"],
                "duree": ["durée", "duree"],
                "debut_bascule": ["début", "debut bascule"],
                "fin_bascule": ["fin", "fin bascule"],
                "altitude_cible": ["cible", "orbite", "altitude"],
            }

            # Remise à blanc des champs
            for champ in self.champs.values():
                champ.delete(0, "end")
                champ.configure(**COULEUR_CHAMP_NORMAL)

            parametres_trouves = set()

            for _, row in df.iterrows():
                texte_ligne = ""
                valeur_num = None

                for col in df.columns:
                    cellule = row[col]
                    if pd.isna(cellule):
                        continue
                    if isinstance(cellule, str):
                        texte_ligne += " " + cellule.lower()
                    elif isinstance(cellule, numbers.Real) and not isinstance(cellule, bool):
                        valeur_num = float(cellule)

                if valeur_num is None:
                    continue

                for cle, synonymes in mots_cles.items():
                    if any(syn in texte_ligne for syn in synonymes):
                        if cle in self.champs:
                            self.champs[cle].delete(0, "end")
                            self.champs[cle].insert(0, str(valeur_num))
                            parametres_trouves.add(cle)
                        break

            cles_manquantes = set(self.champs.keys()) - parametres_trouves

            if cles_manquantes:
                noms_manquants = []
                for cle in cles_manquantes:
                    self.champs[cle].configure(**COULEUR_CHAMP_ERREUR)
                    noms_manquants.append(self.noms_parametres[cle])

                messagebox.showwarning(
                    "Paramètres manquants",
                    "Le fichier a été importé mais il manque des données obligatoires :\n\n- "
                    + "\n- ".join(sorted(noms_manquants))
                    + "\n\nVeuillez les remplir manuellement."
                )
            else:
                messagebox.showinfo(
                    "Importation réussie",
                    "L'importation est terminée.\nTous les paramètres ont été détectés et mis à jour."
                )

        except Exception as e:
            messagebox.showerror("Erreur Excel", f"Impossible de lire le fichier :\n{e}")

    # ========================================================
    # RÉINITIALISATION
    # ========================================================
    def reinitialiser(self):
        for cle, _, valeur in self.parametres_interface:
            self.champs[cle].delete(0, "end")
            self.champs[cle].insert(0, str(valeur))
            self.champs[cle].configure(**COULEUR_CHAMP_NORMAL)

        self.champ_date.delete(0, "end")
        self.champ_lieu.set("Kourou (Guyane)")
        self.afficher_meteo("En attente des données météorologiques...", "neutre")
        self.meteo_validee = False

        self.controleur.donnees_simulation = None
        self.controleur.parametres_simulation = None
        self.controleur.texte_meteo_rapport = ""
        self.controleur.pages["PageResultats"].vider()


# ============================================================
# PAGE 3 : RÉSULTATS
# ============================================================
class PageResultats(ctk.CTkFrame):
    TEXTE_VIDE = "Aucune simulation pour le moment.\n\nConfigurez les paramètres puis cliquez sur « DÉCOLLAGE »."

    def __init__(self, parent, controleur):
        super().__init__(parent, fg_color="transparent")
        self.controleur = controleur
        self.canvas = None
        self.figure = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self, text="Tableau de Bord des Résultats",
            font=ctk.CTkFont(size=28, weight="bold"), text_color="#111827"
        ).grid(row=0, column=0, columnspan=2, pady=(30, 20))

        cadre_rapport = ctk.CTkFrame(
            self, fg_color="#F9FAFB", border_width=1, border_color="#E5E7EB", corner_radius=10
        )
        cadre_rapport.grid(row=1, column=0, sticky="nsew", padx=(30, 15), pady=10)

        self.bandeau = ctk.CTkLabel(
            cadre_rapport, text="", height=44, corner_radius=8, font=ctk.CTkFont(size=15, weight="bold")
        )

        # Zone « valeurs exactes » (affichée seulement si l'orbite n'est pas atteinte)
        self.zone_optim = ctk.CTkFrame(cadre_rapport, fg_color="transparent")
        self.bouton_optim = ctk.CTkButton(
            self.zone_optim, text="🔧 Calculer les valeurs exactes pour atteindre l'orbite",
            height=40, fg_color="#3B82F6", hover_color="#2563EB", command=self.basculer_optimisation
        )
        self.bouton_optim.pack(fill="x")
        self.barre_optim = ctk.CTkProgressBar(self.zone_optim)
        self.label_optim = ctk.CTkLabel(self.zone_optim, text="", text_color="#4B5563", font=ctk.CTkFont(size=12))
        self.bouton_appliquer = ctk.CTkButton(
            self.zone_optim, text="✅ Appliquer ces valeurs aux paramètres",
            height=40, fg_color="#10B981", hover_color="#059669", command=self.appliquer_solution
        )
        self.optim_en_cours = False
        self.annuler = False
        self.solution = None

        self.boite_bilan = ctk.CTkTextbox(
            cadre_rapport, font=ctk.CTkFont(size=14), fg_color="#FFFFFF",
            text_color="black", border_color="#D1D5DB", border_width=1
        )
        self.boite_bilan.pack(fill="both", expand=True, padx=20, pady=20)

        self.cadre_graphiques = ctk.CTkFrame(
            self, fg_color="#F9FAFB", border_width=1, border_color="#E5E7EB", corner_radius=10
        )
        self.cadre_graphiques.grid(row=1, column=1, sticky="nsew", padx=(15, 30), pady=10)

        self.menu_graph = ctk.CTkSegmentedButton(
            self.cadre_graphiques, selected_color="#3B82F6", selected_hover_color="#2563EB",
            values=["Trajectoire", "Altitude", "Vitesse", "Masse"], command=self.changer_graphique
        )
        self.menu_graph.pack(pady=20)
        self.menu_graph.set("Trajectoire")

        self.zone_dessin = ctk.CTkFrame(self.cadre_graphiques, fg_color="transparent")
        self.zone_dessin.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.vider()

    def _detruire_graphique(self):
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
            self.canvas = None
        if self.figure is not None:
            plt.close(self.figure)
            self.figure = None

    def _ecrire_bilan(self, texte):
        self.boite_bilan.configure(state="normal")
        self.boite_bilan.delete("1.0", "end")
        self.boite_bilan.insert("1.0", texte)
        self.boite_bilan.configure(state="disabled")

    def _reinitialiser_zone_optim(self):
        self.zone_optim.pack_forget()
        self.barre_optim.pack_forget()
        self.label_optim.pack_forget()
        self.bouton_appliquer.pack_forget()
        self.bouton_optim.configure(
            state="normal", text="🔧 Calculer les valeurs exactes pour atteindre l'orbite",
            fg_color="#3B82F6", hover_color="#2563EB"
        )
        self.solution = None

    def vider(self):
        self.annuler = True
        self._reinitialiser_zone_optim()
        self.bandeau.pack_forget()
        self._detruire_graphique()
        self._ecrire_bilan(self.TEXTE_VIDE)

    def afficher_resultats(self):
        res = self.controleur.donnees_simulation
        if not res:
            return

        bilan = ""
        if self.controleur.texte_meteo_rapport:
            bilan += self.controleur.texte_meteo_rapport + "\n" + ("-" * 30) + "\n\n"
        bilan += "🚀 PERFORMANCES DE VOL\n\n"
        for nom, valeur in res["bilan"].items():
            bilan += f"• {nom} : {valeur}\n"

        self.annuler = True  # stoppe un éventuel calcul précédent
        self._reinitialiser_zone_optim()
        self.bandeau.pack_forget()

        params = self.controleur.parametres_simulation
        if params:
            try:
                analyse = analyser_orbite(params, res["historique"])
            except Exception as e:
                analyse = None
                bilan += f"\n(Analyse de l'orbite indisponible : {e})\n"

            if analyse:
                bilan += "\n" + ("-" * 30) + "\n\n🎯 ANALYSE DE L'ORBITE\n\n"
                for ligne in analyse["lignes"]:
                    bilan += f"• {ligne}\n"

                if analyse["atteinte"]:
                    self.bandeau.configure(text="✅ Orbite visée atteinte", fg_color="#D1E7DD", text_color="#0F5132")
                    bilan += "\nAucun ajustement nécessaire.\n"
                else:
                    self.bandeau.configure(text="⚠️ Orbite visée non atteinte", fg_color="#FFF3CD", text_color="#856404")
                    bilan += "\n💡 CONSEILS POUR Y ARRIVER\n\n"
                    for i, conseil in enumerate(analyse["conseils"], 1):
                        bilan += f"{i}. {conseil}\n\n"
                    bilan += "👉 Clique sur « Calculer les valeurs exactes » ci-dessous : des réglages vérifiés par simulation te seront proposés.\n"
                    self.zone_optim.pack(side="bottom", fill="x", padx=20, pady=(0, 20), before=self.boite_bilan)
                self.bandeau.pack(fill="x", padx=20, pady=(20, 0), before=self.boite_bilan)

        self._ecrire_bilan(bilan)
        self.menu_graph.set("Trajectoire")
        self.changer_graphique("Trajectoire")

    # ----------------------------------------------------
    # Calcul des valeurs exactes (dans un thread)
    # ----------------------------------------------------
    def basculer_optimisation(self):
        if self.optim_en_cours:
            self.annuler = True
            self.bouton_optim.configure(state="disabled", text="Annulation...")
            return

        params = self.controleur.parametres_simulation
        if not params:
            return

        self.optim_en_cours = True
        self.annuler = False
        self.fini = False
        self.resultat_opt = None
        self.erreur_opt = None
        self.etat_opt = {"essais": 0, "max": MAX_ESSAIS, "cout": None}
        self.solution = None

        self.bouton_appliquer.pack_forget()
        self.bouton_optim.configure(text="⏹ Annuler le calcul", fg_color="#9CA3AF", hover_color="#6B7280")
        self.barre_optim.set(0)
        self.barre_optim.pack(fill="x", pady=(10, 0))
        self.label_optim.configure(text="Démarrage du calcul...")
        self.label_optim.pack(fill="x", pady=(4, 0))

        def progression(n, maxi, cout):
            self.etat_opt.update(essais=n, max=maxi, cout=cout)

        def travail():
            try:
                self.resultat_opt = optimiser_parametres(dict(params), progression, lambda: self.annuler)
            except Exception as e:
                self.erreur_opt = e
            finally:
                self.fini = True

        gc.disable()  # évite que le ramasse-miettes libère des objets Tk depuis le thread de calcul
        self.thread_opt = threading.Thread(target=travail, daemon=True)
        self.thread_opt.start()
        self.after(200, self._suivre_optimisation)

    def _suivre_optimisation(self):
        e = self.etat_opt
        self.barre_optim.set(min(1.0, e["essais"] / e["max"]))
        if e["cout"] is not None:
            ecart = math.sqrt(e["cout"] / 2) * 100
            self.label_optim.configure(
                text=f"Essai {e['essais']}/{e['max']} — écart à l'orbite visée : {ecart:.1f} %"
            )

        if not self.fini:
            self.after(200, self._suivre_optimisation)
            return

        self.optim_en_cours = False
        gc.enable()
        gc.collect()  # nettoyage fait ici, dans le thread principal
        self.bouton_optim.configure(
            state="normal", text="🔧 Recalculer les valeurs exactes", fg_color="#3B82F6", hover_color="#2563EB"
        )
        self.barre_optim.pack_forget()
        self.label_optim.pack_forget()

        if self.erreur_opt:
            messagebox.showerror("Erreur de calcul", str(self.erreur_opt))
            return
        if self.resultat_opt:
            self.afficher_solution(self.resultat_opt)

    def afficher_solution(self, res):
        params = self.controleur.parametres_simulation
        modif, orb = res["modif"], res["orbite"]
        h_km = params["altitude_cible"] / 1000

        noms = {
            "debut_bascule": ("Début de bascule", "s"),
            "fin_bascule": ("Fin de bascule", "s"),
            "masse": ("Masse initiale", "kg"),
        }
        texte = "\n" + ("-" * 30) + "\n\n🔧 VALEURS EXACTES À UTILISER\n\n"
        if res["annule"]:
            texte += "(Calcul interrompu : meilleur résultat trouvé jusque-là)\n\n"

        for cle, (nom, unite) in noms.items():
            if cle in modif:
                nouvelle = f"{modif[cle]:.2f}" if cle != "masse" else fmt(modif[cle])
                ancienne = f"{params[cle]:.2f}" if cle != "masse" else fmt(params[cle])
                texte += f"• {nom} : {nouvelle} {unite}  (actuellement {ancienne} {unite})\n"
        if "masse" not in modif:
            texte += "• Tous les autres paramètres restent inchangés.\n"

        if orb and not orb["echappement"]:
            texte += (
                f"\nRésultat vérifié par simulation :\n"
                f"périgée {fmt(orb['peri'] / 1000, 'km')} / apogée {fmt(orb['apo'] / 1000, 'km')} "
                f"(cible : {fmt(h_km, 'km')})\n"
            )

        if res["succes"]:
            texte += "\n✅ Orbite atteinte avec ces valeurs.\n"
        else:
            texte += (
                "\n⚠️ Aucune combinaison de bascule et de masse initiale ne permet d'atteindre l'orbite avec "
                "cette fusée. Ce sont les meilleures valeurs trouvées : modifie aussi la masse à vide, la "
                "poussée ou la consommation (voir les conseils ci-dessus).\n"
            )

        self.boite_bilan.configure(state="normal")
        self.boite_bilan.insert("end", texte)
        self.boite_bilan.configure(state="disabled")
        try:
            self.boite_bilan.see("end")
        except Exception:
            pass

        self.solution = modif
        self.bouton_appliquer.pack(fill="x", pady=(10, 0))

    def appliquer_solution(self):
        if not self.solution:
            return
        page = self.controleur.pages["PageParametres"]
        for cle, valeur in self.solution.items():
            champ = page.champs[cle]
            champ.delete(0, "end")
            champ.insert(0, str(valeur))
            champ.configure(**COULEUR_CHAMP_NORMAL)
        self.controleur.afficher_page("PageParametres")
        messagebox.showinfo(
            "Valeurs appliquées",
            "Les nouvelles valeurs sont renseignées.\nClique sur DÉCOLLAGE pour relancer la simulation."
        )

    def changer_graphique(self, choix):
        if not self.controleur.donnees_simulation:
            return
        historique = self.controleur.donnees_simulation["historique"]

        self._detruire_graphique()
        temps = [pt["temps"] for pt in historique]

        if choix == "Trajectoire":
            self.figure = afficher_trajectoire([pt["x"] for pt in historique], [pt["y"] for pt in historique])
        elif choix == "Altitude":
            self.figure = afficher_altitude(temps, [pt["altitude"] for pt in historique])
        elif choix == "Vitesse":
            self.figure = afficher_vitesse(temps, [pt["vitesse"] for pt in historique])
        elif choix == "Masse":
            self.figure = afficher_masse(temps, [pt["masse"] for pt in historique])
        else:
            return

        self.canvas = FigureCanvasTkAgg(self.figure, master=self.zone_dessin)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)


# ============================================================
# DÉMARRAGE DU PROGRAMME
# ============================================================
if __name__ == "__main__":
    app = InterfaceFusee()
    try:
        if pyi_splash:
            pyi_splash.update_text("Interface prête !")
            pyi_splash.close()
    except Exception:
        pass
    app.mainloop()