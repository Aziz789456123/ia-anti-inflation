"""Liens pour suivre l'itinéraire avec le GPS du téléphone (Google Maps, Waze)."""

from __future__ import annotations

from urllib.parse import urlencode

from .geo import Point


def lien_google_maps(depart: Point, etapes: list[Point], mode: str = "driving", retour: bool = True) -> str:
    """Itinéraire départ -> étapes (-> retour au départ) dans Google Maps.

    Format officiel : https://developers.google.com/maps/documentation/urls/get-started
    """
    if not retour and etapes:
        destination, etapes = etapes[-1], etapes[:-1]
    else:
        destination = depart
    params = {"api": 1, "origin": f"{depart.lat},{depart.lon}",
              "destination": f"{destination.lat},{destination.lon}", "travelmode": mode}
    if etapes:
        params["waypoints"] = "|".join(f"{p.lat},{p.lon}" for p in etapes)
    return "https://www.google.com/maps/dir/?" + urlencode(params)


def lien_waze(destination: Point) -> str:
    """Navigation Waze vers une destination (Waze ne gère qu'un arrêt à la fois)."""
    return f"https://waze.com/ul?ll={destination.lat},{destination.lon}&navigate=yes"
