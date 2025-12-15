"""
Module de mise a jour automatique.
Verifie les nouvelles versions et permet la mise a jour depuis GitHub.
"""

import os
import subprocess
import json
from typing import Dict, Optional, List
from datetime import datetime

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

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
    
    def _get_local_version(self) -> Optional[str]:
        """Recupere la version depuis le git local."""
        try:
            git_dir = os.path.join(self.install_dir, '.git')
            if not os.path.exists(git_dir):
                return None
            
            result = subprocess.run(
                ['git', 'describe', '--tags', '--abbrev=0'],
                capture_output=True, text=True, timeout=10,
                cwd=self.install_dir
            )
            if result.returncode == 0:
                return result.stdout.strip().lstrip('v')
            
            # Pas de tag, utiliser le hash du commit
            result = subprocess.run(
                ['git', 'rev-parse', '--short', 'HEAD'],
                capture_output=True, text=True, timeout=10,
                cwd=self.install_dir
            )
            if result.returncode == 0:
                return result.stdout.strip()
            
            return None
        except Exception:
            return None
    
    def _get_remote_commits(self) -> List[Dict]:
        """Recupere les commits distants via git fetch."""
        commits = []
        try:
            git_dir = os.path.join(self.install_dir, '.git')
            if not os.path.exists(git_dir):
                return commits
            
            # Fetch les dernieres modifications
            subprocess.run(
                ['git', 'fetch', 'origin'],
                capture_output=True, text=True, timeout=30,
                cwd=self.install_dir
            )
            
            # Recuperer les commits distants pas encore en local
            result = subprocess.run(
                ['git', 'log', 'HEAD..origin/master', '--oneline', '-n', '10'],
                capture_output=True, text=True, timeout=10,
                cwd=self.install_dir
            )
            
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split(' ', 1)
                        commits.append({
                            'sha': parts[0],
                            'message': parts[1] if len(parts) > 1 else '',
                            'date': '',
                            'author': ''
                        })
            
            # Si pas de nouveaux commits, recuperer les derniers commits locaux
            if not commits:
                result = subprocess.run(
                    ['git', 'log', '-n', '5', '--pretty=format:%h|%s|%ci|%an'],
                    capture_output=True, text=True, timeout=10,
                    cwd=self.install_dir
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            parts = line.split('|')
                            commits.append({
                                'sha': parts[0] if len(parts) > 0 else '',
                                'message': parts[1] if len(parts) > 1 else '',
                                'date': parts[2][:10] if len(parts) > 2 else '',
                                'author': parts[3] if len(parts) > 3 else ''
                            })
            
            return commits
        except Exception:
            return commits
    
    def _check_git_updates(self) -> Dict:
        """Verifie les mises a jour via git."""
        result = {
            'update_available': False,
            'commits_behind': 0,
            'latest_commit': None
        }
        
        try:
            git_dir = os.path.join(self.install_dir, '.git')
            if not os.path.exists(git_dir):
                return result
            
            # Fetch
            subprocess.run(
                ['git', 'fetch', 'origin'],
                capture_output=True, timeout=30,
                cwd=self.install_dir
            )
            
            # Compter les commits de retard
            cmd_result = subprocess.run(
                ['git', 'rev-list', '--count', 'HEAD..origin/master'],
                capture_output=True, text=True, timeout=10,
                cwd=self.install_dir
            )
            
            if cmd_result.returncode == 0:
                count = int(cmd_result.stdout.strip() or '0')
                result['commits_behind'] = count
                result['update_available'] = count > 0
            
            # Recuperer le dernier commit distant
            cmd_result = subprocess.run(
                ['git', 'log', 'origin/master', '-1', '--pretty=format:%h|%s'],
                capture_output=True, text=True, timeout=10,
                cwd=self.install_dir
            )
            
            if cmd_result.returncode == 0 and cmd_result.stdout:
                parts = cmd_result.stdout.split('|', 1)
                result['latest_commit'] = {
                    'sha': parts[0],
                    'message': parts[1] if len(parts) > 1 else ''
                }
            
            return result
        except Exception:
            return result
    
    def get_latest_release(self) -> Optional[Dict]:
        """Recupere les informations sur la derniere release."""
        # D'abord essayer l'API GitHub (repos publics)
        if HAS_REQUESTS:
            try:
                url = f"{self.GITHUB_API}/{self.repo_owner}/{self.repo_name}/releases/latest"
                response = requests.get(url, headers=self._get_headers(), timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'version': data.get('tag_name', '').lstrip('v'),
                        'name': data.get('name', ''),
                        'body': data.get('body', ''),
                        'published_at': data.get('published_at', ''),
                        'html_url': data.get('html_url', '')
                    }
            except Exception:
                pass
        
        # Fallback: utiliser git local
        git_info = self._check_git_updates()
        if git_info.get('latest_commit'):
            return {
                'version': git_info['latest_commit']['sha'],
                'name': f"{git_info['commits_behind']} commit(s) en attente",
                'body': git_info['latest_commit']['message'],
                'is_commit': True,
                'commits_behind': git_info['commits_behind']
            }
        
        return None
    
    def get_changelog(self, limit: int = 10) -> List[Dict]:
        """Recupere l'historique des commits recents."""
        # D'abord essayer l'API GitHub
        if HAS_REQUESTS:
            try:
                url = f"{self.GITHUB_API}/{self.repo_owner}/{self.repo_name}/commits"
                response = requests.get(
                    url, headers=self._get_headers(), 
                    params={'per_page': limit}, timeout=10
                )
                
                if response.status_code == 200:
                    commits = response.json()
                    return [{
                        'sha': c.get('sha', '')[:7],
                        'message': c.get('commit', {}).get('message', '').split('\n')[0][:100],
                        'date': c.get('commit', {}).get('committer', {}).get('date', ''),
                        'author': c.get('commit', {}).get('author', {}).get('name', 'Unknown')
                    } for c in commits]
            except Exception:
                pass
        
        # Fallback: utiliser git local
        return self._get_remote_commits()
    
    def check_for_updates(self) -> Dict:
        """Verifie si une mise a jour est disponible."""
        result = {
            'update_available': False,
            'current_version': self.current_version,
            'latest_version': self.current_version,
            'changelog': '',
            'error': None,
            'commits_behind': 0
        }
        
        try:
            # Verifier via git d'abord (plus fiable pour repos prives)
            git_info = self._check_git_updates()
            
            if git_info.get('update_available'):
                result['update_available'] = True
                result['commits_behind'] = git_info.get('commits_behind', 0)
                if git_info.get('latest_commit'):
                    commits_behind = git_info['commits_behind']
                    result['latest_version'] = f"{self.current_version}+{commits_behind}"
                    result['changelog'] = git_info['latest_commit'].get('message', '')
                return result
            
            # Essayer l'API GitHub pour les releases
            latest = self.get_latest_release()
            if latest:
                result['latest_version'] = latest.get('version', self.current_version)
                result['changelog'] = latest.get('body', '')
                result['release_url'] = latest.get('html_url', '')
                
                if not latest.get('is_commit'):
                    result['update_available'] = self._compare_versions(
                        self.current_version, 
                        latest.get('version', '')
                    )
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _compare_versions(self, current: str, latest: str) -> bool:
        """Compare deux versions semantiques."""
        try:
            def parse_version(v):
                v = v.lstrip('v').split('-')[0].split('+')[0]
                parts = v.split('.')
                return [int(p) for p in parts if p.isdigit()]
            
            current_parts = parse_version(current)
            latest_parts = parse_version(latest)
            
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
        """Execute la mise a jour via git pull."""
        result = {
            'success': False,
            'message': '',
            'details': ''
        }
        
        try:
            git_dir = os.path.join(self.install_dir, '.git')
            if not os.path.exists(git_dir):
                result['message'] = "Pas un repository Git. Mise a jour manuelle requise."
                return result
            
            original_dir = os.getcwd()
            
            try:
                os.chdir(self.install_dir)
                
                # Git fetch
                subprocess.run(
                    ['git', 'fetch', 'origin'],
                    capture_output=True, text=True, timeout=60
                )
                
                # Git pull
                pull_result = subprocess.run(
                    ['git', 'pull', 'origin', 'master'],
                    capture_output=True, text=True, timeout=120
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
            result['message'] = "Git non installe"
        except Exception as e:
            result['message'] = f"Erreur: {str(e)}"
        
        return result
    
    def get_update_status(self) -> Dict:
        """Retourne le statut complet pour l'interface web."""
        update_check = self.check_for_updates()
        changelog = self.get_changelog(5)
        
        return {
            'current_version': self.current_version,
            'latest_version': update_check.get('latest_version', self.current_version),
            'update_available': update_check.get('update_available', False),
            'commits_behind': update_check.get('commits_behind', 0),
            'changelog': update_check.get('changelog', ''),
            'release_url': update_check.get('release_url', ''),
            'recent_commits': changelog,
            'error': update_check.get('error'),
            'install_dir': self.install_dir
        }
