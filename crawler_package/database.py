"""
Module de gestion de la base de donnees SQLite.
Stocke les resultats du crawling avec recherche FTS5 et chiffrement.
"""

import sqlite3
import json
import csv
import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple
from urllib.parse import urlparse
from threading import Lock
import threading

from .logger import Log


# Import optionnel du chiffrement
try:
    from .encryption import encryptor, EncryptionConfig
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    encryptor = None


class DatabaseManager:
    """Gestionnaire de base de donnees SQLite thread-safe avec FTS5 et chiffrement."""
    
    SENSITIVE_FIELDS = ['emails', 'ip_leaks', 'secrets_found']
    
    def __init__(self, db_file: str):
        self.db_file = db_file
        self._lock = Lock()
        self._init_db()
    
    @contextmanager
    def _get_connection(self):
        """Context manager pour connexion thread-safe."""
        conn = sqlite3.connect(self.db_file, check_same_thread=False)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def _encrypt_sensitive(self, data: Dict) -> Dict:
        """Chiffre les champs sensibles."""
        if not ENCRYPTION_AVAILABLE or not EncryptionConfig.ENCRYPTION_ENABLED:
            return data
        
        result = data.copy()
        for field in self.SENSITIVE_FIELDS:
            if field in result and result[field]:
                if isinstance(result[field], list):
                    result[field] = [encryptor.cipher.encrypt(str(v)) for v in result[field]]
                elif isinstance(result[field], dict):
                    result[field] = {k: [encryptor.cipher.encrypt(str(v)) for v in vals] 
                                    for k, vals in result[field].items()}
        return result
    
    def _decrypt_sensitive(self, data: Dict) -> Dict:
        """Dechiffre les champs sensibles."""
        if not ENCRYPTION_AVAILABLE:
            return data
        
        result = data.copy()
        for field in self.SENSITIVE_FIELDS:
            if field in result and result[field]:
                if isinstance(result[field], list):
                    result[field] = [encryptor.cipher.decrypt(str(v)) for v in result[field]]
                elif isinstance(result[field], dict):
                    result[field] = {k: [encryptor.cipher.decrypt(str(v)) for v in vals]
                                    for k, vals in result[field].items()}
        return result
    
    def _init_db(self):
        """Initialise le schema complet de la base."""
        with self._get_connection() as conn:
            # Table principale intel
            conn.execute('''
                CREATE TABLE IF NOT EXISTS intel (
                    url TEXT PRIMARY KEY,
                    domain TEXT,
                    title TEXT,
                    status INTEGER DEFAULT 0,
                    depth INTEGER DEFAULT 0,
                    tech_stack TEXT DEFAULT '[]',
                    secrets_found TEXT DEFAULT '{}',
                    ip_leaks TEXT DEFAULT '[]',
                    emails TEXT DEFAULT '[]',
                    comments TEXT DEFAULT '[]',
                    cryptos TEXT DEFAULT '{}',
                    socials TEXT DEFAULT '{}',
                    json_data TEXT DEFAULT '[]',
                    content_length INTEGER DEFAULT 0,
                    content_text TEXT DEFAULT '',
                    content_hash TEXT DEFAULT '',
                    language TEXT DEFAULT '',
                    keywords TEXT DEFAULT '[]',
                    category TEXT DEFAULT '',
                    site_type TEXT DEFAULT '',
                    tags TEXT DEFAULT '[]',
                    risk_score INTEGER DEFAULT 0,
                    threat_score REAL DEFAULT 0,
                    priority_score INTEGER DEFAULT 50,
                    crawl_count INTEGER DEFAULT 0,
                    intel_density REAL DEFAULT 0,
                    sentiment_score REAL DEFAULT 0,
                    marked_important INTEGER DEFAULT 0,
                    marked_false_positive INTEGER DEFAULT 0,
                    encrypted INTEGER DEFAULT 0,
                    found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_crawl TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # MIGRATION: Ajouter les colonnes manquantes AVANT de creer les index
            self._migrate_columns(conn)
            
            # Index (apres migration)
            conn.execute('CREATE INDEX IF NOT EXISTS idx_domain ON intel(domain)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_status ON intel(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_found_at ON intel(found_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_category ON intel(category)')
            
            # Index sur colonnes potentiellement nouvelles (avec try/except)
            try:
                conn.execute('CREATE INDEX IF NOT EXISTS idx_risk ON intel(risk_score)')
            except:
                pass
            try:
                conn.execute('CREATE INDEX IF NOT EXISTS idx_priority ON intel(priority_score)')
            except:
                pass
            try:
                conn.execute('CREATE INDEX IF NOT EXISTS idx_site_type ON intel(site_type)')
            except:
                pass
            
            # Table FTS5 pour recherche full-text
            try:
                conn.execute('''
                    CREATE VIRTUAL TABLE IF NOT EXISTS intel_fts USING fts5(
                        url, domain, title, content_text, emails_text, 
                        content='intel', content_rowid='rowid'
                    )
                ''')
            except:
                pass
            
            # Table pour les domaines avec profils
            conn.execute('''
                CREATE TABLE IF NOT EXISTS domains (
                    domain TEXT PRIMARY KEY,
                    status TEXT DEFAULT 'normal',
                    trust_level TEXT DEFAULT 'unknown',
                    crawl_profile TEXT DEFAULT 'default',
                    max_depth INTEGER DEFAULT 5,
                    delay_ms INTEGER DEFAULT 1000,
                    max_pages INTEGER DEFAULT 100,
                    priority_boost INTEGER DEFAULT 0,
                    notes TEXT DEFAULT '',
                    total_pages INTEGER DEFAULT 0,
                    success_pages INTEGER DEFAULT 0,
                    intel_count INTEGER DEFAULT 0,
                    avg_risk_score REAL DEFAULT 0,
                    last_intel_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Table pour les listes de domaines
            conn.execute('''
                CREATE TABLE IF NOT EXISTS domain_lists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT UNIQUE,
                    list_type TEXT,
                    reason TEXT DEFAULT '',
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Table pour les alertes avancees
            conn.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT UNIQUE,
                    type TEXT,
                    severity TEXT DEFAULT 'info',
                    trigger TEXT DEFAULT '',
                    title TEXT,
                    message TEXT,
                    url TEXT,
                    domain TEXT,
                    entities TEXT DEFAULT '{}',
                    metadata TEXT DEFAULT '{}',
                    webhook_sent INTEGER DEFAULT 0,
                    read INTEGER DEFAULT 0,
                    acknowledged INTEGER DEFAULT 0,
                    acknowledged_by TEXT,
                    acknowledged_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_alert_severity ON alerts(severity)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_alert_read ON alerts(read)')
            
            # Table pour les stats horaires
            conn.execute('''
                CREATE TABLE IF NOT EXISTS hourly_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hour TEXT UNIQUE,
                    urls_crawled INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    new_domains INTEGER DEFAULT 0,
                    intel_found INTEGER DEFAULT 0,
                    queue_size INTEGER DEFAULT 0,
                    alerts_created INTEGER DEFAULT 0,
                    avg_response_time REAL DEFAULT 0
                )
            ''')
            
            # Table pour les regles de priorite
            conn.execute('''
                CREATE TABLE IF NOT EXISTS priority_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    condition_type TEXT,
                    condition_value TEXT,
                    priority_modifier INTEGER DEFAULT 0,
                    enabled INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Table pour les entites OSINT enrichie
            conn.execute('''
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT,
                    subtype TEXT DEFAULT '',
                    value TEXT,
                    normalized_value TEXT,
                    source_url TEXT,
                    source_domain TEXT,
                    confidence REAL DEFAULT 0.5,
                    validated INTEGER DEFAULT 0,
                    enriched INTEGER DEFAULT 0,
                    risk_score REAL DEFAULT 0,
                    metadata TEXT DEFAULT '{}',
                    enrichment_data TEXT DEFAULT '{}',
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    occurrence_count INTEGER DEFAULT 1,
                    UNIQUE(entity_type, value)
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_entity_type ON entities(entity_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_entity_value ON entities(value)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_entity_domain ON entities(source_domain)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_entity_risk ON entities(risk_score)')
            
            # Table pour le graphe d'entites (edges)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS entity_graph (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_entity_id INTEGER,
                    target_entity_id INTEGER,
                    relationship TEXT DEFAULT 'co-occurrence',
                    weight REAL DEFAULT 1.0,
                    evidence TEXT DEFAULT '[]',
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    occurrence_count INTEGER DEFAULT 1,
                    UNIQUE(source_entity_id, target_entity_id),
                    FOREIGN KEY(source_entity_id) REFERENCES entities(id),
                    FOREIGN KEY(target_entity_id) REFERENCES entities(id)
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_graph_source ON entity_graph(source_entity_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_graph_target ON entity_graph(target_entity_id)')
            
            # Table pour les correlations detectees
            conn.execute('''
                CREATE TABLE IF NOT EXISTS correlations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity1_id INTEGER,
                    entity2_id INTEGER,
                    correlation_score REAL,
                    confidence REAL,
                    relationship_type TEXT,
                    evidence TEXT DEFAULT '[]',
                    interpretation TEXT DEFAULT '',
                    status TEXT DEFAULT 'pending',
                    reviewed_by TEXT,
                    reviewed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(entity1_id) REFERENCES entities(id),
                    FOREIGN KEY(entity2_id) REFERENCES entities(id)
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_corr_score ON correlations(correlation_score)')
            
            # Table pour l'audit
            conn.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    event_type TEXT,
                    user_id TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    action TEXT,
                    query TEXT,
                    details TEXT DEFAULT '{}',
                    response_time_ms INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'success',
                    signature TEXT
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id)')
            
            # Migration colonnes
            self._migrate_columns(conn)
    
    def _migrate_columns(self, conn):
        """Ajoute les nouvelles colonnes si necessaire."""
        # Migration intel
        existing = self._get_existing_columns(conn, 'intel')
        new_columns = {
            'content_text': 'TEXT DEFAULT ""',
            'content_hash': 'TEXT DEFAULT ""',
            'risk_score': 'INTEGER DEFAULT 0',
            'priority_score': 'INTEGER DEFAULT 50',
            'crawl_count': 'INTEGER DEFAULT 0',
            'intel_density': 'REAL DEFAULT 0',
            'threat_score': 'REAL DEFAULT 0',
            'sentiment_score': 'REAL DEFAULT 0',
            'site_type': 'TEXT DEFAULT ""',
            'marked_important': 'INTEGER DEFAULT 0',
            'marked_false_positive': 'INTEGER DEFAULT 0',
            'encrypted': 'INTEGER DEFAULT 0'
        }
        for col, col_type in new_columns.items():
            if col not in existing:
                try:
                    conn.execute(f'ALTER TABLE intel ADD COLUMN {col} {col_type}')
                    Log.info(f"Added column {col} to intel table")
                except Exception as e:
                    Log.debug(f"Column {col} migration: {e}")
        
        # Migration entities (si la table existe)
        try:
            existing_entities = self._get_existing_columns(conn, 'entities')
            entity_columns = {
                'subtype': 'TEXT DEFAULT ""',
                'confidence': 'REAL DEFAULT 0.5',
                'validated': 'INTEGER DEFAULT 0',
                'enriched': 'INTEGER DEFAULT 0',
                'risk_score': 'REAL DEFAULT 0',
                'enrichment_data': 'TEXT DEFAULT "{}"',
                'occurrence_count': 'INTEGER DEFAULT 1'
            }
            for col, col_type in entity_columns.items():
                if col not in existing_entities:
                    try:
                        conn.execute(f'ALTER TABLE entities ADD COLUMN {col} {col_type}')
                    except:
                        pass
        except:
            pass  # Table entities n'existe pas encore

    def _get_existing_columns(self, conn, table: str) -> Set[str]:
        """Retourne les colonnes existantes."""
        cursor = conn.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in cursor.fetchall()}
    
    def save(self, data: Dict[str, Any]):
        """Sauvegarde les donnees d'une page crawlee."""
        domain = urlparse(data['url']).netloc
        risk_score = self._calculate_risk_score(data)
        intel_density = self._calculate_intel_density(data)
        
        # Chiffrer les donnees sensibles si active
        if ENCRYPTION_AVAILABLE and EncryptionConfig.ENCRYPTION_ENABLED:
            data = self._encrypt_sensitive(data)
            encrypted = 1
        else:
            encrypted = 0
        
        with self._lock:
            with self._get_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO intel 
                    (url, domain, title, status, depth, tech_stack, secrets_found, 
                     ip_leaks, emails, comments, cryptos, socials, json_data, 
                     content_length, content_text, language, category, site_type,
                     risk_score, threat_score, intel_density, sentiment_score, 
                     encrypted, crawl_count, last_crawl)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?,
                            COALESCE((SELECT crawl_count FROM intel WHERE url = ?) + 1, 1),
                            CURRENT_TIMESTAMP)
                ''', (
                    data['url'], domain, data.get('title', ''), data.get('status', 0),
                    data.get('depth', 0), json.dumps(data.get('tech_stack', [])),
                    json.dumps(data.get('secrets', {})), json.dumps(data.get('ip_leaks', [])),
                    json.dumps(data.get('emails', [])), json.dumps(data.get('comments', [])),
                    json.dumps(data.get('cryptos', {})), json.dumps(data.get('socials', {})),
                    json.dumps(data.get('json_data', [])), data.get('content_length', 0),
                    data.get('content_text', '')[:5000], data.get('language', ''),
                    data.get('category', ''), data.get('site_type', ''),
                    risk_score, data.get('threat_score', 0), intel_density,
                    data.get('sentiment_score', 0), encrypted, data['url']
                ))
                
                # Mettre a jour stats domaine
                self._update_domain_stats(conn, domain, data)
                
                # Extraire et sauvegarder entites OSINT
                self._extract_entities_advanced(conn, data, domain)
                
                # Creer alertes si necessaire
                if risk_score >= 70:
                    self._create_alert(conn, 'high_risk', 
                        f"Site a haut risque: {domain} (score: {risk_score})", 
                        data['url'], domain, 'danger', {'risk_score': risk_score})
                
                secrets = data.get('secrets', {})
                if secrets:
                    for secret_type in secrets.keys():
                        self._create_alert(conn, 'secret_found',
                            f"{secret_type} trouve sur {domain}",
                            data['url'], domain, 'warning', {'type': secret_type})
    
    def _calculate_risk_score(self, data: Dict) -> int:
        """Calcule un score de risque (0-100)."""
        score = 0
        
        secrets = data.get('secrets', {})
        if secrets:
            score += min(len(secrets) * 10, 30)
        
        cryptos = data.get('cryptos', {})
        if cryptos:
            score += min(sum(len(v) for v in cryptos.values()) * 2, 20)
        
        emails = data.get('emails', [])
        if emails:
            score += min(len(emails), 10)
        
        if data.get('ip_leaks'):
            score += 20
        
        title = data.get('title', '').lower()
        suspicious = ['market', 'shop', 'buy', 'sell', 'drug', 'weapon', 
                     'hack', 'leak', 'dump', 'card', 'fraud', 'exploit',
                     'ransomware', 'creds', 'password', 'login', 'account']
        for word in suspicious:
            if word in title:
                score += 5
        
        return min(score, 100)
    
    def _calculate_intel_density(self, data: Dict) -> float:
        """Calcule la densite d'intel (intel/ko)."""
        content_len = max(data.get('content_length', 1), 1)
        intel_count = (
            len(data.get('secrets', {})) +
            len(data.get('cryptos', {})) +
            len(data.get('emails', [])) +
            len(data.get('socials', {}))
        )
        return round(intel_count / (content_len / 1024), 4)
    
    def _update_domain_stats(self, conn, domain: str, data: Dict):
        """Met a jour les statistiques du domaine."""
        has_intel = bool(data.get('secrets') or data.get('cryptos') or data.get('emails'))
        
        conn.execute('''
            INSERT INTO domains (domain, total_pages, success_pages, intel_count, last_intel_at, updated_at)
            VALUES (?, 1, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(domain) DO UPDATE SET
                total_pages = total_pages + 1,
                success_pages = success_pages + ?,
                intel_count = intel_count + ?,
                last_intel_at = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE last_intel_at END,
                updated_at = CURRENT_TIMESTAMP
        ''', (domain, 
              1 if data.get('status') == 200 else 0,
              1 if has_intel else 0,
              datetime.now() if has_intel else None,
              1 if data.get('status') == 200 else 0,
              1 if has_intel else 0,
              has_intel))
    
    def _extract_entities_advanced(self, conn, data: Dict, domain: str):
        """Extrait et sauvegarde les entites OSINT avec enrichissement."""
        url = data['url']
        entity_ids = []
        
        # Emails
        for email in data.get('emails', [])[:50]:
            eid = self._save_entity_advanced(conn, 'email', '', email, url, domain, 0.9)
            if eid:
                entity_ids.append(eid)
        
        # Crypto
        for coin, addresses in data.get('cryptos', {}).items():
            for addr in addresses[:20]:
                eid = self._save_entity_advanced(conn, 'crypto', coin, addr, url, domain, 0.85)
                if eid:
                    entity_ids.append(eid)
        
        # Socials
        for network, handles in data.get('socials', {}).items():
            for handle in handles[:10]:
                eid = self._save_entity_advanced(conn, 'social', network, handle, url, domain, 0.80)
                if eid:
                    entity_ids.append(eid)
        
        # Creer les liens de co-occurrence
        for i, source_id in enumerate(entity_ids):
            for target_id in entity_ids[i+1:]:
                self._save_entity_edge(conn, source_id, target_id, 'co-occurrence', url)
    
    def _save_entity_advanced(self, conn, entity_type: str, subtype: str, value: str, 
                              url: str, domain: str, confidence: float = 0.5,
                              metadata: Dict = None) -> Optional[int]:
        """Sauvegarde une entite avec metadonnees."""
        try:
            cursor = conn.execute('''
                INSERT INTO entities (entity_type, subtype, value, normalized_value, 
                                     source_url, source_domain, confidence, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_type, value) DO UPDATE SET
                    last_seen = CURRENT_TIMESTAMP,
                    occurrence_count = occurrence_count + 1
                RETURNING id
            ''', (entity_type, subtype, value, value.lower(), url, domain, 
                  confidence, json.dumps(metadata or {})))
            row = cursor.fetchone()
            return row[0] if row else None
        except Exception as e:
            # Fallback pour SQLite < 3.35
            try:
                conn.execute('''
                    INSERT OR REPLACE INTO entities 
                    (entity_type, subtype, value, normalized_value, source_url, source_domain, confidence, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (entity_type, subtype, value, value.lower(), url, domain,
                      confidence, json.dumps(metadata or {})))
                cursor = conn.execute(
                    "SELECT id FROM entities WHERE entity_type = ? AND value = ?",
                    (entity_type, value)
                )
                row = cursor.fetchone()
                return row[0] if row else None
            except:
                return None
    
    def _save_entity_edge(self, conn, source_id: int, target_id: int, 
                          relationship: str, evidence: str):
        """Sauvegarde un lien entre entites."""
        if not source_id or not target_id:
            return
        
        # Ordre consistant
        if source_id > target_id:
            source_id, target_id = target_id, source_id
        
        try:
            conn.execute('''
                INSERT INTO entity_graph (source_entity_id, target_entity_id, relationship, evidence)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(source_entity_id, target_entity_id) DO UPDATE SET
                    last_seen = CURRENT_TIMESTAMP,
                    occurrence_count = occurrence_count + 1,
                    weight = weight + 0.1
            ''', (source_id, target_id, relationship, json.dumps([evidence])))
        except:
            pass
    
    def _create_alert(self, conn, alert_type: str, message: str, url: str, 
                      domain: str, severity: str, data: Dict = None):
        """Cree une nouvelle alerte."""
        alert_id = f"ALT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{hash(url) % 10000:04d}"
        conn.execute('''
            INSERT INTO alerts (alert_id, type, title, message, url, domain, severity, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (alert_id, alert_type, message[:100], message, url, domain, 
              severity, json.dumps(data or {})))
    
    # ========== GRAPHE D'ENTITES ==========
    
    def get_entity_graph(self, entity_id: int = None, limit: int = 100) -> Dict:
        """Recupere le graphe d'entites."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            
            # Noeuds
            if entity_id:
                cursor = conn.execute("""
                    SELECT e.* FROM entities e
                    JOIN entity_graph g ON e.id = g.source_entity_id OR e.id = g.target_entity_id
                    WHERE g.source_entity_id = ? OR g.target_entity_id = ?
                    LIMIT ?
                """, (entity_id, entity_id, limit))
            else:
                cursor = conn.execute("""
                    SELECT * FROM entities ORDER BY occurrence_count DESC LIMIT ?
                """, (limit,))
            
            nodes = [dict(row) for row in cursor.fetchall()]
            node_ids = {n['id'] for n in nodes}
            
            # Edges
            if node_ids:
                placeholders = ','.join('?' * len(node_ids))
                cursor = conn.execute(f"""
                    SELECT * FROM entity_graph 
                    WHERE source_entity_id IN ({placeholders}) 
                       OR target_entity_id IN ({placeholders})
                """, list(node_ids) + list(node_ids))
                edges = [dict(row) for row in cursor.fetchall()]
            else:
                edges = []
            
            return {
                'nodes': nodes,
                'edges': edges,
                'stats': {
                    'total_nodes': len(nodes),
                    'total_edges': len(edges)
                }
            }
    
    def get_cross_domain_entities(self, min_domains: int = 2, limit: int = 100) -> List[Dict]:
        """Recupere les entites presentes sur plusieurs domaines."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT entity_type, value, COUNT(DISTINCT source_domain) as domain_count,
                       GROUP_CONCAT(DISTINCT source_domain) as domains,
                       SUM(occurrence_count) as total_occurrences,
                       MAX(risk_score) as max_risk
                FROM entities
                GROUP BY entity_type, value
                HAVING domain_count >= ?
                ORDER BY domain_count DESC, total_occurrences DESC
                LIMIT ?
            """, (min_domains, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def save_correlation(self, entity1_id: int, entity2_id: int, score: float,
                        confidence: float, relationship: str, evidence: List[str],
                        interpretation: str = ""):
        """Sauvegarde une correlation."""
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO correlations 
                (entity1_id, entity2_id, correlation_score, confidence, 
                 relationship_type, evidence, interpretation)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (entity1_id, entity2_id, score, confidence, relationship,
                  json.dumps(evidence), interpretation))
    
    def get_high_correlations(self, min_score: float = 0.7, limit: int = 50) -> List[Dict]:
        """Recupere les correlations elevees."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT c.*, 
                       e1.entity_type as entity1_type, e1.value as entity1_value,
                       e2.entity_type as entity2_type, e2.value as entity2_value
                FROM correlations c
                JOIN entities e1 ON c.entity1_id = e1.id
                JOIN entities e2 ON c.entity2_id = e2.id
                WHERE c.correlation_score >= ?
                ORDER BY c.correlation_score DESC
                LIMIT ?
            """, (min_score, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    # ========== AUDIT ==========
    
    def log_audit(self, event_type: str, user_id: str, ip: str, user_agent: str,
                  action: str = None, query: str = None, details: Dict = None,
                  response_time_ms: int = 0, status: str = 'success', signature: str = ''):
        """Enregistre un log d'audit."""
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO audit_log 
                (timestamp, event_type, user_id, ip_address, user_agent, action, 
                 query, details, response_time_ms, status, signature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (datetime.utcnow().isoformat(), event_type, user_id, ip, user_agent,
                  action, query, json.dumps(details or {}), response_time_ms, 
                  status, signature))
    
    def get_audit_logs(self, user: str = None, event_type: str = None,
                       days: int = None, limit: int = 100) -> List[Dict]:
        """Recupere les logs d'audit."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            
            where = []
            params = []
            
            if user:
                where.append("user_id = ?")
                params.append(user)
            if event_type:
                where.append("event_type = ?")
                params.append(event_type)
            if days:
                where.append("timestamp >= datetime('now', ?)")
                params.append(f'-{days} days')
            
            sql = "SELECT * FROM audit_log"
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
    
    # ========== RECHERCHE FULL-TEXT ==========
    
    def search_fulltext(self, query: str, filters: Dict = None, limit: int = 100, offset: int = 0) -> Tuple[List[Dict], int]:
        """Recherche full-text avec filtres."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            
            where_clauses = ["status = 200"]
            params = []
            
            if query:
                where_clauses.append("(title LIKE ? OR domain LIKE ? OR url LIKE ? OR content_text LIKE ?}")
                search_pattern = f"%{query}%"
                params.extend([search_pattern] * 4)
            
            if filters:
                if filters.get('time_range'):
                    time_map = {
                        'hour': '-1 hour', 'day': '-1 day', 
                        'week': '-7 days', 'month': '-30 days'
                    }
                    if filters['time_range'] in time_map:
                        where_clauses.append(f"found_at >= datetime('now', ?)")
                        params.append(time_map[filters['time_range']])
                
                if filters.get('intel_type'):
                    type_map = {
                        'crypto': "cryptos != '{}'",
                        'email': "emails != '[]'",
                        'social': "socials != '{}'",
                        'secret': "secrets_found != '{}'",
                        'ip_leak': "ip_leaks != '[]'"
                    }
                    if filters['intel_type'] in type_map:
                        where_clauses.append(type_map[filters['intel_type']])
                
                if filters.get('min_risk'):
                    where_clauses.append("risk_score >= ?")
                    params.append(filters['min_risk'])
                
                if filters.get('category'):
                    where_clauses.append("category = ?")
                    params.append(filters['category'])
                
                if filters.get('domain'):
                    where_clauses.append("domain LIKE ?")
                    params.append(f"%{filters['domain']}%")
                
                if filters.get('exclude_false_positive'):
                    where_clauses.append("marked_false_positive = 0")
                
                if filters.get('important_only'):
                    where_clauses.append("marked_important = 1")
            
            where_sql = " AND ".join(where_clauses)
            
            # Compter total
            count_sql = f"SELECT COUNT(*) FROM intel WHERE {where_sql}"
            cursor = conn.execute(count_sql, params)
            total = cursor.fetchone()[0]
            
            # Recuperer resultats
            sql = f"""
                SELECT * FROM intel WHERE {where_sql}
                ORDER BY risk_score DESC, found_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            cursor = conn.execute(sql, params)
            
            results = []
            json_fields = ['tech_stack', 'secrets_found', 'ip_leaks', 'emails', 
                          'comments', 'cryptos', 'socials', 'tags']
            
            for row in cursor.fetchall():
                data = dict(row)
                for field in json_fields:
                    try:
                        data[field] = json.loads(data[field]) if data.get(field) else []
                    except:
                        data[field] = []
                
                # Dechiffrer si necessaire
                if data.get('encrypted') and ENCRYPTION_AVAILABLE:
                    data = self._decrypt_sensitive(data)
                
                results.append(data)
            
            return results, total
    
    def get_intel_item(self, url: str) -> Optional[Dict]:
        """Recupere les details complets d'un item intel."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM intel WHERE url = ?", (url,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            data = dict(row)
            json_fields = ['tech_stack', 'secrets_found', 'ip_leaks', 'emails', 
                          'comments', 'cryptos', 'socials', 'tags', 'json_data']
            for field in json_fields:
                try:
                    data[field] = json.loads(data[field]) if data.get(field) else []
                except:
                    data[field] = []
            
            # Dechiffrer si necessaire
            if data.get('encrypted') and ENCRYPTION_AVAILABLE:
                data = self._decrypt_sensitive(data)
            
            cursor = conn.execute("""
                SELECT entity_type, value, first_seen, confidence, enriched FROM entities 
                WHERE source_url = ? ORDER BY entity_type
            """, (url,))
            data['entities'] = [dict(r) for r in cursor.fetchall()]
            
            return data
    
    def mark_intel(self, url: str, mark_type: str, value: bool = True):
        """Marque un item intel."""
        column = 'marked_important' if mark_type == 'important' else 'marked_false_positive'
        with self._get_connection() as conn:
            conn.execute(f"UPDATE intel SET {column} = ? WHERE url = ?", (1 if value else 0, url))
    
    # ========== GESTION PRIORITE ET QUEUE ==========
    
    def get_queue_advanced(self, limit: int = 100, sort_by: str = 'priority') -> List[Dict]:
        """Recupere la queue avec priorite calculee."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            
            order_map = {
                'priority': 'priority_score DESC, depth ASC',
                'depth': 'depth ASC, priority_score DESC',
                'recent': 'found_at DESC',
                'risk': 'risk_score DESC'
            }
            order = order_map.get(sort_by, order_map['priority'])
            
            cursor = conn.execute(f"""
                SELECT i.url, i.domain, i.depth, i.priority_score, i.risk_score,
                       i.found_at, d.status as domain_status, d.priority_boost
                FROM intel i
                LEFT JOIN domains d ON i.domain = d.domain
                WHERE i.status = 0
                ORDER BY {order}
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def update_priority(self, url: str, priority: int):
        """Met a jour la priorite d'une URL."""
        with self._get_connection() as conn:
            conn.execute("UPDATE intel SET priority_score = ? WHERE url = ?", (priority, url))
    
    def boost_domain(self, domain: str, boost: int):
        """Booste la priorite d'un domaine."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE domains SET priority_boost = ? WHERE domain = ?
            """, (boost, domain))
            conn.execute("""
                UPDATE intel SET priority_score = priority_score + ? WHERE domain = ?
            """, (boost, domain))
    
    def freeze_domain(self, domain: str, freeze: bool = True):
        """Gele/degele un domaine."""
        status = 'frozen' if freeze else 'normal'
        with self._get_connection() as conn:
            conn.execute("UPDATE domains SET status = ? WHERE domain = ?", (status, domain))
    
    def get_priority_rules(self) -> List[Dict]:
        """Recupere les regles de priorite."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM priority_rules ORDER BY id")
            return [dict(row) for row in cursor.fetchall()]
    
    def add_priority_rule(self, name: str, condition_type: str, condition_value: str, modifier: int):
        """Ajoute une regle de priorite."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO priority_rules (name, condition_type, condition_value, priority_modifier)
                VALUES (?, ?, ?, ?)
            """, (name, condition_type, condition_value, modifier))
    
    # ========== GESTION DOMAINES ==========
    
    def get_domain_profile(self, domain: str) -> Optional[Dict]:
        """Recupere le profil complet d'un domaine."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM domains WHERE domain = ?", (domain,))
            row = cursor.fetchone()
            if not row:
                return None
            
            data = dict(row)
            
            # Stats supplementaires
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_urls,
                    SUM(CASE WHEN status = 200 THEN 1 ELSE 0 END) as success_urls,
                    AVG(risk_score) as avg_risk,
                    MAX(risk_score) as max_risk,
                    SUM(CASE WHEN secrets_found != '{}' THEN 1 ELSE 0 END) as with_secrets
                FROM intel WHERE domain = ?
            """, (domain,))
            stats = cursor.fetchone()
            data.update(dict(stats))
            
            return data
    
    def update_domain_profile(self, domain: str, profile: Dict):
        """Met a jour le profil d'un domaine."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO domains (domain, status, trust_level, crawl_profile, max_depth, 
                                    delay_ms, max_pages, priority_boost, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(domain) DO UPDATE SET
                    status = ?, trust_level = ?, crawl_profile = ?, max_depth = ?,
                    delay_ms = ?, max_pages = ?, priority_boost = ?, notes = ?,
                    updated_at = CURRENT_TIMESTAMP
            """, (domain, profile.get('status', 'normal'), profile.get('trust_level', 'unknown'),
                  profile.get('crawl_profile', 'default'), profile.get('max_depth', 5),
                  profile.get('delay_ms', 1000), profile.get('max_pages', 100),
                  profile.get('priority_boost', 0), profile.get('notes', ''),
                  profile.get('status', 'normal'), profile.get('trust_level', 'unknown'),
                  profile.get('crawl_profile', 'default'), profile.get('max_depth', 5),
                  profile.get('delay_ms', 1000), profile.get('max_pages', 100),
                  profile.get('priority_boost', 0), profile.get('notes', '')))
    
    def get_domains_list(self, status: str = None, limit: int = 100) ? List[Dict]:
        """Liste les domaines avec leurs stats."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            
            sql = "SELECT * FROM domains"
            params = []
            if status:
                sql += " WHERE status = ?"
                params.append(status)
            sql += " ORDER BY total_pages DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
    
    # ========== MONITORING ET STATS ==========
    
    def record_hourly_stats(self, stats: Dict):
        """Enregistre les stats horaires."""
        hour = datetime.now().strftime('%Y-%m-%d %H:00')
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO hourly_stats (hour, urls_crawled, success_count, error_count, 
                                         new_domains, intel_found, queue_size)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(hour) DO UPDATE SET
                    urls_crawled = urls_crawled + ?,
                    success_count = success_count + ?,
                    error_count = error_count + ?,
                    new_domains = new_domains + ?,
                    intel_found = intel_found + ?,
                    queue_size = ?
            """, (hour, stats.get('crawled', 0), stats.get('success', 0), 
                  stats.get('errors', 0), stats.get('new_domains', 0),
                  stats.get('intel', 0), stats.get('queue', 0),
                  stats.get('crawled', 0), stats.get('success', 0),
                  stats.get('errors', 0), stats.get('new_domains', 0),
                  stats.get('intel', 0), stats.get('queue', 0)))
    
    def get_hourly_stats(self, hours: int = 24) -> List[Dict]:
        """Recupere les stats horaires."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM hourly_stats 
                WHERE hour >= datetime('now', ?)
                ORDER BY hour DESC
            """, (f'-{hours} hours',))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_error_stats(self) -> Dict:
        """Statistiques des erreurs."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count FROM intel 
                WHERE status != 200 AND status != 0
                GROUP BY status ORDER BY count DESC
            """)
            errors = {row[0]: row[1] for row in cursor.fetchall()}
            
            cursor = conn.execute("""
                SELECT COUNT(*) FROM intel WHERE status >= 500
            """)
            server_errors = cursor.fetchone()[0]
            
            cursor = conn.execute("""
                SELECT COUNT(*) FROM intel WHERE status >= 400 AND status < 500
            """)
            client_errors = cursor.fetchone()[0]
            
            return {
                'by_code': errors,
                'server_errors': server_errors,
                'client_errors': client_errors,
                'total_errors': server_errors + client_errors
            }
    
    def get_entities(self, entity_type: str = None, limit: int = 100) ? List[Dict]:
        """Recupere les entites extraites."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            
            sql = "SELECT * FROM entities"
            params = []
            if entity_type:
                sql += " WHERE entity_type = ?"
                params.append(entity_type)
            sql += " ORDER BY occurrence_count DESC, last_seen DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_entity_stats(self) -> Dict:
        """Stats sur les entites."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT entity_type, COUNT(*) as count, 
                       SUM(occurrence_count) as total_occurrences
                FROM entities 
                GROUP BY entity_type ORDER BY count DESC
            """)
            return {row[0]: {'unique': row[1], 'total': row[2]} for row in cursor.fetchall()}
    
    # ========== ALERTES ==========
    
    def get_alerts(self, limit: int = 50, unread_only: bool = False, severity: str = None) ? List[Dict]:
        """Recupere les alertes."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            
            where = []
            params = []
            if unread_only:
                where.append("read = 0")
            if severity:
                where.append("severity = ?")
                params.append(severity)
            
            sql = "SELECT * FROM alerts"
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(sql, params)
            results = []
            for row in cursor.fetchall():
                data = dict(row)
                try:
                    data['metadata'] = json.loads(data.get('metadata', '{}'))
                    data['entities'] = json.loads(data.get('entities', '{}'))
                except:
                    pass
                results.append(data)
            return results
    
    def mark_alerts_read(self, alert_ids: List[int] = None):
        with self._get_connection() as conn:
            if alert_ids:
                placeholders = ','.join('?' * len(alert_ids))
                conn.execute(f"UPDATE alerts SET read = 1 WHERE id IN ({placeholders})", alert_ids)
            else:
                conn.execute("UPDATE alerts SET read = 1")
    
    def clear_alerts(self):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM alerts")
    
    def add_to_blacklist(self, domain: str, reason: str = ""):
        with self._get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO domain_lists (domain, list_type, reason)
                VALUES (?, 'blacklist', ?)
            ''', (domain, reason))
    
    def add_to_whitelist(self, domain: str, reason: str = ""):
        with self._get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO domain_lists (domain, list_type, reason)
                VALUES (?, 'whitelist', ?)
            ''', (domain, reason))
    
    def is_blacklisted(self, domain: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM domain_lists WHERE domain = ? AND list_type = 'blacklist'",
                (domain,)
            )
            return cursor.fetchone() is not None
    
    def get_domain_lists(self) -> Dict[str, List[Dict]]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM domain_lists ORDER BY added_at DESC")
            rows = [dict(row) for row in cursor.fetchall()]
            return {
                'blacklist': [r for r in rows if r['list_type'] == 'blacklist'],
                'whitelist': [r for r in rows if r['list_type'] == 'whitelist']
            }
    
    def remove_from_list(self, domain: str):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM domain_lists WHERE domain = ?", (domain,))
    
    def get_visited_urls(self) -> Set[str]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT url FROM intel")
            return {row[0] for row in cursor.fetchall()}
    
    def get_stats(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 200 THEN 1 ELSE 0 END) as success,
                    COUNT(DISTINCT domain) as domains,
                    SUM(CASE WHEN secrets_found != '{}' THEN 1 ELSE 0 END) as with_secrets,
                    SUM(CASE WHEN cryptos != '{}' THEN 1 ELSE 0 END) as with_crypto,
                    SUM(CASE WHEN emails != '[]' THEN 1 ELSE 0 END) as with_emails,
                    AVG(risk_score) as avg_risk,
                    MAX(risk_score) as max_risk,
                    SUM(content_length) as total_size
                FROM intel
            """)
            row = cursor.fetchone()
            
            try:
                cursor3 = conn.execute("SELECT COUNT(*) FROM alerts WHERE read = 0")
                unread_alerts = cursor3.fetchone()[0]
            except:
                unread_alerts = 0
            
            try:
                cursor4 = conn.execute("SELECT COUNT(*) FROM entities")
                total_entities = cursor4.fetchone()[0]
            except:
                total_entities = 0
            
            return {
                'total': row[0] or 0,
                'success': row[1] or 0,
                'domains': row[2] or 0,
                'with_secrets': row[3] or 0,
                'with_crypto': row[4] or 0,
                'with_emails': row[5] or 0,
                'avg_risk': round(row[6] or 0, 1),
                'max_risk': row[7] or 0,
                'total_size_mb': round((row[8] or 0) / 1024 / 1024, 2),
                'unread_alerts': unread_alerts,
                'total_entities': total_entities
            }
    
    def export_json(self, filepath: str, filters: Dict = None) -> int:
        results, _ = self.search_fulltext('', filters, limit=10000)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        return len(results)
    
    def export_csv(self, filepath: str, include_all: bool = False) -> int:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            
            if include_all:
                cursor = conn.execute("SELECT * FROM intel ORDER BY found_at DESC")
            else:
                cursor = conn.execute("""
                    SELECT * FROM intel 
                    WHERE status = 200 AND (secrets_found != '{}' OR cryptos != '{}' OR emails != '[]')
                    ORDER BY risk_score DESC
                """)
            
            rows = cursor.fetchall()
            if not rows:
                return 0
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['URL', 'Domain', 'Title', 'Status', 'Risk', 'Category',
                               'Emails', 'Crypto', 'Secrets', 'Found At'])
                
                for row in rows:
                    emails = json.loads(row['emails']) if row['emails'] else []
                    cryptos = json.loads(row['cryptos']) if row['cryptos'] else {}
                    secrets = json.loads(row['secrets_found']) if row['secrets_found'] else {}
                    
                    writer.writerow([
                        row['url'], row['domain'], (row['title'] or '')[:100],
                        row['status'], row['risk_score'] if 'risk_score' in row.keys() else 0,
                        row['category'] if 'category' in row.keys() else '',
                        '; '.join(emails[:5]),
                        '; '.join([f"{k}:{len(v)}" for k, v in cryptos.items()]),
                        '; '.join(secrets.keys()), row['found_at']
                    ])
            return len(rows)
    
    def export_emails(self, filepath: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT DISTINCT value FROM entities WHERE entity_type = 'email'")
            emails = [row[0] for row in cursor.fetchall()]
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# Emails - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                f.write(f"# Total: {len(emails)}\n\n")
                for email in sorted(emails):
                    f.write(f"{email}\n")
            return len(emails)
    
    def export_crypto(self, filepath: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT entity_type, value FROM entities 
                WHERE entity_type LIKE 'crypto_%'
            """)
            
            crypto_data = {}
            for row in cursor.fetchall():
                coin = row[0].replace('crypto_', '').upper()
                if coin not in crypto_data:
                    crypto_data[coin] = set()
                crypto_data[coin].add(row[1])
            
            total = 0
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# Crypto - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
                for coin, addrs in sorted(crypto_data.items()):
                    f.write(f"\n## {coin} ({len(addrs)})\n")
                    for addr in sorted(addrs):
                        f.write(f"{addr}\n")
                    total += len(addrs)
            return total
    
    def get_timeline_stats(self, days: int = 7) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT DATE(found_at) as date, COUNT(*) as total,
                       SUM(CASE WHEN status = 200 THEN 1 ELSE 0 END) as success,
                       COUNT(DISTINCT domain) as domains
                FROM intel WHERE found_at >= DATE('now', ?)
                GROUP BY DATE(found_at) ORDER BY date DESC
            """, (f'-{days} days',))
            return [{'date': r[0], 'total': r[1], 'success': r[2], 'domains': r[3]} for r in cursor.fetchall()]
    
    def get_pending_urls(self, limit: int = 1000) ? List[tuple]:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT url, depth FROM intel WHERE status = 0 OR status >= 400
                ORDER BY priority_score DESC, depth ASC LIMIT ?
            """, (limit,))
            return cursor.fetchall()
    
    def get_high_risk_sites(self, min_score: int = 50, limit: int = 50) ? List[Dict]:
        results, _ = self.search_fulltext('', {'min_risk': min_score}, limit)
        return results
    
    def get_successful_urls_for_recrawl(self, min_depth: int = 0) ? List[str]:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT url FROM intel WHERE status = 200 AND depth >= ?
                ORDER BY found_at DESC LIMIT 500
            """, (min_depth,))
            return [row[0] for row in cursor.fetchall()]
    
    def purge_old_data(self, days: int = 30, anonymize: bool = False):
        with self._get_connection() as conn:
            if anonymize:
                conn.execute("""
                    UPDATE intel SET 
                        emails = '[]', secrets_found = '{}', ip_leaks = '[]',
                        content_text = ''
                    WHERE found_at < datetime('now', ?)
                """, (f'-{days} days',))
            else:
                conn.execute("DELETE FROM intel WHERE found_at < datetime('now', ?)", (f'-{days} days',))
                conn.execute("DELETE FROM alerts WHERE created_at < datetime('now', ?)", (f'-{days} days',))
                conn.execute("DELETE FROM entities WHERE last_seen < datetime('now', ?)", (f'-{days} days',))
    
    def vacuum(self):
        with self._get_connection() as conn:
            conn.execute("VACUUM")
