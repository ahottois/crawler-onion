"""
Module d'extraction d'entites avancee.
Regex patterns complets pour crypto, contacts, documents, socials.
"""

import re
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

from .logger import Log


@dataclass
class ExtractedEntity:
    """Entite extraite avec metadonnees."""
    type: str
    subtype: str
    value: str
    raw_value: str
    confidence: float
    context: str = ""
    source_url: str = ""
    source_domain: str = ""
    position: int = 0
    validated: bool = False
    enriched: bool = False
    metadata: Dict = field(default_factory=dict)
    found_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class EntityPatterns:
    """Tous les patterns regex pour extraction d'entites."""
    
    # ========== CRYPTO WALLETS ==========
    CRYPTO_PATTERNS = {
        'bitcoin': {
            'pattern': r'\b(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\b',
            'description': 'Bitcoin address (P2PKH, P2SH, Bech32)',
            'confidence': 0.85
        },
        'bitcoin_legacy': {
            'pattern': r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b',
            'description': 'Bitcoin legacy address',
            'confidence': 0.80
        },
        'monero': {
            'pattern': r'\b4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}\b',
            'description': 'Monero address',
            'confidence': 0.90
        },
        'ethereum': {
            'pattern': r'\b0x[a-fA-F0-9]{40}\b',
            'description': 'Ethereum/ERC-20 address',
            'confidence': 0.85
        },
        'zcash_transparent': {
            'pattern': r'\bt1[a-zA-Z0-9]{33}\b',
            'description': 'Zcash transparent address',
            'confidence': 0.85
        },
        'zcash_shielded': {
            'pattern': r'\bz[a-zA-Z0-9]{93}\b',
            'description': 'Zcash shielded address',
            'confidence': 0.85
        },
        'dash': {
            'pattern': r'\bX[a-zA-Z0-9]{33}\b',
            'description': 'Dash address',
            'confidence': 0.85
        },
        'dogecoin': {
            'pattern': r'\bD[a-zA-Z0-9]{33}\b',
            'description': 'Dogecoin address',
            'confidence': 0.85
        },
        'litecoin': {
            'pattern': r'\b[LM][a-km-zA-HJ-NP-Z1-9]{26,33}\b',
            'description': 'Litecoin address',
            'confidence': 0.80
        },
        'ripple': {
            'pattern': r'\br[0-9a-zA-Z]{24,34}\b',
            'description': 'Ripple/XRP address',
            'confidence': 0.75
        },
        'tron': {
            'pattern': r'\bT[A-Za-z1-9]{33}\b',
            'description': 'Tron/TRX address',
            'confidence': 0.85
        },
        'solana': {
            'pattern': r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b',
            'description': 'Solana address',
            'confidence': 0.60  # Lower because generic base58
        },
    }
    
    # ========== CONTACT INFO ==========
    CONTACT_PATTERNS = {
        'email': {
            'pattern': r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
            'description': 'Email address',
            'confidence': 0.90
        },
        'email_obfuscated': {
            'pattern': r'\b[a-zA-Z0-9._%+-]+\s*[\[\(\{]?\s*(?:@|at|AT)\s*[\]\)\}]?\s*[a-zA-Z0-9.-]+\s*[\[\(\{]?\s*(?:\.|dot|DOT)\s*[\]\)\}]?\s*[a-zA-Z]{2,}\b',
            'description': 'Obfuscated email',
            'confidence': 0.75
        },
        'phone_us': {
            'pattern': r'\+?1[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
            'description': 'US phone number',
            'confidence': 0.85
        },
        'phone_fr': {
            'pattern': r'\+?33\s?[0-9]{1,2}[-.\s]?[0-9]{2}[-.\s]?[0-9]{2}[-.\s]?[0-9]{2}[-.\s]?[0-9]{2}\b',
            'description': 'French phone number',
            'confidence': 0.85
        },
        'phone_de': {
            'pattern': r'\+?49\s?[0-9]{2,5}[-.\s]?[0-9]{3,9}\b',
            'description': 'German phone number',
            'confidence': 0.80
        },
        'phone_uk': {
            'pattern': r'\+?44\s?[0-9]{2,5}[-.\s]?[0-9]{3,8}\b',
            'description': 'UK phone number',
            'confidence': 0.80
        },
        'phone_intl': {
            'pattern': r'\+[0-9]{1,3}\s?[0-9\s.-]{9,15}\b',
            'description': 'International phone',
            'confidence': 0.70
        },
        'telegram': {
            'pattern': r'@[a-zA-Z][a-zA-Z0-9_]{4,31}(?!_by_bot)\b',
            'description': 'Telegram handle',
            'confidence': 0.85
        },
        'discord_user': {
            'pattern': r'\b[a-zA-Z0-9_]{2,32}#[0-9]{4}\b',
            'description': 'Discord username#tag',
            'confidence': 0.90
        },
        'discord_new': {
            'pattern': r'@[a-z0-9_.]{2,32}\b',
            'description': 'New Discord username',
            'confidence': 0.60
        },
        'jabber_xmpp': {
            'pattern': r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(im|chat|xmpp)\b',
            'description': 'Jabber/XMPP address',
            'confidence': 0.85
        },
        'session_id': {
            'pattern': r'\b05[a-f0-9]{64}\b',
            'description': 'Session messenger ID',
            'confidence': 0.90
        },
        'tox_id': {
            'pattern': r'\b[A-F0-9]{76}\b',
            'description': 'Tox ID',
            'confidence': 0.85
        },
    }
    
    # ========== DOCUMENTS & PII ==========
    DOCUMENT_PATTERNS = {
        'ssn_us': {
            'pattern': r'\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b',
            'description': 'US Social Security Number',
            'confidence': 0.70,
            'sensitive': True
        },
        'passport_generic': {
            'pattern': r'\b[A-Z]{1,2}[0-9]{6,9}\b',
            'description': 'Passport number',
            'confidence': 0.50,
            'sensitive': True
        },
        'credit_card': {
            'pattern': r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b',
            'description': 'Credit card number',
            'confidence': 0.80,
            'sensitive': True
        },
        'iban': {
            'pattern': r'\b[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}\b',
            'description': 'IBAN',
            'confidence': 0.75,
            'sensitive': True
        },
        'bic_swift': {
            'pattern': r'\b[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b',
            'description': 'BIC/SWIFT code',
            'confidence': 0.70
        },
        'drivers_license_us': {
            'pattern': r'\b[A-Z][0-9]{7,8}\b',
            'description': 'US drivers license',
            'confidence': 0.40,
            'sensitive': True
        },
        'national_id_fr': {
            'pattern': r'\b[12][0-9]{2}[0-9]{2}[0-9]{2}[0-9]{3}[0-9]{3}[0-9]{2}\b',
            'description': 'French national ID (INSEE)',
            'confidence': 0.80,
            'sensitive': True
        },
        'ip_address': {
            'pattern': r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
            'description': 'IPv4 address',
            'confidence': 0.95
        },
        'ipv6_address': {
            'pattern': r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b',
            'description': 'IPv6 address',
            'confidence': 0.90
        },
        'mac_address': {
            'pattern': r'\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b',
            'description': 'MAC address',
            'confidence': 0.90
        },
    }
    
    # ========== SOCIAL MEDIA URLs ==========
    SOCIAL_PATTERNS = {
        'twitter': {
            'pattern': r'(?:https?://)?(?:www\.)?(?:twitter|x)\.com/([a-zA-Z0-9_]{1,15})\b',
            'description': 'Twitter/X profile',
            'confidence': 0.95
        },
        'reddit': {
            'pattern': r'(?:https?://)?(?:www\.)?reddit\.com/(?:u|user)/([a-zA-Z0-9_-]{3,20})\b',
            'description': 'Reddit profile',
            'confidence': 0.95
        },
        'telegram_channel': {
            'pattern': r'(?:https?://)?(?:www\.)?t\.me/([a-zA-Z][a-zA-Z0-9_]{4,31})\b',
            'description': 'Telegram channel/user',
            'confidence': 0.95
        },
        'discord_invite': {
            'pattern': r'(?:https?://)?(?:www\.)?discord\.(?:gg|com/invite)/([a-zA-Z0-9]+)\b',
            'description': 'Discord invite',
            'confidence': 0.95
        },
        'instagram': {
            'pattern': r'(?:https?://)?(?:www\.)?instagram\.com/([a-zA-Z0-9_.]{1,30})\b',
            'description': 'Instagram profile',
            'confidence': 0.95
        },
        'facebook': {
            'pattern': r'(?:https?://)?(?:www\.)?facebook\.com/([a-zA-Z0-9.]+)\b',
            'description': 'Facebook profile',
            'confidence': 0.90
        },
        'youtube': {
            'pattern': r'(?:https?://)?(?:www\.)?youtube\.com/(?:channel|c|user|@)/([a-zA-Z0-9_-]+)\b',
            'description': 'YouTube channel',
            'confidence': 0.95
        },
        'github': {
            'pattern': r'(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?)\b',
            'description': 'GitHub profile',
            'confidence': 0.95
        },
        'linkedin': {
            'pattern': r'(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9-]+)\b',
            'description': 'LinkedIn profile',
            'confidence': 0.95
        },
        'keybase': {
            'pattern': r'(?:https?://)?(?:www\.)?keybase\.io/([a-zA-Z0-9_]+)\b',
            'description': 'Keybase profile',
            'confidence': 0.95
        },
    }
    
    # ========== USERNAMES & CREDENTIALS ==========
    USERNAME_PATTERNS = {
        'username_labeled': {
            'pattern': r'(?:user(?:name)?|account|handle|login|nick)[\s:=]+([a-zA-Z0-9._-]{3,32})',
            'description': 'Labeled username',
            'confidence': 0.80
        },
        'password_labeled': {
            'pattern': r'(?:pass(?:word)?|pwd|secret)[\s:=]+([^\s]{4,64})',
            'description': 'Labeled password',
            'confidence': 0.85,
            'sensitive': True
        },
        'api_key_generic': {
            'pattern': r'(?:api[_-]?key|apikey|api[_-]?secret)[\s:=]+([a-zA-Z0-9_-]{20,64})',
            'description': 'API key',
            'confidence': 0.85,
            'sensitive': True
        },
        'bearer_token': {
            'pattern': r'[Bb]earer\s+([a-zA-Z0-9._-]{20,500})',
            'description': 'Bearer token',
            'confidence': 0.90,
            'sensitive': True
        },
        'private_key': {
            'pattern': r'-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----',
            'description': 'Private key header',
            'confidence': 0.95,
            'sensitive': True
        },
        'aws_access_key': {
            'pattern': r'\bAKIA[0-9A-Z]{16}\b',
            'description': 'AWS Access Key ID',
            'confidence': 0.95,
            'sensitive': True
        },
        'aws_secret_key': {
            'pattern': r'\b[A-Za-z0-9/+=]{40}\b',
            'description': 'Possible AWS Secret Key',
            'confidence': 0.40,
            'sensitive': True
        },
        'github_token': {
            'pattern': r'\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36}\b',
            'description': 'GitHub token',
            'confidence': 0.95,
            'sensitive': True
        },
        'jwt_token': {
            'pattern': r'\beyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\b',
            'description': 'JWT token',
            'confidence': 0.95,
            'sensitive': True
        },
    }
    
    # ========== ADDRESSES ==========
    ADDRESS_PATTERNS = {
        'us_address': {
            'pattern': r'\d{1,5}\s+[a-zA-Z\s]+(?:St|Street|Rd|Road|Ave|Avenue|Blvd|Boulevard|Dr|Drive|Ln|Lane|Ct|Court)\.?,\s*[a-zA-Z\s]+,\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?',
            'description': 'US address',
            'confidence': 0.75
        },
        'zip_code_us': {
            'pattern': r'\b\d{5}(?:-\d{4})?\b',
            'description': 'US ZIP code',
            'confidence': 0.50
        },
        'postal_code_uk': {
            'pattern': r'\b[A-Z]{1,2}[0-9][0-9A-Z]?\s*[0-9][A-Z]{2}\b',
            'description': 'UK postal code',
            'confidence': 0.80
        },
    }
    
    # ========== HASHES ==========
    HASH_PATTERNS = {
        'md5': {
            'pattern': r'\b[a-fA-F0-9]{32}\b',
            'description': 'MD5 hash',
            'confidence': 0.70
        },
        'sha1': {
            'pattern': r'\b[a-fA-F0-9]{40}\b',
            'description': 'SHA1 hash',
            'confidence': 0.75
        },
        'sha256': {
            'pattern': r'\b[a-fA-F0-9]{64}\b',
            'description': 'SHA256 hash',
            'confidence': 0.80
        },
        'sha512': {
            'pattern': r'\b[a-fA-F0-9]{128}\b',
            'description': 'SHA512 hash',
            'confidence': 0.85
        },
        'bcrypt': {
            'pattern': r'\$2[aby]?\$[0-9]{2}\$[./A-Za-z0-9]{53}',
            'description': 'Bcrypt hash',
            'confidence': 0.95
        },
        'ntlm': {
            'pattern': r'\b[a-fA-F0-9]{32}:[a-fA-F0-9]{32}\b',
            'description': 'NTLM hash pair',
            'confidence': 0.85
        },
    }


