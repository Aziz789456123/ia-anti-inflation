"""Tests du « Magic Scan » (sans appel à l'IA)."""

import base64
import io

from PIL import Image

from moteur.donnees import charger_catalogue
from moteur.scan import analyser_reponse, consigne, lire_texte, preparer_image

CATALOGUE = charger_catalogue()
NOMS = [p.nom for p in CATALOGUE]
LIBELLES = {p.nom: p.libelle for p in CATALOGUE}


def test_reponse_de_l_ia_rattachee_au_catalogue():
    reponse = """Voici : {"lignes": [
        {"lu": "2 paquets de pâtes", "produit": "Spaghetti (1 kg)", "quantite": 2},
        {"lu": "thon", "produit": "Thon albacore au naturel", "quantite": 1},
        {"lu": "lait", "produit": null, "quantite": 2},
        {"lu": "riz", "produit": "Riz thaï (1 kg)", "quantite": "1"}]}"""
    res = analyser_reponse(reponse, NOMS, LIBELLES)
    assert res.reconnus == {"Spaghetti": 2, "Thon albacore au naturel": 1, "Riz thaï": 1}
    assert res.non_reconnus == ["lait"]
    assert len(res.lignes_lues) == 4


def test_produit_invente_par_l_ia_ignore():
    res = analyser_reponse('{"lignes": [{"lu": "caviar", "produit": "Caviar", "quantite": 1}]}', NOMS, LIBELLES)
    assert res.reconnus == {} and res.non_reconnus == ["caviar"]


def test_liste_tapee_au_clavier():
    res = lire_texte("2 paquets de pâtes\nriz, thon x3\nhuile\ncafé en grains\nlait\neau 6", NOMS)
    assert res.reconnus["Spaghetti"] == 2
    assert res.reconnus["Thon albacore au naturel"] == 3
    assert res.reconnus["Huile de tournesol"] == 1
    assert res.reconnus["Café en grains"] == 1
    assert res.reconnus["Eau de source"] == 6
    assert res.non_reconnus == ["lait"]


def test_consigne_contient_le_catalogue():
    texte = consigne([LIBELLES[n] for n in NOMS])
    assert "Spaghetti (1 kg)" in texte and '"lignes"' in texte


def test_preparation_de_la_photo():
    tampon = io.BytesIO()
    Image.new("RGB", (4000, 3000), "white").save(tampon, format="PNG")
    donnees, type_media = preparer_image(tampon.getvalue())
    image = Image.open(io.BytesIO(base64.b64decode(donnees)))
    assert type_media == "image/jpeg" and max(image.size) <= 1568
