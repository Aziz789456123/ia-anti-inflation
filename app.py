"""
IA Anti-Inflation · Besançon — version consommateur (épurée)

Ce que voit l'utilisateur, en 3 gestes :
  1. il prend sa liste en photo,
  2. il dit d'où il part et comment il se déplace,
  3. l'application lui dit où aller, combien il paie, et l'y guide.

La version détaillée (comparaisons, prix de l'essence, sources) est dans app_complet.py.
Lancer :   streamlit run app.py
"""

from __future__ import annotations

import os
from datetime import datetime

import folium
import streamlit as st
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
from streamlit_searchbox import st_searchbox

from moteur import Point, Reseau, Transport, itineraire, recommander
from moteur import carburant as carb
from moteur import vehicules as veh
from moteur.donnees import charger_catalogue, charger_magasins, charger_quartiers, charger_sources, table_prix
from moteur.liens import lien_google_maps, lien_waze
from moteur.localisation import adresse_de, lire_geolocalisation, rechercher_adresse
from moteur.scan import MODELE_PAR_DEFAUT, lire_photo, lire_texte

st.set_page_config(page_title="IA Anti-Inflation", page_icon="🛒", layout="centered", initial_sidebar_state="collapsed")

VERT, VERT_FONCE, VERT_PALE = "#16794C", "#0F5A38", "#E6F4EC"
ENCRE, GRIS, TRAIT, FOND = "#14201A", "#5D6B63", "#DCE4DF", "#F4F7F5"
BLEU_GPS = "#1A73E8"
COULEUR = {"Lidl": "#1F4FA3", "Aldi": "#E07B00"}

st.markdown(f"""
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,700&display=swap" rel="stylesheet">
<style>
  html, body, [class*="css"], .stMarkdown, button, input, textarea {{ font-family:"DM Sans", system-ui, sans-serif; }}
  .block-container {{ padding-top:2.4rem; padding-bottom:3rem; max-width:640px; }}
  .tete {{ display:flex; align-items:center; gap:12px; margin-bottom:4px; }}
  .logo {{ width:44px; height:44px; border-radius:13px; background:{VERT}; display:flex; align-items:center; justify-content:center; flex:none; }}
  .nom {{ font-family:"Bricolage Grotesque"; font-weight:800; font-size:1.55rem; color:{ENCRE}; line-height:1; }}
  .slogan {{ color:{GRIS}; font-size:.95rem; margin:2px 0 14px; }}
  .q {{ font-family:"Bricolage Grotesque"; font-weight:800; font-size:1.15rem; color:{ENCRE}; margin:0 0 6px; }}
  .petit {{ color:{GRIS}; font-size:.84rem; line-height:1.45; }}
  .puces {{ display:flex; flex-wrap:wrap; gap:6px; margin:6px 0 2px; }}
  .puce {{ background:{VERT_PALE}; color:{VERT_FONCE}; border-radius:99px; padding:4px 10px; font-size:.82rem; font-weight:600; }}
  .puce.gris {{ background:{FOND}; color:{GRIS}; font-weight:500; }}
  .resultat {{ background:linear-gradient(135deg,{VERT} 0%,{VERT_FONCE} 100%); color:white; border-radius:20px; padding:20px 22px; margin-top:6px; }}
  .resultat .k {{ opacity:.8; font-size:.74rem; letter-spacing:.1em; text-transform:uppercase; }}
  .resultat .ou {{ font-family:"Bricolage Grotesque"; font-weight:800; font-size:1.75rem; line-height:1.1; margin:4px 0 2px; }}
  .resultat .adr {{ opacity:.85; font-size:.9rem; }}
  .resultat .chiffres {{ display:flex; gap:22px; margin-top:14px; flex-wrap:wrap; }}
  .resultat .v {{ font-family:"Bricolage Grotesque"; font-weight:800; font-size:1.6rem; line-height:1.1; }}
  .resultat .l {{ opacity:.82; font-size:.8rem; }}
  .resultat .msg {{ margin-top:12px; font-size:.93rem; line-height:1.45; background:rgba(255,255,255,.12); border-radius:12px; padding:9px 12px; }}
  a.btn {{ display:block; text-align:center; text-decoration:none !important; font-weight:700; border-radius:12px; padding:13px; color:white !important; margin-top:8px; }}
  a.btn.g {{ background:{BLEU_GPS}; }} a.btn.w {{ background:#33CCFF; color:#06222E !important; }}
  .achats {{ padding-left:1.1rem; margin:4px 0 8px; }} .achats li {{ margin:2px 0; }}
  .resultat {{ margin-bottom:12px; }}
  @media (max-width:640px) {{ .resultat .ou {{ font-size:1.45rem; }} }}
</style>
""", unsafe_allow_html=True)


