"""
Module de securite avancee Red Team.
JWT Auth, 2FA TOTP, IP Whitelist, Rate Limiting, Audit Logging signe.
"""

import os
import re
import time
import json
import hmac
import hashlib
import base64
import secrets
import struct
import gzip
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
    JWT_REFRESH_DAYS = 7
    JWT_ALGORITHM = 'HS256'
    
    # Auth
    AUTH_ENABLED = os.environ.get('CRAWLER_AUTH_ENABLED', 'false').lower() == 'true'
    AUTH_USERNAME = os.environ.get('CRAWLER_AUTH_USERNAME', 'admin')
    AUTH_PASSWORD = os.environ.get('CRAWLER_AUTH_PASSWORD', 'changeme')
    
    # 2FA TOTP
    TOTP_ENABLED = os.environ.get('CRAWLER_2FA_ENABLED', 'false').lower() == 'true'
    TOTP_SECRET = os.environ.get('CRAWLER_TOTP_SECRET', '')
    TOTP_ISSUER = 'DarknetCrawler'
    
    # IP Whitelist
    IP_WHITELIST_ENABLED = os.environ.get('CRAWLER_IP_WHITELIST', 'false').lower() == 'true'
    IP_WHITELIST = set(os.environ.get('CRAWLER_ALLOWED_IPS', '127.0.0.1,::1').split(','))
    
    # Rate Limiting (conforme spec Red Team)
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_GLOBAL = 1000       # req/min par IP
    RATE_LIMIT_BURST = 50          # burst max
    RATE_LIMIT_SEARCH = 100        # searches/min par IP
    RATE_LIMIT_ADD_URL = 20        # URL additions/min par IP
    RATE_LIMIT_WINDOW = 60         # secondes
    BLACKLIST_AFTER_SPAM_MIN = 3   # minutes de spam = blacklist
    
    # Validation
    MAX_URL_LENGTH = 2048
    MAX_SEED_URLS = 100
    MAX_QUERY_LENGTH = 500
    
    # Audit
    AUDIT_LOG_FILE = os.environ.get('CRAWLER_AUDIT_LOG', 'audit.log')
    AUDIT_ENABLED = True
    AUDIT_RETENTION_DAYS = 90
    AUDIT_SIGNING_KEY = os.environ.get('CRAWLER_AUDIT_KEY', secrets.token_hex(32))


class TOTPManager:
    """Gestionnaire 2FA TOTP (Time-based One-Time Password)."""
    
    @staticmethod
    def generate_secret() -> str:
        """Genere un secret TOTP base32."""
        return base64.b32encode(secrets.token_bytes(20)).decode('utf-8')
    
    @staticmethod
    def get_totp_uri(secret: str, username: str) -> str:
        """Retourne l'URI pour QR code."""
        return f"otpauth://totp/{SecurityConfig.TOTP_ISSUER}:{username}?secret={secret}&issuer={SecurityConfig.TOTP_ISSUER}"
    
    @staticmethod
    def generate_totp(secret: str, timestamp: int = None) -> str:
        """Genere un code TOTP."""
        if timestamp is None:
            timestamp = int(time.time())
        
        # Time step = 30 secondes
        time_step = timestamp // 30
        
        # Decoder le secret base32
        try:
            key = base64.b32decode(secret.upper() + '=' * (8 - len(secret) % 8))
        except:
            key = base64.b32decode(secret.upper())
        
        # HMAC-SHA1
        msg = struct.pack('>Q', time_step)
        h = hmac.new(key, msg, hashlib.sha1).digest()
        
        # Dynamic truncation
        offset = h[-1] & 0x0F
        code = struct.unpack('>I', h[offset:offset + 4])[0] & 0x7FFFFFFF
        
        return str(code % 1000000).zfill(6)
    
    @classmethod
    def verify_totp(cls, secret: str, code: str, window: int = 1) -> bool:
        """Verifie un code TOTP avec fenetre de tolerance."""
        if not secret or not code:
            return False
        
        timestamp = int(time.time())
        
        # Verifier dans la fenetre (avant et apres)
        for i in range(-window, window + 1):
            expected = cls.generate_totp(secret, timestamp + (i * 30))
            if hmac.compare_digest(expected, code):
                return True
        
        return False


