"""
Module de contrôle Tor.
Interface avec le contrôleur Tor et vérification de connexion.
"""

import socket
from typing import Dict, Optional

import requests


class TorController:
    """Interface avec le contrôleur Tor."""
    
    @staticmethod
    def request_new_circuit(control_port: int, password: str = "") -> bool:
        """
        Demande un nouveau circuit Tor.
        
        Args:
            control_port: Port du contrôleur Tor
            password: Mot de passe d'authentification (optionnel)
            
        Returns:
            True si le nouveau circuit a été créé, False sinon
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                sock.connect(('127.0.0.1', control_port))
                
                # Authentification
                auth_cmd = f'AUTHENTICATE "{password}"\r\n' if password else 'AUTHENTICATE\r\n'
                sock.sendall(auth_cmd.encode())
                
                response = sock.recv(1024).decode()
                if '250 OK' not in response:
                    return False
                
                # Signal pour nouveau circuit
                sock.sendall(b'SIGNAL NEWNYM\r\n')
                response = sock.recv(1024).decode()
                return '250 OK' in response
                
        except (socket.error, socket.timeout, OSError):
            return False
    
    @staticmethod
    def check_tor_connection(proxies: Dict[str, str], timeout: int = 20) -> Optional[str]:
        """
        Vérifie la connexion Tor et retourne l'IP si connecté.
        
        Args:
            proxies: Configuration proxy pour Tor
            timeout: Timeout de la requête en secondes
            
        Returns:
            L'adresse IP Tor si connecté, None sinon
        """
        try:
            session = requests.Session()
            response = session.get(
                "https://check.torproject.org/api/ip",
                proxies=proxies,
                timeout=timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('IsTor', False):
                    return data.get('IP')
            return None
            
        except (requests.RequestException, ValueError):
            return None
    
    @staticmethod
    def get_tor_status(proxies: Dict[str, str], timeout: int = 20) -> Dict[str, any]:
        """
        Obtient le statut complet de la connexion Tor.
        
        Args:
            proxies: Configuration proxy pour Tor
            timeout: Timeout de la requête en secondes
            
        Returns:
            Dictionnaire avec les informations de connexion
        """
        status = {
            'connected': False,
            'ip': None,
            'is_tor': False,
            'error': None
        }
        
        try:
            session = requests.Session()
            response = session.get(
                "https://check.torproject.org/api/ip",
                proxies=proxies,
                timeout=timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                status['connected'] = True
                status['ip'] = data.get('IP')
                status['is_tor'] = data.get('IsTor', False)
                
        except requests.exceptions.ProxyError:
            status['error'] = "Proxy error - Tor not running?"
        except requests.exceptions.Timeout:
            status['error'] = "Connection timeout"
        except requests.exceptions.ConnectionError:
            status['error'] = "Connection refused"
        except Exception as e:
            status['error'] = str(e)
        
        return status
