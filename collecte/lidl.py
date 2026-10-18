"""
Collecte des prix Lidl.

Le site lidl.fr ne vend pas d'alimentaire en ligne. Deux sources publiques existent :
  1. les PRIX OFFICIELS : Lidl publie, pour sa publicité comparative, un document PDF
     « Liste des produits comparés » avec le prix national de ~50 produits du quotidien ;
  2. les PROMOTIONS de la semaine en magasin, sur la page « Alimentation & Boissons ».
Seules les pages autorisées par robots.txt sont lues (pas de filtres ni de pagination).
"""

from __future__ import annotations

import html as html_lib
import io
import json
import re

from .navigateur import NavigateurPoli

PAGE_COMPARATIF = "https://www.lidl.fr/c/lidl-est-moins-cher/s10027822"
PAGE_ALIMENTAIRE = "https://www.lidl.fr/c/manger-boire/s10068374"

ENSEIGNES = r"(E\.\s?Leclerc|Leclerc|Carrefour(?: Hyper| Market)?|Intermarch[ée]|Auchan|Super U|Hyper U|Système U)"
_NB = r"\d+,\d{1,2}"
LIGNE = re.compile(
    rf"(?P<ean>\d{{8,13}})\s+(?:\d{{2,6}}\s+)?(?P<libelle>.+?)\s+(?P<qte>{_NB})\s+(?:(?P<unite>kg|L|l|g)\s+)?"
    rf"(?P<dn>\d{{1,3}},\d{{2}}\s?%)\s+(?P<prix>{_NB})\s+(?P<enseigne>{ENSEIGNES})\s*(?P<reste>.*)$"
)
CONCURRENT = re.compile(rf"(?:\d{{8,14}}\s+)?(?P<libelle>.*?)\s*(?P<qte>{_NB})\s+(?:(?:kg|L|l|g)\s+)?\d{{1,3}},\d{{2}}\s?%\s+(?P<prix>{_NB})\s*$")
TOTAL = re.compile(rf"TOTAL PANIER DE COURSES LIDL\s+(?P<lidl>{_NB}).*?TOTAL PANIER DE COURSES\s+(?P<enseigne>[A-ZÉÈ.\s]+?)\s+(?P<conc>{_NB})\s*$")
DATE_RELEVE = re.compile(r"relev[ée]s le (\d{2})[./](\d{2})[./](\d{4})")


def _nombre(texte: str) -> float:
    return float(texte.replace(",", ".").replace(" ", ""))


def trouver_document(page_html: str) -> tuple[str | None, str | None]:
    """Lien vers le PDF des produits comparés et date des relevés (AAAA-MM-JJ)."""
    lien = re.search(r'href="([^"]*Liste_des_produits_compares[^"]*\.pdf)"', page_html)
    url = None
    if lien:
        url = lien.group(1)
        url = url if url.startswith("http") else "https://www.lidl.fr" + url
    d = DATE_RELEVE.search(html_lib.unescape(page_html))
    return url, (f"{d.group(3)}-{d.group(2)}-{d.group(1)}" if d else None)


def lire_lignes_pdf(contenu: bytes) -> list[str]:
    """Texte du PDF, une ligne du tableau par ligne de texte."""
    import pdfplumber

    lignes = []
    with pdfplumber.open(io.BytesIO(contenu)) as pdf:
        for page in pdf.pages:
            mots = page.extract_words(keep_blank_chars=False, use_text_flow=False, x_tolerance=1.5)
            rangs: dict[int, list] = {}
            for mot in mots:
                rangs.setdefault(round(mot["top"]), []).append(mot)
            # regroupe les lignes dont la hauteur ne diffère que d'un point
            cles = sorted(rangs)
            fusion: list[list] = []
            for cle in cles:
                if fusion and cle - fusion[-1][0] <= 2:
                    fusion[-1][1].extend(rangs[cle])
                else:
                    fusion.append([cle, list(rangs[cle])])
            for _, groupe in fusion:
                lignes.append(" ".join(m["text"] for m in sorted(groupe, key=lambda m: m["x0"])))
    return lignes


def analyser_lignes(lignes: list[str]) -> tuple[dict, list[dict]]:
    """Transforme les lignes du tableau en produits Lidl (+ prix concurrents) et totaux de panier."""
    produits: dict[str, dict] = {}
    paniers = []
    for ligne in lignes:
        ligne = re.sub(r"\s+", " ", ligne).strip()
        t = TOTAL.search(ligne)
        if t:
            paniers.append({"enseigne": t.group("enseigne").strip().title(), "total_lidl": _nombre(t.group("lidl")),
                            "total_concurrent": _nombre(t.group("conc"))})
            continue
        m = LIGNE.search(ligne)
        if not m:
            continue
        ean = m.group("ean")
        p = produits.setdefault(ean, {
            "nom": m.group("libelle").strip(), "marque": None, "quantite": _nombre(m.group("qte")),
            "unite": (m.group("unite") or "").replace("l", "L") or None, "prix": _nombre(m.group("prix")),
            "concurrents_drive": [],
        })
        c = CONCURRENT.search(m.group("reste") or "")
        if c:
            p["concurrents_drive"].append({"enseigne": m.group("enseigne").replace("E. ", "E."),
                                           "produit": c.group("libelle").strip() or None, "prix": _nombre(c.group("prix"))})
    return produits, paniers


def collecter_prix_officiels(nav: NavigateurPoli) -> dict:
    page = nav.get(PAGE_COMPARATIF).text
    url_pdf, date = trouver_document(page)
    if not url_pdf:
        raise RuntimeError("Lien du document « Liste des produits comparés » introuvable sur la page Lidl.")
    produits, paniers = analyser_lignes(lire_lignes_pdf(nav.get(url_pdf).content))
    return {"url_document": url_pdf, "prix_releves_le": date, "produits": produits, "paniers_compares": paniers}


def extraire_offres(page_html: str) -> list[dict]:
    """Offres de la page alimentaire (données intégrées à chaque vignette produit)."""
    offres = []
    for brut in re.findall(r'data-grid-data="([^"]+)"', page_html):
        try:
            d = json.loads(html_lib.unescape(brut))
        except ValueError:
            continue
        prix = d.get("price") or {}
        if not prix.get("price") and d.get("lidlPlus"):
            prix = (d["lidlPlus"][0] or {}).get("price") or {}
        if not prix.get("price") or d.get("category") != "Food":
            continue
        region = ((d.get("regionsPrices") or {}).get("1") or {}).get("currentPrice") or {}
        badges = ((d.get("stockAvailability") or {}).get("badgeInfo") or {}).get("badges") or []
        offres.append({
            "titre": d.get("fullTitle"), "marque": (d.get("brand") or {}).get("name"), "prix": prix.get("price"),
            "ancien_prix": prix.get("oldPrice"), "remise": (region.get("discount") or {}).get("discountText"),
            "format": (prix.get("packaging") or {}).get("text"), "prix_unite": (prix.get("basePrice") or {}).get("text"),
            "debut": region.get("startDate"), "fin": region.get("endDate"),
            "disponibilite": " / ".join(b.get("text", "") for b in badges), "image": d.get("image"),
            "url": "https://www.lidl.fr" + d.get("canonicalPath", ""), "categorie": d.get("category"),
        })
    return offres


def collecter_promos(nav: NavigateurPoli) -> list[dict]:
    return extraire_offres(nav.get(PAGE_ALIMENTAIRE).text)
