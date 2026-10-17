"""ChemAsk : interface Chainlit de l'assistant ChEMBL / PubChem (PFA Assistant LLM).

Lancement (depuis le dossier notebooks/) :  chainlit run app.py -w

- Connexion : page personnalisée (public/connexion.js) avec « Se connecter »,
  « Créer un compte » (e-mail + mot de passe) et « Continuer avec Google » (optionnel).
- Historique : chaque utilisateur retrouve, cherche, rouvre et supprime ses conversations.
- Dashboard : public/dashboard.html lit public/stats.json, mis à jour à chaque question.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

import chainlit as cl
from chainlit.server import app as fastapi_app
from fastapi import Request
from fastapi.responses import JSONResponse
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from dotenv import load_dotenv

load_dotenv(override=True)  # le .env l'emporte sur une ancienne clé du système

BASE = Path(__file__).resolve().parent
DB = BASE / "chemask.db"
STATS = BASE / "public" / "stats.json"

# Clé de signature des sessions de connexion : créée une fois, puis réutilisée.
if not os.environ.get("CHAINLIT_AUTH_SECRET"):
    fichier_secret = BASE / ".auth_secret"
    if not fichier_secret.exists():
        fichier_secret.write_text(secrets.token_hex(32))
    os.environ["CHAINLIT_AUTH_SECRET"] = fichier_secret.read_text().strip()

import assistant  # noqa: E402  (ton assistant.py, dans le même dossier)

AGENT = assistant.creer_agent()  # créé une seule fois, partagé entre les sessions
HISTORIQUE_MAX = 6  # nombre de messages gardés pour les questions de suivi

BASE_DE_L_OUTIL = {
    "rechercher_cible_chembl": "ChEMBL",
    "rechercher_molecule_chembl": "ChEMBL",
    "activites_cible": "ChEMBL",
    "compter_activites": "ChEMBL",
    "fiche_molecule_pubchem": "PubChem",
    "molecule_par_smiles": "PubChem",
}

# --------------------------------------------------------------------------
# Base SQLite : historique des conversations (tables Chainlit) + comptes + métriques
# --------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    "id" TEXT PRIMARY KEY, "identifier" TEXT NOT NULL UNIQUE,
    "metadata" TEXT NOT NULL, "createdAt" TEXT);
CREATE TABLE IF NOT EXISTS threads (
    "id" TEXT PRIMARY KEY, "createdAt" TEXT, "name" TEXT, "userId" TEXT,
    "userIdentifier" TEXT, "tags" TEXT, "metadata" TEXT);
CREATE TABLE IF NOT EXISTS steps (
    "id" TEXT PRIMARY KEY, "name" TEXT NOT NULL, "type" TEXT NOT NULL,
    "threadId" TEXT NOT NULL, "parentId" TEXT, "streaming" INTEGER NOT NULL DEFAULT 0,
    "waitForAnswer" INTEGER, "isError" INTEGER, "metadata" TEXT, "tags" TEXT,
    "input" TEXT, "output" TEXT, "createdAt" TEXT, "command" TEXT, "start" TEXT,
    "end" TEXT, "generation" TEXT, "showInput" TEXT, "language" TEXT, "indent" INTEGER,
    "defaultOpen" INTEGER, "autoCollapse" INTEGER);
CREATE TABLE IF NOT EXISTS elements (
    "id" TEXT PRIMARY KEY, "threadId" TEXT, "type" TEXT, "url" TEXT, "chainlitKey" TEXT,
    "name" TEXT NOT NULL, "display" TEXT, "objectKey" TEXT, "size" TEXT, "page" INTEGER,
    "language" TEXT, "forId" TEXT, "mime" TEXT, "props" TEXT);
CREATE TABLE IF NOT EXISTS feedbacks (
    "id" TEXT PRIMARY KEY, "forId" TEXT NOT NULL, "threadId" TEXT NOT NULL,
    "value" INTEGER NOT NULL, "comment" TEXT);
CREATE TABLE IF NOT EXISTS app_users (
    username TEXT PRIMARY KEY, salt TEXT NOT NULL, hash TEXT NOT NULL, created TEXT);
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, langue TEXT, duree_ms INTEGER,
    outils TEXT, ok INTEGER);
"""