def eur(v: float, d: int = 2) -> str:
    return f"{v:,.{d}f} €".replace(",", " ").replace(".", ",")


def nb(v: float, d: int = 1) -> str:
    return f"{v:.{d}f}".replace(".", ",")


def duree(minutes: float) -> str:
    m = max(1, round(minutes))
    return f"{m} min" if m < 60 else f"{m // 60} h {m % 60:02d}"


def date_fr(iso: str | None) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return iso or "?"


def secret(nom: str, defaut: str | None = None) -> str | None:
    try:
        return st.secrets[nom]
    except Exception:
        return os.environ.get(nom, defaut)


@st.cache_data(ttl=3600)
def donnees():
    return charger_catalogue(), charger_magasins(), charger_quartiers(), charger_sources()


@st.cache_data(ttl=600, show_spinner=False)
def essence(lat: float, lon: float):
    return carb.stations_autour(Point(lat, lon), rayon_km=10)


@st.cache_data(ttl=3600, show_spinner=False)
def suggestions(texte: str):
    return rechercher_adresse(texte)


@st.cache_data(ttl=86400, show_spinner=False)
def adresse_gps(lat: float, lon: float):
    return adresse_de(Point(lat, lon))


catalogue, magasins, quartiers, sources = donnees()
prix = table_prix(catalogue, magasins)
noms = [p.nom for p in catalogue]
libelles = {p.nom: p.libelle for p in catalogue}
EXEMPLE = {"Spaghetti": 1, "Riz thaï": 1, "Huile de tournesol": 1, "Thon albacore au naturel": 1, "Coulommiers": 1,
           "Café soluble": 1, "Petits suisses nature": 1, "Haricots verts extra-fins": 2, "Eau de source": 6}

ss = st.session_state
ss.setdefault("liste", dict(EXEMPLE))
ss.setdefault("liste_source", "exemple")
ss.setdefault("non_compares", [])
ss.setdefault("depart", quartiers["Centre-ville (Granvelle)"])
ss.setdefault("depart_label", "Centre-ville, Besançon")
ss.setdefault("geo_essai", 0)

# ====================================================================== en-tête
st.markdown("""
<div class="tete"><div class="logo"><svg width="25" height="25" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.2"
 stroke-linecap="round" stroke-linejoin="round"><path d="M3 4h2l2.4 10.2a2 2 0 0 0 2 1.6h7.7a2 2 0 0 0 1.9-1.4L21 8H7"/>
 <circle cx="10" cy="20" r="1.4"/><circle cx="17" cy="20" r="1.4"/><path d="M13 9.5v4M11 11.5l2 2 2-2"/></svg></div>
 <div class="nom">IA Anti-Inflation</div></div>
<div class="slogan">Prends ta liste en photo : on te dit où tes courses coûtent le moins cher à Besançon, trajet compris.</div>
""", unsafe_allow_html=True)

