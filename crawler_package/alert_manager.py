"""
Module de gestion des alertes et webhooks.
Alertes temps reel avec severite et triggers.
"""

import os
import json
import threading
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import deque

from .logger import Log


class AlertSeverity(Enum):
    """Niveaux de severite."""
    CRITICAL = 1   # ?? Action immediate
    HIGH = 2       # ?? Important
    MEDIUM = 3     # ?? Informationnel
    LOW = 4        # ?? Debug


@dataclass
class Alert:
    """Alerte."""
    id: str
    severity: AlertSeverity
    trigger: str
    title: str
    description: str
    timestamp: str = ""
    domain: str = ""
    url: str = ""
    entities: Dict = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)
    acknowledged: bool = False
    acknowledged_by: str = ""
    acknowledged_at: str = ""


class AlertTriggers:
    """Definition des triggers d'alertes."""
    
    # CRITICAL - Action immediate
    CRITICAL_TRIGGERS = {
        'ransomware_group_mentioned': {
            'keywords': ['lockbit', 'blackcat', 'alphv', 'conti', 'revil', 'akira', 'blackbasta', 'hive'],
            'description': 'Ransomware group name detected',
            'icon': '??'
        },
        'credentials_dump_detected': {
            'indicators': ['dump', 'leak', 'breach', 'credentials', 'database'],
            'min_count': 3,
            'description': 'Possible credentials dump detected',
            'icon': '??'
        },
        'internal_domain_found': {
            'domains': [],  # A configurer
            'description': 'Internal domain mentioned on darknet',
            'icon': '??'
        },
        'known_malware_c2': {
            'iocs': [],  # A configurer
            'description': 'Known malware C2 infrastructure',
            'icon': '??'
        },
        'wallet_major_transaction': {
            'threshold_btc': 10.0,
            'description': 'Crypto wallet with major transaction detected',
            'icon': '??'
        },
    }
    
    # HIGH - Important
    HIGH_TRIGGERS = {
        'new_breach_site': {
            'keywords': ['leak', 'dump', 'breach', 'stolen'],
            'site_type': 'breach_market',
            'description': 'New breach/leak site discovered',
            'icon': '??'
        },
        'domain_in_watchlist': {
            'watchlist': [],  # A configurer
            'description': 'Monitored domain detected',
            'icon': '??'
        },
        'multiple_patterns_same_domain': {
            'threshold': 5,
            'description': '5+ patterns detected on same domain',
            'icon': '??'
        },
        'domain_mirrors_found': {
            'description': 'Domain mirrors/clones detected',
            'icon': '??'
        },
        'new_marketplace_vendor': {
            'keywords': ['vendor', 'seller', 'shop'],
            'description': 'New marketplace vendor detected',
            'icon': '??'
        },
    }
    
    # MEDIUM - Informationnel
    MEDIUM_TRIGGERS = {
        'new_domain_discovered': {
            'description': 'New .onion domain discovered',
            'icon': '??'
        },
        'unusual_crawl_activity': {
            'threshold_pages': 100,
            'description': 'Unusual crawl activity detected',
            'icon': '??'
        },
        'domain_content_changed': {
            'threshold_percent': 50,
            'description': 'Major content change detected',
            'icon': '??'
        },
        'new_email_pattern': {
            'description': 'New email pattern detected',
            'icon': '??'
        },
        'high_risk_score': {
            'threshold': 70,
            'description': 'High risk score detected',
            'icon': '??'
        },
    }
    
    # LOW - Debug
    LOW_TRIGGERS = {
        'crawler_stats_update': {
            'description': 'Crawler statistics update',
            'icon': '??'
        },
        'pattern_detected': {
            'description': 'Pattern detected',
            'icon': '??'
        },
        'domain_new_page': {
            'description': 'New page discovered on domain',
            'icon': '??'
        },
        'queue_milestone': {
            'milestones': [100, 500, 1000, 5000],
            'description': 'Queue milestone reached',
            'icon': '??'
        },
    }


class WebhookConfig:
    """Configuration webhooks."""
    
    # URL des webhooks
    WEBHOOK_URL = os.environ.get('CRAWLER_WEBHOOK_URL', '')
    SLACK_WEBHOOK = os.environ.get('CRAWLER_SLACK_WEBHOOK', '')
    DISCORD_WEBHOOK = os.environ.get('CRAWLER_DISCORD_WEBHOOK', '')
    TELEGRAM_BOT_TOKEN = os.environ.get('CRAWLER_TELEGRAM_TOKEN', '')
    TELEGRAM_CHAT_ID = os.environ.get('CRAWLER_TELEGRAM_CHAT', '')
    
    # Niveaux a notifier
    NOTIFY_LEVELS = {
        AlertSeverity.CRITICAL: True,
        AlertSeverity.HIGH: True,
        AlertSeverity.MEDIUM: False,
        AlertSeverity.LOW: False,
    }
    
    # Rate limiting webhooks
    WEBHOOK_RATE_LIMIT = 10  # max par minute
    WEBHOOK_COOLDOWN = 60    # secondes


