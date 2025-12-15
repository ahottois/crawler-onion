"""
Module principal du crawler.
Contient la classe OnionCrawler et la logique de crawling.
"""

import time
import random
import threading
import concurrent.futures
from queue import Queue, Empty
from urllib.parse import urljoin, urlparse
from typing import Optional, Set, List

import requests
from bs4 import BeautifulSoup
import urllib3

from .config import Config
from .logger import Log
from .database import DatabaseManager
from .analyzer import ContentAnalyzer
from .tor import TorController
from .web_server import CrawlerWebServer

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class OnionCrawler:
    """Crawler principal pour les sites .onion."""
    
    VERSION = "6.4"
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.db = DatabaseManager(self.config.db_file)
        self.queue: Queue = Queue()
        self.visited: Set[str] = set()
        self.visited_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.active_workers = 0
        self.active_lock = threading.Lock()
        self.stats = {'requests': 0, 'errors': 0, 'success': 0}
        self.stats_lock = threading.Lock()
        self.web_server: Optional[CrawlerWebServer] = None
    
    def _create_session(self) -> requests.Session:
        """Cree une nouvelle session HTTP avec configuration Tor."""
        session = requests.Session()
        session.proxies = self.config.proxies
        session.headers.update({
            'User-Agent': random.choice(self.config.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Referer': random.choice(self.config.referers),
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        return session
    
    def _is_valid_onion_url(self, url: str) -> bool:
        """Verifie si l'URL est une URL .onion valide."""
        try:
            parsed = urlparse(url)
            if '.onion' not in parsed.netloc:
                return False
            if url.lower().endswith(self.config.ignored_extensions):
                return False
            if parsed.scheme not in ('http', 'https'):
                return False
            return True
        except Exception:
            return False
    
    def _normalize_url(self, url: str) -> str:
        """Normalise une URL."""
        url = url.split('#')[0]
        if '?' in url and len(url.split('?')[1]) > 100:
            url = url.split('?')[0]
        if not url.endswith('/') and '.' not in url.split('/')[-1]:
            url = url.rstrip('/') + '/'
        return url
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extrait les liens d'une page."""
        links = []
        for tag in soup.find_all(['a', 'link'], href=True):
            href = tag.get('href', '')
            if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
            try:
                full_url = urljoin(base_url, href)
                normalized = self._normalize_url(full_url)
                if self._is_valid_onion_url(normalized):
                    links.append(normalized)
            except Exception:
                continue
        return links
    
    def _worker(self):
        """Worker de crawling execute dans un thread."""
        session = self._create_session()
        request_count = 0
        
        while not self.stop_event.is_set():
            try:
                url, depth = self.queue.get(timeout=self.config.queue_timeout)
            except Empty:
                with self.active_lock:
                    if self.active_workers <= 1 and self.queue.empty():
                        self.stop_event.set()
                continue
            
            request_count += 1
            if request_count >= self.config.session_recycle:
                session.close()
                session = self._create_session()
                request_count = 0
            
            with self.active_lock:
                self.active_workers += 1
            
            try:
                self._process_url(session, url, depth)
            finally:
                with self.active_lock:
                    self.active_workers -= 1
                self.queue.task_done()
        
        session.close()
    
    def _process_url(self, session: requests.Session, url: str, depth: int):
        """Traite une URL."""
        response = None
        error_msg = ""
        
        for attempt in range(self.config.max_retries):
            try:
                response = session.get(
                    url, 
                    timeout=self.config.timeout, 
                    verify=False, 
                    allow_redirects=True
                )
                break
            except requests.exceptions.Timeout:
                error_msg = "Timeout"
            except requests.exceptions.ConnectionError as e:
                error_msg = "Connection Error" if "SOCKS" not in str(e) else "Unreachable"
            except Exception as e:
                error_msg = str(e)[:50]
            
            if attempt < self.config.max_retries - 1:
                time.sleep(2 ** attempt)
        
        status = response.status_code if response else 0
        title = "Error/Timeout"
        intel = {
            'secrets': {}, 'ip_leaks': [], 'emails': [], 'tech_stack': [],
            'comments': [], 'cryptos': {}, 'socials': {}, 'json_data': []
        }
        content_length = 0
        
        with self.stats_lock:
            self.stats['requests'] += 1
        
        if response and status == 200:
            content_type = response.headers.get('Content-Type', '').lower()
            content_length = len(response.content)
            
            if 'text/html' in content_type:
                try:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    title_tag = soup.find('title')
                    title = title_tag.get_text(strip=True)[:200] if title_tag else "No Title"
                    
                    text = soup.get_text(" ", strip=True)
                    intel = ContentAnalyzer.analyze(text, soup, dict(response.headers))
                    
                    new_links = 0
                    with self.visited_lock:
                        if len(self.visited) < self.config.max_pages:
                            for link in self._extract_links(soup, url):
                                if link not in self.visited:
                                    self.visited.add(link)
                                    self.queue.put((link, depth + 1))
                                    new_links += 1
                    
                    extras = ""
                    if intel['secrets']: extras += " [SECRET]"
                    if intel['cryptos']: extras += " [CRYPTO]"
                    if intel['socials']: extras += " [SOCIAL]"
                    
                    with self.visited_lock:
                        visited_count = len(self.visited)
                    
                    Log.progress(f"Crawl: {visited_count} | Q:{self.queue.qsize()} | +{new_links} | {title[:25]}{extras}")
                    
                    with self.stats_lock:
                        self.stats['success'] += 1
                        
                except Exception as e:
                    Log.error(f"Parse error: {e}")
        else:
            with self.stats_lock:
                self.stats['errors'] += 1
            if error_msg:
                domain = urlparse(url).netloc[:30]
                print(f"\n[FAIL] {domain}... ({error_msg})")
        
        self.db.save({
            'url': url, 
            'title': title, 
            'status': status, 
            'depth': depth, 
            'content_length': content_length,
            **intel
        })
    
    def _verify_tor(self) -> bool:
        """Verifie la connexion Tor."""
        Log.info(f"Test connexion Tor (Port {self.config.tor_socks_port})...")
        
        tor_ip = TorController.check_tor_connection(self.config.proxies)
        if tor_ip:
            Log.success(f"Tor OK. IP: {tor_ip}")
            return True
        
        Log.warn(f"Echec port {self.config.tor_socks_port}. Test port {self.config.tor_fallback_port}...")
        self.config.tor_socks_port = self.config.tor_fallback_port
        
        tor_ip = TorController.check_tor_connection(self.config.proxies)
        if tor_ip:
            Log.success(f"Tor OK (Port {self.config.tor_fallback_port}). IP: {tor_ip}")
            return True
        
        Log.error("Impossible de joindre Tor.")
        return False
    
    def run(self):
        """Lance le crawler."""
        Log.info(f"Demarrage Darknet Crawler v{self.VERSION}")
        
        # Demarrer le serveur web
        if self.config.web_enabled:
            self.web_server = CrawlerWebServer(
                self.config.db_file, 
                self.config.web_port, 
                self
            )
            self.web_server.start()
        
        # Verifier Tor
        if not self._verify_tor():
            return
        
        # Charger les URLs visitees
        self.visited = self.db.get_visited_urls()
        initial_count = len(self.visited)
        if initial_count > 0:
            Log.info(f"Reprise: {initial_count} URLs deja en base")
        
        # Injecter les seeds
        seeds_added = 0
        for seed in self.config.seeds:
            if seed not in self.visited:
                self.visited.add(seed)
                self.queue.put((seed, 0))
                seeds_added += 1
        
        if seeds_added > 0:
            Log.info(f"Injection de {seeds_added} nouveaux seeds")
        
        # Reprendre les URLs en attente
        if self.queue.empty():
            pending = self.db.get_pending_urls(limit=500)
            for url, depth in pending:
                if url not in self.visited:
                    self.queue.put((url, depth))
            if pending:
                Log.info(f"Reprise de {len(pending)} URLs en attente/erreur")
        
        # Rechercher de nouveaux liens
        if self.queue.empty():
            Log.info("Recherche de nouveaux liens depuis les pages crawlees...")
            successful_urls = self.db.get_successful_urls_for_recrawl()
            session = self._create_session()
            new_links_found = 0
            
            for url in successful_urls[:50]:
                try:
                    response = session.get(url, timeout=self.config.timeout, verify=False)
                    if response.status_code == 200 and 'text/html' in response.headers.get('Content-Type', ''):
                        soup = BeautifulSoup(response.content, 'html.parser')
                        for link in self._extract_links(soup, url):
                            if link not in self.visited:
                                self.visited.add(link)
                                self.queue.put((link, 1))
                                new_links_found += 1
                                if new_links_found >= 200:
                                    break
                except Exception:
                    continue
                if new_links_found >= 200:
                    break
            
            session.close()
            if new_links_found > 0:
                Log.info(f"Decouvert {new_links_found} nouveaux liens")
        
        # Verifier si la queue est vide
        if self.queue.empty():
            Log.warn("Aucune URL a crawler. Ajoutez de nouveaux seeds.")
            if self.web_server:
                Log.info(f"Dashboard: http://0.0.0.0:{self.config.web_port}")
                try:
                    while True:
                        time.sleep(60)
                except KeyboardInterrupt:
                    pass
            return
        
        Log.info(f"Queue initialisee avec {self.queue.qsize()} URLs")
        Log.info(f"Demarrage de {self.config.max_workers} workers...")
        
        # Lancer les workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = [executor.submit(self._worker) for _ in range(self.config.max_workers)]
            
            try:
                while not self.stop_event.is_set():
                    time.sleep(2)
                    with self.active_lock:
                        active = self.active_workers
                    if self.queue.empty() and active == 0:
                        self.stop_event.set()
            except KeyboardInterrupt:
                Log.warn("\nInterruption utilisateur...")
                self.stop_event.set()
            
            concurrent.futures.wait(futures, timeout=30)
        
        # Finalisation
        print()
        Log.info("Export des resultats...")
        count = self.db.export_json(self.config.json_file)
        
        db_stats = self.db.get_stats()
        Log.info("=" * 50)
        Log.info(f"URLs crawlees: {db_stats['total']}")
        Log.info(f"Succes: {db_stats['success']}")
        Log.info(f"Domaines: {db_stats['domains']}")
        Log.info(f"Intel: {count}")
        
        if count > 0:
            Log.success(f"Resultats: {self.config.json_file}")
        
        if self.web_server:
            self.web_server.stop()
