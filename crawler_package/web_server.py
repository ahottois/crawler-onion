"""
Module du serveur web integre.
Dashboard pour visualiser et controler le crawler.
"""

import json
import sqlite3
import socket
import threading
import html
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse, parse_qs

from .logger import Log
from .updater import Updater


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
        
        # Initialiser l'updater si config disponible
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
                current_version="6.4.0"
            )
    
    def _get_data(self) -> Dict[str, Any]:
        """Recupere les donnees depuis la base."""
        data = {
            'total_urls': 0, 'success_urls': 0, 'domains': 0, 'intel_count': 0,
            'queue_size': 0, 'status': 'STOPPED', 'intel_rows': [], 'recent_rows': [],
            'domain_rows': [], 'graph_nodes': [], 'total_emails': 0, 'total_cryptos': 0,
            'total_socials': 0, 'timeline': []
        }
        
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            c.execute("SELECT COUNT(*) as total, SUM(CASE WHEN status = 200 THEN 1 ELSE 0 END) as success, COUNT(DISTINCT domain) as domains FROM intel")
            row = c.fetchone()
            data['total_urls'] = row['total'] or 0
            data['success_urls'] = row['success'] or 0
            data['domains'] = row['domains'] or 0
            
            c.execute("SELECT COUNT(*) FROM intel WHERE status = 200 AND (secrets_found != '{}' OR cryptos != '{}' OR socials != '{}' OR emails != '[]' OR ip_leaks != '[]')")
            data['intel_count'] = c.fetchone()[0] or 0
            
            c.execute("SELECT domain, title, url, secrets_found, cryptos, socials, emails, ip_leaks, found_at FROM intel WHERE status = 200 AND (secrets_found != '{}' OR cryptos != '{}' OR socials != '{}' OR emails != '[]' OR ip_leaks != '[]') ORDER BY found_at DESC LIMIT 20")
            data['intel_rows'] = [dict(r) for r in c.fetchall()]
            
            c.execute("SELECT status, url, title, found_at FROM intel ORDER BY found_at DESC LIMIT 30")
            data['recent_rows'] = [dict(r) for r in c.fetchall()]
            
            c.execute("SELECT domain, COUNT(*) as pages, SUM(CASE WHEN status = 200 THEN 1 ELSE 0 END) as success FROM intel GROUP BY domain ORDER BY pages DESC LIMIT 15")
            data['domain_rows'] = [dict(r) for r in c.fetchall()]
            
            c.execute("SELECT domain, title, status, secrets_found, cryptos, socials, emails, ip_leaks FROM intel WHERE status = 200 GROUP BY domain ORDER BY found_at DESC LIMIT 50")
            data['graph_nodes'] = [dict(r) for r in c.fetchall()]
            
            c.execute("SELECT emails, cryptos, socials FROM intel WHERE status = 200")
            for row in c.fetchall():
                try:
                    emails = json.loads(row[0]) if row[0] else []
                    cryptos = json.loads(row[1]) if row[1] else {}
                    socials = json.loads(row[2]) if row[2] else {}
                    data['total_emails'] += len(emails) if isinstance(emails, list) else 0
                    data['total_cryptos'] += sum(len(v) for v in cryptos.values()) if isinstance(cryptos, dict) else 0
                    data['total_socials'] += sum(len(v) for v in socials.values()) if isinstance(socials, dict) else 0
                except: pass
            
            c.execute("SELECT domain, title, found_at, secrets_found, cryptos, socials FROM intel WHERE status = 200 ORDER BY found_at DESC LIMIT 30")
            data['timeline'] = [dict(r) for r in c.fetchall()]
            
            conn.close()
        except Exception as e:
            Log.error(f"Erreur DB web: {e}")
        
        if self.crawler:
            data['queue_size'] = self.crawler.queue.qsize() if hasattr(self.crawler, 'queue') else 0
            data['status'] = 'RUNNING' if not self.crawler.stop_event.is_set() else 'STOPPED'
        
        return data
    
    def _search(self, query: str, filter_type: str = 'all', limit: int = 50) -> List[Dict]:
        """Recherche dans la base de donnees."""
        results = []
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            base_query = "SELECT * FROM intel WHERE status = 200"
            params = []
            
            if query:
                base_query += " AND (title LIKE ? OR domain LIKE ? OR url LIKE ?)"
                params.extend([f'%{query}%', f'%{query}%', f'%{query}%'])
            
            if filter_type == 'crypto':
                base_query += " AND cryptos != '{}'"
            elif filter_type == 'social':
                base_query += " AND socials != '{}'"
            elif filter_type == 'email':
                base_query += " AND emails != '[]'"
            elif filter_type == 'secret':
                base_query += " AND secrets_found != '{}'"
            
            base_query += f" ORDER BY found_at DESC LIMIT {limit}"
            
            c.execute(base_query, params)
            results = [dict(r) for r in c.fetchall()]
            conn.close()
        except Exception as e:
            Log.error(f"Erreur recherche: {e}")
        return results
    
    def _get_trusted_sites(self) -> Dict[str, Any]:
        """Calcule le score de confiance des sites."""
        data = {'sites': [], 'high_trust': 0, 'medium_trust': 0, 'low_trust': 0, 'total': 0}
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            c.execute("""
                SELECT 
                    domain,
                    COUNT(*) as total_pages,
                    SUM(CASE WHEN status = 200 THEN 1 ELSE 0 END) as success_pages,
                    SUM(CASE WHEN cryptos != '{}' THEN 1 ELSE 0 END) as has_crypto,
                    SUM(CASE WHEN socials != '{}' THEN 1 ELSE 0 END) as has_social,
                    SUM(CASE WHEN emails != '[]' THEN 1 ELSE 0 END) as has_email,
                    SUM(CASE WHEN secrets_found != '{}' THEN 1 ELSE 0 END) as has_secret,
                    MAX(title) as title,
                    MAX(url) as url
                FROM intel
                GROUP BY domain
                HAVING total_pages >= 1
                ORDER BY success_pages DESC
            """)
            
            for row in c.fetchall():
                domain = row['domain']
                total = row['total_pages']
                success = row['success_pages'] or 0
                
                score = 0
                success_rate = (success / total * 100) if total > 0 else 0
                score += min(success_rate * 0.4, 40)
                score += min(total * 2, 20)
                score += 10 if row['has_crypto'] else 0
                score += 10 if row['has_social'] else 0
                score += 10 if row['has_email'] else 0
                score += 10 if row['has_secret'] else 0
                
                trust_level = 'high' if score >= 60 else ('medium' if score >= 30 else 'low')
                
                site_data = {
                    'domain': domain,
                    'score': round(score),
                    'trust_level': trust_level,
                    'total_pages': total,
                    'success_pages': success,
                    'success_rate': round(success_rate, 1),
                    'has_intel': bool(row['has_crypto'] or row['has_social'] or row['has_email'] or row['has_secret']),
                    'title': row['title'] or 'N/A',
                    'url': row['url']
                }
                data['sites'].append(site_data)
                
                if trust_level == 'high': data['high_trust'] += 1
                elif trust_level == 'medium': data['medium_trust'] += 1
                else: data['low_trust'] += 1
            
            data['sites'].sort(key=lambda x: x['score'], reverse=True)
            data['total'] = len(data['sites'])
            conn.close()
        except Exception as e:
            Log.error(f"Erreur trusted sites: {e}")
        return data
    
    def _add_seeds(self, urls: List[str]) -> Dict[str, Any]:
        """Ajoute des URLs a la queue du crawler."""
        if not self.crawler:
            return {'success': False, 'message': 'Crawler non initialise'}
        added, invalid = 0, 0
        for url in urls:
            url = url.strip()
            if not url: continue
            if '.onion' not in url: invalid += 1; continue
            if not url.startswith('http'): url = 'http://' + url
            if not url.endswith('/') and '.' not in url.split('/')[-1]: url += '/'
            with self.crawler.visited_lock:
                if url not in self.crawler.visited:
                    self.crawler.visited.add(url)
                    self.crawler.queue.put((url, 0))
                    added += 1
        if added > 0:
            return {'success': True, 'message': f'{added} URL(s) ajoutee(s)' + (f' ({invalid} invalide(s))' if invalid else '')}
        elif invalid > 0:
            return {'success': False, 'message': f'{invalid} URL(s) invalide(s)'}
        return {'success': False, 'message': 'URLs deja visitees'}
    
    def _refresh_links(self) -> Dict[str, Any]:
        """Force la recherche de nouveaux liens."""
        if not self.crawler:
            return {'success': False, 'message': 'Crawler non initialise'}
        try:
            conn = sqlite3.connect(self.db_file)
            c = conn.cursor()
            c.execute("SELECT url FROM intel WHERE status = 200 ORDER BY found_at DESC LIMIT 100")
            urls = [row[0] for row in c.fetchall()]
            conn.close()
            if not urls: return {'success': False, 'message': 'Aucune page disponible'}
            for url in urls[:30]: self.crawler.queue.put((url, 0))
            return {'success': True, 'message': f'{min(30, len(urls))} pages en queue'}
        except Exception as e:
            return {'success': False, 'message': f'Erreur: {str(e)}'}
    
    def _get_update_status(self) -> Dict[str, Any]:
        """Recupere le statut des mises a jour."""
        return self.updater.get_update_status()
    
    def _perform_update(self) -> Dict[str, Any]:
        """Execute la mise a jour."""
        return self.updater.perform_update()
    
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
                elif path == '/api/stats':
                    self._send_json(server_instance._get_data())
                elif path == '/api/update-status':
                    self._send_json(server_instance._get_update_status())
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
                self.end_headers()
                self.wfile.write(json.dumps(data).encode('utf-8'))
        
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
    
    # Les templates sont dans un fichier separe pour la lisibilite
    def _render_dashboard(self) -> str:
        """Genere la page dashboard."""
        from .web_templates import render_dashboard
        update_status = self._get_update_status()
        return render_dashboard(self._get_data(), self.port, update_status)
    
    def _render_search(self, query: str = '', filter_type: str = 'all') -> str:
        """Genere la page de recherche."""
        from .web_templates import render_search
        results = self._search(query, filter_type) if query or filter_type != 'all' else []
        return render_search(results, query, filter_type, self.port)
    
    def _render_trusted(self) -> str:
        """Genere la page des sites fiables."""
        from .web_templates import render_trusted
        return render_trusted(self._get_trusted_sites(), self.port)
    
    def _render_updates(self) -> str:
        """Genere la page des mises a jour."""
        from .web_templates import render_updates
        return render_updates(self._get_update_status(), self.port)
