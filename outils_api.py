"""Accès aux API ChEMBL et PubChem : un appel = une fonction simple qui renvoie un dictionnaire.

Les fonctions renvoient None quand rien n'est trouvé ou quand l'API ne répond pas.
Les réponses réussies sont gardées dans cache_api.json (valables 30 jours) pour limiter
les appels aux serveurs publics, qui sont parfois instables.
"""
import datetime
import functools
import json
import os
import time
import requests

CHEMBL = "https://www.ebi.ac.uk/chembl/api/data"
PUBCHEM = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

session = requests.Session()
DERNIERE_ERREUR = ""  # dernière erreur rencontrée (utile pour comprendre une panne)
PANNES = 0            # nombre d'appels abandonnés parce que le serveur ne répondait pas

# ---------- Cache sur disque ----------
FICHIER_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache_api.json")
VALIDITE_JOURS = 30   # au-delà, la réponse est redemandée à l'API (-1 = cache désactivé)


def _lire_cache():
    try:
        with open(FICHIER_CACHE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _sauver_cache(cache):
    with open(FICHIER_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)


def avec_cache(fonction):
    """Garde en mémoire (sur disque) le résultat d'une fonction quand l'API a répondu.

    On ne garde jamais un échec (None) : une panne ne doit pas rester dans le cache.
    Pour forcer de nouvelles requêtes : supprimer le fichier cache_api.json.
    """
    @functools.wraps(fonction)
    def enveloppe(*args, **kwargs):
        cle = f"{fonction.__name__}|{args}|{sorted(kwargs.items())}"
        entree = _lire_cache().get(cle)
        if entree:
            age = (datetime.date.today() - datetime.date.fromisoformat(entree["date"])).days
            if age <= VALIDITE_JOURS:
                return entree["resultat"]
        resultat = fonction(*args, **kwargs)
        if resultat is not None:
            cache = _lire_cache()
            cache[cle] = {"date": datetime.date.today().isoformat(), "resultat": resultat}
            _sauver_cache(cache)
        return resultat
    return enveloppe


# ---------- Appels HTTP avec nouvelles tentatives ----------
def _requete(methode, url, delai=60, **options):
    """Envoie une requête et renvoie le JSON, ou None si l'API échoue.

    Les erreurs temporaires (serveur surchargé 429/5xx, coupure réseau) sont retentées
    jusqu'à 4 fois avec une pause croissante. Les erreurs 4xx (ex. 404 : molécule inconnue)
    ne sont pas retentées, car la réponse ne changerait pas.
    PANNES compte les appels abandonnés après ces 4 essais (panne du serveur).
    """
    global DERNIERE_ERREUR, PANNES
    for tentative in range(1, 5):
        try:
            r = session.request(methode, url, timeout=(10, delai), **options)
            if r.status_code == 200:
                return r.json()
            DERNIERE_ERREUR = f"HTTP {r.status_code} sur {url}"
            if r.status_code < 500 and r.status_code != 429:
                return None
        except (requests.RequestException, ValueError) as e:
            DERNIERE_ERREUR = f"{type(e).__name__} sur {url}"
        if tentative < 4:
            time.sleep(5 * tentative)
    PANNES += 1
    return None


def get_json(url, params=None, delai=60):
    """Appel GET : renvoie le JSON, ou None en cas d'erreur."""
    return _requete("GET", url, delai=delai, params=params)


def post_json(url, data=None, delai=60):
    """Appel POST : renvoie le JSON, ou None en cas d'erreur."""
    return _requete("POST", url, delai=delai, data=data)


def etat_serveurs():
    """Test rapide (une seule requête par serveur, sans nouvelle tentative).

    Renvoie {"ChEMBL": (répond ?, détail), "PubChem": (répond ?, détail)}.
    """
    tests = {"ChEMBL": f"{CHEMBL}/target/CHEMBL203.json",
             "PubChem": f"{PUBCHEM}/compound/name/aspirin/property/MolecularFormula/JSON"}
    etat = {}
    for nom, url in tests.items():
        debut = time.time()
        try:
            r = session.get(url, timeout=(10, 30))
            etat[nom] = (r.status_code == 200, f"HTTP {r.status_code} en {time.time() - debut:.1f} s")
        except requests.RequestException as e:
            etat[nom] = (False, f"{type(e).__name__} après {time.time() - debut:.1f} s")
    return etat


# ---------- Outil 1 : cible ChEMBL ----------
@avec_cache
def chercher_cible_chembl(nom_cible):
    """Cherche une protéine cible humaine par son nom (ex. 'EGFR') et renvoie son identifiant ChEMBL."""
    data = get_json(f"{CHEMBL}/target.json",
                    {"target_synonym__icontains": nom_cible,
                     "organism": "Homo sapiens",
                     "target_type": "SINGLE PROTEIN"})
    if not data or not data.get("targets"):
        return None
    t = data["targets"][0]
    return {"nom": t["pref_name"], "chembl_id": t["target_chembl_id"], "type": t["target_type"]}


# ---------- Outil 2 : molécule ChEMBL ----------
@avec_cache
def chercher_molecule_chembl(nom_molecule):
    """Cherche une molécule par son nom exact (ex. 'gefitinib') et renvoie son identifiant ChEMBL."""
    data = get_json(f"{CHEMBL}/molecule.json", {"pref_name__iexact": nom_molecule})
    if not data or not data.get("molecules"):
        return None
    m = data["molecules"][0]
    return {"nom": m["pref_name"], "chembl_id": m["molecule_chembl_id"]}


@avec_cache
def nom_chembl(type_objet, chembl_id):
    """Nom officiel d'une cible ('target') ou d'une molécule ('molecule') à partir de son identifiant.

    Sert à vérifier les références du jeu de test (appel simple, délai court).
    """
    data = get_json(f"{CHEMBL}/{type_objet}/{chembl_id}.json", delai=20)
    if not data:
        return None
    return {"chembl_id": chembl_id, "nom": data.get("pref_name") or ""}


# ---------- Outil 3 : bioactivités d'une cible ----------
# Noms de mesures acceptés (en minuscules) et leur nom officiel dans ChEMBL
TYPES_MESURE = {"ic50": "IC50", "ki": "Ki", "kd": "Kd", "ec50": "EC50",
                "potency": "Potency", "gi50": "GI50"}


@avec_cache
def activites_cible_chembl(target_id, type_mesure="IC50", n=10):
    """Renvoie les n molécules les plus puissantes sur une cible, pour un type de mesure donné.

    On garde les mesures exactes (relation '='), en nM et validées par ChEMBL (pChEMBL),
    triées de la plus puissante à la moins puissante, sans doublon de molécule.
    """
    type_mesure = TYPES_MESURE.get(str(type_mesure).strip().lower(), type_mesure)
    data = get_json(f"{CHEMBL}/activity.json",
                    {"target_chembl_id": target_id,
                     "standard_type": type_mesure,
                     "standard_relation": "=",
                     "standard_units": "nM",
                     "pchembl_value__isnull": "false",
                     "order_by": "-pchembl_value",
                     "limit": 100})
    if not data or not data.get("activities"):
        return None
    vus, resultats = set(), []
    for a in data["activities"]:
        mid = a["molecule_chembl_id"]
        if mid in vus:
            continue
        vus.add(mid)
        resultats.append({"molecule_chembl_id": mid,
                          "nom": a.get("molecule_pref_name"),
                          "type_mesure": a["standard_type"],
                          "valeur_nM": a["standard_value"],
                          "pchembl": a["pchembl_value"],
                          "assay": a["assay_chembl_id"],
                          "document": a["document_chembl_id"]})
        if len(resultats) >= n:
            break
    return resultats


# ---------- Outil 4 : fiche molécule PubChem ----------
@avec_cache
def chercher_molecule_pubchem(nom_molecule):
    """Renvoie la formule, le poids moléculaire et le nom IUPAC d'une molécule (par son nom)."""
    data = get_json(f"{PUBCHEM}/compound/name/{nom_molecule}/property/"
                    "MolecularWeight,MolecularFormula,IUPACName/JSON")
    if not data:
        return None
    p = data["PropertyTable"]["Properties"][0]
    return {"cid_pubchem": p["CID"], "formule": p["MolecularFormula"],
            "poids_g_mol": p["MolecularWeight"], "nom_iupac": p["IUPACName"]}


# ---------- Outil 5 : comptage pour une cible ----------
@avec_cache
def compter_activites_chembl(target_id):
    """Nombre total de MESURES d'activité d'une cible (une seule requête, rapide)."""
    data = get_json(f"{CHEMBL}/activity.json",
                    {"target_chembl_id": target_id, "limit": 1})
    if not data or "page_meta" not in data:
        return None
    return {"target_chembl_id": target_id,
            "nombre_mesures_activite": data["page_meta"]["total_count"]}


TAILLE_PAGE = 200  # pages petites = requêtes plus légères pour le serveur ChEMBL


@avec_cache
def compter_molecules_chembl(target_id):
    """Nombre de molécules DISTINCTES ayant au moins une mesure d'activité sur la cible.

    ChEMBL ne fournit pas ce nombre directement : on lit toutes les mesures, par petites
    pages, et on compte les molécules différentes (plusieurs centaines de requêtes pour
    l'EGFR). La progression est enregistrée dans le cache : si le serveur plante, on peut
    relancer la fonction et elle reprend à la dernière page lue.
    Renvoie None si le serveur reste en panne (jamais de chiffre approximatif).
    """
    cle_prog = f"progression_comptage|{target_id}"
    prog = _lire_cache().get(cle_prog) or {"offset": 0, "molecules": [], "mesures": 0}
    molecules, mesures, offset = set(prog["molecules"]), prog["mesures"], prog["offset"]
    echecs, pages = 0, 0

    def sauver_progression():
        cache = _lire_cache()
        cache[cle_prog] = {"offset": offset, "molecules": sorted(molecules), "mesures": mesures}
        _sauver_cache(cache)

    while True:
        data = get_json(f"{CHEMBL}/activity.json",
                        {"target_chembl_id": target_id, "limit": TAILLE_PAGE, "offset": offset})
        if not data:
            echecs += 1
            if echecs >= 5:
                sauver_progression()  # on pourra reprendre ici au prochain lancement
                return None
            time.sleep(30)
            continue
        echecs = 0
        activites = data.get("activities", [])
        for a in activites:
            if a.get("molecule_chembl_id"):
                molecules.add(a["molecule_chembl_id"])
        mesures += len(activites)
        offset += len(activites)
        pages += 1
        if not activites or not data["page_meta"].get("next"):
            break  # plus rien à lire (garde-fou : évite une boucle infinie sur une page vide)
        if pages % 5 == 0:
            sauver_progression()
        time.sleep(0.3)  # petite pause entre les pages pour ménager le serveur

    cache = _lire_cache()                 # comptage terminé : on efface la progression
    cache.pop(cle_prog, None)
    _sauver_cache(cache)
    return {"target_chembl_id": target_id,
            "nombre_molecules_distinctes": len(molecules),
            "nombre_mesures_activite": mesures}


# ---------- Outil 6 : molécule connue dans PubChem à partir d'un SMILES ----------
@avec_cache
def chercher_smiles_pubchem(smiles):
    """Cherche une molécule par sa structure SMILES : CID, propriétés et nombre d'essais où elle est active."""
    data = post_json(f"{PUBCHEM}/compound/smiles/cids/JSON", data={"smiles": smiles})
    if not data:
        return None
    cids = data.get("IdentifierList", {}).get("CID", [])
    if not cids or cids[0] == 0:
        return None
    cid = cids[0]

    resultat = {"cid_pubchem": cid}

    props = get_json(f"{PUBCHEM}/compound/cid/{cid}/property/"
                     "MolecularWeight,MolecularFormula,IUPACName/JSON")
    if props:
        p = props["PropertyTable"]["Properties"][0]
        resultat.update({"formule": p["MolecularFormula"],
                         "poids_g_mol": p["MolecularWeight"],
                         "nom_iupac": p["IUPACName"]})

    aids = get_json(f"{PUBCHEM}/compound/cid/{cid}/aids/JSON", {"aids_type": "active"})
    if aids:
        liste = aids["InformationList"]["Information"][0].get("AID", [])
        resultat["nombre_essais_actifs"] = len(liste)
        resultat["exemples_aid"] = liste[:5]
    else:
        resultat["nombre_essais_actifs"] = 0
    return resultat