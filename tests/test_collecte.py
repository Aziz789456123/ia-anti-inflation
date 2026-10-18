"""Tests des robots de collecte, sur des extraits de pages (sans connexion)."""

import html
import json

from collecte.aldi import extraire_produit
from collecte.lidl import analyser_lignes, extraire_offres, trouver_document
from collecte.navigateur import RobotsTxt

ROBOTS_LIDL = """User-agent: *
Disallow: /cc.js*
Disallow: /user-api/*
Disallow: *search?q=*
Disallow: *?offset=*
Disallow: *id=*
Disallow: *sort=*
"""


def test_robots_txt_avec_jokers():
    r = RobotsTxt(ROBOTS_LIDL)
    assert r.autorise("/c/lidl-est-moins-cher/s10027822")
    assert r.autorise("/static/assets/Liste_des_produits_compares-2435920.pdf")
    assert not r.autorise("/c/manger-boire/s10068374?offset=12")
    assert not r.autorise("/c/manger-boire/s10068374?category.id=10095761")
    assert not r.autorise("/q/search?q=lait")
    assert not r.autorise("/user-api/panier")


def test_robots_txt_allow_plus_precis():
    r = RobotsTxt("User-agent: *\nDisallow: /prive/\nAllow: /prive/public$\n")
    assert not r.autorise("/prive/secret")
    assert r.autorise("/prive/public")


def test_extraction_fiche_aldi():
    produit = {"productSlug": "riz-thai-2597", "name": "Riz Thaï", "brandName": "BON-RI®", "salesUnit": "1KG",
               "isAvailable": True, "currentPrice": {"priceValue": 1.49, "basePrice": [{"basePriceValue": 1.49,
                                                                                       "basePriceScale": "KG"}],
                                                     "validUntil": 1794956399}}
    api = json.dumps([["PRODUCT_GET", {"res": {"data": [produit]}}]])
    page = ('<html><script id="__NEXT_DATA__" type="application/json">'
            + json.dumps({"props": {"pageProps": {"apiData": api}}}) + "</script></html>")
    p = extraire_produit(page, "riz-thai-2597")
    assert p["prix"] == 1.49 and p["unite_vente"] == "1KG" and p["marque"] == "BON-RI®"
    assert extraire_produit(page, "autre-produit") is None


def test_lecture_lignes_pdf_lidl():
    lignes = [
        "MDD 4056489818151 31402 Combino Spaghetti 1,00 kg 100,00% 0,88 E.Leclerc 3564700012345 TURINI "
        "Pâtes Spaghetti Turini 1kg 1,00 kg 100,00% 1,33",
        "MDD 20001872 1234 Ocean Sea Calamars à la romaine 0,50 kg 100,00% 2,35 Carrefour Hyper 0,50 kg 98,00% 4,24",
        "TOTAL PANIER DE COURSES LIDL 40,8 TOTAL PANIER DE COURSES E.LECLERC 50,22",
    ]
    produits, paniers = analyser_lignes(lignes)
    assert produits["4056489818151"]["prix"] == 0.88
    assert produits["4056489818151"]["quantite"] == 1.0
    assert produits["4056489818151"]["concurrents_drive"][0]["prix"] == 1.33
    assert produits["20001872"]["concurrents_drive"][0]["enseigne"] == "Carrefour Hyper"
    assert paniers == [{"enseigne": "E.Leclerc", "total_lidl": 40.8, "total_concurrent": 50.22}]


def test_lien_et_date_du_document_lidl():
    page = ('<a href="/static/assets/Liste_des_produits_compares-2435920.pdf">LISTE</a>'
            "<p>*Prix moyens relev&eacute;s le 04.07.2026, sur 25 produits</p>")
    url, date = trouver_document(page)
    assert url == "https://www.lidl.fr/static/assets/Liste_des_produits_compares-2435920.pdf"
    assert date == "2026-07-04"


def test_offres_lidl():
    vignette = {"fullTitle": "MILBONA Feta AOP", "brand": {"name": "MILBONA"}, "category": "Food",
                "canonicalPath": "/p/milbona-feta-aop/p11000024",
                "price": {"price": 2.49, "oldPrice": 2.94, "packaging": {"text": "240 g"},
                          "basePrice": {"text": "1 kg = 10,38"}}}
    page = f'<div data-grid-data="{html.escape(json.dumps(vignette))}"></div>'
    offres = extraire_offres(page)
    assert offres[0]["prix"] == 2.49 and offres[0]["ancien_prix"] == 2.94
    assert offres[0]["url"] == "https://www.lidl.fr/p/milbona-feta-aop/p11000024"
