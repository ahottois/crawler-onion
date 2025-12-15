#!/usr/bin/env python3
"""
Darknet Omniscient Crawler v6.4
Lanceur simplifie a la racine du projet.

Usage: python run.py [options]
"""

import sys
import os

# Ajouter le repertoire courant au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawler_package.main import main

if __name__ == "__main__":
    main()
