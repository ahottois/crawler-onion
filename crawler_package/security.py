"""
Module de securite avancee.
JWT Auth, IP Whitelist, Rate Limiting, Audit Logging, Validation.
"""

import os
import re
import time
import json
import hmac
import hashlib
import base64
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict
from threading import Lock
from functools import wraps

from .logger import Log


class SecurityConfig:
    """Configuration de securite."""
    
    # JWT
    JWT_SECRET = os.environ.get('CRAWLER_JWT_SECRET', secrets.token_hex(32))
    JWT_EXPIRY_HOURS = 24
    JWT_ALGORITHM = 'HS256'
    
    # Auth
    AUTH_ENABLED = os.environ.get('CRAWLER_AUTH_ENABLED', 'false').lower() == 'true'
    AUTH_USERNAME = os.environ.get('CRAWLER_AUTH_USERNAME', 'admin')
    AUTH_PASSWORD = os.environ.get('CRAWLER_AUTH_PASSWORD', 'changeme')
    
    # IP Whitelist
    IP_WHITELIST_ENABLED = os.environ.get('CRAWLER_IP_WHITELIST', 'false').lower() == 'true'
    IP_WHITELIST = set(os.environ.get('CRAWLER_ALLOWED_IPS', '127.0.0.1,::1').split(','))
    
    # Rate Limiting
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_REQUESTS = 100  # par minute par IP
    RATE_LIMIT_SEARCH = 10     # recherches par seconde
    RATE_LIMIT_WINDOW = 60     # secondes
    
    # Validation
    MAX_URL_LENGTH = 2048
    MAX_SEED_URLS = 100
    MAX_QUERY_LENGTH = 200
    
    # Audit
    AUDIT_LOG_FILE = os.environ.get('CRAWLER_AUDIT_LOG', 'audit.log')
    AUDIT_ENABLED = True


class JWTManager:
    """Gestionnaire de tokens JWT."""
    
    @staticmethod
    def _base64url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')
    
    @staticmethod
    def _base64url_decode(data: str) -> bytes:
        padding = 4 - len(data) % 4
        if padding != 4:
            data += '=' * padding
        return base64.urlsafe_b64decode(data)
    
    @classmethod
    def create_token(cls, user: str, extra_claims: Dict = None) -> str:
        """Cree un token JWT."""
        header = {'alg': SecurityConfig.JWT_ALGORITHM, 'typ': 'JWT'}
        
        now = datetime.utcnow()
        payload = {
            'sub': user,
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(hours=SecurityConfig.JWT_EXPIRY_HOURS)).timestamp()),
            'jti': secrets.token_hex(16)
        }
        if extra_claims:
            payload.update(extra_claims)
        
        header_b64 = cls._base64url_encode(json.dumps(header).encode())
        payload_b64 = cls._base64url_encode(json.dumps(payload).encode())
        
        signature_input = f"{header_b64}.{payload_b64}"
        signature = hmac.new(
            SecurityConfig.JWT_SECRET.encode(),
            signature_input.encode(),
            hashlib.sha256
        ).digest()
        signature_b64 = cls._base64url_encode(signature)
        
        return f"{header_b64}.{payload_b64}.{signature_b64}"
    
    @classmethod
    def verify_token(cls, token: str) -> Tuple[bool, Optional[Dict], str]:
        """Verifie un token JWT. Retourne (valid, payload, error)."""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return False, None, "Invalid token format"
            
            header_b64, payload_b64, signature_b64 = parts
            
            # Verifier signature
            signature_input = f"{header_b64}.{payload_b64}"
            expected_sig = hmac.new(
                SecurityConfig.JWT_SECRET.encode(),
                signature_input.encode(),
                hashlib.sha256
            ).digest()
            
            provided_sig = cls._base64url_decode(signature_b64)
            if not hmac.compare_digest(expected_sig, provided_sig):
                return False, None, "Invalid signature"
            
            # Decoder payload
            payload = json.loads(cls._base64url_decode(payload_b64))
            
            # Verifier expiration
            if payload.get('exp', 0) < time.time():
                return False, None, "Token expired"
            
            return True, payload, ""
            
        except Exception as e:
            return False, None, f"Token error: {str(e)}"


