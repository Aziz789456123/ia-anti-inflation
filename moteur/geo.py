"""
Distances, itinéraires routiers et instructions de conduite.

Les trajets sont calculés en direct avec OSRM sur les routes d'OpenStreetMap
(service public router.project-osrm.org). Sans connexion, on estime la distance
à vol d'oiseau majorée de 30 %, pour que l'application fonctionne toujours.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field
from functools import lru_cache
from math import asin, cos, radians, sin, sqrt

RAYON_TERRE_KM = 6371.0
COEFF_ROUTE = 1.3          # une route n'est jamais en ligne droite
VITESSE_VILLE_KMH = 30.0   # pour estimer une durée sans itinéraire
OSRM = "https://router.project-osrm.org"
AGENT = {"User-Agent": "IA-Anti-Inflation-Besancon/1.0"}


@dataclass(frozen=True)
class Point:
    lat: float
    lon: float
    id: str = ""


@dataclass
class Trajet:
    """Un tronçon : d'un point à un autre."""
    km: float
    minutes: float
    trace: list[tuple[float, float]] = field(default_factory=list)   # suite de (lat, lon)
    instructions: list[str] = field(default_factory=list)
    source: str = "estimation"


def distance_vol_oiseau_km(a: Point, b: Point) -> float:
    d_lat, d_lon = radians(b.lat - a.lat), radians(b.lon - a.lon)
    h = sin(d_lat / 2) ** 2 + cos(radians(a.lat)) * cos(radians(b.lat)) * sin(d_lon / 2) ** 2
    return 2 * RAYON_TERRE_KM * asin(sqrt(h))


def _estimation(a: Point, b: Point) -> Trajet:
    km = distance_vol_oiseau_km(a, b) * COEFF_ROUTE
    return Trajet(km, km / VITESSE_VILLE_KMH * 60, [(a.lat, a.lon), (b.lat, b.lon)], [], "estimation")


def _get_json(url: str, timeout: float = 6) -> dict | None:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=timeout) as r:
            return json.load(r)
    except Exception:
        return None


def _coords(points) -> str:
    return ";".join(f"{p.lon:.5f},{p.lat:.5f}" for p in points)


# ------------------------------------------------------------------ matrice de distances
@lru_cache(maxsize=256)
def _matrice_osrm(cle: tuple) -> tuple | None:
    points = [Point(lat, lon) for lat, lon in cle]
    d = _get_json(f"{OSRM}/table/v1/driving/{_coords(points)}?annotations=distance,duration")
    if not d or d.get("code") != "Ok":
        return None
    km = tuple(tuple((x or 0) / 1000 for x in ligne) for ligne in d["distances"])
    mn = tuple(tuple((x or 0) / 60 for x in ligne) for ligne in d["durations"])
    return km, mn


def matrice(points: list[Point], en_ligne: bool = True) -> tuple[list[list[float]], list[list[float]], str]:
    """Distances (km) et durées (min) en voiture entre tous les points, en un seul appel."""
    cle = tuple((round(p.lat, 5), round(p.lon, 5)) for p in points)
    res = _matrice_osrm(cle) if en_ligne else None
    if res:
        return [list(l) for l in res[0]], [list(l) for l in res[1]], "itinéraire routier"
    km = [[0.0 if i == j else _estimation(a, b).km for j, b in enumerate(points)] for i, a in enumerate(points)]
    mn = [[x / VITESSE_VILLE_KMH * 60 for x in ligne] for ligne in km]
    return km, mn, "estimation"


# ------------------------------------------------------------------ itinéraire détaillé
DIRECTIONS = {
    "left": "à gauche", "right": "à droite", "slight left": "légèrement à gauche",
    "slight right": "légèrement à droite", "sharp left": "franchement à gauche",
    "sharp right": "franchement à droite", "straight": "tout droit", "uturn": "demi-tour",
}


def _ordinal(n: int) -> str:
    return "1re" if n == 1 else f"{n}e"


def instruction_fr(step: dict) -> str:
    """Traduit une étape OSRM en phrase simple, comme un GPS."""
    m = step.get("maneuver", {})
    type_, modif = m.get("type", ""), m.get("modifier", "")
    route = step.get("name") or step.get("ref") or ""
    sur = f" sur {route}" if route else ""
    direction = DIRECTIONS.get(modif, "")
    if type_ == "depart":
        return f"Partez{sur}" if route else "Partez"
    if type_ == "arrive":
        cote = {"left": " (sur votre gauche)", "right": " (sur votre droite)"}.get(modif, "")
        return f"Vous êtes arrivé{cote}"
    if type_ in ("roundabout", "rotary"):
        sortie = m.get("exit")
        return f"Au rond-point, prenez la {_ordinal(sortie)} sortie{sur}" if sortie else f"Prenez le rond-point{sur}"
    if type_ in ("exit roundabout", "exit rotary"):
        return f"Sortez du rond-point{sur}"
    if type_ == "roundabout turn":
        return f"Au rond-point, tournez {direction}{sur}"
    if modif == "uturn":
        return f"Faites demi-tour{sur}"
    if type_ in ("turn", "end of road"):
        if modif == "straight":
            return f"Continuez tout droit{sur}"
        return f"Tournez {direction}{sur}"
    if type_ == "fork":
        return f"À l'embranchement, restez {direction}{sur}"
    if type_ in ("on ramp",):
        return f"Prenez la bretelle {direction}{sur}".replace("  ", " ")
    if type_ in ("off ramp",):
        return f"Prenez la sortie {direction}{sur}".replace("  ", " ")
    if type_ == "merge":
        return f"Insérez-vous {direction}{sur}".replace("  ", " ")
    if type_ in ("new name", "continue", "notification"):
        return f"Continuez{sur}" if modif in ("straight", "") else f"Continuez {direction}{sur}"
    return f"Continuez{sur}"


def _distance_lisible(m: float) -> str:
    return f"{round(m / 10) * 10:.0f} m" if m < 1000 else f"{m / 1000:.1f} km".replace(".", ",")


@lru_cache(maxsize=128)
def _route_osrm(cle: tuple) -> list[Trajet] | None:
    points = [Point(lat, lon) for lat, lon in cle]
    d = _get_json(f"{OSRM}/route/v1/driving/{_coords(points)}?overview=false&geometries=geojson&steps=true")
    if not d or d.get("code") != "Ok":
        return None
    trajets = []
    for leg in d["routes"][0]["legs"]:
        trace, consignes = [], []
        for step in leg.get("steps", []):
            trace += [(lat, lon) for lon, lat in step.get("geometry", {}).get("coordinates", [])]
            phrase = instruction_fr(step)
            if step.get("distance", 0) > 0 and step["maneuver"]["type"] != "arrive":
                phrase += f" — {_distance_lisible(step['distance'])}"
            if not consignes or consignes[-1] != phrase:
                consignes.append(phrase)
        trajets.append(Trajet(leg["distance"] / 1000, leg["duration"] / 60, trace, consignes, "itinéraire routier"))
    return trajets


def itineraire(points: list[Point], en_ligne: bool = True) -> list[Trajet]:
    """Tronçons successifs points[0] -> points[1] -> … avec tracé et instructions."""
    cle = tuple((round(p.lat, 5), round(p.lon, 5)) for p in points)
    res = _route_osrm(cle) if en_ligne else None
    if res:
        return res
    return [_estimation(a, b) for a, b in zip(points, points[1:])]


def distance_route_km(a: Point, b: Point, en_ligne: bool = True) -> float:
    return matrice([a, b], en_ligne)[0][0][1]
