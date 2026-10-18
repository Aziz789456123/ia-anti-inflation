"""Tests du moteur de décision (sans connexion internet : distances estimées)."""

import pytest

from moteur import Magasin, Point, Reseau, Transport, recommander
from moteur.donnees import charger_catalogue, charger_magasins, charger_quartiers, contenance, table_prix

MAISON = Point(47.24, 6.02, "maison")
A = Magasin("A", "EnseigneA", "Magasin A", "Discount", Point(47.24, 6.03, "A"))   # tout près
B = Magasin("B", "EnseigneB", "Magasin B", "Discount", Point(47.24, 6.04, "B"))   # un peu plus loin
PRIX = {"pates": {"A": 1.00, "B": 1.20}, "cafe": {"A": 5.00, "B": 3.00}}


def reco(liste, magasins, transport, seuil=5, depart=MAISON):
    return recommander(liste, PRIX, magasins, depart, transport, seuil=seuil,
                       reseau=Reseau(depart, magasins, en_ligne=False))


def test_on_reste_au_plus_proche_si_l_autre_ne_fait_pas_gagner_assez():
    r = reco({"cafe": 1}, [A, B], Transport.sans_voiture(), seuil=5)
    assert r.plus_proche.magasins[0].id == "A"
    assert r.gain_de_temps.magasins[0].id == "B"      # B est 2 € moins cher…
    assert r.conseil.magasins[0].id == "A"            # … mais c'est sous le seuil de 5 €


def test_deux_magasins_si_le_gain_depasse_le_seuil():
    r = reco({"pates": 30, "cafe": 5}, [A, B], Transport.sans_voiture(), seuil=5)
    assert r.conseil.nb_magasins == 2
    assert r.conseil.affectation == {"pates": "A", "cafe": "B"}


def test_le_cout_de_l_essence_peut_changer_le_choix():
    loin = Magasin("B", "EnseigneB", "Magasin B", "Discount", Point(47.40, 6.30, "B"))  # environ 35 km
    a_pied = reco({"cafe": 1}, [A, loin], Transport.sans_voiture(), seuil=0)
    voiture = reco({"cafe": 1}, [A, loin], Transport.voiture(6.0, 2.0), seuil=0)
    assert a_pied.conseil.magasins[0].id == "B"
    assert voiture.conseil.magasins[0].id == "A"


def test_cout_et_litres_du_trajet():
    s = reco({"cafe": 1}, [A], Transport.voiture(5.0, 2.0)).conseil
    assert s.energie == pytest.approx(s.distance_km * 0.05)
    assert s.cout_trajet == pytest.approx(round(s.distance_km * 0.05 * 2.0, 2))


def test_liste_vide_refusee():
    with pytest.raises(ValueError):
        reco({}, [A, B], Transport.voiture())


def test_contenances():
    assert contenance("500G") == 500
    assert contenance("1.5L") == 1500
    assert contenance("50 cl") == 500
    assert contenance("720 g") == 720
    assert contenance(None, 0.23, "kg") == 230
    assert contenance("La boite") is None


def test_catalogue_reel_et_paquets():
    catalogue = {p.nom: p for p in charger_catalogue()}
    assert len(catalogue) >= 15
    spaghetti = catalogue["Spaghetti"]
    assert spaghetti.offres["Aldi"].nb_paquets == 2          # Aldi vend des paquets de 500 g
    assert spaghetti.offres["Lidl"].nb_paquets == 1
    assert spaghetti.offres["Aldi"].prix == pytest.approx(2 * spaghetti.offres["Aldi"].prix_paquet)


def test_recommandation_sur_les_vraies_donnees():
    magasins, quartiers = charger_magasins(), charger_quartiers()
    prix = table_prix(charger_catalogue(), magasins)
    depart = quartiers["Planoise"]
    r = recommander({"Spaghetti": 1, "Café en grains": 1}, prix, magasins, depart, Transport.voiture(6, 2.1),
                    seuil=2, reseau=Reseau(depart, magasins, en_ligne=False))
    assert r.conseil.total > 0
    assert set(r.par_enseigne) == {"Lidl", "Aldi"}