class WebhookSender:
    """Envoi de webhooks."""
    
    def __init__(self):
        self._sent_count = 0
        self._last_reset = datetime.utcnow()
        self._lock = threading.Lock()
    
    def _check_rate_limit(self) -> bool:
        """Verifie le rate limit."""
        with self._lock:
            now = datetime.utcnow()
            if (now - self._last_reset).seconds >= WebhookConfig.WEBHOOK_COOLDOWN:
                self._sent_count = 0
                self._last_reset = now
            
            if self._sent_count >= WebhookConfig.WEBHOOK_RATE_LIMIT:
                return False
            
            self._sent_count += 1
            return True
    
    def send_generic(self, url: str, payload: Dict) -> bool:
        """Envoie un webhook generique."""
        if not url or not self._check_rate_limit():
            return False
        
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status == 200
                
        except Exception as e:
            Log.error(f"Webhook error: {e}")
            return False
    
    def send_slack(self, alert: Alert) -> bool:
        """Envoie vers Slack."""
        if not WebhookConfig.SLACK_WEBHOOK:
            return False
        
        color = {
            AlertSeverity.CRITICAL: '#ff0000',
            AlertSeverity.HIGH: '#ff8800',
            AlertSeverity.MEDIUM: '#ffff00',
            AlertSeverity.LOW: '#00ff00',
        }.get(alert.severity, '#888888')
        
        payload = {
            'attachments': [{
                'color': color,
                'title': f"{alert.severity.name}: {alert.title}",
                'text': alert.description,
                'fields': [
                    {'title': 'Trigger', 'value': alert.trigger, 'short': True},
                    {'title': 'Domain', 'value': alert.domain or 'N/A', 'short': True},
                ],
                'footer': 'Darknet Crawler',
                'ts': int(datetime.utcnow().timestamp())
            }]
        }
        
        return self.send_generic(WebhookConfig.SLACK_WEBHOOK, payload)
    
    def send_discord(self, alert: Alert) -> bool:
        """Envoie vers Discord."""
        if not WebhookConfig.DISCORD_WEBHOOK:
            return False
        
        color = {
            AlertSeverity.CRITICAL: 0xff0000,
            AlertSeverity.HIGH: 0xff8800,
            AlertSeverity.MEDIUM: 0xffff00,
            AlertSeverity.LOW: 0x00ff00,
        }.get(alert.severity, 0x888888)
        
        payload = {
            'embeds': [{
                'title': f"?? {alert.severity.name}: {alert.title}",
                'description': alert.description,
                'color': color,
                'fields': [
                    {'name': 'Trigger', 'value': alert.trigger, 'inline': True},
                    {'name': 'Domain', 'value': alert.domain or 'N/A', 'inline': True},
                ],
                'footer': {'text': 'Darknet Crawler'},
                'timestamp': datetime.utcnow().isoformat()
            }]
        }
        
        return self.send_generic(WebhookConfig.DISCORD_WEBHOOK, payload)
    
    def send_telegram(self, alert: Alert) -> bool:
        """Envoie vers Telegram."""
        if not WebhookConfig.TELEGRAM_BOT_TOKEN or not WebhookConfig.TELEGRAM_CHAT_ID:
            return False
        
        icon = {
            AlertSeverity.CRITICAL: '??',
            AlertSeverity.HIGH: '??',
            AlertSeverity.MEDIUM: '??',
            AlertSeverity.LOW: '??',
        }.get(alert.severity, '?')
        
        message = f"""
{icon} *{alert.severity.name}*: {alert.title}

{alert.description}

*Trigger*: `{alert.trigger}`
*Domain*: `{alert.domain or 'N/A'}`
*Time*: {alert.timestamp}
"""
        
        url = f"https://api.telegram.org/bot{WebhookConfig.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': WebhookConfig.TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        return self.send_generic(url, payload)
    
    def send_all(self, alert: Alert):
        """Envoie a tous les webhooks configures."""
        # Webhook generique
        if WebhookConfig.WEBHOOK_URL:
            payload = {
                'timestamp': alert.timestamp,
                'severity': alert.severity.name,
                'trigger': alert.trigger,
                'title': alert.title,
                'description': alert.description,
                'domain': alert.domain,
                'url': alert.url,
                'entities': alert.entities,
                'metadata': alert.metadata
            }
            self.send_generic(WebhookConfig.WEBHOOK_URL, payload)
        
        # Slack
        self.send_slack(alert)
        
        # Discord
        self.send_discord(alert)
        
        # Telegram
        self.send_telegram(alert)


