"""
Module de gestion de la base de donnees SQLite.
Stocke les resultats du crawling de maniere persistante.
"""

import sqlite3
import json
import csv
import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional
from urllib.parse import urlparse
from threading import Lock
import threading

from .logger import Log


class DatabaseManager:
    """Gestionnaire de base de donnees SQLite thread-safe."""
    
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
    
    def _init_db(self):
        """Initialise le schema de la base de donnees."""
        with self._get_connection() as conn:
            # Table principale
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
                    language TEXT DEFAULT '',
                    keywords TEXT DEFAULT '[]',
                    category TEXT DEFAULT '',
                    tags TEXT DEFAULT '[]',
                    risk_score INTEGER DEFAULT 0,
                    found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_crawl TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_domain ON intel(domain)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_status ON intel(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_risk ON intel(risk_score)')
            
            # Table pour les domaines blacklistes/whitelistes
            conn.execute('''
                CREATE TABLE IF NOT EXISTS domain_lists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT UNIQUE,
                    list_type TEXT,
                    reason TEXT DEFAULT '',
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Table pour les alertes
            conn.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT,
                    message TEXT,
                    url TEXT,
                    domain TEXT,
                    severity TEXT DEFAULT 'info',
                    read INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Migration: ajouter les colonnes manquantes
            existing = self._get_existing_columns(conn)
            new_columns = {
                'language': 'TEXT DEFAULT ""',
                'keywords': 'TEXT DEFAULT "[]"',
                'category': 'TEXT DEFAULT ""',
                'tags': 'TEXT DEFAULT "[]"',
                'risk_score': 'INTEGER DEFAULT 0',
                'last_crawl': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            }
            for col, col_type in new_columns.items():
                if col not in existing:
                    try:
                        conn.execute(f'ALTER TABLE intel ADD COLUMN {col} {col_type}')
                    except:
                        pass
    
    def _get_existing_columns(self, conn) -> Set[str]:
        """Retourne les colonnes existantes."""
        cursor = conn.execute("PRAGMA table_info(intel)")
        return {row[1] for row in cursor.fetchall()}
    
    def save(self, data: Dict[str, Any]):
        """Sauvegarde les donnees d'une page crawlee."""
        domain = urlparse(data['url']).netloc
        risk_score = self._calculate_risk_score(data)
        
        with self._lock:
            with self._get_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO intel 
                    (url, domain, title, status, depth, tech_stack, secrets_found, 
                     ip_leaks, emails, comments, cryptos, socials, json_data, 
                     content_length, risk_score, last_crawl)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    data['url'],
                    domain,
                    data.get('title', ''),
                    data.get('status', 0),
                    data.get('depth', 0),
                    json.dumps(data.get('tech_stack', [])),
                    json.dumps(data.get('secrets', {})),
                    json.dumps(data.get('ip_leaks', [])),
                    json.dumps(data.get('emails', [])),
                    json.dumps(data.get('comments', [])),
                    json.dumps(data.get('cryptos', {})),
                    json.dumps(data.get('socials', {})),
                    json.dumps(data.get('json_data', [])),
                    data.get('content_length', 0),
                    risk_score
                ))
                
                # Creer une alerte si risque eleve
                if risk_score >= 70:
                    self._create_alert(conn, 'high_risk', 
                        f"Site a haut risque detecte: {domain}", 
                        data['url'], domain, 'danger')
                elif data.get('secrets'):
                    self._create_alert(conn, 'secret_found',
                        f"Secret trouve sur {domain}",
                        data['url'], domain, 'warning')
    
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
                     'hack', 'leak', 'dump', 'card', 'fraud', 'exploit']
        for word in suspicious:
            if word in title:
                score += 5
        
        return min(score, 100)
    
    def _create_alert(self, conn, alert_type: str, message: str, url: str, domain: str, severity: str):
        """Cree une nouvelle alerte."""
        conn.execute('''
            INSERT INTO alerts (type, message, url, domain, severity)
            VALUES (?, ?, ?, ?, ?)
        ''', (alert_type, message, url, domain, severity))
    
    def get_visited_urls(self) -> Set[str]:
        """Retourne l'ensemble des URLs deja visitees."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT url FROM intel")
            return {row[0] for row in cursor.fetchall()}
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques completes."""
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
            
            # Top domaines
            cursor2 = conn.execute("""
                SELECT domain, COUNT(*) as pages, AVG(risk_score) as risk
                FROM intel WHERE status = 200
                GROUP BY domain ORDER BY pages DESC LIMIT 10
            """)
            top_domains = [{'domain': r[0], 'pages': r[1], 'risk': round(r[2] or 0, 1)} 
                          for r in cursor2.fetchall()]
            
            # Alertes non lues
            try:
                cursor3 = conn.execute("SELECT COUNT(*) FROM alerts WHERE read = 0")
                unread_alerts = cursor3.fetchone()[0]
            except:
                unread_alerts = 0
            
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
                'top_domains': top_domains,
                'unread_alerts': unread_alerts
            }
    
    def get_alerts(self, limit: int = 50, unread_only: bool = False) -> List[Dict]:
        """Recupere les alertes."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM alerts"
            if unread_only:
                query += " WHERE read = 0"
            query += " ORDER BY created_at DESC LIMIT ?"
            cursor = conn.execute(query, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def mark_alerts_read(self, alert_ids: List[int] = None):
        """Marque les alertes comme lues."""
        with self._get_connection() as conn:
            if alert_ids:
                placeholders = ','.join('?' * len(alert_ids))
                conn.execute(f"UPDATE alerts SET read = 1 WHERE id IN ({placeholders})", alert_ids)
            else:
                conn.execute("UPDATE alerts SET read = 1")
    
    def clear_alerts(self):
        """Supprime toutes les alertes."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM alerts")
    
    def add_to_blacklist(self, domain: str, reason: str = ""):
        """Ajoute un domaine a la blacklist."""
        with self._get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO domain_lists (domain, list_type, reason)
                VALUES (?, 'blacklist', ?)
            ''', (domain, reason))
    
    def add_to_whitelist(self, domain: str, reason: str = ""):
        """Ajoute un domaine a la whitelist."""
        with self._get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO domain_lists (domain, list_type, reason)
                VALUES (?, 'whitelist', ?)
            ''', (domain, reason))
    
    def is_blacklisted(self, domain: str) -> bool:
        """Verifie si un domaine est blackliste."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM domain_lists WHERE domain = ? AND list_type = 'blacklist'",
                (domain,)
            )
            return cursor.fetchone() is not None
    
    def get_domain_lists(self) -> Dict[str, List[Dict]]:
        """Recupere les listes de domaines."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM domain_lists ORDER BY added_at DESC")
            rows = [dict(row) for row in cursor.fetchall()]
            return {
                'blacklist': [r for r in rows if r['list_type'] == 'blacklist'],
                'whitelist': [r for r in rows if r['list_type'] == 'whitelist']
            }
    
    def remove_from_list(self, domain: str):
        """Retire un domaine des listes."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM domain_lists WHERE domain = ?", (domain,))
    
    def export_json(self, filepath: str, filters: Dict = None) -> int:
        """Exporte les resultats en JSON."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM intel WHERE status = 200"
            params = []
            
            if filters:
                if filters.get('domain'):
                    query += " AND domain LIKE ?"
                    params.append(f"%{filters['domain']}%")
                if filters.get('min_risk'):
                    query += " AND risk_score >= ?"
                    params.append(filters['min_risk'])
                if filters.get('has_crypto'):
                    query += " AND cryptos != '{}'"
                if filters.get('has_secrets'):
                    query += " AND secrets_found != '{}'"
            
            cursor = conn.execute(query, params)
            
            results = []
            json_fields = ['tech_stack', 'secrets_found', 'ip_leaks', 'emails', 
                          'comments', 'cryptos', 'socials', 'json_data']
            
            for row in cursor.fetchall():
                data = dict(row)
                for field in json_fields:
                    try:
                        data[field] = json.loads(data[field]) if data.get(field) else []
                    except:
                        data[field] = []
                
                has_intel = any([data['secrets_found'], data['ip_leaks'], data['emails'],
                                data['cryptos'], data['socials']])
                if has_intel or not filters:
                    results.append(data)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        return len(results)
    
    def export_csv(self, filepath: str, include_all: bool = False) -> int:
        """Exporte les resultats en CSV."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            
            if include_all:
                cursor = conn.execute("SELECT * FROM intel ORDER BY found_at DESC")
            else:
                cursor = conn.execute("""
                    SELECT * FROM intel 
                    WHERE status = 200 AND (
                        secrets_found != '{}' OR cryptos != '{}' OR 
                        socials != '{}' OR emails != '[]'
                    )
                    ORDER BY risk_score DESC
                """)
            
            rows = cursor.fetchall()
            if not rows:
                return 0
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['URL', 'Domain', 'Title', 'Status', 'Risk Score', 
                               'Emails', 'Crypto', 'Secrets', 'Socials', 'Found At'])
                
                for row in rows:
                    emails = json.loads(row['emails']) if row['emails'] else []
                    cryptos = json.loads(row['cryptos']) if row['cryptos'] else {}
                    secrets = json.loads(row['secrets_found']) if row['secrets_found'] else {}
                    socials = json.loads(row['socials']) if row['socials'] else {}
                    
                    writer.writerow([
                        row['url'],
                        row['domain'],
                        (row['title'] or '')[:100],
                        row['status'],
                        row['risk_score'] if 'risk_score' in row.keys() else 0,
                        '; '.join(emails[:5]),
                        '; '.join([f"{k}:{len(v)}" for k, v in cryptos.items()]),
                        '; '.join(secrets.keys()),
                        '; '.join(socials.keys()),
                        row['found_at']
                    ])
            
            return len(rows)
    
    def export_emails(self, filepath: str) -> int:
        """Exporte uniquement les emails."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT DISTINCT domain, emails FROM intel 
                WHERE emails != '[]' AND status = 200
            """)
            
            all_emails = set()
            domain_emails = {}
            
            for row in cursor.fetchall():
                domain = row[0]
                emails = json.loads(row[1]) if row[1] else []
                for email in emails:
                    all_emails.add(email)
                    if domain not in domain_emails:
                        domain_emails[domain] = set()
                    domain_emails[domain].add(email)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# Emails - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                f.write(f"# Total: {len(all_emails)} emails\n\n")
                
                for domain, emails in sorted(domain_emails.items()):
                    f.write(f"\n## {domain}\n")
                    for email in sorted(emails):
                        f.write(f"{email}\n")
            
            return len(all_emails)
    
    def export_crypto(self, filepath: str) -> int:
        """Exporte les adresses crypto."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT domain, cryptos FROM intel 
                WHERE cryptos != '{}' AND status = 200
            """)
            
            crypto_data = {}
            
            for row in cursor.fetchall():
                cryptos = json.loads(row[1]) if row[1] else {}
                for coin, addresses in cryptos.items():
                    if coin not in crypto_data:
                        crypto_data[coin] = set()
                    for addr in addresses:
                        crypto_data[coin].add(addr)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# Crypto Addresses - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
                
                total = 0
                for coin, addresses in sorted(crypto_data.items()):
                    if addresses:
                        f.write(f"\n## {coin} ({len(addresses)})\n")
                        for addr in sorted(addresses):
                            f.write(f"{addr}\n")
                        total += len(addresses)
            
            return total
    
    def get_high_risk_sites(self, min_score: int = 50, limit: int = 50) -> List[Dict]:
        """Recupere les sites a haut risque."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT url, domain, title, risk_score, cryptos, emails, secrets_found
                FROM intel WHERE status = 200 AND risk_score >= ?
                ORDER BY risk_score DESC LIMIT ?
            """, (min_score, limit))
            
            results = []
            for row in cursor.fetchall():
                data = dict(row)
                data['cryptos'] = json.loads(data['cryptos']) if data['cryptos'] else {}
                data['emails'] = json.loads(data['emails']) if data['emails'] else []
                data['secrets_found'] = json.loads(data['secrets_found']) if data['secrets_found'] else {}
                results.append(data)
            return results
    
    def get_timeline_stats(self, days: int = 7) -> List[Dict]:
        """Statistiques par jour."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    DATE(found_at) as date,
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 200 THEN 1 ELSE 0 END) as success,
                    COUNT(DISTINCT domain) as domains
                FROM intel
                WHERE found_at >= DATE('now', ?)
                GROUP BY DATE(found_at)
                ORDER BY date DESC
            """, (f'-{days} days',))
            
            return [{'date': r[0], 'total': r[1], 'success': r[2], 'domains': r[3]} 
                   for r in cursor.fetchall()]
    
    def get_pending_urls(self, limit: int = 1000) -> List[tuple]:
        """Retourne les URLs en attente."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT url, depth FROM intel 
                WHERE status = 0 OR status >= 400
                ORDER BY depth ASC, found_at DESC
                LIMIT ?
            """, (limit,))
            return cursor.fetchall()
    
    def get_successful_urls_for_recrawl(self, min_depth: int = 0) -> List[str]:
        """Retourne les URLs reussies pour extraire de nouveaux liens."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT url FROM intel 
                WHERE status = 200 AND depth >= ?
                ORDER BY found_at DESC
                LIMIT 500
            """, (min_depth,))
            return [row[0] for row in cursor.fetchall()]
