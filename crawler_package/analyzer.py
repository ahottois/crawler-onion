"""
Module d'analyse de contenu des pages web.
Extrait secrets, cryptos, emails, IPs et autres donnees sensibles.
"""

import re
from typing import Dict, List, Any, Tuple
from bs4 import BeautifulSoup, Comment
from collections import Counter


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
        'SSH_KEY': re.compile(r'ssh-(?:rsa|dss|ed25519)\s+[A-Za-z0-9+/=]+'),
        'BEARER_TOKEN': re.compile(r'Bearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+'),
    }
    
    # Patterns pour adresses crypto
    PATTERNS_CRYPTO = {
        'BTC': re.compile(r'\b(bc1[a-zA-HJ-NP-Z0-9]{39,59}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b'),
        'ETH': re.compile(r'\b0x[a-fA-F0-9]{40}\b'),
        'XMR': re.compile(r'\b4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}\b'),
        'LTC': re.compile(r'\b[LM][a-km-zA-HJ-NP-Z1-9]{26,33}\b'),
        'DOGE': re.compile(r'\bD[5-9A-HJ-NP-U][1-9A-HJ-NP-Za-km-z]{32}\b'),
        'BCH': re.compile(r'\bbitcoincash:[qp][a-z0-9]{41}\b'),
        'DASH': re.compile(r'\bX[1-9A-HJ-NP-Za-km-z]{33}\b'),
        'ZEC': re.compile(r'\bt[13][a-km-zA-HJ-NP-Z1-9]{33}\b'),
    }
    
    # Patterns pour reseaux sociaux/messagerie
    PATTERNS_SOCIAL = {
        'Telegram': re.compile(r'(?:https?://)?(?:t\.me|telegram\.me)/([a-zA-Z0-9_]{5,})'),
        'Discord': re.compile(r'(?:https?://)?(?:discord\.gg|discordapp\.com/invite)/([a-zA-Z0-9]+)'),
        'Jabber': re.compile(r'[a-zA-Z0-9._%+-]+@(?:jabber|xmpp)\.[a-z]{2,}'),
        'Session': re.compile(r'\b05[a-fA-F0-9]{64}\b'),
        'Wickr': re.compile(r'(?i)wickr\s*:\s*([a-zA-Z0-9_]+)'),
        'Signal': re.compile(r'(?i)signal\s*:\s*\+?([0-9\s\-]+)'),
        'Matrix': re.compile(r'@[a-zA-Z0-9._=-]+:[a-zA-Z0-9.-]+'),
        'ICQ': re.compile(r'(?i)icq\s*:\s*(\d{5,})'),
        'Tox': re.compile(r'[A-F0-9]{76}'),
    }
    
    # Patterns pour detecter les types de sites
    CATEGORY_PATTERNS = {
        'marketplace': re.compile(r'(?i)\b(market|shop|store|buy|sell|vendor|listing|cart|checkout)\b'),
        'forum': re.compile(r'(?i)\b(forum|thread|post|topic|reply|member|board)\b'),
        'leak_dump': re.compile(r'(?i)\b(leak|dump|breach|database|combo|collection)\b'),
        'hacking': re.compile(r'(?i)\b(hack|exploit|vulnerability|0day|zero.?day|malware|rat|botnet)\b'),
        'carding': re.compile(r'(?i)\b(card|cvv|fullz|bin|bank|cc|credit|debit)\b'),
        'drugs': re.compile(r'(?i)\b(weed|cocaine|mdma|lsd|pills|pharma|cannabis|marijuana)\b'),
        'documents': re.compile(r'(?i)\b(passport|id|license|ssn|identity|document|fake)\b'),
        'weapons': re.compile(r'(?i)\b(weapon|gun|firearm|ammo|ammunition|explosive)\b'),
        'crypto_service': re.compile(r'(?i)\b(mixer|tumbler|exchange|wallet|swap|launder)\b'),
        'hosting': re.compile(r'(?i)\b(hosting|vps|server|domain|bulletproof|offshore)\b'),
    }
    
    # Mots-cles suspects par categorie
    KEYWORDS_SUSPICIOUS = [
        'escrow', 'pgp', 'btc', 'xmr', 'bitcoin', 'monero', 'anonymous',
        'private', 'secure', 'encrypted', 'tor', 'onion', 'hidden',
        'vendor', 'buyer', 'seller', 'shipping', 'stealth', 'worldwide'
    ]
    
    # Autres patterns
    PATTERN_IPV4 = re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b')
    PATTERN_EMAIL = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    PATTERN_ONION = re.compile(r'[a-z2-7]{16,56}\.onion')
    PATTERN_PHONE = re.compile(r'(?:\+|00)[1-9]\d{6,14}')
    PATTERN_PGP = re.compile(r'-----BEGIN PGP (?:PUBLIC|PRIVATE) KEY BLOCK-----')
    
    # Indicateurs de langue
    LANGUAGE_INDICATORS = {
        'en': ['the', 'and', 'for', 'with', 'you', 'this', 'that', 'have', 'from'],
        'ru': ['?', '?', '??', '???', '??', '???', '???', '???', '??'],
        'de': ['und', 'die', 'der', 'das', 'ist', 'nicht', 'mit', 'auf', 'f�r'],
        'fr': ['et', 'le', 'la', 'les', 'de', 'des', 'un', 'une', 'pour', 'que'],
        'es': ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'una', 'los', 'las'],
        'zh': ['?', '?', '?', '?', '?', '?', '?', '?', '?'],
        'pt': ['de', 'que', 'e', 'do', 'da', 'em', 'um', 'para', 'com'],
    }
    
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
            'connect.sid': 'Express.js',
            'XSRF-TOKEN': 'Angular/Laravel',
        }
        
        for indicator, tech in cookie_indicators.items():
            if indicator in cookies:
                stack.append(tech)
        
        return list(set(stack))
    
    @classmethod
    def detect_language(cls, text: str) -> str:
        """Detecte la langue principale du texte."""
        if not text or len(text) < 50:
            return ''
        
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        if not words:
            return ''
        
        scores = {}
        for lang, indicators in cls.LANGUAGE_INDICATORS.items():
            score = sum(1 for word in words if word in indicators)
            if score > 0:
                scores[lang] = score
        
        if scores:
            return max(scores, key=scores.get)
        return 'en'  # Default to English
    
    @classmethod
    def extract_keywords(cls, text: str, title: str = '', limit: int = 20) -> List[str]:
        """Extrait les mots-cles importants."""
        if not text:
            return []
        
        # Combiner titre et texte (titre a plus de poids)
        combined = (title + ' ') * 3 + text
        
        # Extraire les mots (3+ caracteres)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', combined.lower())
        
        # Filtrer les mots courants
        stopwords = {'the', 'and', 'for', 'with', 'you', 'this', 'that', 'have', 
                    'from', 'are', 'was', 'were', 'been', 'being', 'has', 'had',
                    'will', 'would', 'could', 'should', 'may', 'might', 'must',
                    'can', 'not', 'all', 'any', 'some', 'more', 'most', 'other'}
        
        filtered = [w for w in words if w not in stopwords and len(w) > 3]
        
        # Compter et retourner les plus frequents
        counter = Counter(filtered)
        return [word for word, _ in counter.most_common(limit)]
    
    @classmethod
    def detect_category(cls, text: str, title: str = '') -> str:
        """Detecte la categorie probable du site."""
        combined = (title + ' ' + text).lower()
        
        category_scores = {}
        for category, pattern in cls.CATEGORY_PATTERNS.items():
            matches = pattern.findall(combined)
            if matches:
                category_scores[category] = len(matches)
        
        if category_scores:
            return max(category_scores, key=category_scores.get)
        return ''
    
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
    def _extract_onion_links(cls, text: str) -> List[str]:
        """Extrait les liens .onion du texte."""
        onions = set(cls.PATTERN_ONION.findall(text))
        return list(onions)[:50]
    
    @classmethod
    def _extract_pgp_keys(cls, text: str) -> bool:
        """Detecte la presence de cles PGP."""
        return bool(cls.PATTERN_PGP.search(text))
    
    @classmethod
    def _extract_phone_numbers(cls, text: str) -> List[str]:
        """Extrait les numeros de telephone."""
        phones = set(cls.PATTERN_PHONE.findall(text))
        return list(phones)[:10]
    
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
            
            # Aussi chercher les ld+json (structured data)
            for script in soup.find_all('script', type='application/ld+json'):
                if script.string:
                    content = script.string.strip()
                    if 10 < len(content) < 5000:
                        json_data.append(content)
        except Exception:
            pass
        return json_data[:5]
    
    @classmethod
    def _extract_forms(cls, soup: BeautifulSoup) -> List[Dict]:
        """Extrait les informations sur les formulaires."""
        forms = []
        try:
            for form in soup.find_all('form'):
                form_info = {
                    'action': form.get('action', ''),
                    'method': form.get('method', 'get').upper(),
                    'inputs': []
                }
                for inp in form.find_all(['input', 'textarea', 'select']):
                    inp_type = inp.get('type', 'text')
                    inp_name = inp.get('name', '')
                    if inp_name and inp_type not in ['hidden', 'submit']:
                        form_info['inputs'].append({
                            'name': inp_name,
                            'type': inp_type
                        })
                if form_info['inputs']:
                    forms.append(form_info)
        except Exception:
            pass
        return forms[:10]
    
    @classmethod
    def _extract_meta_info(cls, soup: BeautifulSoup) -> Dict[str, str]:
        """Extrait les meta informations."""
        meta = {}
        try:
            for tag in soup.find_all('meta'):
                name = tag.get('name', tag.get('property', ''))
                content = tag.get('content', '')
                if name and content:
                    meta[name] = content[:200]
        except Exception:
            pass
        return meta
    
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
        title = ''
        try:
            title_tag = soup.find('title')
            title = title_tag.get_text(strip=True) if title_tag else ''
        except:
            pass
        
        return {
            'secrets': cls._extract_secrets(text),
            'cryptos': cls._extract_cryptos(text),
            'socials': cls._extract_socials(text),
            'emails': cls._extract_emails(text),
            'ip_leaks': cls._extract_ips(text),
            'tech_stack': cls.extract_tech_stack(headers),
            'comments': cls._extract_comments(soup),
            'json_data': cls._extract_json_data(soup),
            'language': cls.detect_language(text),
            'keywords': cls.extract_keywords(text, title),
            'category': cls.detect_category(text, title),
            'onion_links': cls._extract_onion_links(text),
            'has_pgp': cls._extract_pgp_keys(text),
            'phones': cls._extract_phone_numbers(text),
            'forms': cls._extract_forms(soup),
            'meta': cls._extract_meta_info(soup)
        }
    
    @classmethod
    def quick_analyze(cls, text: str) -> Dict[str, Any]:
        """Analyse rapide sans BeautifulSoup."""
        return {
            'secrets': cls._extract_secrets(text),
            'cryptos': cls._extract_cryptos(text),
            'socials': cls._extract_socials(text),
            'emails': cls._extract_emails(text),
            'ip_leaks': cls._extract_ips(text),
            'onion_links': cls._extract_onion_links(text),
            'language': cls.detect_language(text),
            'category': cls.detect_category(text)
        }