# ====================================================================== 1. la liste
with st.container(border=True):
    st.markdown('<div class="q">📸 Ta liste de courses</div>', unsafe_allow_html=True)
    onglet_photo, onglet_texte = st.tabs(["Prendre une photo", "L'écrire"])
    with onglet_photo:
        photo = st.file_uploader("Photo de ta liste ou de ton ticket", type=["jpg", "jpeg", "png", "webp"],
                                 label_visibility="collapsed")
        if photo:
            cle = secret("ANTHROPIC_API_KEY")
            if not cle:
                st.info("La lecture des photos sera bientôt disponible. En attendant, écris ta liste dans l'onglet « L'écrire ».")
            elif st.button("✨ Lire ma liste", type="primary", use_container_width=True):
                with st.spinner("Je lis ta liste…"):
                    try:
                        res = lire_photo(photo.getvalue(), noms, libelles, cle, secret("ANTHROPIC_MODEL", MODELE_PAR_DEFAUT))
                    except Exception:
                        res = None
                if res is None:
                    st.error("Je n'ai pas réussi à lire la photo. Réessaie avec une photo nette et bien éclairée.")
                else:
                    ss.liste, ss.liste_source, ss.non_compares = dict(res.reconnus), "photo", res.non_reconnus
                    st.rerun()
    with onglet_texte:
        texte = st.text_area("Ta liste", height=100, label_visibility="collapsed",
                             placeholder="Une ligne par article :\n2 paquets de pâtes\nriz\nthon x3")
        if st.button("Valider ma liste", use_container_width=True):
            if texte.strip():
                res = lire_texte(texte, noms)
                ss.liste, ss.liste_source, ss.non_compares = dict(res.reconnus), "texte", res.non_reconnus
                st.rerun()

    liste = {n: q for n, q in ss.liste.items() if q > 0}
    titre_liste = {"exemple": "Exemple de liste — remplace-la par la tienne", "photo": "Lu sur ta photo",
                   "texte": "Ta liste"}[ss.liste_source]
    st.markdown(f'<div class="petit">{titre_liste} :</div><div class="puces">'
                + "".join(f'<span class="puce">{q} × {n}</span>' for n, q in liste.items())
                + "".join(f'<span class="puce gris">{x} (pas encore comparé)</span>' for x in ss.non_compares[:8])
                + "</div>", unsafe_allow_html=True)

# ====================================================================== 2. le départ
with st.container(border=True):
    st.markdown('<div class="q">📍 Tu pars d\'où ?</div>', unsafe_allow_html=True)
    if st.button("Me localiser", use_container_width=True):
        ss.geo_essai += 1
        ss.geo_attente = True
    if ss.get("geo_attente"):
        rep = get_geolocation(component_key=f"geo_{ss.geo_essai}")
        if rep is not None:
            ss.geo_attente = False
            lu = lire_geolocalisation(rep)
            if lu:
                ss.depart = lu[0]
                ss.depart_label = adresse_gps(round(lu[0].lat, 5), round(lu[0].lon, 5)) or "Ma position"
                st.rerun()
            else:
                st.warning("Localisation refusée : tape ton adresse ci-dessous.")
    choix = st_searchbox(lambda t: [(lab, (p.lat, p.lon, lab)) for lab, p in suggestions(t)],
                         placeholder="ou tape ton adresse", key="adresse")
    if choix and ss.get("adresse_retenue") != choix:
        ss.adresse_retenue = choix
        ss.depart, ss.depart_label = Point(choix[0], choix[1], "adresse"), choix[2]
        st.rerun()
    st.markdown(f'<div class="petit">Départ : <b>{ss.depart_label}</b></div>', unsafe_allow_html=True)

