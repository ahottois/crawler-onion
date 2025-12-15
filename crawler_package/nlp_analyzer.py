"""
Module NLP pour analyse de contenu.
Detection de langue, sentiment, classification de site.
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import Counter

from .logger import Log


@dataclass
class ContentAnalysis:
    """Resultat d'analyse de contenu."""
    language: str = "unknown"
    language_confidence: float = 0.0
    sentiment: str = "neutral"
    sentiment_score: float = 0.0
    site_type: str = "other"
    site_type_confidence: float = 0.0
    threat_indicators: List[str] = field(default_factory=list)
    threat_score: float = 0.0
    keywords: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    is_marketplace: bool = False
    is_forum: bool = False
    is_breach_site: bool = False
    is_ransomware: bool = False


class ThreatKeywords:
    """Mots-cles indicateurs de menaces."""
    
    BREACH = [
        'dump', 'leaked', 'leak', 'breached', 'breach', 'compromised',
        'database', 'db dump', 'stolen', 'hacked', 'records', 'credentials',
        'fullz', 'combolist', 'combo', 'dox', 'doxxed', 'exposed'
    ]
    
    RANSOMWARE = [
        'ransom', 'ransomware', 'encrypted', 'decryptor', 'double extortion',
        'lockbit', 'blackcat', 'alphv', 'conti', 'hive', 'revil', 'sodinokibi',
        'maze', 'ryuk', 'clop', 'akira', 'blackbasta', 'payment', 'bitcoin',
        'deadline', 'proof', 'victim', 'negotiation'
    ]
    
    CREDENTIALS = [
        'password', 'passwd', 'login', 'credentials', 'cleartext', 'hash',
        'ntlm', 'md5', 'sha1', 'bcrypt', 'username', 'user:pass', 'combo',
        'account', 'access', 'auth', 'token', 'api key', 'secret'
    ]
    
    MALWARE = [
        'trojan', 'rat', 'remote access', 'botnet', 'worm', 'virus',
        'backdoor', 'rootkit', 'keylogger', 'stealer', 'crypter', 'fud',
        'exploit', 'payload', 'shellcode', '0day', 'zero-day', 'cve'
    ]
    
    MARKETPLACE = [
        'vendor', 'seller', 'buyer', 'escrow', 'reputation', 'feedback',
        'shipping', 'delivery', 'order', 'purchase', 'price', 'btc',
        'pgp', 'encrypted', 'stealth', 'domestic', 'international',
        'listing', 'product', 'stock', 'available'
    ]
    
    CARDING = [
        'cc', 'cvv', 'fullz', 'dumps', 'track1', 'track2', 'bins',
        'card', 'credit', 'debit', 'visa', 'mastercard', 'amex',
        'cashout', 'cash out', 'atm', 'pos', 'skimmer', 'clone'
    ]
    
    FRAUD = [
        'fraud', 'scam', 'fake', 'counterfeit', 'phishing', 'spoof',
        'identity', 'id', 'passport', 'license', 'document', 'ssn',
        'social security', 'bank', 'transfer', 'wire', 'western union'
    ]
    
    DRUGS = [
        'drug', 'weed', 'cannabis', 'mdma', 'cocaine', 'heroin',
        'meth', 'lsd', 'pills', 'prescription', 'pharma', 'benzo',
        'opioid', 'fentanyl', 'vendor', 'review'
    ]
    
    WEAPONS = [
        'weapon', 'gun', 'firearm', 'ammo', 'ammunition', 'explosive',
        'bomb', 'grenade', 'rifle', 'pistol', 'silencer', 'suppressor'
    ]
    
    HACKING_SERVICES = [
        'hack', 'hacker', 'hacking', 'ddos', 'dos', 'attack', 'service',
        'booter', 'stresser', 'bruteforce', 'crack', 'breach', 'pentest'
    ]


