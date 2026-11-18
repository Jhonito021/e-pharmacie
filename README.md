# PharmaGest — Gestion de pharmacie

Application web de gestion pharmaceutique développée avec Python, Django, SQLite, Bootstrap 5, Pillow et ReportLab. Interface en français et adaptée aux écrans mobiles.

## Fonctionnalités présentes

- Authentification Django, rôles (administrateur, pharmacien, gestionnaire de stock, caissier, responsable de gestion) et protection des vues.
- Catalogue des médicaments : ajout, modification, photo, catégorie, prix, seuil, code-barres, recherche, filtre et pagination. Archivage pour préserver l'historique.
- Fiches détaillées et actions adaptées : consultation, modification, activation/désactivation et suppression lorsque l'historique le permet.
- Catégories modifiables ; clients et fournisseurs désactivables sans supprimer leurs historiques.
- Commandes d'achat en brouillon, modification/suppression de lignes avant validation, annulation avant réception et traçabilité des mouvements.
- Ventes et stocks consultables avec historique ; les corrections passent par le retour ou l'inventaire plutôt que par une suppression directe.
- Stock par lots, dates de péremption, lots bloqués, alertes, inventaire et méthode FEFO à la vente.
- Caisse, panier, prix historisés, paiement et reçu PDF.
- Retours tracés avec remise en stock conditionnelle.
- Tableau de bord, rapports, journal d'audit et administration.
- Tests automatisés de règles essentielles.

## Installation (Windows / Linux / macOS)

Prérequis : Python 3.10 ou supérieur.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations pharmacie
python manage.py migrate
python manage.py creer_donnees_demo
python manage.py runserver
```

Ouvrir http://127.0.0.1:8000

Compte de démonstration :
- Identifiant : `admin`
- Mot de passe : `Admin12345`

Changez immédiatement ce mot de passe pour toute utilisation autre qu'une démonstration.

## Administration

L'administration Django est disponible sur `/admin/`. Elle centralise les clients, médicaments, fournisseurs, stocks, achats, ventes, paiements, retours, mouvements de stock et journaux d'audit. Les enregistrements historiques sont consultables mais non modifiables depuis l'administration, afin de préserver la traçabilité.

Le journal des requêtes enregistre chaque requête reçue par Django (utilisateur connecté si présent, méthode, chemin sans paramètres, code HTTP et durée), y compris les erreurs et redirections. Les fichiers statiques servis directement par le serveur web ne sont pas des requêtes Django. Les corps de requête, mots de passe, cookies et adresses IP ne sont pas enregistrés. Les journaux sont consultables en lecture seule depuis l'administration.

## Tests

```bash
python manage.py test pharmacie
```

## Sauvegarde SQLite

Arrêter les écritures puis copier `db.sqlite3` et le dossier `media/` dans un emplacement protégé. Pour une restauration, remplacer ces éléments puis relancer le serveur. En production, prévoir une sauvegarde automatisée et tester régulièrement la restauration.

## Configuration de production

- Définir `SECRET_KEY`, `DEBUG=False` et `ALLOWED_HOSTS` dans l'environnement.
- Utiliser HTTPS, un serveur WSGI/ASGI et une base PostgreSQL.
- Configurer le stockage sécurisé des médias, les sauvegardes et la journalisation.
- Adapter les mentions fiscales, les règles de délivrance et les procédures de paiement aux exigences locales de Madagascar.

## Limites et points à finaliser avant exploitation réelle

Ce livrable constitue une base applicative fonctionnelle pour un projet pédagogique. Il ne remplace pas les validations réglementaires d'une pharmacie. L'intégration réelle Mobile Money doit utiliser l'API du prestataire et confirmer les paiements via un retour serveur fiable. Les procédures de remboursement, facturation fiscale, gestion multi-paiements, blocage/isolement réglementaire des lots et contrôle professionnel doivent être validées avant une mise en production. Le projet ne gère pas la prescription ni le diagnostic médical.
