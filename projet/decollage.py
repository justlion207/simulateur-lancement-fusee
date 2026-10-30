# -*- coding: utf-8 -*-
"""
Created on Tue Sep 29 08:47:44 2026

@author: tristan dupuis  
"""


# PROGRAMME 1 : ANALYSE DU DECOLLAGE

G0 = 9.81


# Fonction 1 : Calculer le poids
def calculer_poids(masse):

    if masse <= 0:
        raise ValueError("La masse doit être positive.")

    poids = masse * G0

    return poids


# Fonction 2 : Calculer la poussée totale
def calculer_poussee(nb_moteurs, poussee_moteur):

    if nb_moteurs < 1 or poussee_moteur < 0:
        raise ValueError("Paramètres des moteurs invalides.")

    poussee_totale = nb_moteurs * poussee_moteur

    return poussee_totale


# Fonction 3 : Vérifier le décollage
def verifier_decollage(poussee, poids):

    if poussee > poids:
        return True

    return False


# Fonction 4 : Calculer l'accélération initiale
def calculer_acceleration(poussee, poids, masse):

    if masse <= 0:
        raise ValueError("La masse doit être positive.")

    force_resultante = poussee - poids

    acceleration = force_resultante / masse

    return acceleration

if __name__ == "__main__":
    test1 = calculer_poids(20000)
    print(test1)
    test2 = calculer_poussee(3,400)
    print(test2)
    test3 = verifier_decollage(6000,200)
    print(test3)
    test4 = calculer_acceleration(566,554,655)
    print(test4)




