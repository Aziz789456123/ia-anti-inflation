"""
Trouver où se trouve l'utilisateur : par son adresse, ou par la position de son téléphone.

Recherche d'adresse : Géoplateforme de l'IGN (service public, Base Adresse Nationale),
avec repli sur l'ancienne API Adresse. Aucune clé n'est nécessaire.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

from .geo import Point

SERVICES = ["https://data.geopf.fr/geocodage", "https://api-adresse.data.gouv.fr"]
CENTRE_BESANCON = Point(47.2378, 6.0241)
AGENT = {"User-Agent": "IA-Anti-Inflation-Besancon/1.0"}


def _appel(chemin: str, params: dict) -> dict | None:
    for base in SERVICES:
        try:
            url = f"{base}/{chemin}?{urllib.parse.urlencode(params)}"
            with urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=5) as r:
                return json.load(r)
        except Exception:
            continue
    return None


def rechercher_adresse(texte: str, autour: Point = CENTRE_BESANCON, nb: int = 6) -> list[tuple[str, Point]]:
    """Suggestions d'adresses, les plus proches de Besançon en premier."""
    if not texte or len(texte.strip()) < 3:
        return []
    d = _appel("search", {"q": texte, "limit": nb, "autocomplete": 1, "lat": autour.lat, "lon": autour.lon})
    resultats = []
    for f in (d or {}).get("features", []):
        lon, lat = f["geometry"]["coordinates"]
        label = f["properties"].get("label", texte)
        resultats.append((label, Point(lat, lon, label)))
    return resultats


def adresse_de(point: Point) -> str | None:
    """Adresse la plus proche d'une position GPS."""
    d = _appel("reverse", {"lat": point.lat, "lon": point.lon, "limit": 1})
    features = (d or {}).get("features", [])
    return features[0]["properties"].get("label") if features else None


def lire_geolocalisation(reponse) -> tuple[Point, float | None] | None:
    """Lit la réponse du navigateur (navigator.geolocation) : position et précision en mètres."""
    if not isinstance(reponse, dict):
        return None
    coords = reponse.get("coords", reponse)
    try:
        return Point(float(coords["latitude"]), float(coords["longitude"]), "Ma position"), coords.get("accuracy")
    except (KeyError, TypeError, ValueError):
        return None
