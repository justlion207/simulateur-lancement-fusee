def verifier_meteo(self):
        # Fonction simulée ou à relier à votre logique d'API météo
        self.meteo_resultat.configure(state="normal")
        self.meteo_resultat.delete("1.0", "end")
        
        site = self.meteo_site.get()
        date = self.meteo_date.get()
        
        if not date:
            self.meteo_resultat.insert("1.0", "Erreur : Veuillez entrer une date valide.")
            self.meteo_resultat.configure(state="disabled")
            return
            
        texte_resultat = f"--- Données météorologiques pour {site} le {date} ---\n\n"
        texte_resultat += "● Statut de lancement : GO (Conditions Nominales)\n\n"
        texte_resultat += "▪ Vent au sol : 12 km/h (Seuil max : 50 km/h)\n"
        texte_resultat += "▪ Température : 26°C (Seuil : 2°C - 35°C)\n"
        texte_resultat += "▪ Précipitations : 0 mm\n"
        texte_resultat += "▪ Risque orageux : Faible\n\n"
        texte_resultat += "Conclusion : Les conditions sont favorables pour le décollage."
        
        self.meteo_resultat.insert("1.0", texte_resultat)
        self.meteo_resultat.configure(state="disabled")