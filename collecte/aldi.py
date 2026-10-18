"""
Collecte des prix Aldi.

Les fiches produits publiques d'aldi.fr (autorisées par robots.txt) contiennent le prix
dans les données de la page (bloc __NEXT_DATA__). On lit une fiche à la fois, avec une pause.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from .navigateur import NavigateurPoli

BASE = "https://www.aldi.fr/fiches-produits/{slug}.html"


def extraire_produit(html: str, slug: str) -> dict | None:
    """Retrouve l'objet produit (nom, prix, unité…) dans le HTML d'une fiche Aldi."""
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return None
    trouve: dict | None = None

    def visiter(v):
        nonlocal trouve
        if trouve is not None:
            return
        if isinstance(v, str):
            if len(v) > 30 and v[:1] in "{[" and "productSlug" in v:
                try:
                    visiter(json.loads(v))
                except ValueError:
                    pass
        elif isinstance(v, list):
            for x in v:
                visiter(x)
        elif isinstance(v, dict):
            if v.get("productSlug") == slug and isinstance(v.get("currentPrice"), dict):
                trouve = v
                return
            for x in v.values():
                visiter(x)

    visiter(json.loads(m.group(1)))
    if not trouve:
        return None
    prix = trouve["currentPrice"]
    base = (prix.get("basePrice") or [{}])[0]
    valide = prix.get("validUntil")
    return {
        "nom": (trouve.get("name") or trouve.get("metaTitle") or slug).strip(),
        "marque": trouve.get("brandName") or None,
        "unite_vente": trouve.get("salesUnit"),
        "prix": float(prix["priceValue"]),
        "prix_base": {"valeur": base.get("basePriceValue"), "par": base.get("basePriceScale")} if base else None,
        "valide_jusqu_au": datetime.fromtimestamp(valide, timezone.utc).date().isoformat() if valide else None,
        "disponible": trouve.get("isAvailable", True),
        "url": BASE.format(slug=slug),
    }


def collecter(slugs: list[str], nav: NavigateurPoli) -> tuple[dict, list[str]]:
    produits, erreurs = {}, []
    for slug in slugs:
        try:
            p = extraire_produit(nav.get(BASE.format(slug=slug)).text, slug)
            if p:
                produits[slug] = p
            else:
                erreurs.append(f"{slug} : prix introuvable dans la page")
        except Exception as exc:  # une fiche en erreur ne bloque pas les autres
            erreurs.append(f"{slug} : {exc}")
    return produits, erreurs
