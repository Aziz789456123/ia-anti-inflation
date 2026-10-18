"""
« Magic Scan » : transformer une photo de liste de courses en liste de produits.

L'utilisateur photographie sa liste écrite à la main (ou un ticket de caisse). Un modèle d'IA
capable de lire les images (Claude, d'Anthropic) lit chaque ligne et la rattache au produit
correspondant du catalogue, avec la quantité. Sans clé d'IA, une liste tapée au clavier est
reconnue par mots-clés.
"""

from __future__ import annotations

import base64
import io
import json
import re
import unicodedata
from dataclasses import dataclass, field

MODELE_PAR_DEFAUT = "claude-haiku-5-5"   # modèle rapide et peu coûteux, qui lit les images
COTE_MAX = 1568                          # taille conseillée par Anthropic pour le côté le plus long


@dataclass
class ResultatScan:
    reconnus: dict[str, int] = field(default_factory=dict)     # nom du produit -> quantité
    non_reconnus: list[str] = field(default_factory=list)      # articles lus mais pas encore comparés
    lignes_lues: list[str] = field(default_factory=list)


# ------------------------------------------------------------------ image
def preparer_image(contenu: bytes) -> tuple[str, str]:
    """Redresse, réduit et convertit la photo en JPEG (base64) pour l'envoyer à l'IA."""
    from PIL import Image, ImageOps

    image = ImageOps.exif_transpose(Image.open(io.BytesIO(contenu))).convert("RGB")
    image.thumbnail((COTE_MAX, COTE_MAX))
    tampon = io.BytesIO()
    image.save(tampon, format="JPEG", quality=88)
    return base64.standard_b64encode(tampon.getvalue()).decode(), "image/jpeg"


# ------------------------------------------------------------------ IA
def consigne(noms_catalogue: list[str]) -> str:
    catalogue = "\n".join(f"- {n}" for n in noms_catalogue)
    return f"""Cette photo montre une liste de courses (écrite à la main ou imprimée) ou un ticket de caisse.

1. Lis chaque article, une ligne à la fois.
2. Pour chaque article, choisis dans le CATALOGUE ci-dessous le produit qui correspond (recopie son nom exact),
   ou null si aucun ne correspond vraiment. Exemples : « pâtes » -> Spaghetti ; « riz » -> Riz thaï ;
   « huile » -> Huile de tournesol ; « café » -> Café soluble ; « lait » -> null.
3. Donne la quantité en nombre de produits du catalogue (1 si rien n'est précisé). Exemple : « 2 kg de spaghetti »
   avec « Spaghetti (1 kg) » -> 2 ; « pack d'eau » avec « Eau de source (1,5 L) » -> 6.

CATALOGUE :
{catalogue}

Réponds uniquement avec ce JSON, sans aucun texte autour :
{{"lignes": [{{"lu": "texte lu sur la photo", "produit": "nom exact du catalogue ou null", "quantite": 1}}]}}"""


def analyser_reponse(texte: str, noms_catalogue: list[str], libelles: dict[str, str] | None = None) -> ResultatScan:
    """Lit la réponse JSON de l'IA et la vérifie contre le catalogue."""
    m = re.search(r"\{.*\}", texte, re.S)
    if not m:
        raise ValueError("Réponse de l'IA illisible.")
    donnees = json.loads(m.group(0))
    correspondances = {_simplifier(n): n for n in noms_catalogue}
    for nom, libelle in (libelles or {}).items():
        correspondances[_simplifier(libelle)] = nom
    res = ResultatScan()
    for ligne in donnees.get("lignes", []):
        lu = str(ligne.get("lu") or "").strip()
        if lu:
            res.lignes_lues.append(lu)
        produit = correspondances.get(_simplifier(str(ligne.get("produit") or "")))
        try:
            quantite = max(1, min(30, int(round(float(ligne.get("quantite") or 1)))))
        except (TypeError, ValueError):
            quantite = 1
        if produit:
            res.reconnus[produit] = res.reconnus.get(produit, 0) + quantite
        elif lu:
            res.non_reconnus.append(lu)
    return res


def lire_photo(contenu: bytes, noms_catalogue: list[str], libelles: dict[str, str], cle_api: str,
               modele: str = MODELE_PAR_DEFAUT) -> ResultatScan:
    import anthropic

    donnees, type_media = preparer_image(contenu)
    client = anthropic.Anthropic(api_key=cle_api)
    message = client.messages.create(
        model=modele,
        max_tokens=1500,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": type_media, "data": donnees}},
            {"type": "text", "text": consigne([libelles.get(n, n) for n in noms_catalogue])},
        ]}],
    )
    texte = "".join(b.text for b in message.content if getattr(b, "type", "") == "text")
    return analyser_reponse(texte, noms_catalogue, libelles)


# ------------------------------------------------------------------ sans IA : liste tapée
MOTS_CLES = {
    "Café en grains": ["cafe en grains", "cafe en grain", "cafe grains", "grains de cafe"],
    "Café soluble": ["cafe soluble", "nescafe", "cafe"],
    "Huile de colza": ["huile de colza", "colza"],
    "Huile de tournesol": ["huile de tournesol", "tournesol", "huile"],
    "Pommes rissolées": ["pommes rissolees", "rissolees", "rissolee"],
    "Purée nature (flocons)": ["puree"],
    "Petits suisses nature": ["petits suisses", "petit suisse", "petits-suisses"],
    "Haricots verts extra-fins": ["haricots verts", "haricots", "haricot"],
    "Macédoine de légumes": ["macedoine"],
    "Crème fraîche épaisse 15 %": ["creme fraiche", "creme"],
    "Thon albacore au naturel": ["thon"],
    "Vinaigre d'alcool blanc": ["vinaigre"],
    "Couscous moyen": ["couscous", "semoule"],
    "Coulommiers": ["coulommiers", "brie", "camembert"],
    "Beurre allégé": ["beurre"],
    "Ratatouille": ["ratatouille"],
    "Eau de source": ["eau"],
    "Dattes": ["dattes", "datte"],
    "Penne": ["penne"],
    "Riz thaï": ["riz"],
    "Spaghetti": ["spaghetti", "spaghettis", "pates"],
}
NOMBRES = {"un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "dix": 10, "douze": 12}


def _simplifier(texte: str) -> str:
    sans_accents = "".join(c for c in unicodedata.normalize("NFD", texte.lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]+", " ", sans_accents).strip()


def _quantite(ligne: str) -> int:
    m = re.search(r"(?:^|\s|x)(\d{1,2})(?:\s*x)?(?=\s|$)", ligne)
    if m:
        return max(1, min(30, int(m.group(1))))
    for mot, valeur in NOMBRES.items():
        if re.search(rf"\b{mot}\b", ligne):
            return valeur
    return 1


def lire_texte(texte: str, noms_catalogue: list[str]) -> ResultatScan:
    """Reconnaît une liste tapée au clavier (une ligne ou une virgule par article)."""
    res = ResultatScan()
    for brut in re.split(r"[\n,;]+", texte):
        ligne = _simplifier(brut)
        if not ligne:
            continue
        res.lignes_lues.append(brut.strip())
        trouve = None
        for produit, mots in MOTS_CLES.items():
            if produit in noms_catalogue and any(re.search(rf"\b{re.escape(m)}\b", ligne) for m in mots):
                trouve = produit
                break
        if trouve:
            res.reconnus[trouve] = res.reconnus.get(trouve, 0) + _quantite(ligne)
        else:
            res.non_reconnus.append(brut.strip())
    return res