# ====================================================================== 3. le déplacement
stations, _ = essence(round(ss.depart.lat, 3), round(ss.depart.lon, 3))
with st.container(border=True):
    st.markdown('<div class="q">🚗 Tu y vas comment ?</div>', unsafe_allow_html=True)
    mode = st.segmented_control("Mode", ["🚗 Voiture", "🚶 À pied", "🚲 Vélo", "🚌 Bus"], default="🚗 Voiture",
                                label_visibility="collapsed") or "🚗 Voiture"
    transport, carburant, station = Transport.sans_voiture(), None, None
    if mode == "🚗 Voiture":
        with st.expander("Ma voiture : citadine essence (modifier)"):
            marques = veh.marques()
            marque = st.selectbox("Marque", ["Je ne sais pas"] + marques)
            if marque == "Je ne sais pas":
                vehicule = veh.vehicule_type(veh.categories()[1], "Essence")
            else:
                modele = st.selectbox("Modèle", veh.modeles(marque))
                motos = veh.motorisations(marque, modele)
                moto = st.selectbox("Motorisation", motos, index=motos.index("Essence") if "Essence" in motos else 0)
                vehicule = veh.vehicule(marque, modele, moto)
        if vehicule.electrique:
            transport = Transport.voiture(vehicule.conso_ville, 0.20, "kWh")
        else:
            carburant = carb.CARBURANT_PAR_MOTORISATION.get(vehicule.motorisation, "SP95-E10")
            station = carb.moins_chere(stations, carburant) or next((s for s in stations if carburant in s.prix), None)
            transport = Transport.voiture(vehicule.conso_ville, station.prix[carburant] if station else 2.0)

# ====================================================================== résultat
st.write("")
if not liste:
    st.info("Ajoute au moins un produit à ta liste pour voir où aller.")
    st.stop()

depart = ss.depart
reseau = Reseau(depart, magasins)
reco = recommander(liste, prix, magasins, depart, transport, seuil=2, reseau=reseau)
c, g = reco.conseil, reco.gain_de_temps
voiture = transport.motorise
vitesse = {"🚶 À pied": 4.5, "🚲 Vélo": 14, "🚌 Bus": 15}.get(mode)
minutes = c.minutes if voiture or not vitesse else c.distance_km / vitesse * 60

if c.nb_magasins > 1:
    ou, adresse = f"{c.magasins[0].nom} puis {c.magasins[1].nom}", "Deux magasins : le détour vaut le coup"
else:
    ou, adresse = c.magasins[0].nom, c.magasins[0].adresse

autres = [s for k, s in reco.par_enseigne.items() if c.nb_magasins > 1 or k != c.magasins[0].enseigne]
autre = min(autres, key=lambda s: s.total) if autres else None
ecart = round(autre.total - c.total, 2) if autre else 0
if ecart > 0.004:
    message = (f"Tu économises <b>{eur(ecart)}</b> par rapport à {autre.enseignes}"
               f"{', essence comprise' if voiture else ''}, soit environ <b>{eur(ecart * 52, 0)} par an</b> "
               "si tu fais ces courses chaque semaine.")
elif autre:
    message = (f"C'est le plus proche. {autre.magasins[0].nom} serait {eur(-ecart)} moins cher, "
               "mais c'est plus loin : ça ne vaut pas le détour.")
else:
    message = ""
trajet = f"essence {eur(c.cout_trajet)}" if voiture else "sans frais de trajet"

st.markdown(f"""
<div class="resultat">
  <div class="k">Notre conseil</div>
  <div class="ou">👉 Va chez {ou}</div>
  <div class="adr">{adresse}</div>
  <div class="chiffres">
    <div><div class="v">{eur(c.total)}</div><div class="l">tu paies au total ({trajet})</div></div>
    <div><div class="v">{duree(minutes)}</div><div class="l">aller-retour · {nb(c.distance_km)} km</div></div>
  </div>
  {f'<div class="msg">{message}</div>' if message else ''}
</div>""", unsafe_allow_html=True)

# --- carte
etapes = itineraire([depart, *(m.position for m in c.magasins), depart])
carte = folium.Map(location=[depart.lat, depart.lon], zoom_start=13, tiles="CartoDB.Voyager", zoom_snap=0.25,
                   zoom_control=False)
