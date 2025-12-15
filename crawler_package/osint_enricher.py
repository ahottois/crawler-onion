"""
Module d'enrichissement OSINT passif.
Enrichissement emails, domaines, wallets, IPs.
"""

import re
import socket
import hashlib
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse

from .logger import Log


@dataclass
class EnrichedEmail:
    """Email enrichi."""
    email: str
    domain: str
    local_part: str
    domain_type: str = "unknown"  # free, corporate, temp, unknown
    is_valid_format: bool = False
    mx_exists: bool = False
    disposable: bool = False
    company: str = ""
    breach_count: int = 0
    first_seen: str = ""
    last_seen: str = ""
    sources: List[str] = field(default_factory=list)
    risk_score: float = 0.0


@dataclass
class EnrichedDomain:
    """Domaine enrichi."""
    domain: str
    tld: str
    is_onion: bool = False
    created_date: str = ""
    registrar: str = ""
    name_servers: List[str] = field(default_factory=list)
    mx_records: List[str] = field(default_factory=list)
    ip_addresses: List[str] = field(default_factory=list)
    asn: str = ""
    country: str = ""
    organization: str = ""
    is_datacenter: bool = False
    is_vpn: bool = False
    is_proxy: bool = False
    open_ports: List[int] = field(default_factory=list)
    technologies: List[str] = field(default_factory=list)
    risk_score: float = 0.0


@dataclass
class EnrichedWallet:
    """Wallet crypto enrichi."""
    address: str
    crypto_type: str
    network: str = "mainnet"
    balance: float = 0.0
    balance_usd: float = 0.0
    transaction_count: int = 0
    first_seen: str = ""
    last_active: str = ""
    total_received: float = 0.0
    total_sent: float = 0.0
    linked_addresses: List[str] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)  # exchange, mixer, etc.
    risk_score: float = 0.0
    is_known_bad: bool = False


@dataclass
class EnrichedIP:
    """IP enrichie."""
    ip: str
    version: int = 4
    is_private: bool = False
    hostname: str = ""
    country: str = ""
    city: str = ""
    region: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    asn: str = ""
    organization: str = ""
    isp: str = ""
    is_datacenter: bool = False
    is_proxy: bool = False
    is_vpn: bool = False
    is_tor_exit: bool = False
    is_tor_relay: bool = False
    reputation_score: float = 0.0
    abuse_reports: int = 0
    open_ports: List[int] = field(default_factory=list)


class EmailEnricher:
    """Enrichissement d'emails."""
    
    # Domaines email gratuits connus
    FREE_EMAIL_DOMAINS = {
        'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
        'icloud.com', 'mail.com', 'protonmail.com', 'proton.me', 'tutanota.com',
        'gmx.com', 'gmx.net', 'yandex.com', 'yandex.ru', 'mail.ru',
        'zoho.com', 'fastmail.com', 'hushmail.com', 'guerrillamail.com'
    }
    
    # Domaines email temporaires/jetables
    DISPOSABLE_DOMAINS = {
        'tempmail.com', 'temp-mail.org', 'guerrillamail.com', '10minutemail.com',
        'throwaway.email', 'mailinator.com', 'fakeinbox.com', 'dispostable.com',
        'tempail.com', 'getnada.com', 'mohmal.com', 'maildrop.cc'
    }
    
    @classmethod
    def enrich(cls, email: str) -> EnrichedEmail:
        """Enrichit un email."""
        result = EnrichedEmail(email=email, domain="", local_part="")
        
        if not email or '@' not in email:
            return result
        
        try:
            local, domain = email.lower().split('@', 1)
            result.local_part = local
            result.domain = domain
            result.is_valid_format = cls._validate_format(email)
            
            # Type de domaine
            if domain in cls.FREE_EMAIL_DOMAINS:
                result.domain_type = "free"
            elif domain in cls.DISPOSABLE_DOMAINS:
                result.domain_type = "disposable"
                result.disposable = True
                result.risk_score = 0.8
            else:
                result.domain_type = "corporate"
                result.company = cls._guess_company(domain)
            
            # Check MX (passif - juste format)
            result.mx_exists = '.' in domain and len(domain) > 3
            
            # Risk score
            if result.disposable:
                result.risk_score = 0.8
            elif result.domain_type == "free":
                result.risk_score = 0.3
            else:
                result.risk_score = 0.2
            
        except Exception as e:
            Log.debug(f"Email enrichment error: {e}")
        
        return result
    
    @staticmethod
    def _validate_format(email: str) -> bool:
        """Valide le format email."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def _guess_company(domain: str) -> str:
        """Devine le nom de l'entreprise depuis le domaine."""
        # Retirer TLD
        parts = domain.split('.')
        if len(parts) >= 2:
            name = parts[-2]
            # Capitaliser
            return name.capitalize()
        return ""


