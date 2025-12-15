"""
Module de configuration du crawler.
Contient tous les parametres configurables.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Config:
    """Configuration centralisee du crawler."""
    
    # Version et infos du projet
    version: str = "7.0.0"
    repo_owner: str = "ahottois"
    repo_name: str = "crawler-onion"
    
    # Parametres de crawl
    max_workers: int = 15
    max_pages: int = 50000
    timeout: int = 90
    max_retries: int = 5
    session_recycle: int = 40
    queue_timeout: int = 10
    
    # Fichiers
    db_file: str = "darknet_omniscient.db"
    json_file: str = "darknet_report.json"
    
    # Configuration Tor
    tor_socks_port: int = 9050
    tor_control_port: int = 9051
    tor_password: str = ""
    tor_fallback_port: int = 9150
    
    # Serveur Web
    web_port: int = 4587
    web_enabled: bool = True
    
    # Extensions a ignorer
    ignored_extensions: tuple = (
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.pdf', '.css', 
        '.ico', '.svg', '.mp4', '.zip', '.tar', '.gz', '.iso', 
        '.xml', '.json', '.woff', '.woff2', '.ttf', '.eot'
    )
    
    # User agents rotatifs
    user_agents: List[str] = field(default_factory=lambda: [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0'
    ])
    
    # Referers pour paraitre plus naturel
    referers: List[str] = field(default_factory=lambda: [
        "https://www.google.com/",
        "https://duckduckgo.com/",
        "http://dark.fail/"
    ])
    
    # URLs de depart (seeds)
    seeds: List[str] = field(default_factory=lambda: [
        # Moteurs de recherche stables
        "http://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion/",
        "http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion/",
        "http://haystak5njsmn2hqkewecpaxetahtwhsbsa64jom2k22z5afxhnpxfid.onion/",
        # Annuaires
        "http://taxi2anrytox735rup7olin54r2bypco6rytsl5qmayrah7xn2vkmwad.onion/",
        # Wikis
        "http://zqktlwiuavvvqqt4ybvgvi7tyo4hjl5xgfuvpdf6otjiycgwqbym2qad.onion/wiki/index.php/Main_Page",
        "http://s4k4ceiapwwgcm3mkb6e4diqecpo7kvdnfr5gg7sph7jjppqkvwwqtyd.onion/",
        "http://2fd6cemt4gmccflhm6imvdfvli3nf7zn6rfrwpsy7uhxrgbypvwf5fad.onion/",
        # Forums
        "http://dreadytofatroptsdj6io7l3xptbet6onoyno2yv7jicoxknyazubrad.onion/",
        "http://recon222tttn4ob7ujdhbn3s4gjre7net2rlvmwn77xvptzp4hge4ad.onion/"
    ])
    
    @property
    def proxies(self) -> Dict[str, str]:
        """Retourne la configuration proxy pour Tor."""
        return {
            'http': f'socks5h://127.0.0.1:{self.tor_socks_port}',
            'https': f'socks5h://127.0.0.1:{self.tor_socks_port}'
        }