class RateLimiter:
    """Rate limiter par IP."""
    
    def __init__(self):
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._searches: Dict[str, List[float]] = defaultdict(list)
        self._lock = Lock()
        self._blocked_ips: Set[str] = set()
        self._block_until: Dict[str, float] = {}
    
    def _cleanup_old(self, timestamps: List[float], window: float) -> List[float]:
        """Nettoie les timestamps anciens."""
        cutoff = time.time() - window
        return [t for t in timestamps if t > cutoff]
    
    def check_rate_limit(self, ip: str, is_search: bool = False) -> Tuple[bool, str]:
        """Verifie le rate limit. Retourne (allowed, message)."""
        if not SecurityConfig.RATE_LIMIT_ENABLED:
            return True, ""
        
        now = time.time()
        
        with self._lock:
            # Verifier si IP bloquee
            if ip in self._blocked_ips:
                block_end = self._block_until.get(ip, 0)
                if now < block_end:
                    remaining = int(block_end - now)
                    return False, f"IP blocked for {remaining}s"
                else:
                    self._blocked_ips.discard(ip)
                    del self._block_until[ip]
            
            # Rate limit general
            self._requests[ip] = self._cleanup_old(
                self._requests[ip], 
                SecurityConfig.RATE_LIMIT_WINDOW
            )
            
            if len(self._requests[ip]) >= SecurityConfig.RATE_LIMIT_REQUESTS:
                # Bloquer temporairement
                self._blocked_ips.add(ip)
                self._block_until[ip] = now + 300  # 5 min block
                AuditLogger.log('RATE_LIMIT_EXCEEDED', ip, {'requests': len(self._requests[ip])})
                return False, "Rate limit exceeded (100/min)"
            
            self._requests[ip].append(now)
            
            # Rate limit recherche
            if is_search:
                self._searches[ip] = self._cleanup_old(self._searches[ip], 1)
                
                if len(self._searches[ip]) >= SecurityConfig.RATE_LIMIT_SEARCH:
                    return False, "Search rate limit (10/sec)"
                
                self._searches[ip].append(now)
        
        return True, ""
    
    def get_stats(self) -> Dict:
        """Stats du rate limiter."""
        with self._lock:
            return {
                'active_ips': len(self._requests),
                'blocked_ips': list(self._blocked_ips),
                'total_requests_tracked': sum(len(v) for v in self._requests.values())
            }


class IPWhitelist:
    """Gestionnaire de whitelist IP."""
    
    def __init__(self):
        self._whitelist: Set[str] = set(SecurityConfig.IP_WHITELIST)
        self._lock = Lock()
    
    def is_allowed(self, ip: str) -> bool:
        """Verifie si l'IP est autorisee."""
        if not SecurityConfig.IP_WHITELIST_ENABLED:
            return True
        
        with self._lock:
            # Localhost toujours autorise
            if ip in ('127.0.0.1', '::1', 'localhost'):
                return True
            return ip in self._whitelist
    
    def add_ip(self, ip: str):
        """Ajoute une IP."""
        with self._lock:
            self._whitelist.add(ip)
    
    def remove_ip(self, ip: str):
        """Retire une IP."""
        with self._lock:
            self._whitelist.discard(ip)
    
    def get_list(self) -> List[str]:
        """Retourne la liste."""
        with self._lock:
            return list(self._whitelist)


