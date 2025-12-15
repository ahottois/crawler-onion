# Darknet Omniscient Crawler v6.4

Crawler Tor modulaire pour l'exploration et l'analyse de sites .onion avec interface web integree.

## Installation rapide (Ubuntu Server)

```bash
curl -sSL https://raw.githubusercontent.com/ahottois/crawler-onion/master/install.sh | bash
```

## Structure du projet

```
crawler-onion/
??? run.py                          # Lanceur principal
??? install.sh                      # Script d'installation Ubuntu
??? requirements.txt                # Dependances Python
??? README.md                       # Documentation
??? crawler_package/
    ??? __init__.py                 # Exports du package
    ??? config.py                   # Configuration centralisee
    ??? logger.py                   # Systeme de logging
    ??? database.py                 # Gestion SQLite
    ??? analyzer.py                 # Analyse de contenu
    ??? tor.py                      # Interface Tor
    ??? utils.py                    # Utilitaires
    ??? web_server.py               # Serveur HTTP
    ??? web_templates.py            # Templates HTML
    ??? crawler.py                  # Crawler principal
    ??? main.py                     # Point d'entree CLI
```

## Installation manuelle

1. **Cloner le repository** :
```bash
git clone https://github.com/ahottois/crawler-onion.git
cd crawler-onion
```

2. **Installer les dependances** :
```bash
pip install -r requirements.txt
```

3. **S'assurer que Tor est installe et en cours d'execution** :
```bash
# Linux
sudo apt install tor
sudo systemctl start tor

# Windows - Telecharger le Tor Browser ou le service Tor
```

## Utilisation

### Lancement basique
```bash
python run.py
```

### Options disponibles
```bash
python run.py --help

Options:
  --workers N      Nombre de workers paralleles (defaut: 15)
  --timeout N      Timeout en secondes (defaut: 90)
  --max-pages N    Nombre max de pages a crawler (defaut: 50000)
  --db FILE        Fichier de base de donnees
  --output FILE    Fichier JSON de sortie
  --reset          Supprimer la base de donnees existante
  --add-seed URL   Ajouter une URL seed
  --web-port N     Port du serveur web (defaut: 4587)
  --no-web         Desactiver le serveur web
```

### Exemples
```bash
# Crawler avec 20 workers
python run.py --workers 20

# Reinitialiser la base et ajouter un seed
python run.py --reset --add-seed http://example.onion/

# Sans interface web
python run.py --no-web

# Changer le port du dashboard
python run.py --web-port 8080
```

## Interface Web

L'interface web est accessible par defaut sur `http://localhost:4587`

### Pages disponibles :
- **Dashboard** : Vue d'ensemble et statistiques en temps reel
- **Recherche** : Recherche dans la base de donnees
- **Sites Fiables** : Classement des sites par score de confiance

### Fonctionnalites :
- Ajout de seeds depuis l'interface
- Visualisation des domaines crawles
- Timeline des decouvertes
- Export des donnees

## Donnees extraites

Le crawler extrait automatiquement :
- **Secrets** : Cles API, tokens, credentials
- **Crypto** : Adresses Bitcoin, Ethereum, Monero, Litecoin
- **Social** : Liens Telegram, Discord, Jabber, Session, Wickr
- **Emails** : Adresses email
- **IPs** : Fuites d'adresses IP publiques
- **Tech Stack** : Technologies utilisees (serveur, framework)

## Modules

| Module | Description |
|--------|-------------|
| `config.py` | Configuration centralisee avec dataclass |
| `logger.py` | Logging thread-safe avec couleurs |
| `database.py` | Gestion SQLite avec migrations automatiques |
| `analyzer.py` | Extraction de donnees via regex |
| `tor.py` | Interface avec le proxy Tor |
| `web_server.py` | Serveur HTTP leger integre |
| `web_templates.py` | Templates HTML pour le dashboard |
| `crawler.py` | Logique de crawling multi-threade |

## Avertissement

Ce projet est fourni a des fins educatives et de recherche uniquement. L'utilisation de ce crawler doit se faire dans le respect des lois applicables.

## Licence

MIT License
