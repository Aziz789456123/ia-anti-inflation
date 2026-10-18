"""
Consommation des voitures en ville.

Source : ADEME, jeu de données « Car Labelling » (consommations officielles WLTP des véhicules
vendus en France). Pour des trajets de courses en ville, on retient la moyenne des cycles
« basse vitesse » et « moyenne vitesse », plus réalistes que la valeur mixte.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


@dataclass(frozen=True)
class Vehicule:
    libelle: str
    motorisation: str
    conso_ville: float      # L/100 km, ou kWh/100 km pour l'électrique
    unite: str              # "L/100 km" ou "kWh/100 km"

    @property
    def electrique(self) -> bool:
        return self.motorisation == "Électrique"


@lru_cache(maxsize=1)
def _modeles() -> list[dict]:
    with open(DATA / "vehicules_ademe.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=1)
def _categories() -> list[dict]:
    with open(DATA / "vehicules_categories.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def marques() -> list[str]:
    return sorted({r["marque"] for r in _modeles()})


def modeles(marque: str) -> list[str]:
    return sorted({r["modele"] for r in _modeles() if r["marque"] == marque})


def motorisations(marque: str, modele: str) -> list[str]:
    return [r["motorisation"] for r in _modeles() if r["marque"] == marque and r["modele"] == modele]


def vehicule(marque: str, modele: str, motorisation: str) -> Vehicule:
    r = next(r for r in _modeles() if (r["marque"], r["modele"], r["motorisation"]) == (marque, modele, motorisation))
    return Vehicule(f"{marque} {modele}", motorisation, float(r["conso_ville"]), r["unite"])


def categories() -> list[str]:
    return list(dict.fromkeys(r["categorie"] for r in _categories()))


def motorisations_categorie(categorie: str) -> list[str]:
    return [r["motorisation"] for r in _categories() if r["categorie"] == categorie]


def vehicule_type(categorie: str, motorisation: str) -> Vehicule:
    r = next(r for r in _categories() if r["categorie"] == categorie and r["motorisation"] == motorisation)
    return Vehicule(categorie.split(" (")[0], motorisation, float(r["conso_ville"]), r["unite"])
