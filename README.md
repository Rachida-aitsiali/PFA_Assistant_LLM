# ChemAsk · Assistant conversationnel ChEMBL et PubChem

Projet de Fin d'Année · Master Data Science & Big Data (DSDB), M1
Faculté des Sciences Ben M'Sick, Université Hassan II de Casablanca
Auteure : AIT SI ALI Rachida · Encadrement : Pr. AIT DAOUD Mohamed, Mme ELYAZYD Oumaima

ChemAsk répond en français et en anglais à des questions sur des cibles protéiques, des molécules et
leurs activités biologiques, en interrogeant les bases **ChEMBL** et **PubChem**
(LLM + appel de fonctions, LangChain). Chaque réponse cite la base et les identifiants utilisés ;
quand l'information n'existe pas, l'assistant le dit au lieu d'inventer.

## 1. Principe

Le modèle de langage (Groq, `openai/gpt-oss-120b`) ne répond pas de mémoire : il choisit parmi 6 outils
qui interrogent les API officielles, lit les résultats bruts, puis rédige la réponse à partir de ce que
les bases renvoient.

| Outil | Base | Rôle |
|---|---|---|
| `rechercher_cible_chembl` | ChEMBL | identifiant d'une cible protéique |
| `rechercher_molecule_chembl` | ChEMBL | identifiant d'une molécule |
| `activites_cible` | ChEMBL | molécules les plus puissantes sur une cible (IC50, Ki, Kd…) |
| `compter_activites` | ChEMBL | nombre de molécules testées sur une cible |
| `fiche_molecule_pubchem` | PubChem | formule, poids moléculaire, identifiants |
| `molecule_par_smiles` | PubChem | molécule correspondant à un SMILES |

## 2. Installation

Prérequis : Python 3.12, Git, et un compte gratuit sur https://console.groq.com pour obtenir une clé API.

```bash
git clone https://github.com/Rachida-aitsiali/PFA_Assistant_LLM.git
cd PFA_Assistant_LLM
python -m venv .venv
```

Activer l'environnement : `.venv\Scripts\activate` (Windows) ou `source .venv/bin/activate` (Linux / macOS). Puis :

```bash
pip install -r requirements.txt
```

Créer le fichier `notebooks/.env` avec une seule ligne (ne jamais le publier) :

```
GROQ_API_KEY=ta_cle_ici
```

Option « Continuer avec Google » : ajouter aussi `OAUTH_GOOGLE_CLIENT_ID` et `OAUTH_GOOGLE_CLIENT_SECRET`
dans ce fichier. Sans ces deux lignes, la connexion se fait par e-mail et mot de passe uniquement.

## 3. Lancer l'interface

```bash
cd notebooks
python creer_images.py        # une seule fois : crée logo, avatar et illustrations dans public/
chainlit run app.py -w
```

Ouvrir http://localhost:8000.