class AlertManager:
    """Gestionnaire d'alertes centralise."""
    
    def __init__(self, max_history: int = 1000):
        self._alerts: deque = deque(maxlen=max_history)
        self._alert_count = 0
        self._lock = threading.Lock()
        self._webhook_sender = WebhookSender()
        self._callbacks: List[Callable[[Alert], None]] = []
        
        # Watchlists configurables
        self.watchlist_domains: set = set()
        self.watchlist_emails: set = set()
        self.watchlist_wallets: set = set()
        self.internal_domains: set = set()
    
    def _generate_alert_id(self) -> str:
        """Genere un ID unique pour une alerte."""
        self._alert_count += 1
        return f"ALT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self._alert_count:05d}"
    
    def create_alert(self, severity: AlertSeverity, trigger: str, title: str,
                    description: str, domain: str = "", url: str = "",
                    entities: Dict = None, metadata: Dict = None,
                    send_webhook: bool = True) -> Alert:
        """Cree et enregistre une alerte."""
        
        alert = Alert(
            id=self._generate_alert_id(),
            severity=severity,
            trigger=trigger,
            title=title,
            description=description,
            timestamp=datetime.utcnow().isoformat() + 'Z',
            domain=domain,
            url=url,
            entities=entities or {},
            metadata=metadata or {}
        )
        
        with self._lock:
            self._alerts.appendleft(alert)
        
        Log.warning(f"[ALERT] {severity.name}: {title}")
        
        # Callbacks
        for callback in self._callbacks:
            try:
                callback(alert)
            except Exception as e:
                Log.error(f"Alert callback error: {e}")
        
        # Webhook
        if send_webhook and WebhookConfig.NOTIFY_LEVELS.get(severity, False):
            threading.Thread(
                target=self._webhook_sender.send_all,
                args=(alert,),
                daemon=True
            ).start()
        
        return alert
    
    def register_callback(self, callback: Callable[[Alert], None]):
        """Enregistre un callback pour les nouvelles alertes."""
        self._callbacks.append(callback)
    
    def get_alerts(self, severity: AlertSeverity = None, 
                   acknowledged: bool = None,
                   limit: int = 100,
                   since: str = None) -> List[Alert]:
        """Recupere les alertes avec filtres."""
        with self._lock:
            alerts = list(self._alerts)
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        
        if since:
            alerts = [a for a in alerts if a.timestamp >= since]
        
        return alerts[:limit]
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system") -> bool:
        """Acquitte une alerte."""
        with self._lock:
            for alert in self._alerts:
                if alert.id == alert_id:
                    alert.acknowledged = True
                    alert.acknowledged_by = acknowledged_by
                    alert.acknowledged_at = datetime.utcnow().isoformat()
                    return True
        return False
    
    def get_unacknowledged_count(self, severity: AlertSeverity = None) -> int:
        """Compte les alertes non acquittees."""
        with self._lock:
            alerts = [a for a in self._alerts if not a.acknowledged]
            if severity:
                alerts = [a for a in alerts if a.severity == severity]
            return len(alerts)
    
    def get_stats(self) -> Dict:
        """Stats des alertes."""
        with self._lock:
            alerts = list(self._alerts)
        
        return {
            'total': len(alerts),
            'unacknowledged': len([a for a in alerts if not a.acknowledged]),
            'by_severity': {
                'critical': len([a for a in alerts if a.severity == AlertSeverity.CRITICAL]),
                'high': len([a for a in alerts if a.severity == AlertSeverity.HIGH]),
                'medium': len([a for a in alerts if a.severity == AlertSeverity.MEDIUM]),
                'low': len([a for a in alerts if a.severity == AlertSeverity.LOW]),
            },
            'recent_24h': len([
                a for a in alerts 
                if a.timestamp >= (datetime.utcnow().isoformat()[:10])
            ])
        }
    
    # ========== TRIGGER CHECKS ==========
    
    def check_ransomware(self, content: str, domain: str = "", url: str = "") -> Optional[Alert]:
        """Verifie la presence de groupes ransomware."""
        content_lower = content.lower()
        
        for keyword in AlertTriggers.CRITICAL_TRIGGERS['ransomware_group_mentioned']['keywords']:
            if keyword in content_lower:
                return self.create_alert(
                    severity=AlertSeverity.CRITICAL,
                    trigger='ransomware_group_mentioned',
                    title=f"?? Ransomware Group Detected: {keyword.upper()}",
                    description=f"Ransomware group '{keyword}' mentioned in content",
                    domain=domain,
                    url=url,
                    entities={'ransomware_group': keyword}
                )
        return None
    
    def check_credentials_dump(self, entities: Dict, domain: str = "", url: str = "") -> Optional[Alert]:
        """Verifie si c'est un dump de credentials."""
        indicators = AlertTriggers.CRITICAL_TRIGGERS['credentials_dump_detected']['indicators']
        count = sum(1 for ind in indicators if ind in str(entities).lower())
        
        if count >= AlertTriggers.CRITICAL_TRIGGERS['credentials_dump_detected']['min_count']:
            return self.create_alert(
                severity=AlertSeverity.CRITICAL,
                trigger='credentials_dump_detected',
                title="?? Credentials Dump Detected",
                description=f"Possible credentials dump with {count} indicators",
                domain=domain,
                url=url,
                entities=entities
            )
        return None
    
    def check_internal_domain(self, content: str, domain: str = "", url: str = "") -> Optional[Alert]:
        """Verifie la presence de domaines internes."""
        for internal in self.internal_domains:
            if internal.lower() in content.lower():
                return self.create_alert(
                    severity=AlertSeverity.CRITICAL,
                    trigger='internal_domain_found',
                    title=f"?? Internal Domain Found: {internal}",
                    description=f"Internal domain '{internal}' mentioned on darknet",
                    domain=domain,
                    url=url,
                    entities={'internal_domain': internal}
                )
        return None
    
    def check_watchlist_domain(self, found_domain: str, url: str = "") -> Optional[Alert]:
        """Verifie si un domaine est dans la watchlist."""
        if found_domain in self.watchlist_domains:
            return self.create_alert(
                severity=AlertSeverity.HIGH,
                trigger='domain_in_watchlist',
                title=f"?? Watchlist Domain: {found_domain}",
                description=f"Monitored domain '{found_domain}' detected",
                domain=found_domain,
                url=url
            )
        return None
    
    def check_new_breach_site(self, site_type: str, title: str, 
                              domain: str = "", url: str = "") -> Optional[Alert]:
        """Verifie si c'est un nouveau site de breach."""
        if site_type == 'breach_market':
            return self.create_alert(
                severity=AlertSeverity.HIGH,
                trigger='new_breach_site',
                title=f"?? New Breach Site: {title[:50]}",
                description=f"New breach/leak site discovered: {title}",
                domain=domain,
                url=url,
                metadata={'site_type': site_type}
            )
        return None
    
    def check_high_risk_score(self, risk_score: float, 
                              domain: str = "", url: str = "") -> Optional[Alert]:
        """Verifie si le risk score est eleve."""
        threshold = AlertTriggers.MEDIUM_TRIGGERS['high_risk_score']['threshold']
        
        if risk_score >= threshold:
            return self.create_alert(
                severity=AlertSeverity.MEDIUM,
                trigger='high_risk_score',
                title=f"?? High Risk Score: {risk_score}",
                description=f"Page with risk score {risk_score}/100",
                domain=domain,
                url=url,
                metadata={'risk_score': risk_score}
            )
        return None
    
    def check_multiple_patterns(self, pattern_count: int,
                                domain: str = "", url: str = "") -> Optional[Alert]:
        """Verifie si plusieurs patterns sont detectes."""
        threshold = AlertTriggers.HIGH_TRIGGERS['multiple_patterns_same_domain']['threshold']
        
        if pattern_count >= threshold:
            return self.create_alert(
                severity=AlertSeverity.HIGH,
                trigger='multiple_patterns_same_domain',
                title=f"?? Multiple Patterns: {pattern_count} detected",
                description=f"{pattern_count} patterns detected on same domain",
                domain=domain,
                url=url,
                metadata={'pattern_count': pattern_count}
            )
        return None
    
    def run_all_checks(self, content: str, entities: Dict, 
                       site_type: str, risk_score: float,
                       domain: str = "", url: str = "", title: str = ""):
        """Execute tous les checks d'alertes."""
        alerts = []
        
        # Critical
        alert = self.check_ransomware(content, domain, url)
        if alert: alerts.append(alert)
        
        alert = self.check_credentials_dump(entities, domain, url)
        if alert: alerts.append(alert)
        
        alert = self.check_internal_domain(content, domain, url)
        if alert: alerts.append(alert)
        
        # High
        alert = self.check_watchlist_domain(domain, url)
        if alert: alerts.append(alert)
        
        alert = self.check_new_breach_site(site_type, title, domain, url)
        if alert: alerts.append(alert)
        
        entity_count = sum(len(v) if isinstance(v, list) else 1 for v in entities.values())
        alert = self.check_multiple_patterns(entity_count, domain, url)
        if alert: alerts.append(alert)
        
        # Medium
        alert = self.check_high_risk_score(risk_score, domain, url)
        if alert: alerts.append(alert)
        
        return alerts


# Instance globale
alert_manager = AlertManager()
