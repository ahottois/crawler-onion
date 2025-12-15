"""
Module du serveur web integre.
Dashboard pour visualiser et controler le crawler.
"""

import json
import sqlite3
import socket
import threading
import html
import os
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse, parse_qs

from .logger import Log
from .updater import Updater
from .daemon import DaemonManager


class CrawlerWebServer:
    """Serveur web leger pour visualiser les resultats du crawler."""
    
    def __init__(self, db_file: str, port: int, crawler_ref=None, config=None):
        self.db_file = db_file
        self.port = port
        self.crawler = crawler_ref
        self.config = config
        self.server = None
        self.thread = None
        self._running = False
        
        # Initialiser l'updater
        if config:
            self.updater = Updater(
                repo_owner=config.repo_owner,
                repo_name=config.repo_name,
                current_version=config.version
            )
        else:
            self.updater = Updater(
                repo_owner="ahottois",
                repo_name="crawler-onion",
                current_version="6.5.0"
            )
        
        # Initialiser le gestionnaire de daemon
        self.daemon = DaemonManager()
    
    def _get_db_connection(self):
        """Retourne une connexion a la base."""
        return sqlite3.connect(self.db_file)
    
    def _get_data(self) -> Dict[str, Any]:
        """Recupere les donnees pour le dashboard."""
        data = {
            'status': 'RUNNING' if self.crawler and self.crawler.running else 'STOPPED',
            'total_urls': 0, 'success_urls': 0, 'domains': 0,
            'queue_size': 0, 'intel_count': 0,
            'total_emails': 0, 'total_cryptos': 0, 'total_socials': 0,
            'avg_risk': 0, 'high_risk_count': 0,
            'recent_rows': [], 'intel_rows': [], 'domain_rows': []
        }
        
        try:
            conn = self._get_db_connection()
            conn.row_factory = sqlite3.Row
            
            # Stats globales
            cursor = conn.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN status = 200 THEN 1 ELSE 0 END) as success,
                       COUNT(DISTINCT domain) as domains,
                       SUM(CASE WHEN secrets_found != '{}' OR cryptos != '{}' OR emails != '[]' THEN 1 ELSE 0 END) as intel,
                       AVG(risk_score) as avg_risk,
                       SUM(CASE WHEN risk_score >= 50 THEN 1 ELSE 0 END) as high_risk
                FROM intel
            """)
            row = cursor.fetchone()
            if row:
                data['total_urls'] = row['total'] or 0
                data['success_urls'] = row['success'] or 0
                data['domains'] = row['domains'] or 0
                data['intel_count'] = row['intel'] or 0
                data['avg_risk'] = round(row['avg_risk'] or 0, 1)
                data['high_risk_count'] = row['high_risk'] or 0
            
            # Queue
            cursor = conn.execute("SELECT COUNT(*) FROM intel WHERE status = 0")
            data['queue_size'] = cursor.fetchone()[0] or 0
            
            # Compteurs speciaux
            cursor = conn.execute("SELECT emails, cryptos, socials FROM intel WHERE status = 200")
            for row in cursor.fetchall():
                try:
                    emails = json.loads(row[0]) if row[0] else []
                    cryptos = json.loads(row[1]) if row[1] else {}
                    socials = json.loads(row[2]) if row[2] else {}
                    data['total_emails'] += len(emails)
                    data['total_cryptos'] += sum(len(v) for v in cryptos.values())
                    data['total_socials'] += sum(len(v) for v in socials.values())
                except: pass
            
            # Recent URLs
            cursor = conn.execute("""
                SELECT url, title, status, risk_score FROM intel 
                ORDER BY last_crawl DESC LIMIT 15
            """)
            data['recent_rows'] = [dict(row) for row in cursor.fetchall()]
            
            # Intel rows
            cursor = conn.execute("""
                SELECT domain, title, secrets_found, cryptos, socials, emails, risk_score
                FROM intel 
                WHERE status = 200 AND (secrets_found != '{}' OR cryptos != '{}' OR emails != '[]')
                ORDER BY risk_score DESC LIMIT 10
            """)
            data['intel_rows'] = [dict(row) for row in cursor.fetchall()]
            
            # Top domains
            cursor = conn.execute("""
                SELECT domain, COUNT(*) as pages, 
                       SUM(CASE WHEN status = 200 THEN 1 ELSE 0 END) as success,
                       AVG(risk_score) as risk
                FROM intel GROUP BY domain 
                ORDER BY pages DESC LIMIT 10
            """)
            data['domain_rows'] = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
        except Exception as e:
            Log.error(f"Erreur lecture DB: {e}")
        
        return data
    
    def _search(self, query: str, filter_type: str = 'all') -> List[Dict]:
        """Recherche dans la base."""
        results = []
        try:
            conn = self._get_db_connection()
            conn.row_factory = sqlite3.Row
            
            sql = "SELECT * FROM intel WHERE status = 200"
            params = []
            
            if query:
                sql += " AND (title LIKE ? OR domain LIKE ? OR url LIKE ?)"
                params.extend([f'%{query}%'] * 3)
            
            if filter_type == 'crypto':
                sql += " AND cryptos != '{}'"
            elif filter_type == 'social':
                sql += " AND socials != '{}'"
            elif filter_type == 'email':
                sql += " AND emails != '[]'"
            elif filter_type == 'secret':
                sql += " AND secrets_found != '{}'"
            elif filter_type == 'high_risk':
                sql += " AND risk_score >= 50"
            
            sql += " ORDER BY risk_score DESC LIMIT 100"
            
            cursor = conn.execute(sql, params)
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
        except Exception as e:
            Log.error(f"Erreur recherche: {e}")
        
        return results
    
    def _get_trusted_sites(self) -> Dict[str, Any]:
        """Recupere les sites fiables."""
        data = {'sites': [], 'total': 0, 'high_trust': 0, 'medium_trust': 0, 'low_trust': 0}
        try:
            conn = self._get_db_connection()
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute("""
                SELECT domain, 
                       COUNT(*) as total_pages,
                       SUM(CASE WHEN status = 200 THEN 1 ELSE 0 END) as success_pages,
                       MAX(title) as title,
                       SUM(CASE WHEN secrets_found != '{}' OR cryptos != '{}' THEN 1 ELSE 0 END) as intel_pages,
                       AVG(risk_score) as avg_risk
                FROM intel 
                GROUP BY domain 
                HAVING total_pages >= 2
                ORDER BY success_pages DESC
                LIMIT 100
            """)
            
            for row in cursor.fetchall():
                success_rate = int((row['success_pages'] / row['total_pages']) * 100) if row['total_pages'] > 0 else 0
                score = min(100, row['success_pages'] * 2 + (10 if row['intel_pages'] > 0 else 0))
                trust_level = 'high' if score >= 70 else ('medium' if score >= 40 else 'low')
                
                site = {
                    'domain': row['domain'],
                    'title': row['title'] or '',
                    'total_pages': row['total_pages'],
                    'success_rate': success_rate,
                    'score': score,
                    'trust_level': trust_level,
                    'has_intel': row['intel_pages'] > 0,
                    'avg_risk': round(row['avg_risk'] or 0, 1)
                }
                data['sites'].append(site)
                
                if trust_level == 'high': data['high_trust'] += 1
                elif trust_level == 'medium': data['medium_trust'] += 1
                else: data['low_trust'] += 1
            
            data['total'] = len(data['sites'])
            conn.close()
        except Exception as e:
            Log.error(f"Erreur sites fiables: {e}")
        
        return data
    
    def _get_alerts(self, limit: int = 50) -> List[Dict]:
        """Recupere les alertes."""
        alerts = []
        try:
            conn = self._get_db_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM alerts ORDER BY created_at DESC LIMIT ?
            """, (limit,))
            alerts = [dict(row) for row in cursor.fetchall()]
            conn.close()
        except:
            pass
        return alerts
    
    def _get_domain_lists(self) -> Dict:
        """Recupere les listes de domaines."""
        lists = {'blacklist': [], 'whitelist': []}
        try:
            conn = self._get_db_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM domain_lists ORDER BY added_at DESC")
            for row in cursor.fetchall():
                d = dict(row)
                if d['list_type'] == 'blacklist':
                    lists['blacklist'].append(d)
                else:
                    lists['whitelist'].append(d)
            conn.close()
        except:
            pass
        return lists
    
    def _add_seeds(self, urls: List[str]) -> Dict:
        """Ajoute des URLs a la queue."""
        if not urls:
            return {'success': False, 'message': 'Aucune URL fournie'}
        
        added = 0
        try:
            conn = self._get_db_connection()
            for url in urls:
                url = url.strip()
                if url and '.onion' in url:
                    try:
                        conn.execute("""
                            INSERT OR IGNORE INTO intel (url, domain, status, depth)
                            VALUES (?, ?, 0, 0)
                        """, (url, urlparse(url).netloc))
                        added += 1
                    except: pass
            conn.commit()
            conn.close()
        except Exception as e:
            return {'success': False, 'message': str(e)}
        
        return {'success': True, 'message': f'{added} URLs ajoutees'}
    
    def _refresh_links(self) -> Dict:
        """Extrait de nouveaux liens des pages crawlees."""
        return {'success': True, 'message': 'Extraction en cours...'}
    
    def _get_update_status(self) -> Dict[str, Any]:
        """Recupere le statut des mises a jour."""
        return self.updater.get_update_status()
    
    def _perform_update(self) -> Dict[str, Any]:
        """Execute la mise a jour."""
        return self.updater.perform_update()
    
    def _get_daemon_status(self) -> Dict[str, Any]:
        """Recupere le statut du daemon."""
        return self.daemon.get_full_status()
    
    def _install_daemon(self, data: Dict) -> Dict[str, Any]:
        """Installe le daemon."""
        web_port = data.get('web_port', self.port)
        workers = data.get('workers', 15)
        return self.daemon.install(web_port=web_port, workers=workers)
    
    def _uninstall_daemon(self) -> Dict[str, Any]:
        """Desinstalle le daemon."""
        return self.daemon.uninstall()
    
    def _control_daemon(self, action: str) -> Dict[str, Any]:
        """Controle le daemon."""
        if action == 'start': return self.daemon.start()
        elif action == 'stop': return self.daemon.stop()
        elif action == 'restart': return self.daemon.restart()
        return {'success': False, 'message': 'Action inconnue'}
    
    def _get_daemon_logs(self, lines: int = 50) -> Dict[str, Any]:
        """Recupere les logs du daemon."""
        return self.daemon.get_logs(lines)
    
    def _export_data(self, export_type: str) -> Dict[str, Any]:
        """Exporte les donnees."""
        from .database import DatabaseManager
        db = DatabaseManager(self.db_file)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_dir = os.path.dirname(self.db_file) or '.'
        
        try:
            if export_type == 'json':
                filepath = os.path.join(export_dir, f'export_{timestamp}.json')
                count = db.export_json(filepath)
                return {'success': True, 'message': f'{count} resultats exportes', 'file': filepath}
            
            elif export_type == 'csv':
                filepath = os.path.join(export_dir, f'export_{timestamp}.csv')
                count = db.export_csv(filepath)
                return {'success': True, 'message': f'{count} resultats exportes', 'file': filepath}
            
            elif export_type == 'emails':
                filepath = os.path.join(export_dir, f'emails_{timestamp}.txt')
                count = db.export_emails(filepath)
                return {'success': True, 'message': f'{count} emails exportes', 'file': filepath}
            
            elif export_type == 'crypto':
                filepath = os.path.join(export_dir, f'crypto_{timestamp}.txt')
                count = db.export_crypto(filepath)
                return {'success': True, 'message': f'{count} adresses exportees', 'file': filepath}
            
            else:
                return {'success': False, 'message': 'Type export inconnu'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def _add_to_list(self, data: Dict) -> Dict:
        """Ajoute un domaine a une liste."""
        from .database import DatabaseManager
        db = DatabaseManager(self.db_file)
        
        domain = data.get('domain', '').strip()
        list_type = data.get('list_type', 'blacklist')
        reason = data.get('reason', '')
        
        if not domain:
            return {'success': False, 'message': 'Domaine requis'}
        
        try:
            if list_type == 'blacklist':
                db.add_to_blacklist(domain, reason)
            else:
                db.add_to_whitelist(domain, reason)
            return {'success': True, 'message': f'{domain} ajoute a la {list_type}'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def _remove_from_list(self, data: Dict) -> Dict:
        """Retire un domaine des listes."""
        from .database import DatabaseManager
        db = DatabaseManager(self.db_file)
        
        domain = data.get('domain', '').strip()
        if not domain:
            return {'success': False, 'message': 'Domaine requis'}
        
        try:
            db.remove_from_list(domain)
            return {'success': True, 'message': f'{domain} retire'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def _mark_alerts_read(self) -> Dict:
        """Marque les alertes comme lues."""
        from .database import DatabaseManager
        db = DatabaseManager(self.db_file)
        try:
            db.mark_alerts_read()
            return {'success': True, 'message': 'Alertes marquees comme lues'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def _clear_alerts(self) -> Dict:
        """Supprime les alertes."""
        from .database import DatabaseManager
        db = DatabaseManager(self.db_file)
        try:
            db.clear_alerts()
            return {'success': True, 'message': 'Alertes supprimees'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def _get_stats_advanced(self) -> Dict:
        """Statistiques avancees."""
        from .database import DatabaseManager
        db = DatabaseManager(self.db_file)
        stats = db.get_stats()
        stats['timeline'] = db.get_timeline_stats(7)
        stats['high_risk'] = db.get_high_risk_sites(50, 20)
        return stats
    
    def _create_handler(self):
        """Cree le handler HTTP."""
        server_instance = self
        
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args): pass
            
            def do_GET(self):
                parsed = urlparse(self.path)
                path = parsed.path
                params = parse_qs(parsed.query)
                
                if path == '/' or path == '/index.html':
                    self._send_html(server_instance._render_dashboard())
                elif path == '/search':
                    query = params.get('q', [''])[0]
                    filter_type = params.get('filter', ['all'])[0]
                    self._send_html(server_instance._render_search(query, filter_type))
                elif path == '/trusted':
                    self._send_html(server_instance._render_trusted())
                elif path == '/updates':
                    self._send_html(server_instance._render_updates())
                elif path == '/alerts':
                    self._send_html(server_instance._render_alerts())
                elif path == '/export':
                    self._send_html(server_instance._render_export())
                elif path == '/settings':
                    self._send_html(server_instance._render_settings())
                elif path == '/api/stats':
                    self._send_json(server_instance._get_data())
                elif path == '/api/stats-advanced':
                    self._send_json(server_instance._get_stats_advanced())
                elif path == '/api/update-status':
                    self._send_json(server_instance._get_update_status())
                elif path == '/api/daemon-status':
                    self._send_json(server_instance._get_daemon_status())
                elif path == '/api/daemon-logs':
                    lines = int(params.get('lines', ['50'])[0])
                    self._send_json(server_instance._get_daemon_logs(lines))
                elif path == '/api/alerts':
                    self._send_json({'alerts': server_instance._get_alerts()})
                elif path == '/api/domain-lists':
                    self._send_json(server_instance._get_domain_lists())
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def do_POST(self):
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else '{}'
                try: data = json.loads(body) if body else {}
                except: data = {}
                
                if self.path == '/api/add-seeds':
                    result = server_instance._add_seeds(data.get('urls', []))
                elif self.path == '/api/refresh-links':
                    result = server_instance._refresh_links()
                elif self.path == '/api/perform-update':
                    result = server_instance._perform_update()
                elif self.path == '/api/check-updates':
                    result = server_instance._get_update_status()
                elif self.path == '/api/daemon-install':
                    result = server_instance._install_daemon(data)
                elif self.path == '/api/daemon-uninstall':
                    result = server_instance._uninstall_daemon()
                elif self.path == '/api/daemon-control':
                    result = server_instance._control_daemon(data.get('action', ''))
                elif self.path == '/api/export':
                    result = server_instance._export_data(data.get('type', 'json'))
                elif self.path == '/api/add-to-list':
                    result = server_instance._add_to_list(data)
                elif self.path == '/api/remove-from-list':
                    result = server_instance._remove_from_list(data)
                elif self.path == '/api/mark-alerts-read':
                    result = server_instance._mark_alerts_read()
                elif self.path == '/api/clear-alerts':
                    result = server_instance._clear_alerts()
                else:
                    self.send_response(404)
                    self.end_headers()
                    return
                
                self._send_json(result)
            
            def _send_html(self, content: str):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
            
            def _send_json(self, data: dict):
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(data, default=str).encode('utf-8'))
        
        return Handler
    
    def start(self):
        """Demarre le serveur web."""
        if self._running: return
        try:
            self.server = HTTPServer(('0.0.0.0', self.port), self._create_handler())
            self.server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._running = True
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            Log.success(f"Serveur web demarre sur http://0.0.0.0:{self.port}")
        except Exception as e:
            Log.error(f"Impossible de demarrer le serveur web: {e}")
    
    def stop(self):
        """Arrete le serveur web."""
        if self.server and self._running:
            self.server.shutdown()
            self._running = False
            Log.info("Serveur web arrete")
    
    def _render_dashboard(self) -> str:
        from .web_templates import render_dashboard
        update_status = self._get_update_status()
        return render_dashboard(self._get_data(), self.port, update_status)
    
    def _render_search(self, query: str = '', filter_type: str = 'all') -> str:
        from .web_templates import render_search
        results = self._search(query, filter_type) if query or filter_type != 'all' else []
        return render_search(results, query, filter_type, self.port)
    
    def _render_trusted(self) -> str:
        from .web_templates import render_trusted
        return render_trusted(self._get_trusted_sites(), self.port)
    
    def _render_updates(self) -> str:
        from .web_templates import render_updates
        return render_updates(self._get_update_status(), self._get_daemon_status(), self.port)
    
    def _render_alerts(self) -> str:
        from .web_templates import render_alerts
        return render_alerts(self._get_alerts(), self.port)
    
    def _render_export(self) -> str:
        from .web_templates import render_export
        return render_export(self._get_stats_advanced(), self.port)
    
    def _render_settings(self) -> str:
        from .web_templates import render_settings
        return render_settings(self._get_domain_lists(), self.port)
