#!/usr/bin/env python3
"""
Darknet Omniscient Crawler v6.4
Point d'entrée principal.

Usage:
    python main.py [options]
    
Options:
    --workers N      Nombre de workers parallèles (défaut: 15)
    --timeout N      Timeout en secondes (défaut: 90)
    --max-pages N    Nombre max de pages à crawler (défaut: 50000)
    --db FILE        Fichier de base de données (défaut: darknet_omniscient.db)
    --output FILE    Fichier JSON de sortie (défaut: darknet_report.json)
    --reset          Supprimer la base de données existante
    --add-seed URL   Ajouter une URL seed (peut être répété)
    --web-port N     Port du serveur web (défaut: 4587)
    --no-web         Désactiver le serveur web
"""

import argparse
import os
import sys

from .config import Config
from .crawler import OnionCrawler
from .logger import Log


def parse_arguments():
    """Parse les arguments de la ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Darknet Omniscient Crawler v6.4",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
    python main.py                          # Lancer avec les paramètres par défaut
    python main.py --workers 20             # Utiliser 20 workers
    python main.py --reset                  # Réinitialiser la base de données
    python main.py --add-seed http://xyz.onion/  # Ajouter un seed
    python main.py --no-web                 # Sans interface web
        """
    )
    
    parser.add_argument(
        '--workers', 
        type=int, 
        help='Nombre de workers parallèles'
    )
    parser.add_argument(
        '--timeout', 
        type=int, 
        help='Timeout en secondes'
    )
    parser.add_argument(
        '--max-pages', 
        type=int, 
        help='Nombre max de pages à crawler'
    )
    parser.add_argument(
        '--db', 
        type=str, 
        help='Fichier de base de données'
    )
    parser.add_argument(
        '--output', 
        type=str, 
        help='Fichier JSON de sortie'
    )
    parser.add_argument(
        '--reset', 
        action='store_true', 
        help='Supprimer la base de données existante'
    )
    parser.add_argument(
        '--add-seed', 
        type=str, 
        action='append', 
        dest='extra_seeds',
        help='Ajouter une URL seed (peut être répété)'
    )
    parser.add_argument(
        '--web-port', 
        type=int, 
        default=4587,
        help='Port du serveur web'
    )
    parser.add_argument(
        '--no-web', 
        action='store_true',
        help='Désactiver le serveur web'
    )
    
    return parser.parse_args()


def main():
    """Point d'entrée principal."""
    args = parse_arguments()
    
    # Créer la configuration
    config = Config()
    
    # Appliquer les arguments
    if args.workers:
        config.max_workers = args.workers
    if args.timeout:
        config.timeout = args.timeout
    if args.max_pages:
        config.max_pages = args.max_pages
    if args.db:
        config.db_file = args.db
    if args.output:
        config.json_file = args.output
    if args.web_port:
        config.web_port = args.web_port
    if args.no_web:
        config.web_enabled = False
    
    # Réinitialiser la base si demandé
    if args.reset and os.path.exists(config.db_file):
        os.remove(config.db_file)
        Log.info(f"Base supprimée: {config.db_file}")
    
    # Ajouter les seeds supplémentaires
    if args.extra_seeds:
        config.seeds = list(config.seeds) + args.extra_seeds
    
    # Lancer le crawler
    crawler = OnionCrawler(config)
    crawler.run()


if __name__ == "__main__":
    main()