class EntityExtractor:
    """Extracteur d'entites avance."""
    
    def __init__(self):
        self._compiled_patterns: Dict[str, Dict] = {}
        self._compile_all_patterns()
    
    def _compile_all_patterns(self):
        """Compile tous les patterns regex."""
        pattern_groups = {
            'crypto': EntityPatterns.CRYPTO_PATTERNS,
            'contact': EntityPatterns.CONTACT_PATTERNS,
            'document': EntityPatterns.DOCUMENT_PATTERNS,
            'social': EntityPatterns.SOCIAL_PATTERNS,
            'username': EntityPatterns.USERNAME_PATTERNS,
            'address': EntityPatterns.ADDRESS_PATTERNS,
            'hash': EntityPatterns.HASH_PATTERNS,
        }
        
        for group_name, patterns in pattern_groups.items():
            self._compiled_patterns[group_name] = {}
            for name, config in patterns.items():
                try:
                    self._compiled_patterns[group_name][name] = {
                        'regex': re.compile(config['pattern'], re.IGNORECASE),
                        'description': config['description'],
                        'confidence': config['confidence'],
                        'sensitive': config.get('sensitive', False)
                    }
                except Exception as e:
                    Log.error(f"Failed to compile pattern {name}: {e}")
    
    def extract_all(self, text: str, url: str = "", domain: str = "") -> List[ExtractedEntity]:
        """Extrait toutes les entites d'un texte."""
        if not text:
            return []
        
        entities = []
        seen: Set[Tuple[str, str]] = set()  # (type, value) pour deduplication
        
        for group_name, patterns in self._compiled_patterns.items():
            for pattern_name, config in patterns.items():
                try:
                    for match in config['regex'].finditer(text):
                        value = match.group(1) if match.groups() else match.group(0)
                        
                        # Deduplication
                        key = (pattern_name, value.lower())
                        if key in seen:
                            continue
                        seen.add(key)
                        
                        # Contexte (50 chars avant et apres)
                        start = max(0, match.start() - 50)
                        end = min(len(text), match.end() + 50)
                        context = text[start:end].replace('\n', ' ').strip()
                        
                        entity = ExtractedEntity(
                            type=group_name,
                            subtype=pattern_name,
                            value=value,
                            raw_value=match.group(0),
                            confidence=config['confidence'],
                            context=context,
                            source_url=url,
                            source_domain=domain,
                            position=match.start(),
                            metadata={
                                'description': config['description'],
                                'sensitive': config['sensitive']
                            }
                        )
                        
                        # Validation supplementaire
                        entity = self._validate_entity(entity)
                        
                        entities.append(entity)
                        
                except Exception as e:
                    Log.debug(f"Error extracting {pattern_name}: {e}")
        
        # Trier par position
        entities.sort(key=lambda e: e.position)
        
        return entities
    
    def extract_by_type(self, text: str, entity_type: str, url: str = "", domain: str = "") -> List[ExtractedEntity]:
        """Extrait un type specifique d'entites."""
        if entity_type not in self._compiled_patterns:
            return []
        
        entities = []
        seen: Set[str] = set()
        
        for pattern_name, config in self._compiled_patterns[entity_type].items():
            try:
                for match in config['regex'].finditer(text):
                    value = match.group(1) if match.groups() else match.group(0)
                    
                    if value.lower() in seen:
                        continue
                    seen.add(value.lower())
                    
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    context = text[start:end].replace('\n', ' ').strip()
                    
                    entity = ExtractedEntity(
                        type=entity_type,
                        subtype=pattern_name,
                        value=value,
                        raw_value=match.group(0),
                        confidence=config['confidence'],
                        context=context,
                        source_url=url,
                        source_domain=domain,
                        position=match.start(),
                        metadata={
                            'description': config['description'],
                            'sensitive': config['sensitive']
                        }
                    )
                    
                    entity = self._validate_entity(entity)
                    entities.append(entity)
                    
            except Exception as e:
                Log.debug(f"Error extracting {pattern_name}: {e}")
        
        return entities
    
    def _validate_entity(self, entity: ExtractedEntity) -> ExtractedEntity:
        """Valide et ajuste la confidence d'une entite."""
        
        # Validation specifique par type
        if entity.type == 'crypto':
            entity = self._validate_crypto(entity)
        elif entity.type == 'document':
            entity = self._validate_document(entity)
        elif entity.type == 'contact':
            entity = self._validate_contact(entity)
        
        return entity
    
    def _validate_crypto(self, entity: ExtractedEntity) -> ExtractedEntity:
        """Valide une adresse crypto."""
        value = entity.value
        
        # Bitcoin checksum validation (simplifie)
        if entity.subtype in ('bitcoin', 'bitcoin_legacy'):
            if len(value) < 26 or len(value) > 35:
                entity.confidence *= 0.5
        
        # Ethereum checksum
        if entity.subtype == 'ethereum':
            if not value.startswith('0x'):
                entity.confidence *= 0.5
        
        entity.validated = True
        return entity
    
    def _validate_document(self, entity: ExtractedEntity) -> ExtractedEntity:
        """Valide un document (credit card, SSN, etc.)."""
        
        # Luhn validation pour cartes de credit
        if entity.subtype == 'credit_card':
            if self._luhn_check(entity.value):
                entity.confidence = 0.95
                entity.validated = True
            else:
                entity.confidence *= 0.3
        
        return entity
    
    def _validate_contact(self, entity: ExtractedEntity) -> ExtractedEntity:
        """Valide un contact (email, phone)."""
        
        # Email validation basique
        if entity.subtype == 'email':
            if '@' in entity.value and '.' in entity.value.split('@')[1]:
                entity.validated = True
            else:
                entity.confidence *= 0.5
        
        return entity
    
    def _luhn_check(self, card_number: str) -> bool:
        """Algorithme de Luhn pour validation carte."""
        try:
            digits = [int(d) for d in card_number if d.isdigit()]
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            
            total = sum(odd_digits)
            for d in even_digits:
                total += sum(divmod(d * 2, 10))
            
            return total % 10 == 0
        except:
            return False
    
    def get_summary(self, entities: List[ExtractedEntity]) -> Dict:
        """Resume des entites extraites."""
        summary = {
            'total': len(entities),
            'by_type': {},
            'by_subtype': {},
            'high_confidence': 0,
            'sensitive': 0,
            'validated': 0
        }
        
        for entity in entities:
            # Par type
            if entity.type not in summary['by_type']:
                summary['by_type'][entity.type] = 0
            summary['by_type'][entity.type] += 1
            
            # Par subtype
            key = f"{entity.type}:{entity.subtype}"
            if key not in summary['by_subtype']:
                summary['by_subtype'][key] = 0
            summary['by_subtype'][key] += 1
            
            # Stats
            if entity.confidence >= 0.8:
                summary['high_confidence'] += 1
            if entity.metadata.get('sensitive'):
                summary['sensitive'] += 1
            if entity.validated:
                summary['validated'] += 1
        
        return summary


# Instance globale
entity_extractor = EntityExtractor()