class InputValidator:
    """Validation des entrees utilisateur."""
    
    # Regex pour URL .onion valide
    ONION_REGEX = re.compile(
        r'^https?://[a-z2-7]{16,56}\.onion(/[^\s<>"\']*)?$',
        re.IGNORECASE
    )
    
    # Regex pour domaine .onion
    ONION_DOMAIN_REGEX = re.compile(r'^[a-z2-7]{16,56}\.onion$', re.IGNORECASE)
    
    # Patterns dangereux (injection)
    DANGEROUS_PATTERNS = [
        re.compile(r'<script', re.IGNORECASE),
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'on\w+\s*=', re.IGNORECASE),
        re.compile(r'\{\{.*\}\}'),  # Template injection
        re.compile(r'\$\{.*\}'),     # Expression injection
        re.compile(r';\s*(?:DROP|DELETE|UPDATE|INSERT)', re.IGNORECASE),  # SQL
    ]
    
    @classmethod
    def validate_onion_url(cls, url: str) -> Tuple[bool, str]:
        """Valide une URL .onion."""
        if not url:
            return False, "URL vide"
        
        if len(url) > SecurityConfig.MAX_URL_LENGTH:
            return False, f"URL trop longue (max {SecurityConfig.MAX_URL_LENGTH})"
        
        # Check injection
        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern.search(url):
                return False, "Caracteres non autorises"
        
        if not cls.ONION_REGEX.match(url):
            return False, "Format URL .onion invalide"
        
        return True, ""
    
    @classmethod
    def validate_onion_domain(cls, domain: str) -> Tuple[bool, str]:
        """Valide un domaine .onion."""
        if not domain:
            return False, "Domaine vide"
        
        if len(domain) > 70:
            return False, "Domaine trop long"
        
        if not cls.ONION_DOMAIN_REGEX.match(domain):
            return False, "Format domaine .onion invalide"
        
        return True, ""
    
    @classmethod
    def validate_search_query(cls, query: str) -> Tuple[bool, str]:
        """Valide une requete de recherche."""
        if not query:
            return True, ""  # Requete vide OK
        
        if len(query) > SecurityConfig.MAX_QUERY_LENGTH:
            return False, f"Requete trop longue (max {SecurityConfig.MAX_QUERY_LENGTH})"
        
        # Check injection
        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern.search(query):
                return False, "Caracteres non autorises"
        
        return True, ""
    
    @classmethod
    def validate_seed_urls(cls, urls: List[str]) -> Tuple[bool, str, List[str]]:
        """Valide une liste d'URLs seed. Retourne (valid, error, valid_urls)."""
        if not urls:
            return False, "Aucune URL", []
        
        if len(urls) > SecurityConfig.MAX_SEED_URLS:
            return False, f"Trop d'URLs (max {SecurityConfig.MAX_SEED_URLS})", []
        
        valid_urls = []
        for url in urls:
            url = url.strip()
            if not url:
                continue
            
            is_valid, error = cls.validate_onion_url(url)
            if is_valid:
                valid_urls.append(url)
        
        if not valid_urls:
            return False, "Aucune URL valide", []
        
        return True, "", valid_urls
    
    @classmethod
    def sanitize_string(cls, s: str, max_length: int = 500) -> str:
        """Nettoie une chaine."""
        if not s:
            return ""
        
        # Tronquer
        s = s[:max_length]
        
        # Echapper HTML basique
        s = s.replace('<', '&lt;').replace('>', '&gt;')
        s = s.replace('"', '&quot;').replace("'", '&#39;')
        
        return s


