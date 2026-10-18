"""
Moteur de décision : où faire ses courses pour payer le moins cher, trajet compris ?

1. Pour chaque combinaison de magasins (un seul, ou deux), chaque produit est acheté
   là où il est le moins cher, et l'ordre de passage le plus court est choisi.
2. Le coût total = prix des courses + coût du trajet (essence ou électricité).
3. Règle du détour : on part du magasin le plus proche et on ne va plus loin, ou dans
   un magasin de plus, que si cela fait gagner au moins un montant minimum (le « seuil »).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations, permutations

from .geo import Point, matrice


@dataclass(frozen=True)
class Magasin:
    id: str
    enseigne: str
    nom: str
    format: str
    position: Point
    adresse: str = ""


@dataclass(frozen=True)
class Transport:
    """Ce que coûte un kilomètre : consommation × prix de l'énergie."""
    nom: str
    conso_100km: float = 0.0     # litres (ou kWh) pour 100 km
    prix_energie: float = 0.0    # € par litre (ou par kWh)
    unite: str = "L"             # "L" ou "kWh"

    @property
    def cout_km(self) -> float:
        return self.conso_100km / 100 * self.prix_energie

    @property
    def motorise(self) -> bool:
        return self.cout_km > 0

    @staticmethod
    def voiture(conso_l_100km: float = 6.5, prix_litre: float = 1.85, unite: str = "L") -> "Transport":
        return Transport("Voiture", conso_l_100km, prix_litre, unite)

    @staticmethod
    def sans_voiture() -> "Transport":
        return Transport("À pied, à vélo ou en transports")


class Reseau:
    """Distances et durées entre le point de départ et tous les magasins (calculées une fois)."""

    def __init__(self, depart: Point, magasins: list[Magasin], en_ligne: bool = True):
        self.depart = depart
        self.ids = ["__depart__"] + [m.id for m in magasins]
        self.index = {i: k for k, i in enumerate(self.ids)}
        self.km, self.minutes, self.source = matrice([depart] + [m.position for m in magasins], en_ligne)

    def tournee(self, magasins: tuple[Magasin, ...]) -> tuple[tuple[Magasin, ...], float, float]:
        meilleur = None
        for ordre in permutations(magasins):
            noeuds = ["__depart__", *(m.id for m in ordre), "__depart__"]
            km = sum(self.km[self.index[a]][self.index[b]] for a, b in zip(noeuds, noeuds[1:]))
            mn = sum(self.minutes[self.index[a]][self.index[b]] for a, b in zip(noeuds, noeuds[1:]))
            if meilleur is None or km < meilleur[1]:
                meilleur = (ordre, km, mn)
        return meilleur


@dataclass
class Scenario:
    magasins: tuple[Magasin, ...]
    affectation: dict[str, str]          # produit -> id du magasin où l'acheter
    cout_courses: float
    distance_km: float
    minutes: float
    transport: Transport
    detail: dict[str, float] = field(default_factory=dict)  # id magasin -> montant des courses

    @property
    def cout_trajet(self) -> float:
        return round(self.distance_km * self.transport.cout_km, 2)

    @property
    def energie(self) -> float:
        """Litres (ou kWh) consommés pour le trajet."""
        return self.distance_km * self.transport.conso_100km / 100

    @property
    def total(self) -> float:
        return round(self.cout_courses + self.cout_trajet, 2)

    @property
    def nb_magasins(self) -> int:
        return len(self.magasins)

    @property
    def libelle(self) -> str:
        return " puis ".join(m.nom for m in self.magasins)

    @property
    def enseignes(self) -> str:
        return " + ".join(m.enseigne for m in self.magasins)


@dataclass
class Recommandation:
    conseil: Scenario
    gain_de_temps: Scenario          # meilleur plan avec un seul magasin
    economie_max: Scenario           # meilleur plan, tous nombres de magasins confondus
    pire_magasin_unique: Scenario
    seuil: float
    plus_proche: Scenario | None = None
    par_enseigne: dict[str, Scenario] = field(default_factory=dict)  # meilleur magasin de chaque enseigne

    @property
    def economie_vs_pire(self) -> float:
        return round(self.pire_magasin_unique.total - self.conseil.total, 2)

    @property
    def gain_multi_magasins(self) -> float:
        return round(self.gain_de_temps.total - self.economie_max.total, 2)


def evaluer(liste: dict[str, int], prix: dict[str, dict[str, float]], magasins: tuple[Magasin, ...],
            reseau: Reseau, transport: Transport) -> Scenario:
    """Coût d'un plan utilisant ces magasins (chaque produit au moins cher parmi eux)."""
    affectation, detail = {}, {m.id: 0.0 for m in magasins}
    for produit, quantite in liste.items():
        if quantite <= 0:
            continue
        offres = {m.id: prix[produit][m.id] for m in magasins if m.id in prix.get(produit, {})}
        if not offres:
            raise ValueError(f"« {produit} » n'est vendu dans aucun de ces magasins.")
        moins_cher = min(offres, key=offres.get)
        affectation[produit] = moins_cher
        detail[moins_cher] += offres[moins_cher] * quantite
    utiles = tuple(m for m in magasins if detail[m.id] > 0) or magasins[:1]
    ordre, km, mn = reseau.tournee(utiles)
    return Scenario(ordre, affectation, round(sum(detail.values()), 2), km, mn, transport,
                    {m.id: round(detail[m.id], 2) for m in ordre})


def recommander(liste: dict[str, int], prix: dict[str, dict[str, float]], magasins: list[Magasin],
                depart: Point, transport: Transport, seuil: float = 5.0, max_magasins: int = 2,
                reseau: Reseau | None = None) -> Recommandation:
    if not any(q > 0 for q in liste.values()):
        raise ValueError("La liste de courses est vide.")
    reseau = reseau or Reseau(depart, magasins)

    par_taille: dict[int, Scenario] = {}
    uniques: list[Scenario] = []
    for k in range(1, min(max_magasins, len(magasins)) + 1):
        for combo in combinations(magasins, k):
            if k > 1 and len({m.enseigne for m in combo}) < k:
                continue  # deux magasins de la même enseigne : mêmes prix, détour inutile
            try:
                s = evaluer(liste, prix, combo, reseau, transport)
            except ValueError:
                continue
            if k == 1:
                uniques.append(s)
            if s.nb_magasins not in par_taille or s.total < par_taille[s.nb_magasins].total:
                par_taille[s.nb_magasins] = s
    if not uniques:
        raise ValueError("Aucun magasin ne propose tous les produits de la liste.")

    gain_de_temps = min(uniques, key=lambda s: s.total)
    pire = max(uniques, key=lambda s: s.total)
    economie_max = min(par_taille.values(), key=lambda s: s.total)
    plus_proche = min(uniques, key=lambda s: (s.distance_km, s.total))
    par_enseigne: dict[str, Scenario] = {}
    for s in uniques:
        e = s.magasins[0].enseigne
        if e not in par_enseigne or s.total < par_enseigne[e].total:
            par_enseigne[e] = s

    conseil = plus_proche
    if conseil.total - gain_de_temps.total >= seuil:
        conseil = gain_de_temps
    for taille in sorted(par_taille):
        candidat = par_taille[taille]
        if taille > conseil.nb_magasins and conseil.total - candidat.total >= seuil:
            conseil = candidat
    return Recommandation(conseil, gain_de_temps, economie_max, pire, seuil, plus_proche, par_enseigne)
