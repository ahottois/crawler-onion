"""
Module d'analyse de contenu des pages web.
Extrait secrets, cryptos, emails, IPs et autres donnees sensibles.
"""

import re
from typing import Dict, List, Any
from bs4 import BeautifulSoup, Comment


class ContentAnalyzer:
    """Analyse le contenu des pages pour extraire des informations."""
    
    # Patterns pour secrets/credentials
    PATTERNS_SECRETS = {
        'AWS_KEY': re.compile(r'AKIA[0-9A-Z]{16}'),
        'AWS_SECRET': re.compile(r'(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*[\'"]?([A-Za-z0-9/+=]{40})[\'"]?'),
        'PRIVATE_KEY': re.compile(r'-----BEGIN\s+(RSA|DSA|EC|OPENSSH)?\s*PRIVATE\sKEY-----'),
        'GOOGLE_API': re.compile(r'AIza[0-9A-Za-z\-_]{35}'),
        'GITHUB_TOKEN': re.compile(r'gh[pousr]_[A-Za-z0-9_]{36,}'),
        'GENERIC_API_KEY': re.compile(r'(?i)(api[_-]?key|access[_-]?token|secret[_-]?key|auth[_-]?token)\s*[:=]\s*[\'"]([a-zA-Z0-9\-_]{32,})[\'"]'),
        'DB_CONNECTION': re.compile(r'(?:mysql|postgres|mongodb|redis)://[^\s<>"\']+'),
        'JWT_TOKEN': re.compile(r'eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+'),
    }
    
    # Patterns pour adresses crypto
    PATTERNS_CRYPTO = {
        'BTC': re.compile(r'\b(bc1[a-zA-HJ-NP-Z0-9]{39,59}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b'),
        'ETH': re.compile(r'\b0x[a-fA-F0-9]{40}\b'),
        'XMR': re.compile(r'\b4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}\b'),
        'LTC': re.compile(r'\b[LM][a-km-zA-HJ-NP-Z1-9]{26,33}\b'),
    }
    
    # Patterns pour reseaux sociaux/messagerie
    PATTERNS_SOCIAL = {
        'Telegram': re.compile(r'(?:https?://)?(?:t\.me|telegram\.me)/([a-zA-Z0-9_]{5,})'),
        'Discord': re.compile(r'(?:https?://)?(?:discord\.gg|discordapp\.com/invite)/([a-zA-Z0-9]+)'),
        'Jabber': re.compile(r'[a-zA-Z0-9._%+-]+@(?:jabber|xmpp)\.[a-z]{2,}'),
        'Session': re.compile(r'\b05[a-fA-F0-9]{64}\b'),
        'Wickr': re.compile(r'(?i)wickr\s*:\s*([a-zA-Z0-9_]+)'),
    }
    
    # Autres patterns
    PATTERN_IPV4 = re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b')
    PATTERN_EMAIL = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    
    # IPs privees a ignorer
    PRIVATE_IP_PREFIXES = (
        '127.', '0.', '10.', '192.168.', 
        '172.16.', '172.17.', '172.18.', '172.19.', 
        '172.20.', '172.21.', '172.22.', '172.23.', 
        '172.24.', '172.25.', '172.26.', '172.27.',
        '172.28.', '172.29.', '172.30.', '172.31.', 
        '169.254.'
    )
    
    @classmethod
    def extract_tech_stack(cls, headers: Dict[str, str]) -> List[str]:
        """Extrait les informations sur la stack technique depuis les headers."""
        stack = []
        
        header_mappings = {
            'Server': lambda v: f"Server:{v}",
            'X-Powered-By': lambda v: f"PoweredBy:{v}",
            'X-AspNet-Version': lambda v: f"ASP.NET:{v}",
            'X-Generator': lambda v: f"Generator:{v}",
        }
        
        for header, formatter in header_mappings.items():
            if header in headers:
                stack.append(formatter(headers[header]))
        
        # Detection via cookies
        cookies = headers.get('Set-Cookie', '')
        cookie_indicators = {
            'PHPSESSID': 'PHP', 
            'JSESSIONID': 'Java', 
            'csrftoken': 'Django',
            'laravel_session': 'Laravel', 
            'rack.session': 'Ruby',
            'connect.sid': 'Node.js', 
            'ASP.NET_SessionId': 'ASP.NET'
        }
        
        for indicator, tech in cookie_indicators.items():
            if indicator in cookies:
                stack.append(tech)
        
        return list(set(stack))
    
    @classmethod
    def _extract_secrets(cls, text: str) -> Dict[str, List[str]]:
        """Extrait les secrets potentiels du texte."""
        secrets = {}
        for name, pattern in cls.PATTERNS_SECRETS.items():
            matches = list(set(pattern.findall(text)))
            if matches:
                cleaned = [m if isinstance(m, str) else m[0] if m else None for m in matches]
                cleaned = [m for m in cleaned if m]
                if cleaned:
                    secrets[name] = cleaned[:10]
        return secrets
    
    @classmethod
    def _extract_cryptos(cls, text: str) -> Dict[str, List[str]]:
        """Extrait les adresses crypto du texte."""
        cryptos = {}
        for coin, pattern in cls.PATTERNS_CRYPTO.items():
            matches = list(set(pattern.findall(text)))
            if matches:
                cryptos[coin] = matches[:20]
        return cryptos
    
    @classmethod
    def _extract_socials(cls, text: str) -> Dict[str, List[str]]:
        """Extrait les liens sociaux du texte."""
        socials = {}
        for network, pattern in cls.PATTERNS_SOCIAL.items():
            matches = list(set(pattern.findall(text)))
            if matches:
                socials[network] = matches[:10]
        return socials
    
    @classmethod
    def _extract_emails(cls, text: str) -> List[str]:
        """Extrait les emails du texte."""
        emails = set(cls.PATTERN_EMAIL.findall(text))
        # Filtrer les faux positifs
        emails = {e for e in emails if not e.endswith(('.png', '.jpg', '.gif', '.css', '.js'))}
        return list(emails)[:50]
    
    @classmethod
    def _extract_ips(cls, text: str) -> List[str]:
        """Extrait les IPs publiques du texte."""
        ips = set(cls.PATTERN_IPV4.findall(text))
        public_ips = [ip for ip in ips if not ip.startswith(cls.PRIVATE_IP_PREFIXES)]
        return public_ips[:20]
    
    @classmethod
    def _extract_comments(cls, soup: BeautifulSoup) -> List[str]:
        """Extrait les commentaires HTML pertinents."""
        comments = []
        try:
            for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
                comment_text = str(comment).strip()
                if 10 < len(comment_text) < 500:
                    comments.append(comment_text)
        except Exception:
            pass
        return comments[:20]
    
    @classmethod
    def _extract_json_data(cls, soup: BeautifulSoup) -> List[str]:
        """Extrait les donnees JSON embarquees dans la page."""
        json_data = []
        try:
            for script in soup.find_all('script', type='application/json'):
                if script.string:
                    content = script.string.strip()
                    if 10 < len(content) < 5000:
                        json_data.append(content)
        except Exception:
            pass
        return json_data[:5]
    
    @classmethod
    def analyze(cls, text: str, soup: BeautifulSoup, headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Analyse complete d'une page.
        
        Args:
            text: Texte brut de la page
            soup: Objet BeautifulSoup de la page
            headers: Headers HTTP de la reponse
            
        Returns:
            Dictionnaire contenant toutes les donnees extraites
        """
        return {
            'secrets': cls._extract_secrets(text),
            'cryptos': cls._extract_cryptos(text),
            'socials': cls._extract_socials(text),
            'emails': cls._extract_emails(text),
            'ip_leaks': cls._extract_ips(text),
            'tech_stack': cls.extract_tech_stack(headers),
            'comments': cls._extract_comments(soup),
            'json_data': cls._extract_json_data(soup)
        }