def _db():
    return sqlite3.connect(DB)


with _db() as _con:
    _con.executescript(SCHEMA)
    # Base créée par une version précédente : ajoute la colonne manquante si besoin.
    if "autoCollapse" not in [c[1] for c in _con.execute("PRAGMA table_info(steps)")]:
        _con.execute('ALTER TABLE steps ADD COLUMN "autoCollapse" INTEGER')


class SQLiteDataLayer(SQLAlchemyDataLayer):
    """SQLite ne sait pas stocker une liste : on la convertit en texte JSON."""

    async def update_thread(self, thread_id, name=None, user_id=None, metadata=None, tags=None):
        await super().update_thread(
            thread_id, name, user_id, metadata, json.dumps(tags) if tags is not None else None
        )

    async def create_step(self, step_dict):
        for cle, valeur in list(step_dict.items()):
            if isinstance(valeur, list):
                step_dict[cle] = json.dumps(valeur)
        await super().create_step(step_dict)


@cl.data_layer
def _data_layer():
    return SQLiteDataLayer(conninfo=f"sqlite+aiosqlite:///{DB.as_posix()}")


# --------------------------------------------------------------------------
# Connexion / création de compte
# --------------------------------------------------------------------------
def _hash(mot_de_passe: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode(), salt, 200_000).hex()


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


def _creer_compte(email: str, mot_de_passe: str):
    """Crée un compte. Renvoie None si OK, sinon le code d'erreur."""
    nom = email.strip().lower()
    if not EMAIL_RE.match(nom):
        return "email"
    if len(mot_de_passe) < 6:
        return "password"
    with _db() as con:
        if con.execute("SELECT 1 FROM app_users WHERE username=?", (nom,)).fetchone():
            return "exists"
        salt = secrets.token_bytes(16)
        con.execute(
            "INSERT INTO app_users VALUES (?,?,?,?)",
            (nom, salt.hex(), _hash(mot_de_passe, salt), datetime.now().isoformat()),
        )
    return None


@cl.password_auth_callback
def connexion(username: str, password: str):
    """Connexion à un compte EXISTANT (e-mail + mot de passe)."""
    nom = username.strip().lower()
    with _db() as con:
        ligne = con.execute("SELECT salt, hash FROM app_users WHERE username=?", (nom,)).fetchone()
    if ligne and hmac.compare_digest(_hash(password, bytes.fromhex(ligne[0])), ligne[1]):
        return cl.User(identifier=nom, metadata={"role": "user"})
    return None


async def register(request: Request):
    """POST /register : appelé par la page de connexion (onglet « Créer un compte »)."""
    try:
        data = await request.json()
        erreur = _creer_compte(str(data.get("email", "")), str(data.get("password", "")))
    except Exception:
        erreur = "email"
    if erreur:
        return JSONResponse({"ok": False, "error": erreur}, status_code=400)
    return JSONResponse({"ok": True})


# La route doit passer AVANT celle de Chainlit qui capture toutes les URL.
fastapi_app.add_api_route("/register", register, methods=["POST"])
fastapi_app.router.routes.insert(0, fastapi_app.router.routes.pop())

# Connexion avec Google : active seulement si les identifiants sont dans le .env
if os.environ.get("OAUTH_GOOGLE_CLIENT_ID") and os.environ.get("OAUTH_GOOGLE_CLIENT_SECRET"):

    @cl.oauth_callback
    async def google(provider_id, token, raw_user_data, default_app_user, id_token=None):
        email = (raw_user_data.get("email") or "").strip().lower()
        if provider_id != "google" or not email:
            return None
        return cl.User(
            identifier=email,
            metadata={"role": "user", "provider": "google", "name": raw_user_data.get("name", "")},
        )


