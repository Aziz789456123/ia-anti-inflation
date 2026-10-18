"""Tests de l'essence, des véhicules, des instructions GPS et des liens (sans connexion)."""

from moteur import carburant as carb
from moteur import vehicules as veh
from moteur.geo import Point, instruction_fr, itineraire, matrice
from moteur.liens import lien_google_maps, lien_waze
from moteur.localisation import lire_geolocalisation

CENTRE = Point(47.2380, 6.0243)


def test_stations_de_secours_triees_par_distance():
    stations, info = carb.stations_autour(CENTRE, rayon_km=10, en_ligne=False)
    assert not info["direct"] and stations
    distances = [s.distance_km for s in stations]
    assert distances == sorted(distances)
    assert carb.moins_chere(stations, "SP95-E10") is not None


def test_vehicules_ademe():
    assert "Renault" in veh.marques()
    v = veh.vehicule("Renault", "CLIO", "Essence")
    assert 4 < v.conso_ville < 9 and v.unite == "L/100 km"
    assert veh.vehicule("Renault", "ZOE", "Électrique").electrique
    assert veh.vehicule_type(veh.categories()[1], "Diesel").conso_ville > 0


def test_instructions_en_francais():
    assert instruction_fr({"maneuver": {"type": "turn", "modifier": "right"}, "name": "Rue de Dole"}) == \
        "Tournez à droite sur Rue de Dole"
    assert instruction_fr({"maneuver": {"type": "roundabout", "exit": 2}, "name": ""}) == "Au rond-point, prenez la 2e sortie"
    assert instruction_fr({"maneuver": {"type": "arrive", "modifier": "left"}}) == "Vous êtes arrivé (sur votre gauche)"


def test_estimation_sans_connexion():
    a, b = CENTRE, Point(47.2285, 5.9850)
    km, mn, source = matrice([a, b], en_ligne=False)
    assert source == "estimation" and km[0][1] > 0 and km[1][0] == km[0][1]
    etapes = itineraire([a, b, a], en_ligne=False)
    assert len(etapes) == 2 and etapes[0].trace[0] == (a.lat, a.lon)


def test_liens_gps():
    url = lien_google_maps(CENTRE, [Point(47.2285, 5.985)])
    assert url.startswith("https://www.google.com/maps/dir/?api=1") and "waypoints=" in url
    assert lien_waze(Point(47.2, 6.0)) == "https://waze.com/ul?ll=47.2,6.0&navigate=yes"


def test_lecture_geolocalisation_navigateur():
    point, precision = lire_geolocalisation({"coords": {"latitude": 47.24, "longitude": 6.02, "accuracy": 15}})
    assert (point.lat, point.lon, precision) == (47.24, 6.02, 15)
    assert lire_geolocalisation({"error": "refus"}) is None
    assert lire_geolocalisation(None) is None
