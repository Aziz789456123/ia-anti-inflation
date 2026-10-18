"""
Chargement des données : magasins, prix collectés, panier de comparaison.

Les prix Lidl et Aldi viennent des fichiers data/prix_lidl.json et data/prix_aldi.json,
écrits par les robots de collecte (dossier collecte/). Pour comparer ce qui est comparable,
chaque produit du panier est ramené à la même quantité (ex. 1 kg de spaghetti) :
si un magasin ne vend que des paquets de 500 g, on compte deux paquets.
"""

from __future__ import annotations

import csv
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from .geo import Point
from .optimiseur import Magasin

DATA = Path(__file__).resolve().parent.parent / "data"


@dataclass
class Offre:
    enseigne: str
    libelle: str
    marque: str | None
    prix_paquet: float
    contenance: float            # en g ou ml
    nb_paquets: int
    source: str
    date: str | None
    url: str | None

    @property
    def prix(self) -> float:
        """Prix pour la quantité de référence du produit."""
        return round(self.prix_paquet * self.nb_paquets, 2)

    @property
    def prix_au_kilo(self) -> float:
        return self.prix_paquet / self.contenance * 1000 if self.contenance else 0.0


@dataclass
class Produit:
    nom: str
    rayon: str
    quantite: float
    unite: str                     # "g" ou "ml"
    offres: dict[str, Offre] = field(default_factory=dict)   # enseigne -> offre

    @property
    def format(self) -> str:
        q = self.quantite
        if self.unite == "g":
            return f"{q / 1000:g} kg".replace(".", ",") if q >= 1000 else f"{q:g} g"
        return f"{q / 1000:g} L".replace(".", ",") if q >= 1000 else f"{q / 10:g} cl"

    @property
    def libelle(self) -> str:
        return f"{self.nom} ({self.format})"


def contenance(texte: str | None, quantite: float | None = None, unite: str | None = None) -> float | None:
    """Convertit « 500G », « 1.5L », « 50 cl », ou (0,23 ; kg) en grammes / millilitres."""
    if quantite is not None and unite:
        return quantite * (1000 if unite.lower() in ("kg", "l") else 1)
    if not texte:
        return None
    m = re.search(r"([\d.,]+)\s*(kg|g|l|cl|ml)\b", texte.lower())
    if not m:
        return None
    valeur = float(m.group(1).replace(",", "."))
    return valeur * {"kg": 1000, "g": 1, "l": 1000, "cl": 10, "ml": 1}[m.group(2)]


def _json(nom: str) -> dict:
    try:
        return json.loads((DATA / nom).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def charger_magasins() -> list[Magasin]:
    with open(DATA / "magasins.csv", encoding="utf-8") as f:
        return [Magasin(r["id"], r["enseigne"], r["nom"], r["format"],
                        Point(float(r["latitude"]), float(r["longitude"]), r["id"]), r["adresse"])
                for r in csv.DictReader(f)]


def charger_quartiers() -> dict[str, Point]:
    with open(DATA / "quartiers.csv", encoding="utf-8") as f:
        return {r["quartier"]: Point(float(r["latitude"]), float(r["longitude"]), r["quartier"])
                for r in csv.DictReader(f)}


def charger_sources() -> dict[str, dict]:
    """Informations sur chaque source de prix (date, méthode…), sans la liste des produits."""
    sources = {}
    for nom, fichier in (("Lidl", "prix_lidl.json"), ("Aldi", "prix_aldi.json")):
        d = _json(fichier)
        sources[nom] = {k: v for k, v in d.items() if k != "produits"} | {"nb_produits": len(d.get("produits", {}))}
    return sources


def charger_promos() -> dict:
    return _json("promos_lidl.json")


def charger_catalogue() -> list[Produit]:
    lidl, aldi = _json("prix_lidl.json"), _json("prix_aldi.json")
    pl, pa = lidl.get("produits", {}), aldi.get("produits", {})
    catalogue = []
    with open(DATA / "panier.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            p = Produit(r["produit"], r["rayon"], float(r["quantite"]), r["unite"])
            if (l := pl.get(r["lidl_ean"])) and (c := contenance(None, l["quantite"], l["unite"] or "kg")):
                p.offres["Lidl"] = Offre("Lidl", l["nom"], l.get("marque"), l["prix"], c,
                                         max(1, math.ceil(p.quantite / c - 1e-9)), "Prix officiel publié par Lidl",
                                         lidl.get("prix_releves_le"), lidl.get("url_document"))
            if (a := pa.get(r["aldi_slug"])) and (c := contenance(a.get("unite_vente"))):
                p.offres["Aldi"] = Offre("Aldi", a["nom"].capitalize() if a["nom"].isupper() else a["nom"],
                                         (a.get("marque") or "").replace("®", "") or None, a["prix"], c,
                                         max(1, math.ceil(p.quantite / c - 1e-9)), "Fiche produit aldi.fr",
                                         (aldi.get("collecte_le") or "")[:10] or None, a.get("url"))
            if p.offres:
                catalogue.append(p)
    return catalogue


def table_prix(catalogue: list[Produit], magasins: list[Magasin]) -> dict[str, dict[str, float]]:
    """prix[produit][id_magasin] : même prix dans tous les magasins d'une enseigne (prix nationaux)."""
    return {p.nom: {m.id: p.offres[m.enseigne].prix for m in magasins if m.enseigne in p.offres} for p in catalogue}