1. **Créer un compte** (e-mail + mot de passe d'au moins 6 caractères), puis **Se connecter**.
2. Choisir la langue (Français / English) avec le menu en haut à gauche.
3. Cliquer sur un exemple ou écrire une question. Chaque appel d'outil s'affiche en étape repliable.
4. L'historique des conversations est à gauche : chaque utilisateur retrouve, cherche, rouvre et supprime les siennes.
5. Le tableau de bord (`public/dashboard.html`) affiche les statistiques d'usage : questions, outils appelés,
   langues, temps de réponse. Il est mis à jour à chaque question.

Les mots de passe sont stockés hachés (PBKDF2). Les comptes, l'historique et les statistiques sont dans
la base locale `notebooks/chemask.db`, créée au premier lancement.

## 4. Reproduire l'évaluation, étape par étape

Depuis le dossier `notebooks`, ouvrir les notebooks (VS Code ou `jupyter notebook`) et les exécuter
**dans l'ordre**, cellule par cellule :

1. `01_API_ChEMBL_PubChem.ipynb` : tests des API ChEMBL et PubChem.
2. `02_agent_langchain.ipynb` : construction de l'agent et test de quelques questions.
3. `03_evaluation.ipynb` : pose les 30 questions en français et en anglais, avec et sans outils, note les
   réponses, puis produit `resultats_evaluation.csv` et `resultats_par_type.png`.

Points d'attention :
- **Cache** : les réponses des API sont mémorisées dans `cache_api.json` (30 jours). Le supprimer pour repartir
  de données fraîches ; les références de notation peuvent alors légèrement changer.
- **Quota Groq** : l'offre gratuite est limitée. En cas d'erreur 429, attendre quelques minutes et relancer
  uniquement les questions en erreur.
- **Variabilité** : un LLM peut répondre différemment d'une exécution à l'autre.
- Avant toute cellule qui modifie `resultats_evaluation.csv`, en faire une copie.

## 5. Résultats de l'évaluation

30 questions posées en français et en anglais (60 énoncés), dans deux conditions : LLM seul et LLM + outils.
Les références sont lues dans les bases (ChEMBL, PubChem) au moment du test. Quatre verdicts : correct,
abstention, faux, erreur. Intervalles de confiance de Wilson à 95 %.

| Condition | Réponses correctes | IC à 95 % |
|---|---|---|
| LLM + outils | 59 / 60 (98,3 %) | 91 – 99,7 % |
| LLM seul | 25 / 60 (41,7 %) | 30 – 54 % |

| Type de question | Énoncés | LLM + outils | LLM seul |
|---|---|---|---|
| Formule / poids (PubChem) | 12 | 12 | 12 |
| Identifiant de cible (ChEMBL) | 12 | 12 | 1 |
| Identifiant de molécule (ChEMBL) | 10 | 10 | 0 |
| Plusieurs étapes (ChEMBL) | 10 | 9 | 0 |
| Recherche par SMILES (PubChem) | 8 | 8 | 4 |
| Sans réponse possible | 8 | 8 | 8 |

Limites connues :
- Une réponse du LLM + outils est fausse (question 20, anglais) : le modèle a écrit en toutes lettres un nombre
  que l'outil avait correctement renvoyé.
- Le critère de notation d'une question a été ajusté après lecture des réponses : le nom d'un inhibiteur est
  accepté à la place de son identifiant ChEMBL, à condition que la valeur de Ki soit aussi donnée.
- Jeu de test réduit (60 énoncés) et questions simples, proches des outils disponibles.
- ChEMBL est parfois indisponible (erreurs 500) : le code réessaie, mais une panne longue peut empêcher de répondre.
- Les réponses viennent de bases publiques : à vérifier avant tout usage scientifique.

## 6. Contenu du dépôt

| Fichier | Contenu |
|---|---|
| `notebooks/app.py` | interface web Chainlit : connexion, historique, appel de l'agent, statistiques |
| `notebooks/assistant.py` | outils LangChain, consignes du modèle, agent bilingue |
| `notebooks/outils_api.py` | appels à ChEMBL et PubChem (nouvelles tentatives, cache disque) |
| `notebooks/creer_images.py` | crée logo, avatar, favicon et illustrations dans `public/` |
| `notebooks/public/` | pages et styles de l'interface : connexion, tableau de bord, feuille de style |
| `notebooks/01_API_ChEMBL_PubChem.ipynb` | tests des API |
| `notebooks/02_agent_langchain.ipynb` | construction de l'agent |
| `notebooks/03_evaluation.ipynb` | évaluation du LLM seul et du LLM + outils |
| `notebooks/questions_test.csv` | 30 questions en français et en anglais avec leurs références |
| `notebooks/resultats_evaluation.csv` | réponses et verdicts des 60 énoncés |
| `notebooks/resultats_par_type.png` | graphique des résultats par type de question |
| `requirements.txt` | dépendances Python |

Fichiers créés au lancement et **non publiés** (listés dans `.gitignore`) : `.env`, `chemask.db`, `.auth_secret`,
`public/stats.json`, `__pycache__/`.

## 7. Sécurité

- La clé API est lue dans `.env`, jamais écrite dans le code.
- `.auth_secret` (clé de signature des sessions) et `chemask.db` (comptes et conversations) restent sur la machine.
- Ne jamais publier ces fichiers : si une clé est publiée par erreur, la supprimer sur console.groq.com et en créer une nouvelle.

## 8. Sources

Données : [ChEMBL](https://www.ebi.ac.uk/chembl/) (EMBL-EBI) et [PubChem](https://pubchem.ncbi.nlm.nih.gov/) (NCBI),
via leurs API REST publiques.