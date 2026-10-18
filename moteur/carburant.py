"""
Prix des carburants en direct, station par station.

Source officielle : Ministère de l'Économie, jeu de données « Prix des carburants en France –
flux instantané v2 » (data.economie.gouv.fr). Les stations déclarent leurs prix, le flux est
rafraîchi toutes les 10 minutes environ. Licence Ouverte (Etalab).
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .geo import Point, distance_vol_oiseau_km

API = ("https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/"
       "prix-des-carburants-en-france-flux-instantane-v2/records")
SECOURS = Path(__file__).resolve().parent.parent / "data" / "carburants_secours.json"

# nom affiché -> champ du jeu de données
CARBURANTS = {"SP95-E10": "e10", "Gazole": "gazole", "SP95": "sp95", "SP98": "sp98", "E85": "e85", "GPL": "gplc"}
CARBURANT_PAR_MOTORISATION = {
    "Essence": "SP95-E10", "Hybride essence": "SP95-E10", "Hybride rechargeable essence": "SP95-E10",
    "Diesel": "Gazole", "Hybride diesel": "Gazole", "Hybride rechargeable diesel": "Gazole",
    "GPL": "GPL", "Superéthanol E85": "E85",
}


@dataclass
class Station:
    id: int
    adresse: str
    ville: str
    position: Point
    prix: dict[str, float] = field(default_factory=dict)          # carburant -> €/L
    mis_a_jour: dict[str, datetime] = field(default_factory=dict)  # carburant -> date de mise à jour
    distance_km: float = 0.0

    @property
    def libelle(self) -> str:
        return f"{self.adresse.title()}, {self.ville}"


def _date(texte: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(texte) if texte else None
    except ValueError:
        return None


def _station(d: dict, origine: Point) -> Station:
    geom = d.get("geom") or {}
    lat, lon = d.get("lat", geom.get("lat")), d.get("lon", geom.get("lon"))
    s = Station(int(d["id"]), (d.get("adresse") or "").strip(), (d.get("ville") or "").strip(), Point(lat, lon))
    for nom, champ in CARBURANTS.items():
        valeur = d.get(f"{champ}_prix", d.get(champ))
        if valeur:
            s.prix[nom] = float(valeur)
            if maj := _date(d.get(f"{champ}_maj")):
                s.mis_a_jour[nom] = maj
    s.distance_km = distance_vol_oiseau_km(origine, s.position)
    return s


def stations_autour(origine: Point, rayon_km: float = 10, en_ligne: bool = True) -> tuple[list[Station], dict]:
    """Stations à moins de `rayon_km`, triées par distance. Renvoie aussi l'origine des données."""
    if en_ligne:
        champs = ["id", "adresse", "ville", "geom"] + [f"{c}_{s}" for c in CARBURANTS.values() for s in ("prix", "maj")]
        params = {
            "select": ",".join(champs),
            "where": f"within_distance(geom, geom'POINT({origine.lon} {origine.lat})', {rayon_km}km)",
            "limit": 100,
        }
        try:
            req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params),
                                         headers={"User-Agent": "IA-Anti-Inflation-Besancon/1.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                resultats = json.load(r)["results"]
            stations = sorted((_station(d, origine) for d in resultats), key=lambda s: s.distance_km)
            return [s for s in stations if s.prix], {"direct": True, "recupere_le": datetime.now().astimezone()}
        except Exception:
            pass
    secours = json.loads(SECOURS.read_text(encoding="utf-8"))
    stations = sorted((_station(d, origine) for d in secours["stations"]), key=lambda s: s.distance_km)
    return ([s for s in stations if s.prix and s.distance_km <= rayon_km],
            {"direct": False, "recupere_le": _date(secours.get("collecte_le"))})


def moins_chere(stations: list[Station], carburant: str, rayon_km: float = 5) -> Station | None:
    candidates = [s for s in stations if carburant in s.prix and s.distance_km <= rayon_km]
    return min(candidates, key=lambda s: s.prix[carburant]) if candidates else None