# --------------------------------------------------------------------------
# Statistiques pour le dashboard (public/stats.json)
# --------------------------------------------------------------------------
def _enregistrer(langue: str, duree_ms: int, outils: list, ok: bool):
    with _db() as con:
        con.execute(
            "INSERT INTO metrics (ts, langue, duree_ms, outils, ok) VALUES (?,?,?,?,?)",
            (datetime.now().isoformat(), langue, duree_ms, json.dumps(outils), int(ok)),
        )
    _ecrire_stats()


def _ecrire_stats():
    with _db() as con:
        lignes = con.execute("SELECT ts, langue, duree_ms, outils, ok FROM metrics").fetchall()
        n_conv = con.execute("SELECT COUNT(*) FROM threads").fetchone()[0]
        n_users = con.execute("SELECT COUNT(*) FROM app_users").fetchone()[0]
    outils, bases, langues, jours = {}, {"ChEMBL": 0, "PubChem": 0}, {"fr": 0, "en": 0}, {}
    durees = []
    for ts, langue, duree, liste, ok in lignes:
        langues[langue] = langues.get(langue, 0) + 1
        jours[ts[:10]] = jours.get(ts[:10], 0) + 1
        if ok:
            durees.append(duree)
        for o in json.loads(liste or "[]"):
            outils[o] = outils.get(o, 0) + 1
            b = BASE_DE_L_OUTIL.get(o)
            if b:
                bases[b] += 1
    aujourdhui = datetime.now().date()
    serie = [
        {"jour": (aujourdhui - timedelta(days=i)).isoformat(),
         "n": jours.get((aujourdhui - timedelta(days=i)).isoformat(), 0)}
        for i in range(13, -1, -1)
    ]
    STATS.parent.mkdir(exist_ok=True)
    STATS.write_text(json.dumps({
        "genere": datetime.now().isoformat(timespec="seconds"),
        "conversations": n_conv, "utilisateurs": n_users,
        "questions": len(lignes), "erreurs": sum(1 for l in lignes if not l[4]),
        "latence_moyenne_s": round(sum(durees) / len(durees) / 1000, 1) if durees else None,
        "outils": outils, "bases": bases, "langues": langues, "par_jour": serie,
    }, ensure_ascii=False), encoding="utf-8")


# --------------------------------------------------------------------------
# Appel de l'agent
# --------------------------------------------------------------------------
def _texte(contenu) -> str:
    """Le contenu d'un message peut être une chaîne ou une liste de blocs."""
    if isinstance(contenu, str):
        return contenu
    return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in contenu)


def _repondre(historique: list, question: str, callbacks: list, profil: str):
    # Langue de la question ; si elle n'est pas claire ("bonjour", "hello"),
    # on prend la langue choisie dans le menu en haut à gauche.
    code = assistant.detecter_langue(question) or ("en" if profil == "English" else "fr")
    indice = "(Answer in English.)" if code == "en" else "(Réponds en français.)"
    messages = historique + [{"role": "user", "content": f"{question}\n\n{indice}"}]
    agent = AGENT.agents[code] if hasattr(AGENT, "agents") else AGENT
    res = agent.invoke({"messages": messages}, config={"callbacks": callbacks})
    outils = [m.name for m in res["messages"] if getattr(m, "type", "") == "tool" and m.name]
    return _texte(res["messages"][-1].content), outils, code


