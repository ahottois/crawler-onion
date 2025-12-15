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
from http.cookies import SimpleCookie

from .logger import Log
from .updater import Updater
from .daemon import DaemonManager
from .security import (
    security_manager, SecurityConfig, AuditLogger, 
    InputValidator, SecurityManager
)

# Import des nouveaux modules
try:
    from .entity_extractor import entity_extractor
    from .nlp_analyzer import content_analyzer
    from .osint_enricher import osint_enricher
    from .correlation import entity_graph, correlation_engine
    from .alert_manager import alert_manager, AlertSeverity
    ADVANCED_MODULES = True
except ImportError:
    ADVANCED_MODULES = False


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
        
        # Security
        self.security = security_manager
        
        # Config webhook
        self.webhook_url = os.environ.get('CRAWLER_WEBHOOK_URL', '')
        
        if config:
            self.updater = Updater(
                repo_owner=config.repo_owner,
                repo_name=config.repo_name,
                current_version=config.version
            )
        else:
            self.updater = Updater("ahottois", "crawler-onion", "7.1.0")
        
        self.daemon = DaemonManager()
    
    def _get_db(self):
        """Retourne une instance DatabaseManager."""
        from .database import DatabaseManager
        return DatabaseManager(self.db_file)
    
    def _get_data(self) -> Dict[str, Any]:
        """Donnees pour le dashboard."""
        db = self._get_db()
        stats = db.get_stats()
        
        # Verifier si le crawler est en cours d'execution
        crawler_running = False
        if self.crawler:
            crawler_running = not self.crawler.stop_event.is_set()
        
        data = {
            'status': 'PAUSED' if self._paused else ('RUNNING' if crawler_running else 'STOPPED'),
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
        # Valider la requete
        valid, error = InputValidator.validate_search_query(query)
        if not valid:
            return {'results': [], 'total': 0, 'error': error}
        
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
            import psutil
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
    
    # ========== ACTIONS ==========[]
    
    def _add_seeds(self, urls: List[str], ip: str) -> Dict:
        """Ajoute des URLs avec validation."""
        # Valider les URLs
        valid, error, valid_urls = InputValidator.validate_seed_urls(urls)
        if not valid:
            return {'success': False, 'message': error}
        
        added = 0
        try:
            conn = sqlite3.connect(self.db_file)
            for url in valid_urls:
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO intel (url, domain, status, depth, priority_score)
                        VALUES (?, ?, 0, 0, 50)
                    """, (url, urlparse(url).netloc))
                    added += 1
                except: pass
            conn.commit()
            conn.close()
            
            AuditLogger.log('SEEDS_ADDED', ip, {'count': added, 'urls': valid_urls[:5]})
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
    
    def _control_crawler(self, action: str, ip: str) -> Dict:
        """Controle le crawler."""
        AuditLogger.log('CRAWLER_CONTROL', ip, {'action': action})
        
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
    
    def _export_data(self, export_type: str, filters: Dict = None, ip: str = '') -> Dict:
        """Exporte les donnees."""
        AuditLogger.log('DATA_EXPORT', ip, {'type': export_type})
        
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
    
    def _purge_data(self, days: int, anonymize: bool = False, ip: str = '') -> Dict:
        """Purge les donnees."""
        AuditLogger.log('DATA_PURGE', ip, {'days': days, 'anonymize': anonymize})
        
        db = self._get_db()
        db.purge_old_data(days, anonymize)
        return {'success': True, 'message': f'Donnees > {days} jours {"anonymisees" if anonymize else "supprimees"}'}
    
    def _vacuum_db(self) -> Dict:
        """Optimise la DB."""
        db = self._get_db()
        db.vacuum()
        return {'success': True, 'message': 'Base optimisee'}
    
    # ========== SECURITY ==========[]
    
    def _authenticate(self, username: str, password: str, ip: str) -> Dict:
        """Authentifie un utilisateur."""
        success, token, error = self.security.authenticate(username, password, ip)
        if success:
            return {'success': True, 'token': token}
        return {'success': False, 'message': error}
    
    def _get_security_status(self) -> Dict:
        """Status securite."""
        return self.security.get_security_status()
    
    def _get_audit_logs(self, limit: int = 100) -> Dict:
        """Logs d'audit."""
        return {'logs': AuditLogger.get_recent_logs(limit)}
    
    def _update_ip_whitelist(self, action: str, ip: str, requester_ip: str) -> Dict:
        """Gere la whitelist IP."""
        AuditLogger.log('IP_WHITELIST_UPDATE', requester_ip, {'action': action, 'target_ip': ip})
        
        if action == 'add':
            self.security.ip_whitelist.add_ip(ip)
            return {'success': True, 'message': f'{ip} ajoute'}
        elif action == 'remove':
            self.security.ip_whitelist.remove_ip(ip)
            return {'success': True, 'message': f'{ip} retire'}
        return {'success': False, 'message': 'Action inconnue'}
    
    # ========== UPDATE/DAEMON ==========[]
    
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
    
    # ========== LISTS ==========[]
    
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
    
    # ========== NOUVELLES API =========
    
    def _get_entity_graph(self, entity_id: int = None, limit: int = 100) -> Dict:
        """Recupere le graphe d'entites."""
        db = self._get_db()
        return db.get_entity_graph(entity_id, limit)
    
    def _get_correlations(self, min_score: float = 0.7) -> Dict:
        """Recupere les correlations."""
        db = self._get_db()
        return {
            'correlations': db.get_high_correlations(min_score),
            'cross_domain': db.get_cross_domain_entities(2, 50)
        }
    
    def _analyze_content(self, url: str) -> Dict:
        """Analyse NLP d'un contenu."""
        if not ADVANCED_MODULES:
            return {'error': 'Advanced modules not available'}
        
        db = self._get_db()
        item = db.get_intel_item(url)
        if not item:
            return {'error': 'URL not found'}
        
        analysis = content_analyzer.analyze(item.get('title', ''), item.get('content_text', ''))
        return {
            'url': url,
            'language': analysis.language,
            'sentiment': analysis.sentiment,
            'site_type': analysis.site_type,
            'threat_indicators': analysis.threat_indicators,
            'threat_score': analysis.threat_score,
            'keywords': analysis.keywords,
            'topics': analysis.topics
        }
    
    def _enrich_entity(self, entity_type: str, value: str) -> Dict:
        """Enrichit une entite."""
        if not ADVANCED_MODULES:
            return {'error': 'Advanced modules not available'}
        
        if entity_type == 'email':
            return osint_enricher.enrich_email(value).__dict__
        elif entity_type == 'domain':
            return osint_enricher.enrich_domain(value).__dict__
        elif entity_type.startswith('crypto'):
            coin = entity_type.replace('crypto_', '')
            return osint_enricher.enrich_wallet(value, coin).__dict__
        elif entity_type == 'ip':
            return osint_enricher.enrich_ip(value).__dict__
        
        return {'error': 'Unknown entity type'}
    
    def _get_alerts_advanced(self, severity: str = None, limit: int = 50) -> Dict:
        """Alertes avancees avec stats."""
        db = self._get_db()
        
        if ADVANCED_MODULES:
            alerts = alert_manager.get_alerts(
                severity=AlertSeverity[severity.upper()] if severity else None,
                limit=limit
            )
            stats = alert_manager.get_stats()
        else:
            alerts = db.get_alerts(limit, severity=severity)
            stats = {'total': len(alerts)}
        
        return {
            'alerts': [{'id': a.id, 'severity': a.severity.name, 'title': a.title, 
                       'description': a.description, 'trigger': a.trigger,
                       'domain': a.domain, 'timestamp': a.timestamp,
                       'acknowledged': a.acknowledged} for a in alerts] if ADVANCED_MODULES else alerts,
            'stats': stats
        }
    
    def _acknowledge_alert(self, alert_id: str, user: str = 'admin') -> Dict:
        """Acquitte une alerte."""
        if ADVANCED_MODULES:
            success = alert_manager.acknowledge_alert(alert_id, user)
        else:
            success = True
        return {'success': success}
    
    def _add_watchlist(self, item_type: str, value: str, ip: str) -> Dict:
        """Ajoute a la watchlist."""
        AuditLogger.log('WATCHLIST_ADD', ip, {'type': item_type, 'value': value})
        
        if ADVANCED_MODULES:
            if item_type == 'domain':
                alert_manager.watchlist_domains.add(value)
            elif item_type == 'email':
                alert_manager.watchlist_emails.add(value)
            elif item_type == 'wallet':
                alert_manager.watchlist_wallets.add(value)
            elif item_type == 'internal':
                alert_manager.internal_domains.add(value)
        
        return {'success': True, 'message': f'{value} ajoute a la watchlist {item_type}'}
    
    def _get_watchlists(self) -> Dict:
        """Recupere les watchlists."""
        if ADVANCED_MODULES:
            return {
                'domains': list(alert_manager.watchlist_domains),
                'emails': list(alert_manager.watchlist_emails),
                'wallets': list(alert_manager.watchlist_wallets),
                'internal': list(alert_manager.internal_domains)
            }
        return {'domains': [], 'emails': [], 'wallets': [], 'internal': []}
    
    # ========== HANDLER ==========[]
    
    def _create_handler(self):
        server_instance = self
        
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args): pass
            
            def _get_client_ip(self):
                """Recupere l'IP client."""
                # Check X-Forwarded-For header (reverse proxy)
                forwarded = self.headers.get('X-Forwarded-For')
                if forwarded:
                    return forwarded.split(',')[0].strip()
                return self.client_address[0]
            
            def _get_token(self):
                """Recupere le token JWT."""
                # Check Authorization header
                auth = self.headers.get('Authorization', '')
                if auth.startswith('Bearer '):
                    return auth[7:]
                
                # Check cookie
                cookie = SimpleCookie(self.headers.get('Cookie', ''))
                if 'token' in cookie:
                    return cookie['token'].value
                
                return None
            
            def _check_security(self, is_search: bool = False) -> tuple:
                """Verifie la securite. Retourne (allowed, error, user)."""
                ip = self._get_client_ip()
                token = self._get_token()
                return server_instance.security.check_request(ip, token, is_search)
            
            def _send_error_response(self, code: int, message: str):
                """Envoie une reponse d'erreur."""
                self.send_response(code)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': message}).encode('utf-8'))
            
            def do_GET(self):
                ip = self._get_client_ip()
                parsed = urlparse(self.path)
                path = parsed.path
                params = parse_qs(parsed.query)
                
                # Routes publiques (login)
                if path == '/login':
                    self._send_html(server_instance._render_login())
                    return
                
                # Verifier securite
                allowed, error, user = self._check_security(is_search=(path == '/search' or path.startswith('/api/search')))
                if not allowed:
                    if SecurityConfig.AUTH_ENABLED and path != '/api/login':
                        # Rediriger vers login
                        self.send_response(302)
                        self.send_header('Location', '/login')
                        self.end_headers()
                        return
                    self._send_error_response(403, error)
                    return
                
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
                elif path == '/security':
                    self._send_html(server_instance._render_security())
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
                elif path == '/api/security-status':
                    self._send_json(server_instance._get_security_status())
                elif path == '/api/audit-logs':
                    limit = int(params.get('limit', ['100'])[0])
                    self._send_json(server_instance._get_audit_logs(limit))
                elif path == '/api/update-status':
                    self._send_json(server_instance._get_update_status())
                elif path == '/api/daemon-status':
                    self._send_json(server_instance._get_daemon_status())
                elif path == '/api/daemon-logs':
                    lines = int(params.get('lines', ['50'])[0])
                    self._send_json(server_instance._get_daemon_logs(lines))
                elif path == '/api/domain-lists':
                    self._send_json(server_instance._get_domain_lists())
                # API GET - Ajouter ces routes dans do_GET du Handler
                elif path == '/api/entity-graph':
                    entity_id = int(params.get('id', ['0'])[0]) or None
                    limit = int(params.get('limit', ['100'])[0])
                    self._send_json(server_instance._get_entity_graph(entity_id, limit))
                elif path == '/api/correlations':
                    min_score = float(params.get('min', ['0.7'])[0])
                    self._send_json(server_instance._get_correlations(min_score))
                elif path == '/api/analyze':
                    url = unquote(params.get('url', [''])[0])
                    self._send_json(server_instance._analyze_content(url))
                elif path == '/api/enrich':
                    etype = params.get('type', [''])[0]
                    value = params.get('value', [''])[0]
                    self._send_json(server_instance._enrich_entity(etype, value))
                elif path == '/api/alerts-advanced':
                    severity = params.get('severity', [None])[0]
                    limit = int(params.get('limit', ['50'])[0])
                    self._send_json(server_instance._get_alerts_advanced(severity, limit))
                elif path == '/api/watchlists':
                    self._send_json(server_instance._get_watchlists())
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def do_POST(self):
                ip = self._get_client_ip()
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else '{}'
                try: data = json.loads(body) if body else {}
                except: data = {}
                
                # Route login publique
                if self.path == '/api/login':
                    result = server_instance._authenticate(
                        data.get('username', ''),
                        data.get('password', ''),
                        ip
                    )
                    self._send_json(result)
                    return
                
                # Verifier securite
                allowed, error, user = self._check_security()
                if not allowed:
                    self._send_error_response(403, error)
                    return
                
                # Routes protegees
                if self.path == '/api/add-seeds':
                    result = server_instance._add_seeds(data.get('urls', []), ip)
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
                    result = server_instance._control_crawler(data.get('action', ''), ip)
                elif self.path == '/api/export':
                    result = server_instance._export_data(data.get('type', 'json'), data.get('filters'), ip)
                elif self.path == '/api/purge':
                    result = server_instance._purge_data(data.get('days', 30), data.get('anonymize', False), ip)
                elif self.path == '/api/vacuum':
                    result = server_instance._vacuum_db()
                elif self.path == '/api/ip-whitelist':
                    result = server_instance._update_ip_whitelist(data.get('action'), data.get('ip'), ip)
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
                # API POST - Ajouter ces routes dans do_POST du Handler
                elif self.path == '/api/acknowledge-alert':
                    result = server_instance._acknowledge_alert(data.get('alert_id', ''), data.get('user', 'admin'))
                elif self.path == '/api/add-watchlist':
                    result = server_instance._add_watchlist(data.get('type', ''), data.get('value', ''), ip)
                elif self.path == '/api/logout':
                    token = self._get_token()
                    if token:
                        server_instance.security.logout(token, ip)
                    result = {'success': True, 'message': 'Logged out'}
                elif self.path == '/api/refresh-token':
                    token = data.get('refresh_token', '')
                    success, tokens, error = server_instance.security.refresh_token(token, ip)
                    result = tokens if success else {'success': False, 'message': error}
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
        
        # Verifier si le port est deja utilise
        if self._is_port_in_use():
            Log.warning(f"Port {self.port} deja utilise")
            try:
                # Demander a l'utilisateur
                response = input(f"Le port {self.port} est occupe. Tuer le processus? (o/n): ").strip().lower()
                if response in ('o', 'y', 'oui', 'yes'):
                    if self._kill_port_process():
                        Log.success(f"Processus sur port {self.port} tue")
                        import time
                        time.sleep(1)  # Attendre que le port se libere
                    else:
                        Log.error("Impossible de tuer le processus")
                        return
                else:
                    Log.info("Serveur web non demarre")
                    return
            except EOFError:
                # Mode non-interactif (daemon), tuer automatiquement
                Log.info(f"Mode non-interactif, kill auto du port {self.port}")
                if self._kill_port_process():
                    import time
                    time.sleep(1)
                else:
                    Log.error("Impossible de liberer le port")
                    return
        
        try:
            self.server = HTTPServer(('0.0.0.0', self.port), self._create_handler())
            self.server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._running = True
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            Log.success(f"Serveur web sur http://0.0.0.0:{self.port}")
            
            if SecurityConfig.AUTH_ENABLED:
                Log.info("Auth JWT activee")
            if SecurityConfig.IP_WHITELIST_ENABLED:
                Log.info(f"IP Whitelist active: {len(self.security.ip_whitelist.get_list())} IPs")
        except Exception as e:
            Log.error(f"Erreur serveur web: {e}")
    
    def _is_port_in_use(self) -> bool:
        """Verifie si le port est deja utilise."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', self.port))
                return False
            except OSError:
                return True
    
    def _kill_port_process(self) -> bool:
        """Tue le processus utilisant le port."""
        import subprocess
        try:
            # Linux: lsof + kill
            result = subprocess.run(
                ['lsof', '-t', '-i', f':{self.port}'],
                capture_output=True, text=True, timeout=5
            )
            pids = result.stdout.strip().split('\n')
            killed = False
            for pid in pids:
                if pid:
                    try:
                        subprocess.run(['kill', '-9', pid], timeout=5)
                        killed = True
                    except:
                        pass
            return killed
        except FileNotFoundError:
            # Windows ou lsof non disponible
            try:
                import os
                os.system(f'fuser -k {self.port}/tcp 2>/dev/null')
                return True
            except:
                return False
        except Exception as e:
            Log.error(f"Erreur kill port: {e}")
            return False
    
    def stop(self):
        """Arrete le serveur."""
        if self.server and self._running:
            self.server.shutdown()
            self._running = False
            Log.info("Serveur web arrete")
    
    # ========== RENDER PAGES ==========[]
    
    def _render_login(self) -> str:
        from .web_templates import render_login
        return render_login(self.port)
    
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
    
    def _render_security(self) -> str:
        from .web_templates import render_security
        return render_security(self._get_security_status(), self._get_audit_logs(50), self.port)
    
    def _render_updates(self) -> str:
        from .web_templates import render_updates
        return render_updates(self._get_update_status(), self._get_daemon_status(), self.port)