class LanguageDetector:
    """Detecteur de langue simple base sur stopwords."""
    
    STOPWORDS = {
        'en': ['the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
               'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
               'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she'],
        'fr': ['le', 'de', 'un', 'être', 'et', 'à', 'il', 'avoir', 'ne', 'je',
               'son', 'que', 'se', 'qui', 'ce', 'dans', 'en', 'du', 'elle', 'au',
               'pour', 'pas', 'sur', 'faire', 'plus', 'dire', 'me', 'on', 'mon', 'lui'],
        'de': ['der', 'die', 'und', 'in', 'den', 'von', 'zu', 'das', 'mit', 'sich',
               'des', 'auf', 'für', 'ist', 'im', 'dem', 'nicht', 'ein', 'eine', 'als',
               'auch', 'es', 'an', 'er', 'hat', 'aus', 'bei', 'wir', 'nach', 'am'],
        'es': ['de', 'la', 'que', 'el', 'en', 'y', 'a', 'los', 'se', 'del',
               'las', 'un', 'por', 'con', 'no', 'una', 'su', 'para', 'es', 'al',
               'lo', 'como', 'más', 'pero', 'sus', 'le', 'ya', 'o', 'este', 'si'],
        'ru': ['?', '?', '??', '??', '?', '???', '??', '?', '???', '???',
               '??', '??', '??', '???', '???', '??', '?', '?', '??', '??'],
        'zh': ['?', '?', '?', '?', '?', '?', '?', '?', '?', '?'],
        'pt': ['de', 'que', 'e', 'do', 'da', 'em', 'um', 'para', 'é', 'com',
               'não', 'uma', 'os', 'no', 'se', 'na', 'por', 'mais', 'as', 'dos'],
    }
    
    @classmethod
    def detect(cls, text: str) -> Tuple[str, float]:
        """Detecte la langue d'un texte."""
        if not text or len(text) < 20:
            return 'unknown', 0.0
        
        # Tokeniser
        words = re.findall(r'\b\w+\b', text.lower())
        if not words:
            return 'unknown', 0.0
        
        word_set = set(words)
        total_words = len(words)
        
        scores = {}
        for lang, stopwords in cls.STOPWORDS.items():
            matches = len(word_set.intersection(set(stopwords)))
            scores[lang] = matches / len(stopwords)
        
        if not scores:
            return 'unknown', 0.0
        
        best_lang = max(scores, key=scores.get)
        confidence = min(scores[best_lang] * 2, 1.0)  # Normaliser
        
        # Seuil minimum
        if confidence < 0.15:
            return 'unknown', confidence
        
        return best_lang, round(confidence, 2)


class SentimentAnalyzer:
    """Analyseur de sentiment simple."""
    
    POSITIVE_WORDS = [
        'good', 'great', 'excellent', 'best', 'love', 'amazing', 'awesome',
        'fantastic', 'perfect', 'wonderful', 'happy', 'trusted', 'reliable',
        'fast', 'quality', 'recommend', 'legit', 'verified', 'top'
    ]
    
    NEGATIVE_WORDS = [
        'bad', 'worst', 'terrible', 'awful', 'hate', 'scam', 'fake', 'fraud',
        'slow', 'poor', 'broken', 'failed', 'ripper', 'exit', 'selective',
        'dead', 'down', 'seized', 'compromised', 'warning', 'avoid'
    ]
    
    @classmethod
    def analyze(cls, text: str) -> Tuple[str, float]:
        """Analyse le sentiment. Retourne (sentiment, score -1 to +1)."""
        if not text:
            return 'neutral', 0.0
        
        words = re.findall(r'\b\w+\b', text.lower())
        
        positive_count = sum(1 for w in words if w in cls.POSITIVE_WORDS)
        negative_count = sum(1 for w in words if w in cls.NEGATIVE_WORDS)
        
        total = positive_count + negative_count
        if total == 0:
            return 'neutral', 0.0
        
        score = (positive_count - negative_count) / total
        
        if score > 0.1:
            sentiment = 'positive'
        elif score < -0.1:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        return sentiment, round(score, 2)