class DomainEnricher:
    """Enrichissement de domaines."""
    
    # TLDs suspects/haut risque
    HIGH_RISK_TLDS = {'.onion', '.bit', '.i2p', '.bazar'}
    
    # Providers VPN/Proxy connus
    VPN_PROVIDERS = {
        'nordvpn', 'expressvpn', 'surfshark', 'cyberghost', 'privateinternetaccess',
        'mullvad', 'protonvpn', 'ipvanish', 'purevpn', 'windscribe'
    }
    
    # ASNs de datacenters connus
    DATACENTER_ASNS = {
        'AS14061',  # DigitalOcean
        'AS16509',  # Amazon
        'AS15169',  # Google
        'AS8075',   # Microsoft
        'AS13335',  # Cloudflare
        'AS20473',  # Vultr
        'AS63949',  # Linode
        'AS24940',  # Hetzner
        'AS16276',  # OVH
    }
    
    @classmethod
    def enrich(cls, domain: str) -> EnrichedDomain:
        """Enrichit un domaine."""
        result = EnrichedDomain(domain=domain, tld="")
        
        if not domain:
            return result
        
        try:
            # Extraire TLD
            parts = domain.split('.')
            if parts:
                result.tld = '.' + parts[-1]
            
            # Check .onion
            result.is_onion = domain.endswith('.onion')
            
            # Risk score base sur TLD
            if result.tld in cls.HIGH_RISK_TLDS:
                result.risk_score = 0.7
            elif result.is_onion:
                result.risk_score = 0.8
            else:
                result.risk_score = 0.2
            
            # Detection VPN dans le nom
            domain_lower = domain.lower()
            for vpn in cls.VPN_PROVIDERS:
                if vpn in domain_lower:
                    result.is_vpn = True
                    break
            
        except Exception as e:
            Log.debug(f"Domain enrichment error: {e}")
        
        return result


class WalletEnricher:
    """Enrichissement de wallets crypto."""
    
    # Exchanges connus (prefixes d'adresses)
    KNOWN_EXCHANGES = {
        'bitcoin': {
            '1A1zP1': 'Genesis Block',
            'bc1qgdjqv': 'Binance',
            '3FZbgi': 'Bitfinex',
        },
        'ethereum': {
            '0x28c6c0': 'Binance',
            '0xdac17': 'Tether',
        }
    }
    
    # Addresses connues comme malveillantes
    KNOWN_BAD_ADDRESSES = set()  # A remplir depuis sources externes
    
    @classmethod
    def enrich(cls, address: str, crypto_type: str) -> EnrichedWallet:
        """Enrichit une adresse wallet."""
        result = EnrichedWallet(address=address, crypto_type=crypto_type)
        
        if not address:
            return result
        
        try:
            # Normaliser le type
            crypto_type = crypto_type.lower()
            result.crypto_type = crypto_type
            
            # Detecter le reseau
            result.network = cls._detect_network(address, crypto_type)
            
            # Check si exchange connu
            if crypto_type in cls.KNOWN_EXCHANGES:
                for prefix, label in cls.KNOWN_EXCHANGES[crypto_type].items():
                    if address.startswith(prefix):
                        result.labels.append(f"exchange:{label}")
                        break
            
            # Check si connu malveillant
            if address in cls.KNOWN_BAD_ADDRESSES:
                result.is_known_bad = True
                result.risk_score = 1.0
                result.labels.append("malicious")
            
            # Risk score par defaut
            if not result.is_known_bad:
                result.risk_score = 0.3  # Neutre par defaut
            
        except Exception as e:
            Log.debug(f"Wallet enrichment error: {e}")
        
        return result
    
    @staticmethod
    def _detect_network(address: str, crypto_type: str) -> str:
        """Detecte le reseau (mainnet/testnet)."""
        if crypto_type == 'bitcoin':
            if address.startswith(('1', '3', 'bc1')):
                return 'mainnet'
            elif address.startswith(('m', 'n', 'tb1')):
                return 'testnet'
        elif crypto_type == 'ethereum':
            return 'mainnet'  # Pas de distinction simple
        
        return 'mainnet'


