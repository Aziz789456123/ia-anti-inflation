"""
Accès « poli » aux sites des enseignes.

Règles appliquées à chaque requête :
  1. le fichier robots.txt du site est lu et respecté (y compris les jokers * et $) ;
  2. une pause de plusieurs secondes est faite entre deux pages d'un même site ;
  3. le robot se présente honnêtement (User-Agent explicite) ;
  4. seules des pages publiques sont lues, sans compte ni contournement de protection.
"""

from __future__ import annotations

import os
import re
import time
from urllib.parse import urlsplit

import requests

AGENT = "IA-Anti-Inflation-Besancon/1.0 (projet etudiant-entrepreneur; collecte 1 fois par jour"
CONTACT = os.environ.get("COLLECTE_CONTACT", "")
USER_AGENT = AGENT + (f"; {CONTACT}" if CONTACT else "") + ")"


class RobotsTxt:
    """Lecture d'un robots.txt avec les jokers utilisés par les grands sites (* et $)."""

    def __init__(self, texte: str):
        self.regles: list[tuple[bool, re.Pattern, int]] = []
        groupes, agents, courant = [], [], []
        for brut in texte.splitlines():
            ligne = brut.split("#", 1)[0].strip()
            if ":" not in ligne:
                continue
            cle, valeur = (x.strip() for x in ligne.split(":", 1))
            cle = cle.lower()
            if cle == "user-agent":
                if courant:
                    groupes.append((agents, courant))
                    agents, courant = [], []
                agents.append(valeur.lower())
            elif cle in ("allow", "disallow"):
                courant.append((cle == "allow", valeur))
        if agents or courant:
            groupes.append((agents, courant))
        for agents, regles in groupes:
            if "*" in agents:
                for autorise, chemin in regles:
                    if chemin:
                        self.regles.append((autorise, self._motif(chemin), len(chemin)))

    @staticmethod
    def _motif(chemin: str) -> re.Pattern:
        fin = chemin.endswith("$")
        chemin = chemin[:-1] if fin else chemin
        regex = ".*".join(re.escape(morceau) for morceau in chemin.split("*"))
        if not chemin.startswith("/") and not chemin.startswith("*"):
            regex = ".*" + regex
        return re.compile("^" + regex + ("$" if fin else ""))

    def autorise(self, chemin_et_requete: str) -> bool:
        """La règle la plus longue qui correspond l'emporte ; à égalité, Allow gagne."""
        meilleure = None
        for autorise, motif, longueur in self.regles:
            if motif.match(chemin_et_requete):
                if meilleure is None or longueur > meilleure[1] or (longueur == meilleure[1] and autorise):
                    meilleure = (autorise, longueur)
        return True if meilleure is None else meilleure[0]


class NavigateurPoli:
    def __init__(self, delai_secondes: float = 3.0, timeout: int = 25):
        self.delai = delai_secondes
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "fr-FR,fr;q=0.9"})
        self._robots: dict[str, RobotsTxt] = {}
        self._derniere: dict[str, float] = {}
        self.journal: list[str] = []

    def _robots_de(self, hote: str, schema: str) -> RobotsTxt:
        if hote not in self._robots:
            try:
                r = self.session.get(f"{schema}://{hote}/robots.txt", timeout=self.timeout)
                self._robots[hote] = RobotsTxt(r.text if r.ok else "")
            except requests.RequestException:
                self._robots[hote] = RobotsTxt("")
        return self._robots[hote]

    def autorise(self, url: str) -> bool:
        p = urlsplit(url)
        chemin = (p.path or "/") + (f"?{p.query}" if p.query else "")
        return self._robots_de(p.netloc, p.scheme).autorise(chemin)

    def get(self, url: str) -> requests.Response:
        if not self.autorise(url):
            raise PermissionError(f"Page interdite par robots.txt, non lue : {url}")
        hote = urlsplit(url).netloc
        attente = self.delai - (time.monotonic() - self._derniere.get(hote, 0))
        if attente > 0:
            time.sleep(attente)
        r = self.session.get(url, timeout=self.timeout)
        self._derniere[hote] = time.monotonic()
        self.journal.append(f"{r.status_code} {url}")
        r.raise_for_status()
        return r
