"""
Module de gestion du daemon systemd.
Permet d'installer, desinstaller et controler le crawler comme service.
"""

import os
import pwd
import subprocess
import sys
from typing import Dict, Optional

from .logger import Log


class DaemonManager:
    """Gestionnaire du service systemd pour le crawler."""
    
    SERVICE_NAME = "crawler-onion"
    
    def __init__(self, install_dir: str = None):
        self.install_dir = install_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.service_file = f"/etc/systemd/system/{self.SERVICE_NAME}.service"
        self.user = self._get_current_user()
    
    def _get_current_user(self) -> str:
        """Retourne l'utilisateur courant."""
        try:
            return pwd.getpwuid(os.getuid()).pw_name
        except:
            return os.environ.get('USER', 'ubuntu')
    
    def _get_python_path(self) -> str:
        """Retourne le chemin vers l'executable Python du venv."""
        venv_python = os.path.join(self.install_dir, 'venv', 'bin', 'python')
        if os.path.exists(venv_python):
            return venv_python
        return sys.executable
    
    def _generate_service_file(self, web_port: int = 4587, workers: int = 15) -> str:
        """Genere le contenu du fichier service systemd."""
        python_path = self._get_python_path()
        run_script = os.path.join(self.install_dir, 'run.py')
        
        return f"""[Unit]
Description=Darknet Omniscient Crawler - Tor .onion Crawler
Documentation=https://github.com/ahottois/crawler-onion
After=network.target tor.service
Wants=tor.service

[Service]
Type=simple
User={self.user}
Group={self.user}
WorkingDirectory={self.install_dir}
Environment="PATH={os.path.join(self.install_dir, 'venv', 'bin')}:/usr/local/bin:/usr/bin:/bin"
ExecStart={python_path} {run_script} --workers {workers} --web-port {web_port}
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier={self.SERVICE_NAME}

# Securite
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
"""
    
    def _run_command(self, cmd: list, sudo: bool = False) -> Dict:
        """Execute une commande systeme."""
        try:
            if sudo:
                cmd = ['sudo'] + cmd
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Timeout'}
        except FileNotFoundError:
            return {'success': False, 'error': 'Commande non trouvee'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def is_systemd_available(self) -> bool:
        """Verifie si systemd est disponible."""
        return os.path.exists('/run/systemd/system')
    
    def is_installed(self) -> bool:
        """Verifie si le service est installe."""
        return os.path.exists(self.service_file)
    
    def get_status(self) -> Dict:
        """Retourne le statut du service."""
        status = {
            'systemd_available': self.is_systemd_available(),
            'installed': self.is_installed(),
            'active': False,
            'enabled': False,
            'status_text': 'Non installe',
            'error': None
        }
        
        if not status['systemd_available']:
            status['status_text'] = 'Systemd non disponible'
            return status
        
        if not status['installed']:
            return status
        
        # Verifier si actif
        result = self._run_command(['systemctl', 'is-active', self.SERVICE_NAME])
        status['active'] = result.get('stdout', '').strip() == 'active'
        
        # Verifier si enabled
        result = self._run_command(['systemctl', 'is-enabled', self.SERVICE_NAME])
        status['enabled'] = result.get('stdout', '').strip() == 'enabled'
        
        # Obtenir le statut complet
        result = self._run_command(['systemctl', 'status', self.SERVICE_NAME, '--no-pager'])
        if status['active']:
            status['status_text'] = 'En cours d\'execution'
        elif status['installed']:
            status['status_text'] = 'Arrete'
        
        return status
    
    def install(self, web_port: int = 4587, workers: int = 15) -> Dict:
        """Installe le service systemd."""
        result = {
            'success': False,
            'message': '',
            'details': ''
        }
        
        if not self.is_systemd_available():
            result['message'] = 'Systemd non disponible sur ce systeme'
            return result
        
        try:
            # Generer le fichier service
            service_content = self._generate_service_file(web_port, workers)
            
            # Creer un fichier temporaire
            temp_file = '/tmp/crawler-onion.service'
            with open(temp_file, 'w') as f:
                f.write(service_content)
            
            # Copier vers /etc/systemd/system avec sudo
            cmd_result = self._run_command(['cp', temp_file, self.service_file], sudo=True)
            if not cmd_result.get('success'):
                result['message'] = 'Erreur lors de la copie du fichier service'
                result['details'] = cmd_result.get('stderr', cmd_result.get('error', ''))
                return result
            
            # Nettoyer le fichier temporaire
            os.remove(temp_file)
            
            # Recharger systemd
            cmd_result = self._run_command(['systemctl', 'daemon-reload'], sudo=True)
            if not cmd_result.get('success'):
                result['message'] = 'Erreur lors du rechargement de systemd'
                result['details'] = cmd_result.get('stderr', '')
                return result
            
            # Activer le service au demarrage
            cmd_result = self._run_command(['systemctl', 'enable', self.SERVICE_NAME], sudo=True)
            if not cmd_result.get('success'):
                result['message'] = 'Erreur lors de l\'activation du service'
                result['details'] = cmd_result.get('stderr', '')
                return result
            
            result['success'] = True
            result['message'] = 'Service installe avec succes!'
            result['details'] = f'Le service {self.SERVICE_NAME} est maintenant installe et active au demarrage.'
            
            Log.success(f"Service {self.SERVICE_NAME} installe")
            
        except Exception as e:
            result['message'] = f'Erreur: {str(e)}'
        
        return result
    
    def uninstall(self) -> Dict:
        """Desinstalle le service systemd."""
        result = {
            'success': False,
            'message': '',
            'details': ''
        }
        
        if not self.is_installed():
            result['message'] = 'Le service n\'est pas installe'
            return result
        
        try:
            # Arreter le service
            self._run_command(['systemctl', 'stop', self.SERVICE_NAME], sudo=True)
            
            # Desactiver le service
            self._run_command(['systemctl', 'disable', self.SERVICE_NAME], sudo=True)
            
            # Supprimer le fichier service
            cmd_result = self._run_command(['rm', self.service_file], sudo=True)
            if not cmd_result.get('success'):
                result['message'] = 'Erreur lors de la suppression du fichier service'
                result['details'] = cmd_result.get('stderr', '')
                return result
            
            # Recharger systemd
            self._run_command(['systemctl', 'daemon-reload'], sudo=True)
            
            result['success'] = True
            result['message'] = 'Service desinstalle avec succes!'
            
            Log.info(f"Service {self.SERVICE_NAME} desinstalle")
            
        except Exception as e:
            result['message'] = f'Erreur: {str(e)}'
        
        return result
    
    def start(self) -> Dict:
        """Demarre le service."""
        result = {'success': False, 'message': ''}
        
        if not self.is_installed():
            result['message'] = 'Le service n\'est pas installe'
            return result
        
        cmd_result = self._run_command(['systemctl', 'start', self.SERVICE_NAME], sudo=True)
        if cmd_result.get('success'):
            result['success'] = True
            result['message'] = 'Service demarre!'
            Log.success(f"Service {self.SERVICE_NAME} demarre")
        else:
            result['message'] = 'Erreur au demarrage'
            result['details'] = cmd_result.get('stderr', '')
        
        return result
    
    def stop(self) -> Dict:
        """Arrete le service."""
        result = {'success': False, 'message': ''}
        
        if not self.is_installed():
            result['message'] = 'Le service n\'est pas installe'
            return result
        
        cmd_result = self._run_command(['systemctl', 'stop', self.SERVICE_NAME], sudo=True)
        if cmd_result.get('success'):
            result['success'] = True
            result['message'] = 'Service arrete!'
            Log.info(f"Service {self.SERVICE_NAME} arrete")
        else:
            result['message'] = 'Erreur a l\'arret'
            result['details'] = cmd_result.get('stderr', '')
        
        return result
    
    def restart(self) -> Dict:
        """Redemarre le service."""
        result = {'success': False, 'message': ''}
        
        if not self.is_installed():
            result['message'] = 'Le service n\'est pas installe'
            return result
        
        cmd_result = self._run_command(['systemctl', 'restart', self.SERVICE_NAME], sudo=True)
        if cmd_result.get('success'):
            result['success'] = True
            result['message'] = 'Service redemarre!'
            Log.success(f"Service {self.SERVICE_NAME} redemarre")
        else:
            result['message'] = 'Erreur au redemarrage'
            result['details'] = cmd_result.get('stderr', '')
        
        return result
    
    def get_logs(self, lines: int = 50) -> Dict:
        """Recupere les logs du service."""
        result = {'success': False, 'logs': '', 'message': ''}
        
        if not self.is_installed():
            result['message'] = 'Le service n\'est pas installe'
            return result
        
        cmd_result = self._run_command([
            'journalctl', 
            '-u', self.SERVICE_NAME, 
            '-n', str(lines),
            '--no-pager',
            '-o', 'short-iso'
        ])
        
        if cmd_result.get('success') or cmd_result.get('stdout'):
            result['success'] = True
            result['logs'] = cmd_result.get('stdout', '')
        else:
            result['message'] = 'Erreur lors de la recuperation des logs'
            result['details'] = cmd_result.get('stderr', '')
        
        return result
    
    def get_full_status(self) -> Dict:
        """Retourne le statut complet pour l'interface web."""
        status = self.get_status()
        status['service_name'] = self.SERVICE_NAME
        status['install_dir'] = self.install_dir
        status['user'] = self.user
        status['service_file'] = self.service_file
        
        # Obtenir les logs recents
        if status['installed']:
            logs_result = self.get_logs(20)
            status['recent_logs'] = logs_result.get('logs', '')
        else:
            status['recent_logs'] = ''
        
        return status
