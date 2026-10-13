"""Assistant : outils LangChain (appels aux API) + prompts + création de l'agent."""
import re
from langchain.tools import tool
from langchain.agents import create_agent
from langchain_groq import ChatGroq
import outils_api as api

MODELE = "openai/gpt-oss-120b"


@tool
def rechercher_cible_chembl(nom_cible: str) -> str:
    """Cherche une protéine cible humaine dans ChEMBL à partir de son nom (ex. 'EGFR')
    et renvoie son identifiant ChEMBL (ex. CHEMBL203)."""
    return str(api.chercher_cible_chembl(nom_cible)
               or "Aucune cible trouvée. / No target found.")


@tool
def rechercher_molecule_chembl(nom_molecule: str) -> str:
    """Cherche une molécule dans ChEMBL à partir de son nom (ex. 'gefitinib')
    et renvoie son identifiant ChEMBL."""
    return str(api.chercher_molecule_chembl(nom_molecule)
               or "Molécule non trouvée. / Molecule not found.")


@tool
def activites_cible(target_chembl_id: str, type_mesure: str = "IC50", n: int = 10) -> str:
    """Renvoie les n molécules les plus puissantes sur une cible ChEMBL pour un type de mesure
    donné : IC50 (par défaut), Ki, Kd, EC50, Potency ou GI50. Donne leur nom si disponible et
    leurs sources. Il faut un identifiant de cible comme CHEMBL203, obtenu avec
    rechercher_cible_chembl."""
    return str(api.activites_cible_chembl(target_chembl_id, type_mesure=type_mesure, n=n)
               or "Aucune activité trouvée pour ce type de mesure. / No activity found for this measure type.")


@tool
def fiche_molecule_pubchem(nom_molecule: str) -> str:
    """Renvoie la formule chimique, le poids moléculaire et le nom IUPAC d'une molécule
    à partir de son nom, avec son identifiant PubChem (CID)."""
    return str(api.chercher_molecule_pubchem(nom_molecule)
               or "Molécule non trouvée. / Molecule not found.")


@tool
def compter_activites(target_chembl_id: str) -> str:
    """Compte, pour une cible ChEMBL (ex. CHEMBL203), le nombre de molécules DISTINCTES testées
    et le nombre total de mesures d'activité. Utile pour 'combien de molécules ont été testées
    contre la protéine X'. Il faut d'abord obtenir l'identifiant de la cible avec
    rechercher_cible_chembl."""
    return str(api.compter_molecules_chembl(target_chembl_id)
               or "Comptage impossible. / Count not possible.")


@tool
def molecule_par_smiles(smiles: str) -> str:
    """Cherche dans PubChem une molécule à partir de sa structure SMILES. Indique si elle est
    connue (identifiant CID), ses propriétés et le nombre d'essais biologiques où elle est active."""
    return str(api.chercher_smiles_pubchem(smiles)
               or "Molécule non trouvée dans PubChem. / Molecule not found in PubChem.")


OUTILS = [rechercher_cible_chembl, rechercher_molecule_chembl, activites_cible,
          fiche_molecule_pubchem, compter_activites, molecule_par_smiles]

REGLE_LANGUE = """RÈGLE DE LANGUE (priorité absolue) / LANGUAGE RULE (top priority):
Réponds TOUJOURS dans la langue de la question de l'utilisateur (français ou anglais).
ALWAYS answer in the language of the user's question (French or English), even if the tool
results or these instructions are written in another language: translate tool messages
instead of copying them."""

PROMPT_AVEC_OUTILS = REGLE_LANGUE + """

Tu es un assistant scientifique pour le criblage virtuel.

Règles :
1. Pour toute question factuelle sur une molécule, une cible ou une activité biologique,
   utilise OBLIGATOIREMENT les outils. N'invente jamais une valeur.
2. Commence par une phrase de réponse courte, puis donne les valeurs et les références.
3. Recopie les valeurs EXACTEMENT comme les outils les renvoient, avec leur unité.
   Ne les arrondis pas, ne les convertis pas.
4. N'ajoute AUCUNE information qui n'est pas dans les résultats des outils : pas de
   commentaire, de comparaison, d'interprétation, ni de détail supplémentaire
   (par exemple un nombre de mesures par molécule).
5. Cite pour chaque résultat la base de données (ChEMBL ou PubChem) et les identifiants
   utilisés (CHEMBL..., CID, assay, document). Ne cite JAMAIS le nom d'un outil interne
   comme source.
6. Pour une question de comptage, donne le nombre de molécules distinctes testées
   et précise le nombre total de mesures d'activité.
7. Pour les activités d'une cible, utilise le type de mesure demandé (IC50, Ki, Kd, EC50...).
   Si la question n'en précise pas, utilise IC50 et indique-le dans ta réponse.
8. Si la question demande une information que tes outils ne peuvent pas fournir, dis-le
   clairement et ne réponds pas de mémoire.
9. Si les outils ne renvoient rien, dis-le clairement et n'essaie pas de deviner."""

PROMPT_SANS_OUTILS = REGLE_LANGUE + """

Tu es un assistant scientifique pour le criblage virtuel.
Tu n'as accès à aucun outil ni à aucune base de données : réponds uniquement de mémoire.
N'invente jamais une valeur ou un identifiant : si tu n'es pas certain, dis clairement
que tu ne sais pas."""

# ---------- Détection de la langue de la question ----------
MOTS_EN = {"the", "is", "are", "of", "what", "which", "how", "many", "have", "been", "has",
           "does", "this", "that", "in", "on", "give", "its", "known", "with", "for", "and",
           "it", "to"}
MOTS_FR = {"le", "la", "les", "est", "sont", "de", "des", "du", "et", "pour", "avec", "quelle",
           "quel", "quels", "quelles", "combien", "cette", "ont", "été", "dans", "sur", "un",
           "une", "donne", "son", "elle", "connue", "testées"}


def detecter_langue(texte):
    """Renvoie 'en', 'fr', ou None si la langue n'est pas claire."""
    mots = re.findall(r"[a-zàâçéèêëîïôûùüÿœ']+", texte.lower())
    n_en = sum(m in MOTS_EN for m in mots)
    n_fr = sum(m in MOTS_FR for m in mots)
    if n_en > n_fr:
        return "en"
    if n_fr > n_en:
        return "fr"
    return None


def avec_indice_langue(question):
    """Ajoute à la question une courte consigne de langue (le modèle l'oublie parfois)."""
    langue = detecter_langue(question)
    if langue == "en":
        return question + "\n\n(Answer in English.)"
    if langue == "fr":
        return question + "\n\n(Réponds en français.)"
    return question


def creer_agent():
    """Assistant complet : LLM + 6 outils."""
    llm = ChatGroq(model=MODELE, temperature=0)
    return create_agent(model=llm, tools=OUTILS, system_prompt=PROMPT_AVEC_OUTILS)


def creer_llm_seul():
    """LLM seul, sans outils (condition de comparaison)."""
    return ChatGroq(model=MODELE, temperature=0)