class AuditLogger:
    """Logger d'audit pour les actions de securite."""
    
    _lock = Lock()
    _log_file = SecurityConfig.AUDIT_LOG_FILE
    
    @classmethod
    def log(cls, event_type: str, ip: str, details: Dict = None, user: str = None):
        """Enregistre un evenement d'audit."""
        if not SecurityConfig.AUDIT_ENABLED:
            return
        
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': event_type,
            'ip': ip,
            'user': user,
            'details': details or {}
        }
        
        with cls._lock:
            try:
                with open(cls._log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(entry) + '\n')
            except Exception as e:
                Log.error(f"Audit log error: {e}")
    
    @classmethod
    def get_recent_logs(cls, limit: int = 100) -> List[Dict]:
        """Recupere les logs recents."""
        logs = []
        try:
            with open(cls._log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    try:
                        logs.append(json.loads(line.strip()))
                    except:
                        pass
        except FileNotFoundError:
            pass
        except Exception as e:
            Log.error(f"Read audit log error: {e}")
        
        return list(reversed(logs))
    
    @classmethod
    def clear_old_logs(cls, days: int = 30):
        """Supprime les vieux logs."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        try:
            logs_to_keep = []
            with open(cls._log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        entry_time = datetime.fromisoformat(entry['timestamp'])
                        if entry_time > cutoff:
                            logs_to_keep.append(line)
                    except:
                        pass
            
            with open(cls._log_file, 'w', encoding='utf-8') as f:
                f.writelines(logs_to_keep)
                
        except FileNotFoundError:
            pass
        except Exception as e:
            Log.error(f"Clear audit log error: {e}")


class SecurityManager:
    """Gestionnaire de securite centralise."""
    
    def __init__(self):
        self.jwt = JWTManager()
        self.rate_limiter = RateLimiter()
        self.ip_whitelist = IPWhitelist()
        self.validator = InputValidator()
        self.audit = AuditLogger()
    
    def authenticate(self, username: str, password: str, ip: str) -> Tuple[bool, str, str]:
        """Authentifie un utilisateur. Retourne (success, token, error)."""
        if not SecurityConfig.AUTH_ENABLED:
            return True, "", ""
        
        # Verifier rate limit login
        allowed, msg = self.rate_limiter.check_rate_limit(ip)
        if not allowed:
            self.audit.log('AUTH_RATE_LIMITED', ip)
            return False, "", msg
        
        # Verifier credentials
        if username != SecurityConfig.AUTH_USERNAME or password != SecurityConfig.AUTH_PASSWORD:
            self.audit.log('AUTH_FAILED', ip, {'username': username})
            return False, "", "Invalid credentials"
        
        # Generer token
        token = self.jwt.create_token(username, {'ip': ip})
        self.audit.log('AUTH_SUCCESS', ip, {'username': username})
        
        return True, token, ""
    
    def check_request(self, ip: str, token: str = None, is_search: bool = False) -> Tuple[bool, str, Optional[Dict]]:
        """Verifie une requete. Retourne (allowed, error, user_info)."""
        # IP Whitelist
        if not self.ip_whitelist.is_allowed(ip):
            self.audit.log('IP_BLOCKED', ip)
            return False, "IP not allowed", None
        
        # Rate limit
        allowed, msg = self.rate_limiter.check_rate_limit(ip, is_search)
        if not allowed:
            return False, msg, None
        
        # Auth JWT
        if SecurityConfig.AUTH_ENABLED:
            if not token:
                return False, "Authentication required", None
            
            valid, payload, error = self.jwt.verify_token(token)
            if not valid:
                self.audit.log('AUTH_TOKEN_INVALID', ip, {'error': error})
                return False, error, None
            
            return True, "", payload
        
        return True, "", None
    
    def get_security_status(self) -> Dict:
        """Retourne le statut de securite."""
        return {
            'auth_enabled': SecurityConfig.AUTH_ENABLED,
            'ip_whitelist_enabled': SecurityConfig.IP_WHITELIST_ENABLED,
            'ip_whitelist': self.ip_whitelist.get_list(),
            'rate_limit_enabled': SecurityConfig.RATE_LIMIT_ENABLED,
            'rate_limit_stats': self.rate_limiter.get_stats(),
            'jwt_expiry_hours': SecurityConfig.JWT_EXPIRY_HOURS
        }


# Instance globale
security_manager = SecurityManager()
