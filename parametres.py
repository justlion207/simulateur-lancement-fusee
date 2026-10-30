"""Paramètres centraux du scénario pédagogique (unités SI).

Les valeurs SLS sont des ordres de grandeur tirés des diapositives.
La masse à vide, le débit, Cd et la loi de bascule sont des hypothèses
de simulation, et NON des données NASA certifiées.
"""
# Constantes physiques : définies dans trajectoire.py (MU, R_TERRE, RHO0...)
MASSE_INITIALE = 2_608_000.0   
POUSSEE_TOTALE = 39_100_000.0   
MASSE_VIDE = 850_000.0       
CARBURANT_INITIAL = MASSE_INITIALE - MASSE_VIDE
DUREE_PROPULSION_REFERENCE = 500.0  
CONSOMMATION = CARBURANT_INITIAL / DUREE_PROPULSION_REFERENCE
DIAMETRE = 8.4                
CD = 0.3                      
SURFACE = 3.141592653589793 * (DIAMETRE / 2)**2 
ALTITUDE_CIBLE = 200_000.0   
DUREE_SIMULATION = 900.0      
DT = 0.5                      
DEBUT_BASCULE = 15.0          
FIN_BASCULE = 240.0           
TOLERANCE_VITESSE = 0.05       
