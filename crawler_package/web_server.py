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
from urllib.parse import urlparse, parse_qs, unquote

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
        self._paused = False
        
        # Config webhook
        self.webhook_url = os.environ.get('CRAWLER_WEBHOOK_URL', '')
        
        if config:
            self.updater = Updater(
                repo_owner=config.repo_owner,
                repo_name=config.repo_name,
                current_version=config.version
            )
        else:
            self.updater = Updater("ahottois", "crawler-onion", "7.0.0")
        
        self.daemon = DaemonManager()
    
    def _get_db(self):
        """Retourne une instance DatabaseManager."""
        from .database import DatabaseManager
        return DatabaseManager(self.db_file)
    
    def _get_data(self) -> Dict[str, Any]:
        """Donnees pour le dashboard."""
        db = self._get_db()
        stats = db.get_stats()
        
        data = {
            'status': 'PAUSED' if self._paused else ('RUNNING' if self.crawler and self.crawler.running else 'STOPPED'),
            'total_urls': stats.get('total', 0),
            'success_urls': stats.get('success', 0),
            'domains': stats.get('domains', 0),
            'queue_size': 0,
            'intel_count': stats.get('with_secrets', 0) + stats.get('with_crypto', 0),
            'total_emails': stats.get('with_emails', 0),
            'total_cryptos': stats.get('with_crypto', 0),
            'total_socials': 0,
            'avg_risk': stats.get('avg_risk', 0),
            'unread_alerts': stats.get('unread_alerts', 0),
            'recent_rows': [], 'intel_rows': [], 'domain_rows': []
        }
        
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute("SELECT COUNT(*) FROM intel WHERE status = 0")
            data['queue_size'] = cursor.fetchone()[0]
            
            cursor = conn.execute("""
                SELECT url, title, status, risk_score, domain FROM intel 
                ORDER BY last_crawl DESC LIMIT 15
            """)
            data['recent_rows'] = [dict(row) for row in cursor.fetchall()]
            
            cursor = conn.execute("""
                SELECT domain, title, secrets_found, cryptos, socials, emails, risk_score
                FROM intel WHERE status = 200 AND (secrets_found != '{}' OR cryptos != '{}')
                ORDER BY risk_score DESC LIMIT 10
            """)
            data['intel_rows'] = [dict(row) for row in cursor.fetchall()]
            
            cursor = conn.execute("""
                SELECT domain, COUNT(*) as pages, 
                       SUM(CASE WHEN status = 200 THEN 1 ELSE 0 END) as success,
                       AVG(risk_score) as risk
                FROM intel GROUP BY domain ORDER BY pages DESC LIMIT 10
            """)
            data['domain_rows'] = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
        except Exception as e:
            Log.error(f"Erreur dashboard: {e}")
        
        return data
    
    def _search(self, query: str, filters: Dict = None, page: int = 1, per_page: int = 50):
        """Recherche avec pagination."""
        db = self._get_db()
        offset = (page - 1) * per_page
        results, total = db.search_fulltext(query, filters, per_page, offset)
        return {
            'results': results,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }
    
    def _get_intel_item(self, url: str) -> Optional[Dict]:
        """Detail d'un item intel."""
        db = self._get_db()
        return db.get_intel_item(url)
    
    def _get_queue(self, sort: str = 'priority', limit: int = 100) -> List[Dict]:
        """Queue avec priorite."""
        db = self._get_db()
        return db.get_queue_advanced(limit, sort)
    
    def _get_domains(self, status: str = None) -> List[Dict]:
        """Liste des domaines."""
        db = self._get_db()
        return db.get_domains_list(status, 100)
    
    def _get_domain_profile(self, domain: str) -> Optional[Dict]:
        """Profil d'un domaine."""
        db = self._get_db()
        return db.get_domain_profile(domain)
    
    def _get_entities(self, entity_type: str = None) -> Dict:
        """Entites OSINT."""
        db = self._get_db()
        return {
            'entities': db.get_entities(entity_type, 200),
            'stats': db.get_entity_stats()
        }
    
    def _get_monitoring(self) -> Dict:
        """Donnees monitoring."""
        db = self._get_db()
        return {
            'hourly': db.get_hourly_stats(24),
            'timeline': db.get_timeline_stats(7),
            'errors': db.get_error_stats(),
            'sanity': self._get_sanity_checks()
        }
    
    def _get_sanity_checks(self) -> Dict:
        """Verifications systeme."""
        import shutil
        import psutil
        
        checks = {
            'disk_free_gb': 0,
            'disk_percent': 0,
            'ram_percent': 0,
            'tor_status': 'unknown',
            'db_size_mb': 0,
            'uptime': 'unknown'
        }
        
        try:
            disk = shutil.disk_usage('/')
            checks['disk_free_gb'] = round(disk.free / (1024**3), 2)
            checks['disk_percent'] = round((disk.used / disk.total) * 100, 1)
        except: pass
        
        try:
            checks['ram_percent'] = round(psutil.virtual_memory().percent, 1)
        except: pass
        
        try:
            if os.path.exists(self.db_file):
                checks['db_size_mb'] = round(os.path.getsize(self.db_file) / (1024**2), 2)
        except: pass
        
        try:
            import subprocess
            result = subprocess.run(['systemctl', 'is-active', 'tor'], 
                                  capture_output=True, text=True, timeout=5)
            checks['tor_status'] = result.stdout.strip()
        except: pass
        
        return checks
    
    def _get_alerts(self, limit: int = 50, severity: str = None) -> List[Dict]:
        """Alertes."""
        db = self._get_db()
        return db.get_alerts(limit, False, severity)
    
    def _get_trusted_sites(self) -> Dict:
        """Sites fiables."""
        db = self._get_db()
        domains = db.get_domains_list(None, 100)
        
        sites = []
        for d in domains:
            if d.get('total_pages', 0) < 2:
                continue
            success_rate = int((d.get('success_pages', 0) / d['total_pages']) * 100) if d['total_pages'] > 0 else 0
            score = min(100, d.get('success_pages', 0) * 2 + (10 if d.get('intel_count', 0) > 0 else 0))
            trust_level = 'high' if score >= 70 else ('medium' if score >= 40 else 'low')
            
            sites.append({
                'domain': d['domain'],
                'status': d.get('status', 'normal'),
                'trust_level': d.get('trust_level', trust_level),
                'total_pages': d['total_pages'],
                'success_rate': success_rate,
                'score': score,
                'has_intel': d.get('intel_count', 0) > 0,
                'priority_boost': d.get('priority_boost', 0)
            })
        
        return {
            'sites': sites,
            'total': len(sites),
            'high_trust': len([s for s in sites if s['trust_level'] == 'high']),
            'medium_trust': len([s for s in sites if s['trust_level'] == 'medium']),
            'low_trust': len([s for s in sites if s['trust_level'] == 'low'])
        }
    
    # ========== ACTIONS =========="""
    def _add_seeds(self, urls: List[str]) -> Dict:
        """Ajoute des URLs."""
        if not urls:
            return {'success': False, 'message': 'Aucune URL'}
        
        added = 0
        try:
            conn = sqlite3.connect(self.db_file)
            for url in urls:
                url = url.strip()
                if url and '.onion' in url:
                    try:
                        conn.execute("""
                            INSERT OR IGNORE INTO intel (url, domain, status, depth, priority_score)
                            VALUES (?, ?, 0, 0, 50)
                        """, (url, urlparse(url).netloc))
                        added += 1
                    except: pass
            conn.commit()
            conn.close()
        except Exception as e:
            return {'success': False, 'message': str(e)}
        
        return {'success': True, 'message': f'{added} URLs ajoutees'}
    
    def _mark_intel(self, data: Dict) -> Dict:
        """Marque un item intel."""
        url = data.get('url', '')
        mark_type = data.get('type', 'important')
        value = data.get('value', True)
        
        if not url:
            return {'success': False, 'message': 'URL requise'}
        
        db = self._get_db()
        db.mark_intel(url, mark_type, value)
        return {'success': True, 'message': 'Marque mis a jour'}
    
    def _update_domain(self, data: Dict) -> Dict:
        """Met a jour un profil domaine."""
        domain = data.get('domain', '')
        if not domain:
            return {'success': False, 'message': 'Domaine requis'}
        
        db = self._get_db()
        db.update_domain_profile(domain, data)
        return {'success': True, 'message': 'Profil mis a jour'}
    
    def _boost_domain(self, data: Dict) -> Dict:
        """Booste un domaine."""
        domain = data.get('domain', '')
        boost = data.get('boost', 10)
        
        if not domain:
            return {'success': False, 'message': 'Domaine requis'}
        
        db = self._get_db()
        db.boost_domain(domain, boost)
        return {'success': True, 'message': f'Domaine booste de {boost}'}
    
    def _freeze_domain(self, data: Dict) -> Dict:
        """Gele un domaine."""
        domain = data.get('domain', '')
        freeze = data.get('freeze', True)
        
        db = self._get_db()
        db.freeze_domain(domain, freeze)
        return {'success': True, 'message': f'Domaine {"gele" if freeze else "degele"}'}
    
    def _control_crawler(self, action: str) -> Dict:
        """Controle le crawler."""
        if action == 'pause':
            self._paused = True
            if self.crawler:
                self.crawler.pause()
            return {'success': True, 'message': 'Crawler en pause'}
        elif action == 'resume':
            self._paused = False
            if self.crawler:
                self.crawler.resume()
            return {'success': True, 'message': 'Crawler repris'}
        elif action == 'drain':
            if self.crawler:
                self.crawler.drain_mode = True
            return {'success': True, 'message': 'Mode drain active'}
        return {'success': False, 'message': 'Action inconnue'}
    
    def _get_workers_status(self) -> Dict:
        """Status des workers."""
        if not self.crawler:
            return {'workers': 0, 'active': 0, 'avg_time': 0}
        
        return {
            'workers': getattr(self.crawler, 'num_workers', 0),
            'active': getattr(self.crawler, 'active_workers', 0),
            'avg_time': getattr(self.crawler, 'avg_request_time', 0),
            'total_requests': getattr(self.crawler, 'total_requests', 0)
        }
    
    def _export_data(self, export_type: str, filters: Dict = None) -> Dict:
        """Exporte les donnees."""
        db = self._get_db()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_dir = os.path.dirname(self.db_file) or '.'
        
        try:
            if export_type == 'json':
                filepath = os.path.join(export_dir, f'export_{timestamp}.json')
                count = db.export_json(filepath, filters)
            elif export_type == 'csv':
                filepath = os.path.join(export_dir, f'export_{timestamp}.csv')
                count = db.export_csv(filepath)
            elif export_type == 'emails':
                filepath = os.path.join(export_dir, f'emails_{timestamp}.txt')
                count = db.export_emails(filepath)
            elif export_type == 'crypto':
                filepath = os.path.join(export_dir, f'crypto_{timestamp}.txt')
                count = db.export_crypto(filepath)
            else:
                return {'success': False, 'message': 'Type inconnu'}
            
            return {'success': True, 'message': f'{count} elements exportes', 'file': filepath}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def _purge_data(self, days: int, anonymize: bool = False) -> Dict:
        """Purge les donnees."""
        db = self._get_db()
        db.purge_old_data(days, anonymize)
        return {'success': True, 'message': f'Donnees > {days} jours {"anonymisees" if anonymize else "supprimees"}'}
    
    def _vacuum_db(self) -> Dict:
        """Optimise la DB."""
        db = self._get_db()
        db.vacuum()
        return {'success': True, 'message': 'Base optimisee'}
    
    # ========== UPDATE/DAEMON =========="""
    def _get_update_status(self) -> Dict:
        return self.updater.get_update_status()
    
    def _perform_update(self) -> Dict:
        return self.updater.perform_update()
    
    def _get_daemon_status(self) -> Dict:
        return self.daemon.get_full_status()
    
    def _install_daemon(self, data: Dict) -> Dict:
        return self.daemon.install(data.get('web_port', self.port), data.get('workers', 15))
    
    def _uninstall_daemon(self) -> Dict:
        return self.daemon.uninstall()
    
    def _control_daemon(self, action: str) -> Dict:
        if action == 'start': return self.daemon.start()
        elif action == 'stop': return self.daemon.stop()
        elif action == 'restart': return self.daemon.restart()
        return {'success': False, 'message': 'Action inconnue'}
    
    def _get_daemon_logs(self, lines: int = 50) -> Dict:
        return self.daemon.get_logs(lines)
    
    # ========== LISTS =========="""
    def _add_to_list(self, data: Dict) -> Dict:
        domain = data.get('domain', '').strip()
        list_type = data.get('list_type', 'blacklist')
        reason = data.get('reason', '')
        
        if not domain:
            return {'success': False, 'message': 'Domaine requis'}
        
        db = self._get_db()
        if list_type == 'blacklist':
            db.add_to_blacklist(domain, reason)
        else:
            db.add_to_whitelist(domain, reason)
        return {'success': True, 'message': f'{domain} ajoute'}
    
    def _remove_from_list(self, data: Dict) -> Dict:
        domain = data.get('domain', '').strip()
        if not domain:
            return {'success': False, 'message': 'Domaine requis'}
        
        db = self._get_db()
        db.remove_from_list(domain)
        return {'success': True, 'message': f'{domain} retire'}
    
    def _mark_alerts_read(self) -> Dict:
        db = self._get_db()
        db.mark_alerts_read()
        return {'success': True, 'message': 'Alertes lues'}
    
    def _clear_alerts(self) -> Dict:
        db = self._get_db()
        db.clear_alerts()
        return {'success': True, 'message': 'Alertes supprimees'}
    
    def _refresh_links(self) -> Dict:
        return {'success': True, 'message': 'Extraction en cours...'}
    
    def _get_domain_lists(self) -> Dict:
        db = self._get_db()
        return db.get_domain_lists()
    
    # ========== HANDLER =========="""
    def _create_handler(self):
        server_instance = self
        
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args): pass
            
            def do_GET(self):
                parsed = urlparse(self.path)
                path = parsed.path
                params = parse_qs(parsed.query)
                
                # Pages HTML
                if path == '/' or path == '/index.html':
                    self._send_html(server_instance._render_dashboard())
                elif path == '/search':
                    self._send_html(server_instance._render_search_page(params))
                elif path == '/intel':
                    self._send_html(server_instance._render_intel_page(params))
                elif path == '/intel/detail':
                    url = unquote(params.get('url', [''])[0])
                    self._send_html(server_instance._render_intel_detail(url))
                elif path == '/queue':
                    self._send_html(server_instance._render_queue_page(params))
                elif path == '/domains':
                    self._send_html(server_instance._render_domains_page(params))
                elif path == '/domain/detail':
                    domain = params.get('d', [''])[0]
                    self._send_html(server_instance._render_domain_detail(domain))
                elif path == '/monitoring':
                    self._send_html(server_instance._render_monitoring_page())
                elif path == '/entities':
                    self._send_html(server_instance._render_entities_page(params))
                elif path == '/trusted':
                    self._send_html(server_instance._render_trusted())
                elif path == '/alerts':
                    self._send_html(server_instance._render_alerts())
                elif path == '/export':
                    self._send_html(server_instance._render_export())
                elif path == '/settings':
                    self._send_html(server_instance._render_settings())
                elif path == '/updates':
                    self._send_html(server_instance._render_updates())
                # API GET
                elif path == '/api/stats':
                    self._send_json(server_instance._get_data())
                elif path == '/api/search':
                    q = params.get('q', [''])[0]
                    page = int(params.get('page', ['1'])[0])
                    filters = {
                        'time_range': params.get('time', [None])[0],
                        'intel_type': params.get('type', [None])[0],
                        'min_risk': int(params.get('risk', ['0'])[0]) or None,
                        'category': params.get('cat', [None])[0]
                    }
                    self._send_json(server_instance._search(q, filters, page))
                elif path == '/api/intel':
                    url = unquote(params.get('url', [''])[0])
                    self._send_json(server_instance._get_intel_item(url) or {})
                elif path == '/api/queue':
                    sort = params.get('sort', ['priority'])[0]
                    self._send_json({'queue': server_instance._get_queue(sort)})
                elif path == '/api/domains':
                    status = params.get('status', [None])[0]
                    self._send_json({'domains': server_instance._get_domains(status)})
                elif path == '/api/domain':
                    domain = params.get('d', [''])[0]
                    self._send_json(server_instance._get_domain_profile(domain) or {})
                elif path == '/api/entities':
                    etype = params.get('type', [None])[0]
                    self._send_json(server_instance._get_entities(etype))
                elif path == '/api/monitoring':
                    self._send_json(server_instance._get_monitoring())
                elif path == '/api/alerts':
                    self._send_json({'alerts': server_instance._get_alerts()})
                elif path == '/api/workers':
                    self._send_json(server_instance._get_workers_status())
                elif path == '/api/update-status':
                    self._send_json(server_instance._get_update_status())
                elif path == '/api/daemon-status':
                    self._send_json(server_instance._get_daemon_status())
                elif path == '/api/daemon-logs':
                    lines = int(params.get('lines', ['50'])[0])
                    self._send_json(server_instance._get_daemon_logs(lines))
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
                elif self.path == '/api/mark-intel':
                    result = server_instance._mark_intel(data)
                elif self.path == '/api/update-domain':
                    result = server_instance._update_domain(data)
                elif self.path == '/api/boost-domain':
                    result = server_instance._boost_domain(data)
                elif self.path == '/api/freeze-domain':
                    result = server_instance._freeze_domain(data)
                elif self.path == '/api/control-crawler':
                    result = server_instance._control_crawler(data.get('action', ''))
                elif self.path == '/api/export':
                    result = server_instance._export_data(data.get('type', 'json'), data.get('filters'))
                elif self.path == '/api/purge':
                    result = server_instance._purge_data(data.get('days', 30), data.get('anonymize', False))
                elif self.path == '/api/vacuum':
                    result = server_instance._vacuum_db()
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
        """Demarre le serveur."""
        if self._running: return
        try:
            self.server = HTTPServer(('0.0.0.0', self.port), self._create_handler())
            self.server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._running = True
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            Log.success(f"Serveur web sur http://0.0.0.0:{self.port}")
        except Exception as e:
            Log.error(f"Erreur serveur web: {e}")
    
    def stop(self):
        """Arrete le serveur."""
        if self.server and self._running:
            self.server.shutdown()
            self._running = False
            Log.info("Serveur web arrete")
    
    # ========== RENDER PAGES =========="""
    def _render_dashboard(self) -> str:
        from .web_templates import render_dashboard
        return render_dashboard(self._get_data(), self.port, self._get_update_status())
    
    def _render_search_page(self, params: Dict) -> str:
        from .web_templates import render_search
        query = params.get('q', [''])[0]
        filter_type = params.get('filter', ['all'])[0]
        results = self._search(query, {'intel_type': filter_type if filter_type != 'all' else None})
        return render_search(results.get('results', []), query, filter_type, self.port)
    
    def _render_intel_page(self, params: Dict) -> str:
        from .web_templates import render_intel_list
        page = int(params.get('page', ['1'])[0])
        filters = {
            'time_range': params.get('time', [None])[0],
            'intel_type': params.get('type', [None])[0],
            'min_risk': int(params.get('risk', ['0'])[0]) or None
        }
        results = self._search('', filters, page, 50)
        return render_intel_list(results, filters, self.port)
    
    def _render_intel_detail(self, url: str) -> str:
        from .web_templates import render_intel_detail
        item = self._get_intel_item(url)
        return render_intel_detail(item, self.port)
    
    def _render_queue_page(self, params: Dict) -> str:
        from .web_templates import render_queue
        sort = params.get('sort', ['priority'])[0]
        queue = self._get_queue(sort)
        return render_queue(queue, sort, self.port)
    
    def _render_domains_page(self, params: Dict) -> str:
        from .web_templates import render_domains_list
        status = params.get('status', [None])[0]
        domains = self._get_domains(status)
        return render_domains_list(domains, status, self.port)
    
    def _render_domain_detail(self, domain: str) -> str:
        from .web_templates import render_domain_detail
        profile = self._get_domain_profile(domain)
        return render_domain_detail(profile, self.port)
    
    def _render_monitoring_page(self) -> str:
        from .web_templates import render_monitoring
        data = self._get_monitoring()
        workers = self._get_workers_status()
        return render_monitoring(data, workers, self.port)
    
    def _render_entities_page(self, params: Dict) -> str:
        from .web_templates import render_entities
        etype = params.get('type', [None])[0]
        data = self._get_entities(etype)
        return render_entities(data, etype, self.port)
    
    def _render_trusted(self) -> str:
        from .web_templates import render_trusted
        return render_trusted(self._get_trusted_sites(), self.port)
    
    def _render_alerts(self) -> str:
        from .web_templates import render_alerts
        return render_alerts(self._get_alerts(), self.port)
    
    def _render_export(self) -> str:
        from .web_templates import render_export
        db = self._get_db()
        stats = db.get_stats()
        stats['timeline'] = db.get_timeline_stats(7)
        stats['high_risk'] = db.get_high_risk_sites(50, 20)
        return render_export(stats, self.port)
    
    def _render_settings(self) -> str:
        from .web_templates import render_settings
        return render_settings(self._get_domain_lists(), self.port)
    
    def _render_updates(self) -> str:
        from .web_templates import render_updates
        return render_updates(self._get_update_status(), self._get_daemon_status(), self.port)