class SessionManager:
    """Gestionnaire de sessions."""
    
    def __init__(self):
        self._sessions: Dict[str, Dict] = {}
        self._revoked_tokens: Set[str] = set()
        self._lock = Lock()
    
    def create_session(self, user: str, ip: str, user_agent: str, token_jti: str) -> Dict:
        """Cree une nouvelle session."""
        session = {
            'user': user,
            'ip': ip,
            'user_agent': user_agent,
            'token_jti': token_jti,
            'login_at': datetime.utcnow().isoformat(),
            'last_activity': datetime.utcnow().isoformat(),
            'requests': 0
        }
        
        with self._lock:
            self._sessions[token_jti] = session
        
        return session
    
    def update_activity(self, token_jti: str):
        """Met a jour l'activite de la session."""
        with self._lock:
            if token_jti in self._sessions:
                self._sessions[token_jti]['last_activity'] = datetime.utcnow().isoformat()
                self._sessions[token_jti]['requests'] += 1
    
    def revoke_session(self, token_jti: str):
        """Revoque une session."""
        with self._lock:
            self._revoked_tokens.add(token_jti)
            if token_jti in self._sessions:
                del self._sessions[token_jti]
    
    def is_revoked(self, token_jti: str) -> bool:
        """Verifie si un token est revoque."""
        with self._lock:
            return token_jti in self._revoked_tokens
    
    def get_active_sessions(self, user: str = None) -> List[Dict]:
        """Retourne les sessions actives."""
        with self._lock:
            sessions = list(self._sessions.values())
            if user:
                sessions = [s for s in sessions if s['user'] == user]
            return sessions
    
    def cleanup_old_sessions(self, max_age_hours: int = 48):
        """Nettoie les vieilles sessions."""
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        with self._lock:
            to_remove = []
            for jti, session in self._sessions.items():
                try:
                    last = datetime.fromisoformat(session['last_activity'])
                    if last < cutoff:
                        to_remove.append(jti)
                except:
                    pass
            
            for jti in to_remove:
                del self._sessions[jti]


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
    def create_token(cls, user: str, ip: str, extra_claims: Dict = None, is_refresh: bool = False) -> Tuple[str, str]:
        """Cree un token JWT. Retourne (token, jti)."""
        header = {'alg': SecurityConfig.JWT_ALGORITHM, 'typ': 'JWT'}
        
        now = datetime.utcnow()
        jti = secrets.token_hex(16)
        
        if is_refresh:
            expiry = now + timedelta(days=SecurityConfig.JWT_REFRESH_DAYS)
        else:
            expiry = now + timedelta(hours=SecurityConfig.JWT_EXPIRY_HOURS)
        
        payload = {
            'sub': user,
            'iat': int(now.timestamp()),
            'exp': int(expiry.timestamp()),
            'jti': jti,
            'ip': ip,
            'type': 'refresh' if is_refresh else 'access'
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
        
        return f"{header_b64}.{payload_b64}.{signature_b64}", jti
    
    @classmethod
    def verify_token(cls, token: str, session_mgr: 'SessionManager' = None) -> Tuple[bool, Optional[Dict], str]:
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
            
            # Verifier revocation
            if session_mgr and session_mgr.is_revoked(payload.get('jti', '')):
                return False, None, "Token revoked"
            
            return True, payload, ""
            
        except Exception as e:
            return False, None, f"Token error: {str(e)}"


class RateLimiter:
    """Rate limiter avance par IP avec categories."""
    
    def __init__(self):
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._searches: Dict[str, List[float]] = defaultdict(list)
        self._url_adds: Dict[str, List[float]] = defaultdict(list)
        self._spam_tracker: Dict[str, int] = defaultdict(int)
        self._lock = Lock()
        self._blocked_ips: Set[str] = set()
        self._block_until: Dict[str, float] = {}
    
    def _cleanup_old(self, timestamps: List[float], window: float) -> List[float]:
        """Nettoie les timestamps anciens."""
        cutoff = time.time() - window
        return [t for t in timestamps if t > cutoff]
    
    def check_rate_limit(self, ip: str, request_type: str = 'general') -> Tuple[bool, str]:
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
                    return False, f"IP blocked for {remaining}s (spam detected)"
                else:
                    self._blocked_ips.discard(ip)
                    del self._block_until[ip]
                    self._spam_tracker[ip] = 0
            
            # Rate limit global
            self._requests[ip] = self._cleanup_old(
                self._requests[ip], 
                SecurityConfig.RATE_LIMIT_WINDOW
            )
            
            # Burst check
            recent_burst = len([t for t in self._requests[ip] if t > now - 1])
            if recent_burst >= SecurityConfig.RATE_LIMIT_BURST:
                self._spam_tracker[ip] += 1
                if self._spam_tracker[ip] >= SecurityConfig.BLACKLIST_AFTER_SPAM_MIN:
                    self._blocked_ips.add(ip)
                    self._block_until[ip] = now + 600  # 10 min block
                    AuditLogger.log('SPAM_BLOCKED', ip, {'spam_count': self._spam_tracker[ip]})
                return False, f"Burst limit exceeded ({SecurityConfig.RATE_LIMIT_BURST}/sec)"
            
            # Global limit
            if len(self._requests[ip]) >= SecurityConfig.RATE_LIMIT_GLOBAL:
                self._spam_tracker[ip] += 1
                return False, f"Rate limit exceeded ({SecurityConfig.RATE_LIMIT_GLOBAL}/min)"
            
            self._requests[ip].append(now)
            
            # Rate limit par type
            if request_type == 'search':
                self._searches[ip] = self._cleanup_old(self._searches[ip], 60)
                if len(self._searches[ip]) >= SecurityConfig.RATE_LIMIT_SEARCH:
                    return False, f"Search rate limit ({SecurityConfig.RATE_LIMIT_SEARCH}/min)"
                self._searches[ip].append(now)
            
            elif request_type == 'add_url':
                self._url_adds[ip] = self._cleanup_old(self._url_adds[ip], 60)
                if len(self._url_adds[ip]) >= SecurityConfig.RATE_LIMIT_ADD_URL:
                    return False, f"URL add rate limit ({SecurityConfig.RATE_LIMIT_ADD_URL}/min)"
                self._url_adds[ip].append(now)
        
        return True, ""
    
    def get_stats(self) -> Dict:
        """Stats du rate limiter."""
        with self._lock:
            return {
                'active_ips': len(self._requests),
                'blocked_ips': list(self._blocked_ips),
                'total_requests_tracked': sum(len(v) for v in self._requests.values()),
                'search_requests': sum(len(v) for v in self._searches.values()),
                'url_add_requests': sum(len(v) for v in self._url_adds.values())
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
            if ip in ('127.0.0.1', '::1', 'localhost'):
                return True
            return ip in self._whitelist
    
    def add_ip(self, ip: str):
        with self._lock:
            self._whitelist.add(ip)
    
    def remove_ip(self, ip: str):
        with self._lock:
            self._whitelist.discard(ip)
    
    def get_list(self) -> List[str]:
        with self._lock:
            return list(self._whitelist)


class InputValidator:
    """Validation des entrees utilisateur stricte."""
    
    # Regex pour URL .onion v3 (56 chars) et v2 (16 chars)
    ONION_V3_REGEX = re.compile(
        r'^https?://[a-z2-7]{56}\.onion(/[^\s<>"\']*)?$',
        re.IGNORECASE
    )
    ONION_V2_REGEX = re.compile(
        r'^https?://[a-z2-7]{16}\.onion(/[^\s<>"\']*)?$',
        re.IGNORECASE
    )
    
    # Regex pour domaine .onion
    ONION_DOMAIN_REGEX = re.compile(r'^[a-z2-7]{16,56}\.onion$', re.IGNORECASE)
    
    # Search query: alphanumeric, space, @, -, _, . only
    SEARCH_QUERY_REGEX = re.compile(r'^[a-zA-Z0-9\s@._-]+$')
    
    # Patterns suspects (injection)
    DANGEROUS_PATTERNS = [
        'javascript:',
        'data:',
        '<script',
        'onerror=',
        'onload=',
        'onclick=',
        'onmouseover=',
        '{{',
        '}}',
        '${',
        '}',
        ';--',
        '/*',
        '*/',
        'union',
        'select',
        'insert',
        'update',
        'delete',
        'drop',
        'exec',
        'execute',
    ]
    
    @classmethod
    def validate_onion_url(cls, url: str) -> Tuple[bool, str]:
        """Valide une URL .onion strictement."""
        if not url:
            return False, "URL vide"
        
        url = url.strip()
        
        if len(url) > SecurityConfig.MAX_URL_LENGTH:
            return False, f"URL trop longue (max {SecurityConfig.MAX_URL_LENGTH})"
        
        # Check patterns suspects
        url_lower = url.lower()
        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern in url_lower:
                return False, f"Pattern suspect detecte: {pattern}"
        
        # Valider format .onion v2 ou v3
        if not (cls.ONION_V3_REGEX.match(url) or cls.ONION_V2_REGEX.match(url)):
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
        """Valide une requete de recherche strictement."""
        if not query:
            return True, ""
        
        query = query.strip()
        
        if len(query) > SecurityConfig.MAX_QUERY_LENGTH:
            return False, f"Requete trop longue (max {SecurityConfig.MAX_QUERY_LENGTH})"
        
        # Verifier caracteres autorises
        if not cls.SEARCH_QUERY_REGEX.match(query):
            return False, "Caracteres non autorises (alphanumeric, @, -, _, . seulement)"
        
        return True, ""
    
    @classmethod
    def sanitize_search(cls, query: str) -> str:
        """Sanitize une requete de recherche."""
        if not query:
            return ""
        
        query = query.strip()[:SecurityConfig.MAX_QUERY_LENGTH]
        
        # Garder seulement caracteres autorises
        sanitized = re.sub(r'[^a-zA-Z0-9\s@._-]', '', query)
        
        return sanitized.strip()
    
    @classmethod
    def validate_seed_urls(cls, urls: List[str]) -> Tuple[bool, str, List[str]]:
        """Valide une liste d'URLs seed."""
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
        
        s = s[:max_length]
        s = s.replace('<', '&lt;').replace('>', '&gt;')
        s = s.replace('"', '&quot;').replace("'", '&#39;')
        
        return s


class AuditLogger:
    """Logger d'audit signe et compresse."""
    
    _lock = Lock()
    _log_file = SecurityConfig.AUDIT_LOG_FILE
    
    @classmethod
    def _sign_entry(cls, entry: Dict) -> str:
        """Signe une entree d'audit avec HMAC-SHA256."""
        data = json.dumps(entry, sort_keys=True)
        signature = hmac.new(
            SecurityConfig.AUDIT_SIGNING_KEY.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    @classmethod
    def _mask_sensitive(cls, value: str, type_: str) -> str:
        """Masque les donnees sensibles."""
        if not value:
            return value
        
        if type_ == 'email':
            parts = value.split('@')
            if len(parts) == 2:
                return f"{parts[0][0]}***@{parts[1]}"
        elif type_ == 'phone':
            if len(value) > 6:
                return f"{value[:4]}{'*' * (len(value) - 6)}{value[-2:]}"
        elif type_ == 'wallet':
            if len(value) > 10:
                return f"{value[:6]}...{value[-4:]}"
        
        return value
    
    @classmethod
    def log(cls, event_type: str, ip: str, details: Dict = None, user: str = None):
        """Enregistre un evenement d'audit signe."""
        if not SecurityConfig.AUDIT_ENABLED:
            return
        
        entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'event_type': event_type,
            'ip_address': ip,
            'user_id': user,
            'details': details or {},
            'response_time_ms': 0,
            'status': 'success'
        }
        
        # Signer l'entree
        entry['signature'] = cls._sign_entry(entry)
        
        with cls._lock:
            try:
                with open(cls._log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(entry) + '\n')
            except Exception as e:
                Log.error(f"Audit log error: {e}")
    
    @classmethod
    def log_request(cls, event_type: str, ip: str, user_agent: str, user: str = None,
                    action: str = None, query: str = None, filter_: str = None,
                    results_count: int = 0, response_time_ms: int = 0,
                    status: str = 'success', error: str = None):
        """Log complet d'une requete (format Red Team spec)."""
        entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'event_type': event_type,
            'user_id': user,
            'ip_address': ip,
            'user_agent': user_agent,
            'action': action,
            'query': query,
            'filter': filter_,
            'results_count': results_count,
            'response_time_ms': response_time_ms,
            'status': status,
            'error': error
        }
        
        entry['signature'] = cls._sign_entry(entry)
        
        with cls._lock:
            try:
                with open(cls._log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(entry) + '\n')
            except Exception as e:
                Log.error(f"Audit log error: {e}")
    
    @classmethod
    def get_recent_logs(cls, limit: int = 100, user: str = None, 
                       event_type: str = None, days: int = None) -> List[Dict]:
        """Recupere les logs recents avec filtres."""
        logs = []
        cutoff = None
        
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
        
        try:
            with open(cls._log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in reversed(lines):
                    if len(logs) >= limit:
                        break
                    try:
                        entry = json.loads(line.strip())
                        
                        # Filtres
                        if user and entry.get('user_id') != user:
                            continue
                        if event_type and entry.get('event_type') != event_type:
                            continue
                        if cutoff:
                            entry_time = datetime.fromisoformat(entry['timestamp'].rstrip('Z'))
                            if entry_time < cutoff:
                                continue
                        
                        # Verifier signature
                        sig = entry.pop('signature', '')
                        expected_sig = cls._sign_entry(entry)
                        entry['signature_valid'] = hmac.compare_digest(sig, expected_sig)
                        entry['signature'] = sig
                        
                        logs.append(entry)
                    except:
                        pass
        except FileNotFoundError:
            pass
        except Exception as e:
            Log.error(f"Read audit log error: {e}")
        
        return logs
    
    @classmethod
    def rotate_logs(cls):
        """Rotation quotidienne et compression."""
        today = datetime.utcnow().strftime('%Y%m%d')
        archive_name = f"{cls._log_file}.{today}.gz"
        
        try:
            if os.path.exists(cls._log_file):
                with open(cls._log_file, 'rb') as f_in:
                    with gzip.open(archive_name, 'wb') as f_out:
                        f_out.writelines(f_in)
                
                # Vider le fichier actuel
                open(cls._log_file, 'w').close()
                
                Log.info(f"Audit logs rotated to {archive_name}")
        except Exception as e:
            Log.error(f"Log rotation error: {e}")
    
    @classmethod
    def clear_old_logs(cls, days: int = None):
        """Supprime les vieux logs (retention policy)."""
        if days is None:
            days = SecurityConfig.AUDIT_RETENTION_DAYS
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        try:
            logs_to_keep = []
            with open(cls._log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        entry_time = datetime.fromisoformat(entry['timestamp'].rstrip('Z'))
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
        self.totp = TOTPManager()
        self.session_mgr = SessionManager()
        self.rate_limiter = RateLimiter()
        self.ip_whitelist = IPWhitelist()
        self.validator = InputValidator()
        self.audit = AuditLogger()
    
    def authenticate(self, username: str, password: str, ip: str, 
                    user_agent: str = '', totp_code: str = None) -> Tuple[bool, Dict, str]:
        """Authentifie un utilisateur. Retourne (success, tokens, error)."""
        if not SecurityConfig.AUTH_ENABLED:
            return True, {}, ""
        
        # Verifier rate limit login
        allowed, msg = self.rate_limiter.check_rate_limit(ip)
        if not allowed:
            self.audit.log('AUTH_RATE_LIMITED', ip, {'username': username})
            return False, {}, msg
        
        # Verifier credentials
        if username != SecurityConfig.AUTH_USERNAME or password != SecurityConfig.AUTH_PASSWORD:
            self.audit.log('AUTH_FAILED', ip, {'username': username}, user=username)
            return False, {}, "Invalid credentials"
        
        # Verifier 2FA si active
        if SecurityConfig.TOTP_ENABLED and SecurityConfig.TOTP_SECRET:
            if not totp_code:
                return False, {'requires_2fa': True}, "2FA code required"
            
            if not self.totp.verify_totp(SecurityConfig.TOTP_SECRET, totp_code):
                self.audit.log('AUTH_2FA_FAILED', ip, {'username': username}, user=username)
                return False, {}, "Invalid 2FA code"
        
        # Generer tokens
        access_token, access_jti = self.jwt.create_token(username, ip)
        refresh_token, refresh_jti = self.jwt.create_token(username, ip, is_refresh=True)
        
        # Creer session
        self.session_mgr.create_session(username, ip, user_agent, access_jti)
        
        self.audit.log('AUTH_SUCCESS', ip, {'username': username}, user=username)
        
        return True, {
            'token': access_token,
            'refresh_token': refresh_token,
            'expires_in': SecurityConfig.JWT_EXPIRY_HOURS * 3600,
            'token_type': 'Bearer'
        }, ""
    
    def refresh_token(self, refresh_token: str, ip: str) -> Tuple[bool, Dict, str]:
        """Refresh un access token."""
        valid, payload, error = self.jwt.verify_token(refresh_token, self.session_mgr)
        
        if not valid:
            return False, {}, error
        
        if payload.get('type') != 'refresh':
            return False, {}, "Invalid token type"
        
        # Generer nouveau access token
        username = payload.get('sub')
        new_token, new_jti = self.jwt.create_token(username, ip)
        
        return True, {
            'token': new_token,
            'expires_in': SecurityConfig.JWT_EXPIRY_HOURS * 3600
        }, ""
    
    def logout(self, token: str, ip: str):
        """Deconnexion (revocation du token)."""
        valid, payload, _ = self.jwt.verify_token(token)
        if valid:
            jti = payload.get('jti')
            self.session_mgr.revoke_session(jti)
            self.audit.log('AUTH_LOGOUT', ip, {'jti': jti}, user=payload.get('sub'))
    
    def check_request(self, ip: str, token: str = None, request_type: str = 'general') -> Tuple[bool, str, Optional[Dict]]:
        """Verifie une requete. Retourne (allowed, error, user_info)."""
        # IP Whitelist
        if not self.ip_whitelist.is_allowed(ip):
            self.audit.log('IP_BLOCKED', ip)
            return False, "IP not allowed", None
        
        # Rate limit
        allowed, msg = self.rate_limiter.check_rate_limit(ip, request_type)
        if not allowed:
            return False, msg, None
        
        # Auth JWT
        if SecurityConfig.AUTH_ENABLED:
            if not token:
                return False, "Authentication required", None
            
            valid, payload, error = self.jwt.verify_token(token, self.session_mgr)
            if not valid:
                self.audit.log('AUTH_TOKEN_INVALID', ip, {'error': error})
                return False, error, None
            
            # Update session activity
            self.session_mgr.update_activity(payload.get('jti'))
            
            return True, "", payload
        
        return True, "", None
    
    def setup_2fa(self, username: str) -> Dict:
        """Configure 2FA pour un utilisateur."""
        secret = self.totp.generate_secret()
        uri = self.totp.get_totp_uri(secret, username)
        
        return {
            'secret': secret,
            'uri': uri,
            'manual_entry': secret
        }
    
    def get_security_status(self) -> Dict:
        """Retourne le statut de securite."""
        return {
            'auth_enabled': SecurityConfig.AUTH_ENABLED,
            '2fa_enabled': SecurityConfig.TOTP_ENABLED,
            'ip_whitelist_enabled': SecurityConfig.IP_WHITELIST_ENABLED,
            'ip_whitelist': self.ip_whitelist.get_list(),
            'rate_limit_enabled': SecurityConfig.RATE_LIMIT_ENABLED,
            'rate_limits': {
                'global': f"{SecurityConfig.RATE_LIMIT_GLOBAL}/min",
                'burst': f"{SecurityConfig.RATE_LIMIT_BURST}/sec",
                'search': f"{SecurityConfig.RATE_LIMIT_SEARCH}/min",
                'add_url': f"{SecurityConfig.RATE_LIMIT_ADD_URL}/min"
            },
            'rate_limit_stats': self.rate_limiter.get_stats(),
            'jwt_expiry_hours': SecurityConfig.JWT_EXPIRY_HOURS,
            'active_sessions': len(self.session_mgr.get_active_sessions()),
            'audit_retention_days': SecurityConfig.AUDIT_RETENTION_DAYS
        }


# Instance globale
security_manager = SecurityManager()