for i, t in enumerate(etapes):
    retour = i == len(etapes) - 1
    folium.PolyLine(t.trace, color="white", weight=10, opacity=0.95).add_to(carte)
    folium.PolyLine(t.trace, color=BLEU_GPS, weight=6, opacity=0.6 if retour else 0.95,
                    dash_array="1 10" if retour else None).add_to(carte)
folium.CircleMarker([depart.lat, depart.lon], radius=9, color="white", weight=3, fill=True, fill_color=BLEU_GPS,
                    fill_opacity=1, tooltip="Toi").add_to(carte)
for k, m in enumerate(c.magasins, start=1):
    coul = COULEUR.get(m.enseigne, "#666")
    folium.Marker([m.position.lat, m.position.lon], tooltip=m.nom, icon=folium.DivIcon(
        icon_size=(170, 34), icon_anchor=(17, 17), html=(
            f'<div style="display:flex;align-items:center;gap:5px"><div style="background:{coul};color:white;'
            f'font:800 13px sans-serif;border:3px solid white;box-shadow:0 1px 5px rgba(0,0,0,.35);border-radius:50%;'
            f'width:34px;height:34px;display:flex;align-items:center;justify-content:center">{k}</div>'
            f'<div style="background:white;padding:2px 7px;border-radius:6px;font:700 12px sans-serif;color:{coul};'
            f'box-shadow:0 1px 3px rgba(0,0,0,.3);white-space:nowrap">{m.nom}</div></div>'))).add_to(carte)
pts = [p for t in etapes for p in t.trace]
la, lo = [p[0] for p in pts], [p[1] for p in pts]
mla, mlo = (max(la) - min(la)) * 0.1 + 0.002, (max(lo) - min(lo)) * 0.1 + 0.002
carte.fit_bounds([[min(la) - mla, min(lo) - mlo], [max(la) + mla, max(lo) + mlo * 3]])
st_folium(carte, height=300, use_container_width=True, returned_objects=[], key="carte")

mode_gm = {"🚗 Voiture": "driving", "🚶 À pied": "walking", "🚲 Vélo": "bicycling", "🚌 Bus": "transit"}[mode]
boutons = f'<a class="btn g" href="{lien_google_maps(depart, [m.position for m in c.magasins], mode_gm)}" target="_blank">🧭 Y aller avec Google Maps</a>'
if voiture and c.nb_magasins == 1:
    boutons += f'<a class="btn w" href="{lien_waze(c.magasins[0].position)}" target="_blank">🚙 Y aller avec Waze</a>'
st.markdown(boutons, unsafe_allow_html=True)

# --- ce qu'on achète
with st.container(border=True):
    for m in c.magasins:
        produits = [p for p, mid in c.affectation.items() if mid == m.id]
        lignes = "".join(f"<li>{liste[p]} × {libelles[p]} — <b>{eur(prix[p][m.id] * liste[p])}</b></li>" for p in produits)
        st.markdown(f'<div class="q" style="color:{COULEUR.get(m.enseigne, ENCRE)}">🛒 Chez {m.nom}</div>'
                    f'<ul class="achats">{lignes}</ul><div><b>Total courses : {eur(c.detail[m.id])}</b></div>',
                    unsafe_allow_html=True)

# --- pied de page
sl, sa = sources["Lidl"], sources["Aldi"]
with st.expander("D'où viennent les prix ?"):
    st.markdown(f"""
- **Aldi** : prix affichés sur aldi.fr, relevés le {date_fr(sa.get('collecte_le'))}.
- **Lidl** : prix officiels publiés par Lidl (relevés du {date_fr(sl.get('prix_releves_le'))}).
- **Essence** : prix déclarés par les stations (data.economie.gouv.fr), en direct
  {f"— ici {carburant} à {eur(station.prix[carburant], 3)}/L, {station.libelle}" if station and carburant else ""}.
- **Consommation** : valeurs officielles ADEME · **Cartes et trajets** : OpenStreetMap.
""")
st.caption("IA Anti-Inflation · prototype · Besançon, 2026")
