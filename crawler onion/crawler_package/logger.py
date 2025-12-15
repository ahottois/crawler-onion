"""
Module de logging avec support couleur optionnel.
"""

import sys
import threading
from enum import Enum

# Import optionnel de colorama
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    class Fore:
        GREEN = CYAN = YELLOW = RED = BLUE = MAGENTA = ""
    class Style:
        RESET_ALL = BRIGHT = ""


class LogLevel(Enum):
    """Niveaux de log disponibles."""
    INFO = ("INFO", Fore.GREEN)
    SUCCESS = ("OK", Fore.CYAN)
    WARN = ("WARN", Fore.YELLOW)
    ERROR = ("ERR", Fore.RED)
    ALERT = ("ALERT", Fore.RED + Style.BRIGHT if HAS_COLOR else "")
    TECH = ("TECH", Fore.BLUE)
    MONEY = ("MONEY", Fore.MAGENTA)


class Logger:
    """Gestionnaire de logs thread-safe avec support couleur optionnel."""
    
    _lock = threading.Lock()
    
    @classmethod
    def _log(cls, level: LogLevel, msg: str, to_stderr: bool = False):
        """Méthode interne de log."""
        tag, color = level.value
        with cls._lock:
            output = f"{color}[{tag}]{Style.RESET_ALL} {msg}" if HAS_COLOR else f"[{tag}] {msg}"
            if to_stderr:
                sys.stderr.write(output + "\n")
            else:
                print(output)
    
    @classmethod
    def info(cls, msg: str):
        """Log d'information."""
        cls._log(LogLevel.INFO, msg)
    
    @classmethod
    def success(cls, msg: str):
        """Log de succès."""
        cls._log(LogLevel.SUCCESS, msg)
    
    @classmethod
    def warn(cls, msg: str):
        """Log d'avertissement."""
        cls._log(LogLevel.WARN, msg)
    
    @classmethod
    def error(cls, msg: str):
        """Log d'erreur."""
        cls._log(LogLevel.ERROR, msg, to_stderr=True)
    
    @classmethod
    def alert(cls, msg: str):
        """Log d'alerte critique."""
        cls._log(LogLevel.ALERT, msg)
    
    @classmethod
    def tech(cls, msg: str):
        """Log technique."""
        cls._log(LogLevel.TECH, msg)
    
    @classmethod
    def money(cls, msg: str):
        """Log monétaire/crypto."""
        cls._log(LogLevel.MONEY, msg)
    
    @classmethod
    def progress(cls, msg: str):
        """Affiche une ligne de progression (écrasée)."""
        with cls._lock:
            print(f"\r{msg}", end="", flush=True)


# Alias pour compatibilité
Log = Logger
