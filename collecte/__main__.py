"""
Lance la collecte des prix Lidl et Aldi et met à jour le dossier data/.

    python -m collecte

En cas d'échec d'une source (site indisponible, page modifiée…), les prix précédents
sont conservés : l'application ne se retrouve jamais sans données.
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import aldi, lidl
from .navigateur import NavigateurPoli

DATA = Path(__file__).resolve().parent.parent / "data"
PARIS = ZoneInfo("Europe/Paris")


def maintenant() -> str:
    return datetime.now(PARIS).isoformat(timespec="seconds")


def lire(nom: str) -> dict:
    try:
        return json.loads((DATA / nom).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def ecrire(nom: str, contenu: dict) -> None:
    (DATA / nom).write_text(json.dumps(contenu, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> int:
    nav = NavigateurPoli(delai_secondes=3.0)
    bilan = []

    # --- Aldi : les fiches du panier + celles déjà suivies
    ancien_aldi = lire("prix_aldi.json")
    with open(DATA / "panier.csv", encoding="utf-8") as f:
        slugs = [r["aldi_slug"] for r in csv.DictReader(f) if r["aldi_slug"]]
    slugs += [s for s in ancien_aldi.get("produits", {}) if s not in slugs]
    produits, erreurs = aldi.collecter(slugs, nav)
    if len(produits) >= max(5, len(slugs) // 2):
        ancien_aldi.update({"produits": {**ancien_aldi.get("produits", {}), **produits}, "collecte_le": maintenant()})
        ecrire("prix_aldi.json", ancien_aldi)
        bilan.append(f"Aldi : {len(produits)}/{len(slugs)} prix mis à jour")
    else:
        bilan.append(f"Aldi : échec ({len(produits)} prix lus), anciens prix conservés")
    bilan += [f"  - {e}" for e in erreurs[:10]]

    # --- Lidl : prix officiels (PDF) et promotions
    ancien_lidl = lire("prix_lidl.json")
    try:
        officiel = lidl.collecter_prix_officiels(nav)
        if len(officiel["produits"]) >= 10:
            ancien_lidl.update(officiel)
            ancien_lidl["collecte_le"] = maintenant()
            ecrire("prix_lidl.json", ancien_lidl)
            bilan.append(f"Lidl : {len(officiel['produits'])} prix officiels (relevés du {officiel['prix_releves_le']})")
        else:
            bilan.append("Lidl : document lu mais trop peu de produits, anciens prix conservés")
    except Exception as exc:
        bilan.append(f"Lidl : échec ({exc}), anciens prix conservés")

    try:
        offres = lidl.collecter_promos(nav)
        if offres:
            promos = lire("promos_lidl.json")
            promos.update({"offres": offres, "collecte_le": maintenant()})
            ecrire("promos_lidl.json", promos)
        bilan.append(f"Lidl : {len(offres)} promotions de la semaine")
    except Exception as exc:
        bilan.append(f"Lidl promotions : échec ({exc})")

    print("\n".join(bilan))
    print(f"\n{len(nav.journal)} pages lues, toutes autorisées par robots.txt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