# --------------------------------------------------------------------------
# Interface
# --------------------------------------------------------------------------
TEXTES = {
    "Français": {
        "exemples": [
            ("Inhibiteurs d'EGFR", "Quels sont les 10 inhibiteurs les plus puissants du récepteur EGFR ?"),
            ("Fiche du géfitinib", "Quelle est la formule chimique et le poids moléculaire du géfitinib ?"),
            ("Tests sur VEGFR2", "Combien de molécules ont été testées contre la protéine VEGFR2 dans ChEMBL ?"),
            ("Molécule inconnue", "Quelle est l'IC50 de la molécule ZX-9999 sur EGFR ?"),
        ],
        "erreur": "Une erreur est survenue (clé ou quota Groq, ou API indisponible). Réessayez dans un instant.",
    },
    "English": {
        "exemples": [
            ("EGFR inhibitors", "What are the 10 most potent inhibitors of the EGFR receptor?"),
            ("Gefitinib profile", "What are the chemical formula and molecular weight of gefitinib?"),
            ("VEGFR2 assays", "How many molecules have been tested against VEGFR2 in ChEMBL?"),
            ("Unknown molecule", "What is the IC50 of molecule ZX-9999 on EGFR?"),
        ],
        "erreur": "An error occurred (Groq key or quota, or API unavailable). Please try again shortly.",
    },
}


@cl.set_chat_profiles
async def profils():
    return [
        cl.ChatProfile(
            name="Français",
            icon="/public/icone.png",
            markdown_description=(
                "![ChemAsk](/public/hero.svg)\n\n"
                "# ChemAsk\n"
                "L'assistant qui interroge **ChEMBL** et **PubChem** pour vous : "
                "cibles protéiques, molécules, activités biologiques."
            ),
        ),
        cl.ChatProfile(
            name="English",
            icon="/public/icone.png",
            markdown_description=(
                "![ChemAsk](/public/hero.svg)\n\n"
                "# ChemAsk\n"
                "The assistant that queries **ChEMBL** and **PubChem** for you: "
                "protein targets, molecules, biological activities."
            ),
        ),
    ]


@cl.set_starters
async def starters(user=None, chat_profile=None):
    t = TEXTES.get(chat_profile or "Français", TEXTES["Français"])
    return [cl.Starter(label=l, message=m) for l, m in t["exemples"]]


@cl.on_chat_start
async def debut():
    cl.user_session.set("langue", cl.user_session.get("chat_profile") or "Français")
    cl.user_session.set("historique", [])


@cl.on_chat_resume
async def reprise(thread):
    """Rouvre une ancienne conversation : on recharge son contexte."""
    historique = []
    for s in thread.get("steps", []):
        if s.get("type") == "user_message":
            historique.append({"role": "user", "content": s.get("output", "")})
        elif s.get("type") == "assistant_message":
            historique.append({"role": "assistant", "content": s.get("output", "")})
    cl.user_session.set("historique", historique[-HISTORIQUE_MAX:])
    cl.user_session.set("langue", cl.user_session.get("chat_profile") or "Français")


@cl.on_message
async def message(msg: cl.Message):
    langue = cl.user_session.get("langue", "Français")
    historique = cl.user_session.get("historique", [])
    handler = cl.LangchainCallbackHandler()  # affiche chaque appel d'outil
    debut_s, outils, code, ok = time.time(), [], "en" if langue == "English" else "fr", True
    try:
        # L'appel est bloquant (réseau) : on le sort de la boucle asynchrone.
        texte, outils, code = await cl.make_async(_repondre)(historique, msg.content, [handler], langue)
        historique += [
            {"role": "user", "content": msg.content},
            {"role": "assistant", "content": texte},
        ]
        cl.user_session.set("historique", historique[-HISTORIQUE_MAX:])
    except Exception as e:  # clé invalide, quota, panne ChEMBL, etc.
        ok = False
        texte = f"{TEXTES[langue]['erreur']}\n\n`{type(e).__name__}: {e}`"
    await cl.Message(content=texte, author="Assistant").send()
    try:
        _enregistrer(code, int((time.time() - debut_s) * 1000), outils, ok)
    except Exception:
        pass  # les statistiques ne doivent jamais bloquer une réponse