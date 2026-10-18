"""
IA Anti-Inflation · Besançon
Où faire ses courses moins cher, trajet compris : Lidl ou Aldi ?

Lancer l'application :   streamlit run app.py
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
from streamlit_searchbox import st_searchbox

from moteur import Point, Reseau, Transport, itineraire, recommander
from moteur import carburant as carb
from moteur import vehicules as veh
from moteur.donnees import (charger_catalogue, charger_magasins, charger_promos, charger_quartiers,
                            charger_sources, table_prix)
from moteur.liens import lien_google_maps, lien_waze
from moteur.localisation import adresse_de, lire_geolocalisation, rechercher_adresse
from moteur.scan import MODELE_PAR_DEFAUT, lire_photo, lire_texte

st.set_page_config(page_title="IA Anti-Inflation · Besançon", page_icon="🛒", layout="wide",
                   initial_sidebar_state="collapsed")

# ====================================================================== apparence
VERT, VERT_FONCE, VERT_PALE = "#16794C", "#0F5A38", "#E6F4EC"
ENCRE, GRIS, TRAIT, FOND = "#14201A", "#5D6B63", "#DCE4DF", "#F2F5F3"
ORANGE, BLEU_GPS = "#D9822B", "#1A73E8"
COULEUR = {"Lidl": "#1F4FA3", "Aldi": "#E07B00"}

st.markdown(
    f"""
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,700&display=swap" rel="stylesheet">
<style>
  html, body, [class*="css"], .stMarkdown, .stText, button, input, textarea {{ font-family: "DM Sans", system-ui, sans-serif; }}
  .block-container {{ padding-top: 2.6rem; padding-bottom: 3rem; max-width: 1260px; }}
  h1, h2, h3, h4, .titre {{ font-family: "Bricolage Grotesque", "DM Sans", sans-serif !important; letter-spacing: -0.01em; }}
  .entete {{ display:flex; justify-content:space-between; align-items:flex-end; gap:16px; flex-wrap:wrap; margin-bottom:6px; }}
  .marque {{ display:flex; align-items:center; gap:12px; }}
  .logo {{ width:46px; height:46px; border-radius:13px; background:{VERT}; display:flex; align-items:center; justify-content:center; flex:none; }}
  .nom {{ font-family:"Bricolage Grotesque"; font-weight:800; font-size:1.7rem; color:{ENCRE}; line-height:1; }}
  .slogan {{ color:{GRIS}; font-size:.98rem; margin-top:4px; }}
  .puces {{ display:flex; gap:8px; flex-wrap:wrap; }}
  .puce {{ display:inline-flex; align-items:center; gap:7px; background:{FOND}; border:1px solid {TRAIT}; border-radius:99px;
           padding:5px 11px; font-size:.8rem; color:{ENCRE}; white-space:nowrap; }}
  .puce i {{ width:8px; height:8px; border-radius:50%; background:{VERT}; display:inline-block; }}
  .puce i.orange {{ background:{ORANGE}; }}
  .etiquette {{ display:flex; align-items:center; gap:9px; font-weight:700; font-size:1.02rem; margin-bottom:6px; color:{ENCRE}; }}
  .etiquette .n {{ background:{VERT}; color:white; border-radius:50%; width:24px; height:24px; display:flex; align-items:center;
                   justify-content:center; font-size:.8rem; flex:none; }}
  .choisi {{ background:{VERT_PALE}; border-radius:10px; padding:8px 11px; font-size:.9rem; margin:4px 0 8px; }}
  .petit {{ color:{GRIS}; font-size:.84rem; line-height:1.45; }}
  .reco {{ background:linear-gradient(135deg,{VERT} 0%,{VERT_FONCE} 100%); color:white; border-radius:18px; padding:20px 24px; }}
  .reco .k {{ opacity:.82; font-size:.76rem; letter-spacing:.09em; text-transform:uppercase; }}
  .reco .t {{ font-family:"Bricolage Grotesque"; font-size:1.85rem; font-weight:800; line-height:1.1; margin:5px 0 8px; }}
  .reco .p {{ font-size:1rem; opacity:.96; line-height:1.5; }}
  .kpis {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin:12px 0; }}
  .kpi {{ background:{FOND}; border-radius:14px; padding:11px 13px; min-width:0; }}
  .kpi .l {{ color:{GRIS}; font-size:.78rem; }}
  .kpi .v {{ font-family:"Bricolage Grotesque"; font-size:1.45rem; font-weight:800; font-variant-numeric:tabular-nums; color:{ENCRE}; }}
  .kpi .v.vert {{ color:{VERT}; }}
  .kpi .s {{ color:{GRIS}; font-size:.76rem; }}
  .boutons {{ display:flex; gap:8px; flex-wrap:wrap; margin:10px 0 2px; }}
  a.btn {{ flex:1 1 180px; text-align:center; text-decoration:none !important; font-weight:700; border-radius:11px; padding:11px 12px; color:white !important; }}
  a.btn.g {{ background:{BLEU_GPS}; }}
  a.btn.w {{ background:#33CCFF; color:#06222E !important; }}
  .option {{ border:1px solid {TRAIT}; border-radius:15px; padding:14px 16px; height:100%; }}
  .option.win {{ border:2px solid {VERT}; background:{VERT_PALE}80; }}
  .option h4 {{ margin:6px 0 4px; font-size:1.05rem; }}
  .option .m {{ font-family:"Bricolage Grotesque"; font-size:1.65rem; font-weight:800; margin:4px 0 2px; font-variant-numeric:tabular-nums; }}
  .option .s {{ color:{GRIS}; font-size:.86rem; }}
  .pill {{ display:inline-block; background:{VERT}; color:white; border-radius:99px; padding:2px 10px; font-size:.72rem; font-weight:700; }}
  .pill.gris {{ background:#D4DCD7; color:#26302B; }}
  .panier {{ border-radius:14px; padding:13px 15px; }}
  .panier h4 {{ margin:0 0 6px; }}
  .panier ul {{ margin:0; padding-left:1.1rem; }} .panier li {{ margin:2px 0; }}
  .instr {{ counter-reset:i; list-style:none; padding:0; margin:0 0 10px; }}
  .instr li {{ padding:6px 0 6px 30px; position:relative; border-bottom:1px dashed {TRAIT}; font-size:.9rem; }}
  .instr li::before {{ counter-increment:i; content:counter(i); position:absolute; left:0; top:6px; width:21px; height:21px; border-radius:50%;
                       background:{FOND}; color:{GRIS}; font-size:.72rem; display:flex; align-items:center; justify-content:center; }}
  .promo {{ border:1px solid {TRAIT}; border-radius:14px; padding:13px 15px; height:100%; }}
  .promo .prix {{ font-family:"Bricolage Grotesque"; font-weight:800; font-size:1.5rem; color:{ENCRE}; }}
  .promo .barre {{ text-decoration:line-through; color:{GRIS}; margin-left:6px; }}
  .promo .badge {{ display:inline-block; background:#FFE9D6; color:#8A4300; border-radius:7px; padding:2px 8px; font-size:.74rem; font-weight:700; }}
  .source {{ border-left:4px solid {VERT}; background:{FOND}; border-radius:10px; padding:12px 15px; margin-bottom:10px; }}
  div[data-testid="stTabs"] button p {{ font-size:1rem; font-weight:600; }}
  .presentation {{ background:linear-gradient(120deg,{VERT_PALE} 0%,#F7FBF8 70%); border:1px solid #CFE6D8; border-radius:18px;
                   padding:18px 20px; margin:4px 0 16px; }}
  .pres-titre {{ font-family:"Bricolage Grotesque"; font-weight:800; font-size:1.45rem; line-height:1.2; color:{ENCRE};
                 margin-bottom:12px; text-wrap:balance; }}
  .pres-titre span {{ color:{VERT}; }}
  .pres-etapes {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; }}
  .pres-etape {{ background:white; border-radius:14px; padding:12px 14px; display:flex; gap:11px; align-items:flex-start;
                 font-size:.9rem; color:{GRIS}; line-height:1.45; box-shadow:0 1px 2px rgba(20,32,26,.06); }}
  .pres-etape b {{ color:{ENCRE}; font-size:.97rem; }}
  .pres-etape .ic {{ font-size:1.5rem; line-height:1; flex:none; }}
  .travail {{ border:1px solid {TRAIT}; border-radius:14px; padding:10px 14px; margin-bottom:12px; background:white; }}
  .travail .k {{ font-size:.74rem; letter-spacing:.09em; text-transform:uppercase; color:{GRIS}; margin-bottom:4px; }}
  .travail ul {{ list-style:none; margin:0; padding:0; }}
  .travail li {{ font-size:.86rem; padding:3px 0 3px 24px; position:relative; color:{ENCRE}; }}
  .travail li::before {{ content:"✓"; position:absolute; left:0; top:2px; width:17px; height:17px; border-radius:50%; background:{VERT};
                         color:white; font-size:.68rem; font-weight:800; display:flex; align-items:center; justify-content:center; }}
  .travail li span {{ color:{GRIS}; }}
  @media (max-width: 760px) {{ .pres-etapes {{ grid-template-columns:1fr; gap:8px; }} .pres-titre {{ font-size:1.2rem; }}
                               .kpis {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} .reco .t {{ font-size:1.45rem; }}
                               .nom {{ font-size:1.4rem; }} .block-container {{ padding-top:2rem; }} }}
</style>
""",
    unsafe_allow_html=True,
)


def eur(v: float, d: int = 2) -> str:
    return f"{v:,.{d}f} €".replace(",", " ").replace(".", ",")


def nb(v: float, d: int = 1) -> str:
    return f"{v:.{d}f}".replace(".", ",")


def duree(minutes: float) -> str:
    m = max(1, round(minutes))
    return f"{m} min" if m < 60 else f"{m // 60} h {m % 60:02d}"


def il_y_a(dt: datetime | None) -> str:
    if not dt:
        return "date inconnue"
    s = (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds()
    if s < 3600:
        return f"il y a {max(1, int(s // 60))} min"
    if s < 86400:
        return f"il y a {int(s // 3600)} h"
    return f"il y a {int(s // 86400)} j"


def secret(nom: str, defaut: str | None = None) -> str | None:
    """Réglage secret (clé d'IA…) : dans les « Secrets » de Streamlit Cloud ou une variable d'environnement."""
    try:
        return st.secrets[nom]
    except Exception:
        return os.environ.get(nom, defaut)


def date_fr(iso: str | None) -> str:
    if not iso:
        return "?"
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y")
    except ValueError:
        return iso


# ====================================================================== données (mises en cache)
@st.cache_data(ttl=3600)
def donnees_fixes():
    return charger_catalogue(), charger_magasins(), charger_quartiers(), charger_sources(), charger_promos()


@st.cache_data(ttl=600, show_spinner=False)   # essence : rafraîchie toutes les 10 minutes
def essence(lat: float, lon: float):
    return carb.stations_autour(Point(lat, lon), rayon_km=10)


@st.cache_data(ttl=3600, show_spinner=False)
def suggestions(texte: str):
    return rechercher_adresse(texte)


@st.cache_data(ttl=86400, show_spinner=False)
def adresse_gps(lat: float, lon: float):
    return adresse_de(Point(lat, lon))


catalogue, magasins, quartiers, sources, promos = donnees_fixes()
prix = table_prix(catalogue, magasins)
par_nom = {p.nom: p for p in catalogue}

PANIERS = {
    "Étudiant": {"Spaghetti": 1, "Penne": 1, "Riz thaï": 1, "Huile de tournesol": 1, "Thon albacore au naturel": 1,
                 "Coulommiers": 1, "Café soluble": 1, "Petits suisses nature": 1, "Haricots verts extra-fins": 2,
                 "Pommes rissolées": 1, "Eau de source": 6},
    "Famille": {"Spaghetti": 2, "Penne": 2, "Riz thaï": 1, "Couscous moyen": 1, "Huile de colza": 1,
                "Café en grains": 1, "Coulommiers": 2, "Crème fraîche épaisse 15 %": 1, "Beurre allégé": 2,
                "Petits suisses nature": 2, "Macédoine de légumes": 2, "Ratatouille": 2, "Thon albacore au naturel": 2,
                "Pommes rissolées": 2, "Eau de source": 12, "Dattes": 1, "Purée nature (flocons)": 1},
}

ss = st.session_state
ss.setdefault("depart", quartiers["Centre-ville (Granvelle)"])
ss.setdefault("depart_label", "Centre-ville (Granvelle), Besançon")
ss.setdefault("depart_source", "quartier")
ss.setdefault("panier", "Étudiant")
ss.setdefault("liste_base", dict(PANIERS["Étudiant"]))
ss.setdefault("version_liste", 0)
ss.setdefault("geo_essai", 0)

# ====================================================================== en-tête
date_aldi = sources["Aldi"].get("collecte_le")
date_lidl = sources["Lidl"].get("prix_releves_le")
stations, info_essence = essence(round(ss.depart.lat, 3), round(ss.depart.lon, 3))
puce_essence = ('<span class="puce"><i></i>Essence : prix officiels en direct</span>' if info_essence["direct"]
                else f'<span class="puce"><i class="orange"></i>Essence : copie du {info_essence["recupere_le"]:%d/%m %H:%M}</span>')
st.markdown(
    f"""
<div class="entete">
  <div class="marque">
    <div class="logo"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M3 4h2l2.4 10.2a2 2 0 0 0 2 1.6h7.7a2 2 0 0 0 1.9-1.4L21 8H7"/><circle cx="10" cy="20" r="1.4"/><circle cx="17" cy="20" r="1.4"/><path d="M13 9.5v4M11 11.5l2 2 2-2"/></svg></div>
    <div><div class="nom">IA Anti-Inflation</div>
    <div class="slogan">Vos courses au meilleur prix à Besançon, <b>trajet et essence compris</b>.</div></div>
  </div>
  <div class="puces">
    <span class="puce"><i></i>Aldi : prix du {date_fr(date_aldi)}</span>
    <span class="puce"><i></i>Lidl : prix officiels du {date_fr(date_lidl)}</span>
    {puce_essence}
  </div>
</div>
""",
    unsafe_allow_html=True,
)

onglet_courses, onglet_essence, onglet_promos, onglet_sources = st.tabs(
    ["🛒  Mes courses", "⛽  Prix de l'essence", "🏷️  Promos de la semaine", "ℹ️  D'où viennent les prix"])

# ====================================================================== onglet 1 : courses
with onglet_courses:
    st.markdown(f"""
<div class="presentation">
  <div class="pres-titre">Prenez votre liste en photo : l'IA trouve où vos courses coûtent le moins cher, <span>trajet compris</span>.</div>
  <div class="pres-etapes">
    <div class="pres-etape"><div class="ic">📸</div><div><b>1. Vous photographiez votre liste</b><br>
      L'IA lit votre écriture et reconnaît chaque produit, avec la quantité.</div></div>
    <div class="pres-etape"><div class="ic">🔎</div><div><b>2. L'IA compare tout</b><br>
      Les prix dans les {len(magasins)} Lidl et Aldi de Besançon, le trajet depuis chez vous et l'essence de votre voiture.</div></div>
    <div class="pres-etape"><div class="ic">🧭</div><div><b>3. Elle vous dit où aller</b><br>
      Le magasin le moins cher pour vous, ce que vous économisez, et le trajet jusqu'à la porte.</div></div>
  </div>
</div>""", unsafe_allow_html=True)
    col_saisie, col_resultat = st.columns([1.08, 1.5], gap="large")

    # ---------------------------------------------------------------- saisie
    with col_saisie:
        # 1. Liste
        with st.container(border=True):
            st.markdown('<div class="etiquette"><span class="n">1</span>Votre liste de courses</div>', unsafe_allow_html=True)
            facon = st.segmented_control("Façon", ["📸 Photo de ma liste", "✍️ Je l'écris", "📋 Toute prête"],
                                         default="📸 Photo de ma liste", key="facon_liste",
                                         label_visibility="collapsed") or "📋 Toute prête"
            noms = [p.nom for p in catalogue]
            libelles = {p.nom: p.libelle for p in catalogue}

            def appliquer(resultat, source):
                ss.liste_base, ss.dernier_scan = dict(resultat.reconnus), (source, resultat)
                ss.version_liste += 1
                st.rerun()

            if facon.startswith("📸"):
                st.markdown('<div class="petit">Prenez en photo votre liste écrite à la main, ou un ticket de caisse : '
                            "l'IA la lit et remplit le tableau toute seule.</div>", unsafe_allow_html=True)
                photo = st.file_uploader("Photo de la liste", type=["jpg", "jpeg", "png", "webp"], key="photo_liste",
                                         label_visibility="collapsed")
                if photo:
                    cp, cb = st.columns([1, 2])
                    cp.image(photo, width=140)
                    with cb:
                        cle = secret("ANTHROPIC_API_KEY")
                        if not cle:
                            st.info("La lecture des photos n'est pas encore activée sur cette version (clé d'IA à ajouter, "
                                    "voir le README). En attendant, utilisez « Je l'écris ».")
                        elif st.button("✨  Lire ma liste avec l'IA", type="primary", use_container_width=True):
                            with st.spinner("L'IA lit votre liste…"):
                                try:
                                    resultat = lire_photo(photo.getvalue(), noms, libelles, cle,
                                                          secret("ANTHROPIC_MODEL", MODELE_PAR_DEFAUT))
                                except Exception:
                                    resultat = None
                            if resultat is None:
                                st.error("Je n'ai pas réussi à lire la photo. Réessayez avec une photo nette et bien éclairée.")
                            else:
                                appliquer(resultat, "photo")
                    st.caption("La photo est envoyée à un service d'IA (Claude, d'Anthropic) seulement pour être lue ; "
                               "l'application ne la garde pas.")
            elif facon.startswith("✍️"):
                texte = st.text_area("Votre liste", height=110, label_visibility="collapsed",
                                     placeholder="Une ligne par article, par exemple :\n2 paquets de pâtes\nriz\nthon x3\nhuile")
                if st.button("Remplir le tableau", use_container_width=True):
                    if texte.strip():
                        appliquer(lire_texte(texte, noms), "texte")
                    else:
                        st.warning("Écrivez d'abord votre liste dans la case ci-dessus.")
            else:
                choix_panier = st.segmented_control("Liste", ["Étudiant", "Famille", "Vide"], default=ss.panier,
                                                    label_visibility="collapsed", key="choix_panier")
                if choix_panier and choix_panier != ss.panier:
                    ss.panier, ss.liste_base, ss.dernier_scan = choix_panier, PANIERS.get(choix_panier, {}), None
                    ss.version_liste += 1

            if ss.get("dernier_scan"):
                source, res = ss.dernier_scan
                quoi = "sur la photo" if source == "photo" else "dans votre texte"
                if res.reconnus:
                    st.success(f"✅ {len(res.reconnus)} produits reconnus {quoi} : "
                               + ", ".join(f"{q} × {libelles[n]}" for n, q in res.reconnus.items()))
                else:
                    st.warning(f"Aucun produit du comparateur reconnu {quoi}.")
                if res.non_reconnus:
                    st.caption("Pas encore comparés entre Lidl et Aldi : " + ", ".join(res.non_reconnus[:12]))
            base = ss.liste_base
            tableau = pd.DataFrame([{
                "Combien": base.get(p.nom, 0), "Produit": p.libelle,
                "Lidl": p.offres["Lidl"].prix if "Lidl" in p.offres else None,
                "Aldi": p.offres["Aldi"].prix if "Aldi" in p.offres else None, "nom": p.nom,
            } for p in catalogue])
            edite = st.data_editor(
                tableau, hide_index=True, use_container_width=True, height=330, key=f"liste_{ss.version_liste}",
                column_order=["Combien", "Produit", "Lidl", "Aldi"],
                column_config={
                    "Combien": st.column_config.NumberColumn("Qté", min_value=0, max_value=30, step=1, width=52,
                                                             help="Combien en voulez-vous ? 0 = je n'en prends pas"),
                    "Produit": st.column_config.TextColumn(disabled=True, width="medium"),
                    "Lidl": st.column_config.NumberColumn("Lidl", format="%.2f €", disabled=True, width=62),
                    "Aldi": st.column_config.NumberColumn("Aldi", format="%.2f €", disabled=True, width=62),
                },
            )
            liste = {r.nom: int(r.Combien) for r in edite.itertuples() if r.Combien and r.Combien > 0}
            st.caption(f"{len(liste)} produits · {sum(liste.values())} articles · prix réels pour la quantité indiquée.")

        # 2. Départ
        with st.container(border=True):
            st.markdown('<div class="etiquette"><span class="n">2</span>D\'où partez-vous ?</div>', unsafe_allow_html=True)
            if st.button("📍  Me localiser", use_container_width=True, type="primary"):
                ss.geo_essai += 1
                ss.geo_attente = True
            if ss.get("geo_attente"):
                reponse = get_geolocation(component_key=f"geo_{ss.geo_essai}")
                if reponse is not None:
                    ss.geo_attente = False
                    lu = lire_geolocalisation(reponse)
                    if lu:
                        point, precision = lu
                        ss.depart, ss.depart_source, ss.depart_precision = point, "gps", precision
                        ss.depart_label = adresse_gps(round(point.lat, 5), round(point.lon, 5)) or "Ma position actuelle"
                        st.rerun()
                    else:
                        st.warning("La localisation a été refusée ou n'est pas disponible. Tapez votre adresse ci-dessous.")
                else:
                    st.caption("Autorisez la localisation dans la fenêtre de votre navigateur…")

            choix = st_searchbox(lambda t: [(label, (p.lat, p.lon, label)) for label, p in suggestions(t)],
                                 placeholder="ou tapez votre adresse (ex. 12 rue de Dole)", key="adresse")
            if choix and ss.get("adresse_retenue") != choix:
                ss.adresse_retenue = choix
                ss.depart, ss.depart_label, ss.depart_source = Point(choix[0], choix[1], "adresse"), choix[2], "adresse"
                st.rerun()

            with st.expander("ou choisissez un quartier"):
                q = st.selectbox("Quartier", list(quartiers), index=None, placeholder="Quartier de Besançon",
                                 label_visibility="collapsed")
                if q and ss.get("quartier_retenu") != q:
                    ss.quartier_retenu = q
                    ss.depart, ss.depart_label, ss.depart_source = quartiers[q], f"{q}, Besançon", "quartier"
                    st.rerun()
            icone = {"gps": "📍", "adresse": "🏠", "quartier": "🏘️"}[ss.depart_source]
            st.markdown(f'<div class="choisi">{icone} <b>Départ :</b> {ss.depart_label}</div>', unsafe_allow_html=True)

        # 3. Déplacement
        with st.container(border=True):
            st.markdown('<div class="etiquette"><span class="n">3</span>Comment y allez-vous ?</div>', unsafe_allow_html=True)
            mode = st.segmented_control("Mode", ["🚗 Voiture", "🚶 À pied", "🚲 Vélo", "🚌 Bus, tram"],
                                        default="🚗 Voiture", label_visibility="collapsed") or "🚗 Voiture"
            voiture = mode == "🚗 Voiture"
            transport, vehicule, station_choisie, carburant = Transport.sans_voiture(), None, None, None
            if voiture:
                connu = st.toggle("Je connais le modèle de ma voiture", value=True)
                if connu:
                    c1, c2 = st.columns(2)
                    marques = veh.marques()
                    marque = c1.selectbox("Marque", marques, index=marques.index("Renault"))
                    modeles = veh.modeles(marque)
                    modele = c2.selectbox("Modèle", modeles, index=modeles.index("CLIO") if "CLIO" in modeles else 0)
                    motos = veh.motorisations(marque, modele)
                    moto = st.selectbox("Motorisation", motos, index=motos.index("Essence") if "Essence" in motos else 0)
                    vehicule = veh.vehicule(marque, modele, moto)
                else:
                    cat = st.selectbox("Type de voiture", veh.categories(), index=1)
                    motos = veh.motorisations_categorie(cat)
                    moto = st.selectbox("Motorisation", motos, index=motos.index("Essence") if "Essence" in motos else 0)
                    vehicule = veh.vehicule_type(cat, moto)

                if vehicule.electrique:
                    prix_kwh = st.number_input("Prix de votre électricité (€ par kWh)", 0.05, 1.00, 0.20, 0.01,
                                               help="Regardez sur votre facture d'électricité.")
                    transport = Transport.voiture(vehicule.conso_ville, prix_kwh, "kWh")
                    st.markdown(f'<div class="petit">⚡ {vehicule.libelle} : <b>{nb(vehicule.conso_ville)} kWh pour 100 km</b> '
                                f'en ville (consommation officielle ADEME).</div>', unsafe_allow_html=True)
                else:
                    carburant = carb.CARBURANT_PAR_MOTORISATION.get(vehicule.motorisation, "SP95-E10")
                    avec = [s for s in stations if carburant in s.prix]
                    moins_chere = carb.moins_chere(stations, carburant) or (avec[0] if avec else None)
                    options = ["auto"] + [s.id for s in avec[:15]]
                    libelles = {"auto": (f"La moins chère près de chez moi ({eur(moins_chere.prix[carburant], 3)}/L)"
                                         if moins_chere else "Prix moyen")}
                    libelles |= {s.id: f"{eur(s.prix[carburant], 3)}/L · {s.libelle} ({nb(s.distance_km)} km)" for s in avec[:15]}
                    choix_station = st.selectbox(f"Où faites-vous le plein de {carburant} ?", options,
                                                 format_func=lambda k: libelles[k])
                    station_choisie = moins_chere if choix_station == "auto" else next(s for s in avec if s.id == choix_station)
                    prix_litre = station_choisie.prix[carburant] if station_choisie else 2.0
                    transport = Transport.voiture(vehicule.conso_ville, prix_litre)
                    maj = station_choisie.mis_a_jour.get(carburant) if station_choisie else None
                    st.markdown(f'<div class="petit">⛽ {vehicule.libelle} ({vehicule.motorisation.lower()}) : '
                                f'<b>{nb(vehicule.conso_ville)} L pour 100 km</b> en ville (ADEME) · '
                                f'{carburant} à <b>{eur(prix_litre, 3)}/L</b>, prix déclaré {il_y_a(maj)}.</div>',
                                unsafe_allow_html=True)

        with st.expander("Réglage : quand faire un détour ?"):
            seuil = st.slider("Je vais plus loin, ou dans un 2ᵉ magasin, seulement si j'économise au moins", 0, 10, 2, 1,
                              format="%d €")
            st.caption("Exemple : avec 2 €, si un magasin plus loin ne fait gagner que 1 €, l'application vous laisse au "
                       "plus proche. Ce montant sera fixé grâce au questionnaire.")

    # ---------------------------------------------------------------- résultat
    with col_resultat:
        if not liste:
            st.info("Ajoutez au moins un produit à votre liste pour voir où aller.")
        else:
            depart = ss.depart
            with st.spinner("Calcul des trajets…"):
                reseau = Reseau(depart, magasins)
                reco = recommander(liste, prix, magasins, depart, transport, seuil=seuil, reseau=reseau)
            c, g, e, proche = reco.conseil, reco.gain_de_temps, reco.economie_max, reco.plus_proche
            vitesse = {"🚶 À pied": 4.5, "🚲 Vélo": 14, "🚌 Bus, tram": 15}.get(mode)
            temps = (lambda s: s.minutes) if voiture else (lambda s: s.distance_km / vitesse * 60)
            ess = ", essence comprise" if transport.motorise else ""

            if c.nb_magasins > 1:
                titre = f"Allez chez {c.magasins[0].enseigne} puis chez {c.magasins[1].enseigne}"
                phrase = (f"En passant par <b>{c.libelle}</b>, vous économisez <b>{eur(g.total - c.total)}</b> par rapport "
                          f"à un seul magasin{ess}. Le détour vaut le coup.")
            else:
                m = c.magasins[0]
                titre = f"Allez chez {m.nom}"
                autre = next((s for k, s in reco.par_enseigne.items() if k != m.enseigne), None)
                if c is proche and c is g:
                    phrase = f"C'est le magasin <b>le plus proche</b> et <b>le moins cher</b> pour votre liste{ess}. "
                elif c is proche:
                    phrase = (f"C'est le plus proche. {g.magasins[0].nom} serait {eur(proche.total - g.total)} moins cher{ess}, "
                              f"mais c'est plus loin : <b>pas assez pour faire le détour</b>. ")
                else:
                    phrase = (f"Il est plus loin que {proche.magasins[0].nom}, mais vous économisez "
                              f"<b>{eur(proche.total - c.total)}</b>{ess} : le détour vaut le coup. ")
                if autre and autre.total > c.total:
                    phrase += f"Chez {autre.magasins[0].enseigne}, la même liste vous coûterait {eur(autre.total)}."
            # --- ce que l'IA vient de faire, étape par étape
            scan = ss.get("dernier_scan")
            origine_liste = {"photo": "lue sur votre photo", "texte": "lue dans votre texte"}.get(
                scan[0] if scan else "", f"liste toute prête « {ss.panier} »")
            nb_lidl = sum(m.enseigne == "Lidl" for m in magasins)
            nb_plans = len(magasins) + sum(1 for i, a in enumerate(magasins) for b in magasins[i + 1:] if a.enseigne != b.enseigne)
            if transport.motorise and vehicule:
                energie = (f"{vehicule.libelle} : {nb(vehicule.conso_ville)} {'kWh' if transport.unite == 'kWh' else 'L'}/100 km"
                           + (f" · {carburant} à {eur(transport.prix_energie, 3)}/L" if carburant else ""))
            else:
                energie = "sans voiture : trajet gratuit"
            etapes_ia = [
                f"Liste analysée : <b>{len(liste)} produits</b> <span>({origine_liste})</span>",
                f"Prix comparés dans <b>{len(magasins)} magasins</b> <span>({nb_lidl} Lidl, {len(magasins) - nb_lidl} Aldi)</span>",
                f"Trajets calculés depuis votre point de départ <span>({'routes réelles' if reseau.source != 'estimation' else 'estimation'})</span>",
                f"Coût du trajet : <span>{energie}</span>",
                f"<b>{nb_plans} façons de faire vos courses testées</b>, la meilleure retenue <span>(règle du détour : {seuil} €)</span>",
            ]
            st.markdown('<div class="travail"><div class="k">Ce que l\'IA vient de faire</div><ul>'
                        + "".join(f"<li>{x}</li>" for x in etapes_ia) + "</ul></div>", unsafe_allow_html=True)
            st.markdown(f'<div class="reco"><div class="k">Le conseil de l\'application</div><div class="t">{titre}</div>'
                        f'<div class="p">{phrase}</div></div>', unsafe_allow_html=True)

            # économie : par rapport au meilleur magasin de l'autre enseigne (comparaison juste, trajet compris)
            if c.nb_magasins > 1:
                autre_plan = g
            else:
                autres = [s for k, s in reco.par_enseigne.items() if k != c.magasins[0].enseigne]
                autre_plan = min(autres, key=lambda s: s.total) if autres else reco.pire_magasin_unique
            ecart = round(autre_plan.total - c.total, 2)
            nom_autre = autre_plan.enseignes if c.nb_magasins == 1 else "un seul magasin"
            if ecart > 0.004:
                kpi_economie = (f'<div class="kpi"><div class="l">Vous économisez</div><div class="v vert">{eur(ecart)}</div>'
                                f'<div class="s">vs {nom_autre} · {eur(ecart * 52, 0)}/an*</div></div>')
            else:
                km_gagnes = max(0.0, autre_plan.distance_km - c.distance_km)
                kpi_economie = (f'<div class="kpi"><div class="l">Écart avec {nom_autre}</div><div class="v">+{eur(-ecart)}</div>'
                                f'<div class="s">mais {nb(km_gagnes)} km de trajet en moins</div></div>')
            if transport.motorise:
                unite = "kWh" if transport.unite == "kWh" else "L"
                kpi_energie = (f'<div class="kpi"><div class="l">{"Électricité" if unite == "kWh" else "Essence"} du trajet</div>'
                               f'<div class="v">{eur(c.cout_trajet)}</div><div class="s">{nb(c.energie, 2)} {unite} consommés</div></div>')
            else:
                kpi_energie = '<div class="kpi"><div class="l">Trajet</div><div class="v">0 €</div><div class="s">sans voiture</div></div>'
            st.markdown(
                f"""<div class="kpis">
                <div class="kpi"><div class="l">Vous payez</div><div class="v">{eur(c.total)}</div>
                     <div class="s">courses {eur(c.cout_courses)}</div></div>
                {kpi_economie}
                {kpi_energie}
                <div class="kpi"><div class="l">Aller-retour</div><div class="v">{nb(c.distance_km)} km</div>
                     <div class="s">environ {duree(temps(c))}</div></div></div>""",
                unsafe_allow_html=True,
            )

            # --- carte façon GPS
            etapes = itineraire([depart, *(m.position for m in c.magasins), depart])
            carte = folium.Map(location=[depart.lat, depart.lon], zoom_start=13, tiles="CartoDB.Voyager",
                               control_scale=True, zoom_snap=0.25, zoom_delta=0.5)
            noms = [m.nom for m in c.magasins] + ["votre point de départ"]
            for i, (t, vers) in enumerate(zip(etapes, noms)):
                retour = i == len(etapes) - 1
                folium.PolyLine(t.trace, color="white", weight=11, opacity=0.95).add_to(carte)
                folium.PolyLine(t.trace, color=BLEU_GPS, weight=6, opacity=0.65 if retour else 0.95,
                                dash_array="1 10" if retour else None,
                                tooltip=f"{'Retour' if retour else 'Aller'} vers {vers} : {nb(t.km)} km, {duree(t.minutes)}").add_to(carte)
            precision = ss.get("depart_precision") if ss.depart_source == "gps" else None
            if precision:
                folium.Circle([depart.lat, depart.lon], radius=min(precision, 400), color=BLEU_GPS, weight=0,
                              fill=True, fill_opacity=0.12).add_to(carte)
            folium.CircleMarker([depart.lat, depart.lon], radius=9, color="white", weight=3, fill=True, fill_color=BLEU_GPS,
                                fill_opacity=1, tooltip=f"Départ : {ss.depart_label}").add_to(carte)
            ordre = {m.id: k + 1 for k, m in enumerate(c.magasins)}
            for m in magasins:
                coul, dans = COULEUR.get(m.enseigne, "#666"), m.id in ordre
                taille = 34 if dans else 24
                etiquette = (f'<div style="background:white;padding:2px 7px;border-radius:6px;font:700 12px sans-serif;color:{coul};'
                             f'box-shadow:0 1px 3px rgba(0,0,0,.3);white-space:nowrap">{m.nom}</div>') if dans else ""
                folium.Marker(
                    [m.position.lat, m.position.lon],
                    tooltip=f"{m.nom}" + ("" if dans else " (pas besoin d'y aller)"),
                    popup=folium.Popup(f"<b>{m.nom}</b><br>{m.adresse}", max_width=240),
                    icon=folium.DivIcon(icon_size=(170, taille), icon_anchor=(taille // 2, taille // 2), html=(
                        f'<div style="display:flex;align-items:center;gap:5px;opacity:{1 if dans else .6}">'
                        f'<div style="background:{coul};color:white;font:800 {13 if dans else 10}px sans-serif;border:3px solid white;'
                        f'box-shadow:0 1px 5px rgba(0,0,0,.35);border-radius:50%;width:{taille}px;height:{taille}px;display:flex;'
                        f'align-items:center;justify-content:center">{ordre[m.id] if dans else m.enseigne[0]}</div>{etiquette}</div>')),
                ).add_to(carte)
            if station_choisie and carburant:
                folium.Marker([station_choisie.position.lat, station_choisie.position.lon],
                              tooltip=f"Votre station : {station_choisie.libelle}",
                              icon=folium.DivIcon(icon_size=(110, 26), icon_anchor=(13, 13), html=(
                                  f'<div style="background:{ENCRE};color:white;border-radius:8px;padding:3px 7px;font:700 11px sans-serif;'
                                  f'white-space:nowrap;box-shadow:0 1px 4px rgba(0,0,0,.35)">⛽ {nb(station_choisie.prix[carburant], 3)} €</div>'))
                              ).add_to(carte)
            pts = [p for t in etapes for p in t.trace] + [(s.magasins[0].position.lat, s.magasins[0].position.lon)
                                                          for s in reco.par_enseigne.values()]
            la, lo = [p[0] for p in pts], [p[1] for p in pts]
            mla, mlo = (max(la) - min(la)) * 0.08 + 0.002, (max(lo) - min(lo)) * 0.08 + 0.002
            carte.fit_bounds([[min(la) - mla, min(lo) - mlo], [max(la) + mla, max(lo) + mlo * 3]])
            st_folium(carte, height=440, use_container_width=True, returned_objects=[], key="carte")

            mode_gm = {"🚗 Voiture": "driving", "🚶 À pied": "walking", "🚲 Vélo": "bicycling", "🚌 Bus, tram": "transit"}[mode]
            boutons = (f'<a class="btn g" href="{lien_google_maps(depart, [m.position for m in c.magasins], mode_gm)}" '
                       f'target="_blank">📍 Ouvrir dans Google Maps</a>')
            if voiture and c.nb_magasins == 1:
                boutons += f'<a class="btn w" href="{lien_waze(c.magasins[0].position)}" target="_blank">🚙 Ouvrir dans Waze</a>'
            st.markdown(f'<div class="boutons">{boutons}</div>', unsafe_allow_html=True)
            source_trajet = ("trajets calculés sur les routes (OpenStreetMap)" if etapes[0].source != "estimation"
                             else "trajets estimés (service d'itinéraire momentanément indisponible)")
            st.caption(f"Trait plein : l'aller · pointillés : le retour · {source_trajet}. "
                       "*Par an : si vous faites cette liste une fois par semaine.")

            with st.expander("🧭  Itinéraire détaillé, étape par étape"):
                for k, (t, vers) in enumerate(zip(etapes, noms)):
                    st.markdown(f"**{k + 1}. Vers {vers}** · {nb(t.km)} km · {duree(t.minutes)}")
                    if t.instructions:
                        st.markdown('<ol class="instr">' + "".join(f"<li>{x}</li>" for x in t.instructions) + "</ol>",
                                    unsafe_allow_html=True)
                    else:
                        st.caption("Les instructions s'affichent quand le service d'itinéraire répond.")

    # ---------------------------------------------------------------- comparaison (pleine largeur)
    if liste:
        st.markdown("### Les options comparées")
        options = []
        for sc, nom, expl in [
            (proche, "📍 Le plus proche", f"Tout acheter chez {proche.magasins[0].nom}"),
            (g, "🏷️ Le moins cher en un seul magasin", f"Tout acheter chez {g.magasins[0].nom}"),
            (e, "💰 Le moins cher possible", "Chaque produit là où il est le moins cher"
             + (f" : {e.libelle}" if e.nb_magasins > 1 else "")),
        ]:
            deja = next((o for o in options if o[0].libelle == sc.libelle), None)
            if deja:
                deja[1].append(nom)
            else:
                options.append((sc, [nom], expl))
        for col, (sc, titres, expl) in zip(st.columns(len(options)), options):
            gagne = sc.libelle == c.libelle
            trajet_txt = f" + trajet {eur(sc.cout_trajet)}" if transport.motorise else ""
            col.markdown(
                f'<div class="option {"win" if gagne else ""}"><span class="pill {"" if gagne else "gris"}">'
                f'{"Conseillé" if gagne else "Autre option"}</span><h4>{" · ".join(titres)}</h4>'
                f'<div class="s">{expl}</div><div class="m">{eur(sc.total)}</div>'
                f'<div class="s">courses {eur(sc.cout_courses)}{trajet_txt}<br>{nb(sc.distance_km)} km · {duree(temps(sc))}</div></div>',
                unsafe_allow_html=True)

        st.write("")
        g1, g2 = st.columns([1.15, 1], gap="large")
        with g1:
            plans = sorted(reco.par_enseigne.values(), key=lambda s: s.total)
            if e.nb_magasins > 1:
                plans.append(e)
            noms_plans = [("Seulement " if s.nb_magasins == 1 else "") + s.enseignes for s in plans]
            fig = go.Figure()
            fig.add_bar(name="Courses", x=noms_plans, y=[s.cout_courses for s in plans], marker_color=VERT,
                        text=[eur(s.cout_courses) for s in plans], textposition="inside", insidetextanchor="middle")
            if transport.motorise:
                fig.add_bar(name="Trajet", x=noms_plans, y=[s.cout_trajet for s in plans], marker_color=ORANGE)
            fig.add_scatter(x=noms_plans, y=[s.total for s in plans], mode="text", showlegend=False,
                            text=[f"<b>{eur(s.total)}</b>" for s in plans], textposition="top center")
            fig.update_layout(barmode="stack", height=330, margin=dict(l=8, r=8, t=46, b=8), plot_bgcolor="white",
                              title=dict(text="Le meilleur magasin de chaque enseigne, trajet compris", x=0, font=dict(size=15)),
                              yaxis=dict(title="€", range=[0, max(s.total for s in plans) * 1.2], gridcolor=TRAIT),
                              legend=dict(orientation="h", y=1.12, x=1, xanchor="right"), font=dict(family="DM Sans"))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        with g2:
            st.markdown("#### Quoi acheter, et où")
            for m in c.magasins:
                produits = [p for p, mid in c.affectation.items() if mid == m.id]
                coul = COULEUR.get(m.enseigne, "#666")
                lignes = "".join(
                    f"<li>{liste[p]} × {par_nom[p].libelle} : <b>{eur(prix[p][m.id] * liste[p])}</b></li>" for p in produits)
                st.markdown(f'<div class="panier" style="background:{coul}0F;border:1px solid {coul}55;margin-bottom:10px">'
                            f'<h4 style="color:{coul}">Chez {m.nom}</h4><ul>{lignes}</ul>'
                            f'<div style="margin-top:6px"><b>Total : {eur(c.detail[m.id])}</b></div></div>',
                            unsafe_allow_html=True)

        with st.expander("Voir le détail des prix, produit par produit"):
            lignes = []
            for nom, qte in liste.items():
                p = par_nom[nom]
                ligne = {"Produit": p.libelle, "Quantité": qte}
                for ens in ("Lidl", "Aldi"):
                    o = p.offres.get(ens)
                    ligne[ens] = o.prix * qte if o else None
                    ligne[f"Article {ens}"] = (f"{o.nb_paquets} × {o.libelle}" if o and o.nb_paquets > 1
                                               else (o.libelle if o else "—"))
                lignes.append(ligne)
            detail = pd.DataFrame(lignes)

            def vert(r):
                mini = min(v for v in (r["Lidl"], r["Aldi"]) if pd.notna(v))
                return [f"background-color:{VERT_PALE};font-weight:700" if k in ("Lidl", "Aldi") and r[k] == mini else ""
                        for k in r.index]

            st.dataframe(detail.style.apply(vert, axis=1).format({"Lidl": eur, "Aldi": eur}, na_rep="—"),
                         hide_index=True, use_container_width=True)
            st.caption(f"En vert : le moins cher. Prix Aldi lus sur aldi.fr le {date_fr(date_aldi)}. "
                       f"Prix Lidl : prix nationaux officiels publiés par Lidl (relevés du {date_fr(date_lidl)}). "
                       "Quand un format n'existe pas, on compte plusieurs paquets (ex. 2 × 500 g pour 1 kg).")

# ====================================================================== onglet 2 : essence
with onglet_essence:
    st.markdown("### Le prix de l'essence autour de vous, en direct")
    st.caption(f"Autour de : {ss.depart_label}. Source officielle : Ministère de l'Économie (prix-carburants.gouv.fr), "
               "actualisée toutes les 10 minutes environ.")
    if not info_essence["direct"]:
        st.warning("Le service officiel ne répond pas pour l'instant : affichage de la dernière copie "
                   f"({info_essence['recupere_le']:%d/%m/%Y %H:%M}).")
    choix_c = st.segmented_control("Carburant", list(carb.CARBURANTS), default=carburant or "SP95-E10",
                                   key="carburant_onglet") or "SP95-E10"
    liste_st = sorted([s for s in stations if choix_c in s.prix], key=lambda s: s.prix[choix_c])
    if not liste_st:
        st.info("Aucune station ne vend ce carburant dans un rayon de 10 km.")
    else:
        moins, plus = liste_st[0], liste_st[-1]
        k1, k2, k3 = st.columns(3)
        k1.metric("La moins chère", f"{nb(moins.prix[choix_c], 3)} €/L", help=moins.libelle)
        k2.metric("La plus chère", f"{nb(plus.prix[choix_c], 3)} €/L", help=plus.libelle)
        k3.metric("Écart sur un plein de 40 L", eur((plus.prix[choix_c] - moins.prix[choix_c]) * 40))
        cg, cd = st.columns([1.3, 1], gap="large")
        with cd:
            st.dataframe(pd.DataFrame([{
                "Prix": s.prix[choix_c], "Adresse": s.libelle, "Distance": s.distance_km,
                "Mis à jour": il_y_a(s.mis_a_jour.get(choix_c)),
            } for s in liste_st]), hide_index=True, use_container_width=True, height=420,
                column_config={"Prix": st.column_config.NumberColumn(format="%.3f €"),
                               "Distance": st.column_config.NumberColumn(format="%.1f km")})
        with cg:
            m2 = folium.Map(location=[ss.depart.lat, ss.depart.lon], zoom_start=12, tiles="CartoDB.Voyager")
            pmin, pmax = moins.prix[choix_c], plus.prix[choix_c]
            for s in liste_st:
                r = 0 if pmax == pmin else (s.prix[choix_c] - pmin) / (pmax - pmin)
                coul = VERT if r < 0.34 else (ORANGE if r < 0.67 else "#C0392B")
                folium.Marker([s.position.lat, s.position.lon], tooltip=f"{s.libelle} · {nb(s.prix[choix_c], 3)} €/L",
                              icon=folium.DivIcon(icon_size=(70, 24), icon_anchor=(35, 12), html=(
                                  f'<div style="background:{coul};color:white;border-radius:7px;padding:3px 6px;font:700 11px sans-serif;'
                                  f'text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.35)">{nb(s.prix[choix_c], 3)}</div>'))).add_to(m2)
            folium.CircleMarker([ss.depart.lat, ss.depart.lon], radius=8, color="white", weight=3, fill=True,
                                fill_color=BLEU_GPS, fill_opacity=1, tooltip="Vous").add_to(m2)
            st_folium(m2, height=420, use_container_width=True, returned_objects=[], key="carte_essence")
        if st.button("🔄  Actualiser les prix de l'essence"):
            essence.clear()
            st.rerun()

# ====================================================================== onglet 3 : promos
with onglet_promos:
    st.markdown("### Les promos Lidl de la semaine, en magasin")
    offres = promos.get("offres", [])
    st.caption(f"Lues sur lidl.fr le {date_fr(promos.get('collecte_le'))}. Les dates indiquées sont celles de Lidl.")
    for i in range(0, len(offres), 3):
        for col, o in zip(st.columns(3), offres[i:i + 3]):
            barre = f'<span class="barre">{eur(o["ancien_prix"])}</span>' if o.get("ancien_prix") else ""
            badge = f'<span class="badge">{o["remise"]}</span>' if o.get("remise") else ""
            col.markdown(f'<div class="promo">{badge}<div style="font-weight:700;margin:6px 0 2px">{o["titre"]}</div>'
                         f'<div><span class="prix">{eur(o["prix"])}</span>{barre}</div>'
                         f'<div class="petit">{" · ".join(dict.fromkeys(x for x in (o.get("format"), o.get("prix_unite")) if x))}</div>'
                         f'<div class="petit">📅 {o.get("disponibilite") or ""}</div>'
                         f'<div class="petit"><a href="{o["url"]}" target="_blank">Voir sur lidl.fr</a></div></div>',
                         unsafe_allow_html=True)
        st.write("")

# ====================================================================== onglet 4 : sources
with onglet_sources:
    st.markdown("### D'où viennent les prix")
    sl, sa = sources["Lidl"], sources["Aldi"]
    st.markdown(f"""
<div class="source"><b>Lidl · {sl.get('nb_produits', 0)} produits</b><br>
Lidl ne vend pas d'alimentaire en ligne. Il publie en revanche, pour sa publicité comparative, le <b>prix national</b>
de ses produits du quotidien (le même dans tous ses magasins). Le robot lit ce document public.<br>
<span class="petit">Prix relevés le {date_fr(sl.get('prix_releves_le'))} · lus le {date_fr(sl.get('collecte_le'))} ·
<a href="{sl.get('url_document', '#')}" target="_blank">document Lidl</a></span></div>
<div class="source"><b>Aldi · {sa.get('nb_produits', 0)} produits</b><br>
Le robot lit les fiches produits publiques d'aldi.fr, une page à la fois, avec une pause entre chaque page.<br>
<span class="petit">Lus le {date_fr(sa.get('collecte_le'))}</span></div>
<div class="source"><b>Essence · stations autour de vous</b><br>
Prix déclarés par les stations au Ministère de l'Économie, données publiques actualisées toutes les 10 minutes.</div>
<div class="source"><b>Consommation des voitures · ADEME</b><br>
Consommations officielles (cycle WLTP) des voitures vendues en France ; on retient les valeurs « basse et moyenne vitesse »,
proches d'un trajet de courses en ville.</div>
<div class="source"><b>Lecture des listes en photo · IA Claude (Anthropic)</b><br>
La photo de la liste est lue par un modèle d'IA qui reconnaît l'écriture et rattache chaque article au bon produit.
La photo n'est pas conservée par l'application.</div>
<div class="source"><b>Magasins, cartes et itinéraires · OpenStreetMap</b><br>
Adresses des magasins, fond de carte © OpenStreetMap et CARTO, itinéraires calculés avec OSRM.</div>
""", unsafe_allow_html=True)
    st.markdown("#### Comment le robot de collecte se comporte")
    st.markdown("""
- Il **respecte le fichier robots.txt** de chaque site : une page interdite n'est jamais lue.
- Il passe **une fois par jour**, avec une pause de 3 secondes entre deux pages. Les prix en magasin changent au plus une
  fois par semaine : il est inutile de solliciter les sites plus souvent.
- Il ne lit que des **pages publiques**, sans compte et sans contourner aucune protection.
- Si un site change ou ne répond pas, **les derniers prix connus sont gardés**, et la date affichée le montre.
""")
    comp = sl.get("paniers_compares") or []
    if comp:
        st.markdown("#### Pour info : ce que Lidl publie sur les hypermarchés")
        st.dataframe(pd.DataFrame([{
            "Enseigne comparée": x["enseigne"], "Panier chez Lidl": x["total_lidl"],
            "Même panier chez l'enseigne (prix moyen drive)": x["total_concurrent"],
            "Écart": round((x["total_concurrent"] - x["total_lidl"]) / x["total_lidl"] * 100),
        } for x in comp]), hide_index=True, use_container_width=True,
            column_config={"Panier chez Lidl": st.column_config.NumberColumn(format="%.2f €"),
                           "Même panier chez l'enseigne (prix moyen drive)": st.column_config.NumberColumn(format="%.2f €"),
                           "Écart": st.column_config.NumberColumn(format="+%d %%")})
        st.caption("Chiffres publiés par Lidl dans sa publicité comparative (relevés du "
                   f"{date_fr(sl.get('prix_releves_le'))}).")

st.divider()
st.caption("IA Anti-Inflation · prototype · Mohamed-Aziz Zaanoun, statut national étudiant-entrepreneur (Pépite BFC) · "
           "Prix publiés par les enseignes · Essence : data.economie.gouv.fr · Véhicules : ADEME · Cartes : © OpenStreetMap, CARTO")