class SiteClassifier:
    """Classificateur de type de site darknet."""
    
    SITE_TYPES = {
        'breach_market': {
            'keywords': ThreatKeywords.BREACH + ThreatKeywords.CREDENTIALS,
            'title_indicators': ['dump', 'leak', 'breach', 'database', 'combo'],
            'weight': 1.0
        },
        'ransomware_blog': {
            'keywords': ThreatKeywords.RANSOMWARE,
            'title_indicators': ['lock', 'ransom', 'encrypted', 'victim', 'leak'],
            'weight': 1.2
        },
        'marketplace': {
            'keywords': ThreatKeywords.MARKETPLACE + ThreatKeywords.DRUGS,
            'title_indicators': ['market', 'shop', 'store', 'vendor', 'buy'],
            'weight': 0.9
        },
        'carding_forum': {
            'keywords': ThreatKeywords.CARDING,
            'title_indicators': ['cc', 'cvv', 'card', 'fullz', 'dump'],
            'weight': 1.1
        },
        'hacking_forum': {
            'keywords': ThreatKeywords.HACKING_SERVICES + ThreatKeywords.MALWARE,
            'title_indicators': ['hack', 'exploit', 'forum', 'community'],
            'weight': 1.0
        },
        'discussion_forum': {
            'keywords': ['forum', 'thread', 'post', 'reply', 'member', 'topic', 'discussion'],
            'title_indicators': ['forum', 'board', 'community', 'chan'],
            'weight': 0.7
        },
        'paste_site': {
            'keywords': ['paste', 'text', 'code', 'raw', 'plain'],
            'title_indicators': ['paste', 'bin', 'text'],
            'weight': 0.6
        },
        'hosting_service': {
            'keywords': ['hosting', 'server', 'vps', 'dedicated', 'anonymous'],
            'title_indicators': ['host', 'server', 'cloud'],
            'weight': 0.5
        },
        'email_service': {
            'keywords': ['email', 'mail', 'inbox', 'encrypted', 'anonymous'],
            'title_indicators': ['mail', 'email', 'inbox'],
            'weight': 0.5
        },
        'search_engine': {
            'keywords': ['search', 'find', 'index', 'directory', 'links'],
            'title_indicators': ['search', 'find', 'directory'],
            'weight': 0.5
        },
    }
    
    @classmethod
    def classify(cls, title: str, content: str) -> Tuple[str, float]:
        """Classifie un site. Retourne (type, confidence)."""
        title_lower = title.lower() if title else ""
        content_lower = content.lower() if content else ""
        
        full_text = f"{title_lower} {content_lower}"
        words = set(re.findall(r'\b\w+\b', full_text))
        
        scores = {}
        
        for site_type, config in cls.SITE_TYPES.items():
            score = 0.0
            
            # Keywords dans le contenu
            keyword_matches = len(words.intersection(set(config['keywords'])))
            score += keyword_matches * 0.1 * config['weight']
            
            # Titre indicators (poids plus fort)
            for indicator in config['title_indicators']:
                if indicator in title_lower:
                    score += 0.3 * config['weight']
            
            scores[site_type] = min(score, 1.0)
        
        if not scores:
            return 'other', 0.0
        
        best_type = max(scores, key=scores.get)
        confidence = scores[best_type]
        
        if confidence < 0.2:
            return 'other', confidence
        
        return best_type, round(confidence, 2)