class IPEnricher:
    """Enrichissement d'adresses IP."""
    
    # Ranges IP privees
    PRIVATE_RANGES = [
        ('10.0.0.0', '10.255.255.255'),
        ('172.16.0.0', '172.31.255.255'),
        ('192.168.0.0', '192.168.255.255'),
        ('127.0.0.0', '127.255.255.255'),
    ]
    
    # Noeuds de sortie Tor connus (a mettre a jour)
    TOR_EXIT_NODES: set = set()
    
    @classmethod
    def enrich(cls, ip: str) -> EnrichedIP:
        """Enrichit une adresse IP."""
        result = EnrichedIP(ip=ip)
        
        if not ip:
            return result
        
        try:
            # Detecter version
            if ':' in ip:
                result.version = 6
            else:
                result.version = 4
            
            # Check si privee
            result.is_private = cls._is_private(ip)
            
            # Check Tor exit node
            if ip in cls.TOR_EXIT_NODES:
                result.is_tor_exit = True
                result.risk_score = 0.7
            
            # Risk score
            if result.is_private:
                result.risk_score = 0.1
            elif result.is_tor_exit:
                result.risk_score = 0.7
            else:
                result.risk_score = 0.3
            
        except Exception as e:
            Log.debug(f"IP enrichment error: {e}")
        
        return result
    
    @classmethod
    def _is_private(cls, ip: str) -> bool:
        """Verifie si l'IP est privee."""
        try:
            parts = [int(p) for p in ip.split('.')]
            if len(parts) != 4:
                return False
            
            ip_int = (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3]
            
            for start, end in cls.PRIVATE_RANGES:
                start_parts = [int(p) for p in start.split('.')]
                end_parts = [int(p) for p in end.split('.')]
                
                start_int = (start_parts[0] << 24) + (start_parts[1] << 16) + (start_parts[2] << 8) + start_parts[3]
                end_int = (end_parts[0] << 24) + (end_parts[1] << 16) + (end_parts[2] << 8) + end_parts[3]
                
                if start_int <= ip_int <= end_int:
                    return True
            
            return False
        except:
            return False


class OSINTEnricher:
    """Enrichisseur OSINT centralise."""
    
    def __init__(self):
        self.email_enricher = EmailEnricher()
        self.domain_enricher = DomainEnricher()
        self.wallet_enricher = WalletEnricher()
        self.ip_enricher = IPEnricher()
    
    def enrich_email(self, email: str) -> EnrichedEmail:
        """Enrichit un email."""
        return self.email_enricher.enrich(email)
    
    def enrich_domain(self, domain: str) -> EnrichedDomain:
        """Enrichit un domaine."""
        return self.domain_enricher.enrich(domain)
    
    def enrich_wallet(self, address: str, crypto_type: str) -> EnrichedWallet:
        """Enrichit un wallet."""
        return self.wallet_enricher.enrich(address, crypto_type)
    
    def enrich_ip(self, ip: str) -> EnrichedIP:
        """Enrichit une IP."""
        return self.ip_enricher.enrich(ip)
    
    def enrich_url(self, url: str) -> Dict:
        """Enrichit une URL complete."""
        result = {
            'url': url,
            'domain': None,
            'is_onion': False,
            'path': '',
            'params': {}
        }
        
        try:
            parsed = urlparse(url)
            result['domain'] = self.enrich_domain(parsed.netloc)
            result['is_onion'] = parsed.netloc.endswith('.onion')
            result['path'] = parsed.path
            result['scheme'] = parsed.scheme
        except:
            pass
        
        return result
    
    def batch_enrich(self, entities: List[Dict]) -> List[Dict]:
        """Enrichit un batch d'entites."""
        results = []
        
        for entity in entities:
            entity_type = entity.get('type', '')
            value = entity.get('value', '')
            
            if entity_type == 'email':
                enriched = self.enrich_email(value)
            elif entity_type == 'domain':
                enriched = self.enrich_domain(value)
            elif entity_type.startswith('crypto_'):
                crypto_type = entity_type.replace('crypto_', '')
                enriched = self.enrich_wallet(value, crypto_type)
            elif entity_type == 'ip':
                enriched = self.enrich_ip(value)
            else:
                enriched = None
            
            results.append({
                'original': entity,
                'enriched': enriched.__dict__ if enriched else None
            })
        
        return results


# Instance globale
osint_enricher = OSINTEnricher()
