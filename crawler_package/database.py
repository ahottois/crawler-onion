"""
Module de gestion de la base de donnees SQLite.
Fournit un acces thread-safe aux donnees crawlees.
"""

import sqlite3
import json
import threading
from typing import Dict, List, Set, Any
from contextlib import contextmanager
from urllib.parse import urlparse

from .logger import Log


class DatabaseManager:
    """Gestionnaire de base de donnees SQLite thread-safe."""
    
    def __init__(self, db_file: str):
        self.db_file = db_file
        self._lock = threading.Lock()
        self._init_db()
    
    @contextmanager
    def _get_connection(self):
        """Context manager pour connexion thread-safe."""
        with self._lock:
            conn = sqlite3.connect(self.db_file)
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()
    
    def _get_existing_columns(self, conn) -> Set[str]:
        """Retourne les colonnes existantes de la table intel."""
        cursor = conn.execute("PRAGMA table_info(intel)")
        return {row[1] for row in cursor.fetchall()}
    
    def _init_db(self):
        """Initialise le schema de la base de donnees avec migration automatique."""
        with self._get_connection() as conn:
            # Creer la table si elle n'existe pas
            conn.execute('''
                CREATE TABLE IF NOT EXISTS intel (
                    url TEXT PRIMARY KEY,
                    title TEXT,
                    status INTEGER,
                    depth INTEGER,
                    tech_stack TEXT,
                    secrets_found TEXT,
                    ip_leaks TEXT,
                    emails TEXT,
                    comments TEXT,
                    cryptos TEXT,
                    socials TEXT,
                    json_data TEXT,
                    found_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Migration: ajouter les nouvelles colonnes si elles n'existent pas
            existing_columns = self._get_existing_columns(conn)
            
            migrations = [
                ('domain', 'TEXT'),
                ('content_length', 'INTEGER DEFAULT 0'),
            ]
            
            for column_name, column_type in migrations:
                if column_name not in existing_columns:
                    try:
                        conn.execute(f'ALTER TABLE intel ADD COLUMN {column_name} {column_type}')
                        Log.info(f"Migration: colonne '{column_name}' ajoutee")
                    except sqlite3.OperationalError:
                        pass
            
            # Mettre a jour les domaines manquants
            conn.execute('''
                UPDATE intel 
                SET domain = SUBSTR(
                    SUBSTR(url, INSTR(url, '://') + 3),
                    1,
                    CASE 
                        WHEN INSTR(SUBSTR(url, INSTR(url, '://') + 3), '/') > 0 
                        THEN INSTR(SUBSTR(url, INSTR(url, '://') + 3), '/') - 1
                        ELSE LENGTH(SUBSTR(url, INSTR(url, '://') + 3))
                    END
                )
                WHERE domain IS NULL OR domain = ''
            ''')
            
            # Index pour accelerer les requetes
            try:
                conn.execute('CREATE INDEX IF NOT EXISTS idx_domain ON intel(domain)')
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute('CREATE INDEX IF NOT EXISTS idx_status ON intel(status)')
            except sqlite3.OperationalError:
                pass
    
    def save(self, data: Dict[str, Any]):
        """Sauvegarde les donnees d'une page crawlee."""
        parsed = urlparse(data['url'])
        domain = parsed.netloc
        
        with self._get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO intel 
                (url, domain, title, status, depth, tech_stack, secrets_found, 
                 ip_leaks, emails, comments, cryptos, socials, json_data, content_length)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                data.get('content_length', 0)
            ))
    
    def get_visited_urls(self) -> Set[str]:
        """Retourne l'ensemble des URLs deja visitees."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT url FROM intel")
            return {row[0] for row in cursor.fetchall()}
    
    def get_stats(self) -> Dict[str, int]:
        """Retourne les statistiques de la base."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 200 THEN 1 ELSE 0 END) as success,
                    COUNT(DISTINCT domain) as domains
                FROM intel
            """)
            row = cursor.fetchone()
            return {'total': row[0], 'success': row[1], 'domains': row[2]}
    
    def export_json(self, filepath: str) -> int:
        """Exporte les resultats interessants en JSON."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM intel WHERE status = 200")
            
            results = []
            json_fields = ['tech_stack', 'secrets_found', 'ip_leaks', 'emails', 
                          'comments', 'cryptos', 'socials', 'json_data']
            
            for row in cursor.fetchall():
                data = dict(row)
                for field in json_fields:
                    try:
                        data[field] = json.loads(data[field]) if data[field] else []
                    except (json.JSONDecodeError, TypeError):
                        data[field] = []
                
                has_intel = any([data['secrets_found'], data['ip_leaks'], data['emails'],
                                data['cryptos'], data['socials'], data['comments']])
                if has_intel:
                    results.append(data)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        return len(results)
    
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
