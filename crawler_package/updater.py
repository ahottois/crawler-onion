"""
Module de mise a jour automatique.
Verifie les nouvelles versions et permet la mise a jour depuis GitHub.
"""

import os
import subprocess
import json
from typing import Dict, Optional, List
from datetime import datetime

import requests

from .logger import Log


class Updater:
    """Gestionnaire de mises a jour depuis GitHub."""
    
    GITHUB_API = "https://api.github.com/repos"
    GITHUB_RAW = "https://raw.githubusercontent.com"
    
    def __init__(self, repo_owner: str, repo_name: str, current_version: str, install_dir: str = None):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.current_version = current_version
        self.install_dir = install_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._cache = {}
        self._cache_time = None
        self._cache_duration = 300  # 5 minutes
    
    def _get_headers(self) -> Dict[str, str]:
        """Headers pour les requetes GitHub API."""
        return {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': f'{self.repo_name}/{self.current_version}'
        }
    
    def get_latest_release(self) -> Optional[Dict]:
        """
        Recupere les informations sur la derniere release.
        
        Returns:
            Dictionnaire avec les infos de la release ou None
        """
        try:
            # Utiliser le cache si valide
            now = datetime.now()
            if self._cache.get('release') and self._cache_time:
                if (now - self._cache_time).seconds < self._cache_duration:
                    return self._cache['release']
            
            url = f"{self.GITHUB_API}/{self.repo_owner}/{self.repo_name}/releases/latest"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                release_info = {
                    'version': data.get('tag_name', '').lstrip('v'),
                    'name': data.get('name', ''),
                    'body': data.get('body', ''),
                    'published_at': data.get('published_at', ''),
                    'html_url': data.get('html_url', ''),
                    'assets': data.get('assets', [])
                }
                self._cache['release'] = release_info
                self._cache_time = now
                return release_info
            elif response.status_code == 404:
                # Pas de release, utiliser les commits
                return self._get_latest_from_commits()
            return None
            
        except Exception as e:
            Log.error(f"Erreur verification mise a jour: {e}")
            return None
    
    def _get_latest_from_commits(self) -> Optional[Dict]:
        """Recupere la version depuis les commits si pas de release."""
        try:
            url = f"{self.GITHUB_API}/{self.repo_owner}/{self.repo_name}/commits/master"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'version': data.get('sha', '')[:7],
                    'name': 'Latest commit',
                    'body': data.get('commit', {}).get('message', ''),
                    'published_at': data.get('commit', {}).get('committer', {}).get('date', ''),
                    'html_url': data.get('html_url', ''),
                    'is_commit': True
                }
            return None
        except Exception:
            return None
    
    def get_changelog(self, limit: int = 10) -> List[Dict]:
        """
        Recupere l'historique des commits recents.
        
        Args:
            limit: Nombre de commits a recuperer
            
        Returns:
            Liste des commits
        """
        try:
            url = f"{self.GITHUB_API}/{self.repo_owner}/{self.repo_name}/commits"
            response = requests.get(
                url, 
                headers=self._get_headers(), 
                params={'per_page': limit},
                timeout=10
            )
            
            if response.status_code == 200:
                commits = response.json()
                return [{
                    'sha': c.get('sha', '')[:7],
                    'message': c.get('commit', {}).get('message', '').split('\n')[0][:100],
                    'date': c.get('commit', {}).get('committer', {}).get('date', ''),
                    'author': c.get('commit', {}).get('author', {}).get('name', 'Unknown')
                } for c in commits]
            return []
        except Exception:
            return []
    
    def check_for_updates(self) -> Dict:
        """
        Verifie si une mise a jour est disponible.
        
        Returns:
            Dictionnaire avec le statut de mise a jour
        """
        result = {
            'update_available': False,
            'current_version': self.current_version,
            'latest_version': None,
            'changelog': '',
            'error': None
        }
        
        try:
            latest = self.get_latest_release()
            
            if latest:
                result['latest_version'] = latest.get('version', '')
                result['changelog'] = latest.get('body', '')
                result['release_url'] = latest.get('html_url', '')
                result['published_at'] = latest.get('published_at', '')
                
                # Comparer les versions
                if latest.get('is_commit'):
                    # Pour les commits, toujours proposer la mise a jour
                    result['update_available'] = True
                else:
                    result['update_available'] = self._compare_versions(
                        self.current_version, 
                        latest.get('version', '')
                    )
            else:
                result['error'] = "Impossible de verifier les mises a jour"
                
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _compare_versions(self, current: str, latest: str) -> bool:
        """
        Compare deux versions semantiques.
        
        Returns:
            True si latest > current
        """
        try:
            def parse_version(v):
                # Nettoyer la version
                v = v.lstrip('v').split('-')[0]
                parts = v.split('.')
                return [int(p) for p in parts if p.isdigit()]
            
            current_parts = parse_version(current)
            latest_parts = parse_version(latest)
            
            # Comparer partie par partie
            for i in range(max(len(current_parts), len(latest_parts))):
                c = current_parts[i] if i < len(current_parts) else 0
                l = latest_parts[i] if i < len(latest_parts) else 0
                if l > c:
                    return True
                elif l < c:
                    return False
            return False
        except Exception:
            return latest != current
    
    def perform_update(self) -> Dict:
        """
        Execute la mise a jour via git pull.
        
        Returns:
            Dictionnaire avec le resultat de la mise a jour
        """
        result = {
            'success': False,
            'message': '',
            'details': ''
        }
        
        try:
            # Verifier si c'est un repo git
            git_dir = os.path.join(self.install_dir, '.git')
            if not os.path.exists(git_dir):
                result['message'] = "Pas un repository Git. Mise a jour manuelle requise."
                return result
            
            # Sauvegarder le repertoire courant
            original_dir = os.getcwd()
            
            try:
                os.chdir(self.install_dir)
                
                # Git fetch
                fetch_result = subprocess.run(
                    ['git', 'fetch', 'origin'],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                # Git pull
                pull_result = subprocess.run(
                    ['git', 'pull', 'origin', 'master'],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if pull_result.returncode == 0:
                    result['success'] = True
                    result['message'] = "Mise a jour reussie!"
                    result['details'] = pull_result.stdout
                    
                    # Mettre a jour les dependances pip
                    pip_result = subprocess.run(
                        ['pip', 'install', '-r', 'requirements.txt', '-q'],
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    
                    if pip_result.returncode == 0:
                        result['details'] += "\nDependances mises a jour."
                    
                    Log.success("Mise a jour effectuee avec succes")
                else:
                    result['message'] = "Erreur lors de la mise a jour"
                    result['details'] = pull_result.stderr or pull_result.stdout
                    Log.error(f"Erreur mise a jour: {result['details']}")
                    
            finally:
                os.chdir(original_dir)
                
        except subprocess.TimeoutExpired:
            result['message'] = "Timeout lors de la mise a jour"
        except FileNotFoundError:
            result['message'] = "Git non installe ou non trouve dans le PATH"
        except Exception as e:
            result['message'] = f"Erreur: {str(e)}"
        
        return result
    
    def get_update_status(self) -> Dict:
        """
        Retourne le statut complet pour l'interface web.
        
        Returns:
            Dictionnaire avec toutes les infos de mise a jour
        """
        update_check = self.check_for_updates()
        changelog = self.get_changelog(5)
        
        return {
            'current_version': self.current_version,
            'latest_version': update_check.get('latest_version'),
            'update_available': update_check.get('update_available', False),
            'changelog': update_check.get('changelog', ''),
            'release_url': update_check.get('release_url', ''),
            'published_at': update_check.get('published_at', ''),
            'recent_commits': changelog,
            'error': update_check.get('error'),
            'install_dir': self.install_dir
        }
