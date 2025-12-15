"""
Module utilitaire.
Contient des helpers pour diverses opérations.
"""

import sys
import os
import subprocess

from .logger import Log


class ClipboardHelper:
    """Helper pour copier dans le presse-papier (multi-OS)."""
    
    @staticmethod
    def copy(text: str) -> bool:
        """
        Copie le texte dans le presse-papier.
        
        Args:
            text: Texte à copier
            
        Returns:
            True si la copie a réussi, False sinon
        """
        try:
            content = text.encode('utf-8')
            
            if sys.platform.startswith('linux'):
                # Vérifier si un serveur d'affichage est disponible
                if 'DISPLAY' not in os.environ and 'WAYLAND_DISPLAY' not in os.environ:
                    Log.warn("Pas d'interface graphique détectée. Copie presse-papier ignorée.")
                    return False
                cmd = ['xclip', '-selection', 'clipboard']
            elif sys.platform == 'darwin':
                cmd = ['pbcopy']
            elif sys.platform == 'win32':
                cmd = ['clip']
            else:
                Log.warn("Système non supporté pour la copie automatique.")
                return False
            
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            proc.communicate(input=content)
            return proc.returncode == 0
            
        except FileNotFoundError as e:
            Log.warn(f"Outil de copie non trouvé: {e}")
            return False
        except Exception as e:
            Log.warn(f"Erreur copie presse-papier: {e}")
            return False


class URLHelper:
    """Helper pour la manipulation d'URLs."""
    
    @staticmethod
    def normalize(url: str) -> str:
        """
        Normalise une URL.
        
        Args:
            url: URL à normaliser
            
        Returns:
            URL normalisée
        """
        # Supprimer le fragment
        url = url.split('#')[0]
        
        # Supprimer les query strings trop longues
        if '?' in url and len(url.split('?')[1]) > 100:
            url = url.split('?')[0]
        
        # Ajouter un trailing slash si nécessaire
        if not url.endswith('/') and '.' not in url.split('/')[-1]:
            url = url.rstrip('/') + '/'
        
        return url
    
    @staticmethod
    def is_valid_onion(url: str, ignored_extensions: tuple = ()) -> bool:
        """
        Vérifie si l'URL est une URL .onion valide.
        
        Args:
            url: URL à vérifier
            ignored_extensions: Extensions de fichiers à ignorer
            
        Returns:
            True si l'URL est valide, False sinon
        """
        from urllib.parse import urlparse
        
        try:
            parsed = urlparse(url)
            
            # Vérifier le domaine .onion
            if '.onion' not in parsed.netloc:
                return False
            
            # Vérifier les extensions ignorées
            if url.lower().endswith(ignored_extensions):
                return False
            
            # Vérifier le schéma
            if parsed.scheme not in ('http', 'https'):
                return False
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def extract_domain(url: str) -> str:
        """
        Extrait le domaine d'une URL.
        
        Args:
            url: URL source
            
        Returns:
            Domaine extrait
        """
        from urllib.parse import urlparse
        try:
            return urlparse(url).netloc
        except Exception:
            return ""


class FileHelper:
    """Helper pour les opérations sur fichiers."""
    
    @staticmethod
    def ensure_dir(filepath: str) -> bool:
        """
        Crée le répertoire parent si nécessaire.
        
        Args:
            filepath: Chemin du fichier
            
        Returns:
            True si le répertoire existe ou a été créé
        """
        try:
            directory = os.path.dirname(filepath)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            return True
        except Exception:
            return False
    
    @staticmethod
    def safe_remove(filepath: str) -> bool:
        """
        Supprime un fichier de manière sécurisée.
        
        Args:
            filepath: Chemin du fichier à supprimer
            
        Returns:
            True si le fichier a été supprimé ou n'existait pas
        """
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
            return True
        except Exception:
            return False