class ContentAnalyzer:
    """Analyseur de contenu complet."""
    
    def __init__(self):
        self.lang_detector = LanguageDetector()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.site_classifier = SiteClassifier()
    
    def analyze(self, title: str, content: str) -> ContentAnalysis:
        """Analyse complete d'un contenu."""
        analysis = ContentAnalysis()
        
        full_text = f"{title or ''} {content or ''}"
        
        # Detection langue
        analysis.language, analysis.language_confidence = self.lang_detector.detect(full_text)
        
        # Sentiment
        analysis.sentiment, analysis.sentiment_score = self.sentiment_analyzer.analyze(full_text)
        
        # Classification site
        analysis.site_type, analysis.site_type_confidence = self.site_classifier.classify(title, content)
        
        # Threat indicators
        analysis.threat_indicators, analysis.threat_score = self._detect_threats(full_text)
        
        # Keywords
        analysis.keywords = self._extract_keywords(full_text)
        
        # Topics
        analysis.topics = self._detect_topics(full_text)
        
        # Flags
        analysis.is_marketplace = analysis.site_type == 'marketplace'
        analysis.is_forum = 'forum' in analysis.site_type
        analysis.is_breach_site = analysis.site_type == 'breach_market'
        analysis.is_ransomware = analysis.site_type == 'ransomware_blog'
        
        return analysis
    
    def _detect_threats(self, text: str) -> Tuple[List[str], float]:
        """Detecte les indicateurs de menaces."""
        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))
        
        indicators = []
        scores = {
            'breach': (ThreatKeywords.BREACH, 0.8),
            'ransomware': (ThreatKeywords.RANSOMWARE, 0.9),
            'credentials': (ThreatKeywords.CREDENTIALS, 0.7),
            'malware': (ThreatKeywords.MALWARE, 0.8),
            'carding': (ThreatKeywords.CARDING, 0.8),
            'fraud': (ThreatKeywords.FRAUD, 0.7),
            'hacking': (ThreatKeywords.HACKING_SERVICES, 0.6),
        }
        
        total_score = 0.0
        count = 0
        
        for threat_type, (keywords, weight) in scores.items():
            matches = words.intersection(set(keywords))
            if matches:
                indicators.append(threat_type)
                match_ratio = len(matches) / len(keywords)
                total_score += match_ratio * weight
                count += 1
        
        final_score = total_score / max(count, 1) if count > 0 else 0.0
        
        return indicators, round(min(final_score, 1.0), 2)
    
    def _extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """Extrait les mots-cles principaux."""
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        
        # Exclure stopwords communs
        stopwords = set(['this', 'that', 'with', 'from', 'they', 'have', 'been',
                        'were', 'said', 'each', 'which', 'their', 'will', 'other',
                        'about', 'more', 'some', 'very', 'when', 'come', 'made'])
        
        filtered = [w for w in words if w not in stopwords and len(w) > 3]
        
        counter = Counter(filtered)
        return [word for word, count in counter.most_common(top_n)]
    
    def _detect_topics(self, text: str) -> List[str]:
        """Detecte les topics principaux."""
        topics = []
        text_lower = text.lower()
        
        topic_keywords = {
            'cryptocurrency': ['bitcoin', 'btc', 'ethereum', 'eth', 'monero', 'xmr', 'crypto', 'wallet'],
            'hacking': ['hack', 'exploit', 'vulnerability', 'payload', 'shell', 'root'],
            'data_breach': ['dump', 'leak', 'breach', 'database', 'records', 'exposed'],
            'malware': ['trojan', 'rat', 'botnet', 'malware', 'virus', 'backdoor'],
            'fraud': ['fraud', 'scam', 'phishing', 'fake', 'counterfeit'],
            'drugs': ['drug', 'cannabis', 'mdma', 'cocaine', 'pills'],
            'weapons': ['weapon', 'gun', 'firearm', 'explosive'],
            'identity': ['ssn', 'passport', 'license', 'identity', 'fullz'],
            'carding': ['cvv', 'card', 'dumps', 'bins', 'track'],
            'ransomware': ['ransom', 'encrypted', 'decryptor', 'payment'],
        }
        
        for topic, keywords in topic_keywords.items():
            if any(kw in text_lower for kw in keywords):
                topics.append(topic)
        
        return topics


# Instance globale
content_analyzer = ContentAnalyzer()
