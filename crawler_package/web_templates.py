"""
Templates HTML pour le serveur web.
Separe pour une meilleure lisibilite du code.
"""

import html
import json
import math
from datetime import datetime
from typing import Dict, List, Any, Optional


def _render_simple_chart(labels: List[str], values: List[int]) -> str:
    """Genere un simple bar chart en HTML/CSS."""
    if not values:
        return '<p style="color:#888;">Pas de donnees</p>'
    
    max_val = max(values) if values else 1
    bars = ""
    for i, (label, val) in enumerate(zip(labels, values)):
        height = int((val / max_val) * 100) if max_val > 0 else 0
        bars += '<div style="display:inline-block;width:30px;margin:2px;text-align:center;">'
        bars += '<div style="height:' + str(height) + 'px;background:#00ff00;min-height:2px;"></div>'
        bars += '<div style="font-size:8px;color:#888;">' + str(label) + '</div>'
        bars += '</div>'
    
    return '<div style="height:120px;display:flex;align-items:flex-end;">' + bars + '</div>'


# Remplacer HTML_TEMPLATE
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Darknet Crawler v7.0</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Courier New', monospace; background: #0a0a0a; color: #00ff00; padding: 20px; min-height: 100vh; }}
        .container {{ max-width: 1800px; margin: 0 auto; }}
        h1 {{ color: #00ff00; text-align: center; margin-bottom: 20px; text-shadow: 0 0 10px #00ff00; font-size: 24px; }}
        .nav-tabs {{ display: flex; gap: 5px; margin-bottom: 20px; justify-content: center; flex-wrap: wrap; }}
        .nav-tab {{ padding: 6px 12px; background: #111; border: 1px solid #333; color: #888; cursor: pointer; border-radius: 4px; font-size: 11px; text-decoration: none; }}
        .nav-tab:hover, .nav-tab.active {{ background: #00ff00; color: #000; border-color: #00ff00; }}
        .nav-divider {{ border-left: 1px solid #333; margin: 0 5px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin-bottom: 20px; }}
        .stat-card {{ background: #111; border: 1px solid #00ff00; padding: 10px; text-align: center; border-radius: 4px; }}
        .stat-card h3 {{ color: #888; font-size: 9px; margin-bottom: 4px; }}
        .stat-card .value {{ font-size: 20px; color: #00ff00; }}
        .stat-card small {{ font-size: 9px; color: #666; }}
        .stat-card.alert {{ border-color: #ff4444; }} .stat-card.alert .value {{ color: #ff4444; }}
        .stat-card.warning {{ border-color: #ffaa00; }} .stat-card.warning .value {{ color: #ffaa00; }}
        .stat-card.info {{ border-color: #00aaff; }} .stat-card.info .value {{ color: #00aaff; }}
        .section {{ background: #111; border: 1px solid #333; margin-bottom: 15px; border-radius: 4px; }}
        .section-header {{ background: #1a1a1a; padding: 10px 12px; border-bottom: 1px solid #333; font-weight: bold; font-size: 12px; display: flex; justify-content: space-between; align-items: center; }}
        .section-content {{ padding: 12px; max-height: 300px; overflow-y: auto; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 6px 8px; text-align: left; border-bottom: 1px solid #222; font-size: 11px; }}
        th {{ color: #888; }}
        tr:hover {{ background: #1a1a1a; }}
        .tag {{ display: inline-block; padding: 2px 5px; border-radius: 3px; font-size: 9px; margin: 1px; }}
        .tag-secret {{ background: #ff4444; color: #fff; }}
        .tag-crypto {{ background: #9933ff; color: #fff; }}
        .tag-social {{ background: #00aaff; color: #fff; }}
        .tag-email {{ background: #ffaa00; color: #000; }}
        .url {{ color: #00ff00; word-break: break-all; font-size: 10px; }}
        .domain {{ color: #888; }}
        .title {{ color: #fff; }}
        .footer {{ text-align: center; padding: 15px; color: #444; font-size: 10px; }}
        .control-panel {{ background: #111; border: 1px solid #00ff00; border-radius: 4px; padding: 12px; margin-bottom: 15px; }}
        .control-panel h2 {{ color: #00ff00; margin-bottom: 10px; font-size: 13px; }}
        .control-panel.daemon {{ border-color: #9933ff; }} .control-panel.daemon h2 {{ color: #9933ff; }}
        .form-row {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: flex-end; }}
        .form-group {{ flex: 1; min-width: 120px; margin-bottom: 8px; }}
        .form-group label {{ display: block; color: #888; margin-bottom: 4px; font-size: 10px; }}
        .form-group input, .form-group textarea, .form-group select {{ width: 100%; padding: 6px; background: #0a0a0a; border: 1px solid #333; color: #00ff00; font-family: 'Courier New', monospace; border-radius: 3px; font-size: 11px; }}
        .form-group textarea {{ height: 50px; resize: vertical; }}
        .btn {{ padding: 6px 12px; border: none; border-radius: 3px; cursor: pointer; font-family: 'Courier New', monospace; font-weight: bold; font-size: 10px; margin-right: 4px; margin-bottom: 4px; }}
        .btn-primary {{ background: #00ff00; color: #000; }}
        .btn-primary:hover {{ background: #00cc00; }}
        .btn-warning {{ background: #ffaa00; color: #000; }}
        .btn-danger {{ background: #ff4444; color: #fff; }}
        .btn-purple {{ background: #9933ff; color: #fff; }}
        .btn-small {{ padding: 3px 6px; font-size: 9px; }}
        .btn-copy {{ background: #333; color: #00ff00; border: 1px solid #00ff00; }}
        .btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
        .message {{ padding: 6px; border-radius: 3px; margin-bottom: 10px; display: none; font-size: 11px; }}
        .message.success {{ background: #1a3a1a; border: 1px solid #00ff00; color: #00ff00; display: block; }}
        .message.error {{ background: #3a1a1a; border: 1px solid #ff4444; color: #ff4444; display: block; }}
        .grid-2 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; }}
        .trust-high {{ color: #00ff00; }}
        .trust-medium {{ color: #ffaa00; }}
        .trust-low {{ color: #ff4444; }}
        .trust-score {{ display: inline-block; padding: 2px 6px; border-radius: 8px; font-size: 10px; font-weight: bold; }}
        .changelog {{ background: #0a0a0a; border: 1px solid #333; border-radius: 4px; padding: 10px; white-space: pre-wrap; font-size: 10px; color: #888; max-height: 180px; overflow-y: auto; }}
        .loading {{ display: inline-block; width: 14px; height: 14px; border: 2px solid #333; border-top-color: #00ff00; border-radius: 50%; animation: spin 1s linear infinite; }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
        .daemon-status {{ display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 10px; font-weight: bold; }}
        .daemon-status.active {{ background: #00ff00; color: #000; }}
        .daemon-status.inactive {{ background: #ff4444; color: #fff; }}
        .daemon-status.not-installed {{ background: #666; color: #fff; }}
        .log-viewer {{ background: #000; border: 1px solid #333; border-radius: 4px; padding: 10px; font-family: monospace; font-size: 9px; color: #00ff00; max-height: 200px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; }}
        .info-box {{ background: #1a1a2a; border: 1px solid #9933ff; border-radius: 4px; padding: 10px; margin-bottom: 12px; }}
        .info-box p {{ color: #888; font-size: 10px; margin-bottom: 4px; }}
        .info-box code {{ background: #0a0a0a; padding: 2px 5px; border-radius: 3px; color: #00ff00; font-size: 10px; }}
        .risk-high {{ color: #ff4444; font-weight: bold; }}
        .risk-medium {{ color: #ffaa00; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Darknet Crawler v{version}</h1>
        <div class="nav-tabs">
            <a href="/" class="nav-tab {nav_dashboard}">Dashboard</a>
            <a href="/intel" class="nav-tab">Intel</a>
            <a href="/search" class="nav-tab {nav_search}">Recherche</a>
            <span class="nav-divider"></span>
            <a href="/queue" class="nav-tab">Queue</a>
            <a href="/domains" class="nav-tab">Domaines</a>
            <a href="/trusted" class="nav-tab {nav_trusted}">Sites</a>
            <span class="nav-divider"></span>
            <a href="/entities" class="nav-tab">OSINT</a>
            <a href="/monitoring" class="nav-tab">Monitoring</a>
            <a href="/alerts" class="nav-tab">Alertes</a>
            <span class="nav-divider"></span>
            <a href="/export" class="nav-tab">Export</a>
            <a href="/settings" class="nav-tab">Config</a>
            <a href="/security" class="nav-tab">Securite</a>
            <a href="/updates" class="nav-tab {nav_updates}">Systeme</a>
        </div>
        {update_banner}
        {page_content}
        <div class="footer">Darknet Omniscient Crawler v{version} | Port {port}</div>
    </div>
    <script>
        function copyToClipboard(text) {{ navigator.clipboard.writeText(text); }}
        function showMessage(text, type) {{
            var msg = document.getElementById('message');
            if (msg) {{ msg.textContent = text; msg.className = 'message ' + type; setTimeout(function() {{ msg.className = 'message'; }}, 5000); }}
        }}
        function addSeeds() {{
            var urls = document.getElementById('seedUrls').value.trim().split('\\n').filter(function(u) {{ return u.trim(); }});
            if (urls.length === 0) {{ showMessage('Entrez au moins une URL', 'error'); return; }}
            fetch('/api/add-seeds', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ urls: urls }}) }})
            .then(function(r) {{ return r.json(); }}).then(function(data) {{ showMessage(data.message, data.success ? 'success' : 'error'); if (data.success) document.getElementById('seedUrls').value = ''; }});
        }}
        function checkUpdates() {{
            var btn = document.getElementById('checkUpdateBtn'); var status = document.getElementById('updateStatus');
            if (btn) btn.disabled = true; if (status) status.innerHTML = '<span class="loading"></span> Verification...';
            fetch('/api/check-updates', {{ method: 'POST' }}).then(function(r) {{ return r.json(); }}).then(function(data) {{
                if (btn) btn.disabled = false;
                if (status) {{ if (data.update_available) {{ status.innerHTML = '<span style="color: #ff4444;">Mise a jour: v' + data.latest_version + '</span>'; }} else if (data.error) {{ status.innerHTML = '<span style="color: #ff4444;">Erreur: ' + data.error + '</span>'; }} else {{ status.innerHTML = '<span style="color: #00ff00;">A jour!</span>'; }} }}
            }});
        }}
        function performUpdate() {{
            if (!confirm('Mettre a jour?')) return;
            var btn = document.getElementById('updateBtn'); var status = document.getElementById('updateResult');
            if (btn) btn.disabled = true; if (status) status.innerHTML = '<span class="loading"></span> MAJ...';
            fetch('/api/perform-update', {{ method: 'POST' }}).then(function(r) {{ return r.json(); }}).then(function(data) {{
                if (btn) btn.disabled = false;
                if (status) {{ status.innerHTML = '<span style="color: ' + (data.success ? '#00ff00' : '#ff4444') + ';">' + data.message + '</span>'; }}
            }});
        }}
        function installDaemon() {{
            var port = document.getElementById('daemonPort').value || 4587;
            var workers = document.getElementById('daemonWorkers').value || 15;
            if (!confirm('Installer comme service?')) return;
            var btn = document.getElementById('installDaemonBtn'); var status = document.getElementById('daemonResult');
            if (btn) btn.disabled = true; if (status) status.innerHTML = '<span class="loading"></span> Installation...';
            fetch('/api/daemon-install', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ web_port: parseInt(port), workers: parseInt(workers) }}) }})
            .then(function(r) {{ return r.json(); }}).then(function(data) {{ if (btn) btn.disabled = false; if (status) status.innerHTML = '<span style="color: ' + (data.success ? '#00ff00' : '#ff4444') + ';">' + data.message + '</span>'; if (data.success) setTimeout(function() {{ location.reload(); }}, 2000); }});
        }}
        function uninstallDaemon() {{ if (!confirm('Desinstaller?')) return; fetch('/api/daemon-uninstall', {{ method: 'POST' }}).then(function(r) {{ return r.json(); }}).then(function(data) {{ document.getElementById('daemonResult').innerHTML = '<span style="color: ' + (data.success ? '#00ff00' : '#ff4444') + ';">' + data.message + '</span>'; if (data.success) setTimeout(function() {{ location.reload(); }}, 2000); }}); }}
        function controlDaemon(action) {{ var status = document.getElementById('daemonResult'); if (status) status.innerHTML = '<span class="loading"></span>'; fetch('/api/daemon-control', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ action: action }}) }}).then(function(r) {{ return r.json(); }}).then(function(data) {{ if (status) status.innerHTML = '<span style="color: ' + (data.success ? '#00ff00' : '#ff4444') + ';">' + data.message + '</span>'; setTimeout(function() {{ location.reload(); }}, 1500); }}); }}
        function refreshLogs() {{ var log = document.getElementById('daemonLogs'); if (!log) return; fetch('/api/daemon-logs?lines=50').then(function(r) {{ return r.json(); }}).then(function(data) {{ if (data.logs) log.textContent = data.logs; }}); }}
        if (window.location.pathname === '/') setTimeout(function() {{ location.reload(); }}, 30000);
    </script>
</body>
</html>'''


def _get_update_banner(update_status: Dict[str, Any]) -> str:
    """Genere la banniere de mise a jour si disponible."""
    if not update_status or not update_status.get('update_available'):
        return ''
    latest = update_status.get('latest_version', '?')
    return f'''<div class="update-banner"><span>Nouvelle version disponible: <strong>v{html.escape(str(latest))}</strong></span><a href="/updates" class="btn btn-primary">Voir</a></div>'''


def render_dashboard(data: Dict[str, Any], port: int, update_status: Dict[str, Any] = None) -> str:
    """Genere la page dashboard."""
    version = update_status.get('current_version', '6.4.0') if update_status else '6.4.0'
    update_banner = _get_update_banner(update_status)
    nav_updates_class = 'update-available' if update_status and update_status.get('update_available') else ''
    
    intel_rows_html = ""
    for row in data['intel_rows']:
        tags = []
        try:
            if row.get('secrets_found', '{}') != '{}': tags.append('<span class="tag tag-secret">SECRET</span>')
            if row.get('cryptos', '{}') != '{}':
                for coin in list(json.loads(row['cryptos']).keys())[:2]: tags.append(f'<span class="tag tag-crypto">{html.escape(coin)}</span>')
            if row.get('socials', '{}') != '{}': tags.append('<span class="tag tag-social">SOCIAL</span>')
            if row.get('emails', '[]') != '[]':
                emails = json.loads(row['emails'])
                if emails: tags.append(f'<span class="tag tag-email">{len(emails)}</span>')
        except: pass
        intel_rows_html += f'<tr><td class="domain">{html.escape(str(row.get("domain", ""))[:25])}</td><td class="title">{html.escape(str(row.get("title", ""))[:35])}</td><td>{"".join(tags)}</td></tr>'
    
    recent_rows_html = "".join([f'<tr><td style="color: {"#00ff00" if row.get("status", 0) == 200 else "#ff4444"}">{row.get("status", 0)}</td><td class="url">{html.escape(str(row.get("url", ""))[:70])}</td><td class="title">{html.escape(str(row.get("title", ""))[:30])}</td></tr>' for row in data['recent_rows']])
    domain_rows_html = "".join([f'<tr><td class="domain">{html.escape(str(row.get("domain", ""))[:35])}</td><td>{row.get("pages", 0)}</td><td style="color: #00ff00">{row.get("success", 0)}</td></tr>' for row in data['domain_rows']])
    
    success_rate = round((data['success_urls'] / data['total_urls'] * 100) if data['total_urls'] > 0 else 0, 1)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    page_content = f'''
    <p class="refresh-info">{timestamp} | <button class="btn btn-primary" onclick="location.reload()" style="padding: 3px 10px;">Refresh</button></p>
    <div id="message" class="message"></div>
    <div class="stats-grid">
        <div class="stat-card"><h3>STATUS</h3><div class="value {"status-running" if data["status"] == "RUNNING" else "status-stopped"}">{data["status"]}</div></div>
        <div class="stat-card"><h3>URLS CRAWLEES</h3><div class="value">{data["total_urls"]}</div></div>
        <div class="stat-card info"><h3>SUCCES (200)</h3><div class="value>{data["success_urls"]}</div></div>
        <div class="stat-card"><h3>DOMAINES</h3><div class="value">{data["domains"]}</div></div>
        <div class="stat-card warning"><h3>EN QUEUE</h3><div class="value>{data["queue_size"]}</div></div>
        <div class="stat-card alert"><h3>INTEL</h3><div class="value>{data["intel_count"]}</div></div>
    </div>
    <div class="control-panel"><h2>Ajouter des Sites a Explorer</h2>
        <div class="form-row">
            <div class="form-group" style="flex: 2;"><label>URLs .onion (une par ligne)</label><textarea id="seedUrls" placeholder="http://exemple.onion/"></textarea></div>
            <div class="form-group" style="flex: 1;"><button class="btn btn-primary" onclick="addSeeds()">Ajouter</button><button class="btn btn-warning" onclick="refreshLinks()">Extraire liens</button></div>
        </div>
    </div>
    <div class="grid-2">
        <div class="section"><div class="section-header">Dernieres Intel</div><div class="section-content"><table><thead><tr><th>Domaine</th><th>Titre</th><th>Tags</th></tr></thead><tbody>{intel_rows_html or "<tr><td colspan='3'>Aucune donnee</td></tr>"}</tbody></table></div></div>
        <div class="section"><div class="section-header">Top Domaines</div><div class="section-content"><table><thead><tr><th>Domaine</th><th>Pages</th><th>OK</th></tr></thead><tbody>{domain_rows_html or "<tr><td colspan='3'>Aucune donnee</td></tr>"}</tbody></table></div></div>
    </div>
    <div class="section"><div class="section-header">Dernieres URLs</div><div class="section-content"><table><thead><tr><th>Status</th><th>URL</th><th>Titre</th></tr></thead><tbody>{recent_rows_html or "<tr><td colspan='3'>Aucune donnee</td></tr>"}</tbody></table></div></div>
    <div class="stats-grid">
        <div class="stat-card"><h3>Taux Succes</h3><div class="value" style="font-size: 24px;">{success_rate}%</div></div>
        <div class="stat-card"><h3>Emails</h3><div class="value" style="font-size: 24px;">{data["total_emails"]}</div></div>
        <div class="stat-card"><h3>Crypto</h3><div class="value" style="font-size: 24px;">{data["total_cryptos"]}</div></div>
        <div class="stat-card"><h3>Social</h3><div class="value" style="font-size: 24px;">{data["total_socials"]}</div></div>
    </div>'''
    
    return HTML_TEMPLATE.format(page_content=page_content, port=port, version=version, update_banner=update_banner,
        nav_dashboard='active', nav_search='', nav_trusted='', nav_updates=nav_updates_class)


def render_search(results: List[Dict], query: str, filter_type: str, port: int, update_status: Dict[str, Any] = None) -> str:
    """Genere la page de recherche."""
    version = update_status.get('current_version', '6.4.0') if update_status else '6.4.0'
    nav_updates_class = 'update-available' if update_status and update_status.get('update_available') else ''
    
    search_results_html = ""
    for r in results:
        tags = []
        try:
            if r.get('secrets_found', '{}') != '{}': tags.append('<span class="tag tag-secret">SECRET</span>')
            if r.get('cryptos', '{}') != '{}':
                for coin in list(json.loads(r['cryptos']).keys())[:3]: tags.append(f'<span class="tag tag-crypto">{html.escape(coin)}</span>')
            if r.get('socials', '{}') != '{}': tags.append('<span class="tag tag-social">SOCIAL</span>')
            if r.get('emails', '[]') != '[]': tags.append(f'<span class="tag tag-email">{len(json.loads(r["emails"]))} emails</span>')
        except: pass
        search_results_html += f'''<div class="search-result"><div class="search-result-title">{html.escape(str(r.get("title", "Sans titre"))[:100])}</div><div class="search-result-url">{html.escape(str(r.get("url", ""))[:100])}</div><div class="search-result-meta"><span class="domain">{html.escape(str(r.get("domain", ""))[:40])}</span>{"".join(tags)}<button class="btn btn-copy btn-small" onclick="copyToClipboard('{html.escape(r.get("url", ""))}')">Copier</button></div></div>'''
    
    if not search_results_html:
        search_results_html = '<div style="color: #888; text-align: center; padding: 40px;">Entrez une recherche ou selectionnez un filtre</div>'
    
    page_content = f'''
    <div class="control-panel"><h2>Rechercher dans la Base de Donnees</h2>
        <form method="GET" action="/search"><div class="form-row">
            <div class="form-group" style="flex: 3;"><label>Recherche (titre, domaine, URL)</label><input type="text" name="q" value="{html.escape(query)}" placeholder="Entrez votre recherche..."></div>
            <div class="form-group" style="flex: 1;"><label>Filtrer par</label><select name="filter"><option value="all" {'selected' if filter_type == 'all' else ''}>Tout</option><option value="crypto" {'selected' if filter_type == 'crypto' else ''}>Crypto</option><option value="social" {'selected' if filter_type == 'social' else ''}>Social</option><option value="email" {'selected' if filter_type == 'email' else ''}>Emails</option><option value="secret" {'selected' if filter_type == 'secret' else ''}>Secrets</option></select></div>
            <div class="form-group" style="flex: 0;"><button type="submit" class="btn btn-primary">Rechercher</button></div>
        </div></form>
    </div>
    <div class="section"><div class="section-header">Resultats ({len(results)})</div><div class="section-content" style="max-height: none;">{search_results_html}</div></div>'''
    
    return HTML_TEMPLATE.format(page_content=page_content, port=port, version=version, update_banner='',
        nav_dashboard='', nav_search='active', nav_trusted='', nav_updates=nav_updates_class)


def render_trusted(data: Dict[str, Any], port: int, update_status: Dict[str, Any] = None) -> str:
    """Genere la page des sites fiables."""
    version = update_status.get('current_version', '6.4.0') if update_status else '6.4.0'
    nav_updates_class = 'update-available' if update_status and update_status.get('update_available') else ''
    
    trusted_html = ""
    for site in data['sites'][:12]:
        trust_class = f"trust-{site['trust_level']}"
        trusted_html += f'''<div class="search-result"><div class="search-result-title"><span class="trust-score {trust_class}">{site["score"]}</span> {html.escape(str(site.get("domain", ""))[:50])}</div><div class="search-result-url">{html.escape(str(site.get("title", ""))[:80])}</div><div class="search-result-meta"><span>{site["total_pages"]} pages</span><span style="color: #00ff00">{site["success_rate"]}% succes</span>{"<span class='tag tag-secret'>INTEL</span>" if site["has_intel"] else ""}<button class="btn btn-copy btn-small" onclick="copyToClipboard('http://{html.escape(site.get("domain", ""))}/')">Copier</button></div></div>'''
    
    domain_table_html = ""
    for site in data['sites']:
        trust_class = f"trust-{site['trust_level']}"
        domain_table_html += f'<tr><td class="domain">{html.escape(str(site.get("domain", ""))[:40])}</td><td><span class="trust-score {trust_class}">{site["score"]}</span></td><td>{site["total_pages"]}</td><td style="color: #00ff00">{site["success_rate"]}%</td><td>{"Y" if site["has_intel"] else "-"}</td></tr>'
    
    page_content = f'''
    <div class="stats-grid">
        <div class="stat-card"><h3>SITES ANALYSES</h3><div class="value">{data['total']}</div></div>
        <div class="stat-card info"><h3>HAUTE CONFIANCE</h3><div class="value">{data['high_trust']}</div></div>
        <div class="stat-card warning"><h3>CONFIANCE MOYENNE</h3><div class="value">{data['medium_trust']}</div></div>
        <div class="stat-card alert"><h3>FAIBLE CONFIANCE</h3><div class="value>{data['low_trust']}</div></div>
    </div>
    <div class="section"><div class="section-header">Sites les Plus Fiables</div><div class="section-content" style="max-height: none;"><p style="color: #888; margin-bottom: 15px; font-size: 11px;">Score calcule selon: pages crawlees, taux de succes, presence de donnees structurees.</p>{trusted_html or '<div style="color:#888;">Aucun site analyse</div>'}</div></div>
    <div class="section"><div class="section-header">Tous les Domaines Classes</div><div class="section-content" style="max-height: 500px;"><table><thead><tr><th>Domaine</th><th>Score</th><th>Pages</th><th>Succes</th><th>Intel</th></tr></thead><tbody>{domain_table_html or '<tr><td colspan="5">Aucune donnee</td></tr>'}</tbody></table></div></div>'''
    
    return HTML_TEMPLATE.format(page_content=page_content, port=port, version=version, update_banner='',
        nav_dashboard='', nav_search='', nav_trusted='active', nav_updates=nav_updates_class)


def render_updates(update_status: Dict[str, Any], daemon_status: Dict[str, Any], port: int) -> str:
    """Genere la page systeme (mises a jour + daemon)."""
    version = update_status.get('current_version', '6.4.0')
    latest_raw = update_status.get('latest_version')
    # Afficher la version actuelle si pas de version distante
    latest = latest_raw if latest_raw and latest_raw != 'None' and latest_raw != 'N/A' else version
    update_available = update_status.get('update_available', False)
    commits_behind = update_status.get('commits_behind', 0)
    changelog = update_status.get('changelog', '')
    recent_commits = update_status.get('recent_commits', [])
    error = update_status.get('error')
    
    # Daemon status
    daemon_installed = daemon_status.get('installed', False)
    daemon_active = daemon_status.get('active', False)
    daemon_enabled = daemon_status.get('enabled', False)
    systemd_available = daemon_status.get('systemd_available', False)
    daemon_logs = daemon_status.get('recent_logs', '')
    daemon_user = html.escape(daemon_status.get('user', 'ubuntu'))
    
    # Daemon status badge
    if not systemd_available:
        daemon_badge = '<span class="daemon-status not-installed">Systemd non disponible</span>'
    elif not daemon_installed:
        daemon_badge = '<span class="daemon-status not-installed">Non installe</span>'
    elif daemon_active:
        daemon_badge = '<span class="daemon-status active">Actif</span>'
    else:
        daemon_badge = '<span class="daemon-status inactive">Arrete</span>'
    
    # Commits
    commits_html = ""
    for commit in recent_commits[:5]:
        date_str = commit.get("date", "")
        if date_str and len(date_str) >= 10:
            date_str = date_str[:10]
        commits_html += '<li><span class="commit-sha">' + html.escape(str(commit.get("sha", ""))) + '</span> <span class="commit-date">' + html.escape(date_str) + '</span><br>' + html.escape(str(commit.get("message", ""))) + '</li>'
    if not commits_html:
        commits_html = '<li style="color: #888;">Utilisez "Verifier" pour charger les commits</li>'
    
    # Update status card
    if error:
        update_status_html = '<div class="stat-card warning"><h3>STATUT</h3><div class="value" style="font-size: 12px;">Cliquez Verifier</div></div>'
    elif update_available:
        if commits_behind > 0:
            update_status_html = '<div class="stat-card alert"><h3>EN RETARD</h3><div class="value" style="font-size: 18px;">' + str(commits_behind) + ' commit(s)</div></div>'
        else:
            update_status_html = '<div class="stat-card alert"><h3>MISE A JOUR</h3><div class="value" style="font-size: 18px;"> Disponible</div></div>'
    else:
        update_status_html = '<div class="stat-card info"><h3>STATUT</h3><div class="value" style="font-size: 18px;">A jour</div></div>'
    
    # Daemon controls
    if daemon_installed:
        start_disabled = 'disabled' if daemon_active else ''
        stop_disabled = 'disabled' if not daemon_active else ''
        daemon_controls = '<button class="btn btn-primary" onclick="controlDaemon(\'start\')" ' + start_disabled + '>Demarrer</button>'
        daemon_controls += '<button class="btn btn-warning" onclick="controlDaemon(\'stop\')" ' + stop_disabled + '>Arreter</button>'
        daemon_controls += '<button class="btn btn-purple" onclick="controlDaemon(\'restart\')">Redemarrer</button>'
        daemon_controls += '<button class="btn btn-danger" onclick="uninstallDaemon()">Desinstaller</button>'
    else:
        daemon_controls = '<button id="installDaemonBtn" class="btn btn-purple" onclick="installDaemon()">Installer comme Service</button>'
    
    # Port/Workers form (only if not installed)
    port_workers_form = ""
    if not daemon_installed:
        port_workers_form = '''
        <div class="form-row">
            <div class="form-group" style="flex: 1;">
                <label>Port Web</label>
                <input type="number" id="daemonPort" value="4587" min="1024" max="65535">
            </div>
            <div class="form-group" style="flex: 1;">
                <label>Workers</label>
                <input type="number" id="daemonWorkers" value="15" min="1" max="50">
            </div>
        </div>'''
    
    # Auto-start info
    autostart_info = ""
    if daemon_installed:
        autostart_text = "Oui" if daemon_enabled else "Non"
        autostart_info = '<p style="margin-top: 10px; color: #888; font-size: 11px;">Auto-start: ' + autostart_text + '</p>'
    
    # Logs section
    logs_section = ""
    if daemon_installed:
        logs_content = html.escape(daemon_logs) if daemon_logs else "Aucun log disponible"
        logs_section = '''
    <div class="section">
        <div class="section-header"><span>Logs du Service</span><button class="btn btn-small btn-primary" onclick="refreshLogs()">Actualiser</button></div>
        <div class="section-content" style="max-height: none;">
            <div class="log-viewer" id="daemonLogs">''' + logs_content + '''</div>
        </div>
    </div>'''
    
    # Changelog section
    changelog_content = '<div class="changelog">' + html.escape(changelog) + '</div>' if changelog else '<p style="color: #888;">Aucune note disponible</p>'
    
    page_content = '''
    <div id="message" class="message"></div>
    
    <div class="stats-grid">
        <div class="stat-card"><h3>VERSION</h3><div class="value" style="font-size: 22px;">v''' + html.escape(version) + '''</div></div>
        <div class="stat-card"><h3>DISTANTE</h3><div class="value" style="font-size: 22px;">v''' + html.escape(str(latest)) + '''</div></div>
        ''' + update_status_html + '''
        <div class="stat-card"><h3>SERVICE</h3><div class="value" style="font-size: 14px;">''' + daemon_badge + '''</div></div>
    </div>
    
    <!-- Section Daemon -->
    <div class="control-panel daemon">
        <h2>Installation comme Service (Daemon)</h2>
        <div class="info-box">
            <p>Installez le crawler comme service systemd pour qu'il demarre automatiquement au boot du serveur.</p>
            <p>Service: <code>crawler-onion</code> | Utilisateur: <code>''' + daemon_user + '''</code></p>
        </div>
        ''' + port_workers_form + '''
        <div class="form-row">
            <div class="form-group">
                ''' + daemon_controls + '''
            </div>
        </div>
        <div id="daemonResult" style="margin-top: 10px;"></div>
        ''' + autostart_info + '''
    </div>
    ''' + logs_section + '''
    
    <!-- Section Mises a jour -->
    <div class="control-panel">
        <h2>Mises a Jour (via Git)</h2>
        <div class="info-box">
            <p>Le systeme de mise a jour utilise <code>git pull</code> pour recuperer les dernieres modifications.</p>
            <p>Repository: <code>github.com/ahottois/crawler-onion</code></p>
        </div>
        <div class="form-row">
            <div class="form-group">
                <button id="checkUpdateBtn" class="btn btn-primary" onclick="checkUpdates()">Verifier les mises a jour</button>
                <button id="updateBtn" class="btn btn-danger" onclick="performUpdate()">Mettre a jour maintenant</button>
            </div>
        </div>
        <div id="updateStatus" style="margin-top: 10px; color: #888;"></div>
        <div id="updateResult" style="margin-top: 10px;"></div>
    </div>
    
    <div class="grid-2">
        <div class="section">
            <div class="section-header">Notes de version</div>
            <div class="section-content" style="max-height: none;">
                ''' + changelog_content + '''
            </div>
        </div>
        <div class="section">
            <div class="section-header">Commits recents</div>
            <div class="section-content" style="max-height: none;"><ul class="commit-list">''' + commits_html + '''</ul></div>
        </div>
    </div>
    
    <div class="section">
        <div class="section-header">Commandes utiles</div>
        <div class="section-content" style="max-height: none;">
            <div class="changelog"># Mise a jour manuelle
cd ~/crawler-onion && git pull && pip install -r requirements.txt

# Controle du service
sudo systemctl status crawler-onion
sudo systemctl restart crawler-onion
sudo journalctl -u crawler-onion -f

# Voir les logs en temps reel
tail -f ~/crawler-onion/crawler.log</div>
        </div>
    </div>'''
    
    return HTML_TEMPLATE.format(page_content=page_content, port=port, version=version, update_banner='',
        nav_dashboard='', nav_search='', nav_trusted='', nav_updates='active')


def render_intel_list(data: Dict, filters: Dict, port: int) -> str:
    """Page Intel avec pagination et filtres."""
    version = "7.0.0"
    
    results = data.get('results', [])
    total = data.get('total', 0)
    page = data.get('page', 1)
    total_pages = data.get('total_pages', 1)
    
    # Filtres actifs
    time_filter = filters.get('time_range', '')
    type_filter = filters.get('intel_type', '')
    risk_filter = filters.get('min_risk', 0)
    
    rows_html = ""
    for item in results:
        tags = []
        if item.get('secrets_found'):
            tags.append('<span class="tag tag-secret">SECRET</span>')
        if item.get('cryptos'):
            for coin in list(item['cryptos'].keys())[:2]:
                tags.append('<span class="tag tag-crypto">' + html.escape(coin) + '</span>')
        if item.get('emails'):
            tags.append('<span class="tag tag-email">' + str(len(item['emails'])) + ' emails</span>')
        if item.get('socials'):
            tags.append('<span class="tag tag-social">SOCIAL</span>')
        
        risk_class = 'risk-high' if item.get('risk_score', 0) >= 70 else ('risk-medium' if item.get('risk_score', 0) >= 40 else '')
        important_icon = '&#9733;' if item.get('marked_important') else '';
        
        rows_html += '<tr class="intel-row" onclick="showDetail(\'' + html.escape(item.get('url', '')) + '\')">'
        rows_html += '<td class="domain">' + important_icon + html.escape(str(item.get('domain', ''))[:30]) + '</td>'
        rows_html += '<td class="title">' + html.escape(str(item.get('title', ''))[:40]) + '</td>'
        rows_html += '<td>' + ''.join(tags) + '</td>'
        rows_html += '<td class="' + risk_class + '">' + str(item.get('risk_score', 0)) + '</td>'
        rows_html += '<td>' + html.escape(str(item.get('found_at', ''))[:10]) + '</td>'
        rows_html += '</tr>'
    
    if not rows_html:
        rows_html = '<tr><td colspan="5" style="color: #888; text-align: center;">Aucun resultat</td></tr>'
    
    # Pagination
    pagination_html = '<div class="pagination">'
    if page > 1:
        pagination_html += '<a href="?page=' + str(page-1) + '" class="btn btn-small">Precedent</a>'
    pagination_html += '<span>Page ' + str(page) + ' / ' + str(total_pages) + ' (' + str(total) + ' resultats)</span>'
    if page < total_pages:
        pagination_html += '<a href="?page=' + str(page+1) + '" class="btn btn-small">Suivant</a>'
    pagination_html += '</div>'
    
    page_content = '''
    <div id="message" class="message"></div>
    
    <div class="control-panel">
        <h2>Filtres Intel</h2>
        <form method="GET" action="/intel">
            <div class="form-row">
                <div class="form-group">
                    <label>Periode</label>
                    <select name="time">
                        <option value="">Tout</option>
                        <option value="hour" ''' + ('selected' if time_filter == 'hour' else '') + '''>Derniere heure</option>
                        <option value="day" ''' + ('selected' if time_filter == 'day' else '') + '''>Dernier jour</option>
                        <option value="week" ''' + ('selected' if time_filter == 'week' else '') + '''>Derniere semaine</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Type</label>
                    <select name="type">
                        <option value="">Tous</option>
                        <option value="crypto" ''' + ('selected' if type_filter == 'crypto' else '') + '''>Crypto</option>
                        <option value="email" ''' + ('selected' if type_filter == 'email' else '') + '''>Emails</option>
                        <option value="secret" ''' + ('selected' if type_filter == 'secret' else '') + '''>Secrets</option>
                        <option value="social" ''' + ('selected' if type_filter == 'social' else '') + '''>Social</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Risque min</label>
                    <input type="number" name="risk" value="''' + str(risk_filter or '') + '''" min="0" max="100" placeholder="0">
                </div>
                <div class="form-group" style="flex: 0;">
                    <button type="submit" class="btn btn-primary">Filtrer</button>
                </div>
            </div>
        </form>
    </div>
    
    ''' + pagination_html + '''
    
    <div class="section">
        <div class="section-header">Intel (''' + str(total) + ''')</div>
        <div class="section-content" style="max-height: none;">
            <table>
                <thead>
                    <tr><th>Domaine</th><th>Titre</th><th>Tags</th><th>Risk</th><th>Date</th></tr>
                </thead>
                <tbody>''' + rows_html + '''</tbody>
            </table>
        </div>
    </div>
    
    ''' + pagination_html + '''
    
    <script>
    function showDetail(url) {
        window.location.href = '/intel/detail?url=' + encodeURIComponent(url);
    }
    </script>
    
    <style>
    .intel-row { cursor: pointer; }
    .intel-row:hover { background: #1a2a1a; }
    .risk-high { color: #ff4444; font-weight: bold; }
    .risk-medium { color: #ffaa00; }
    .pagination { display: flex; justify-content: center; gap: 20px; align-items: center; margin: 15px 0; }
    </style>'''
    
    return HTML_TEMPLATE.format(page_content=page_content, port=port, version=version, update_banner='',
        nav_dashboard='', nav_search='', nav_trusted='', nav_updates='')


def render_intel_detail(item: Optional[Dict], port: int) -> str:
    """Detail d'un item intel."""
    version = "7.0.0"
    
    if not item:
        page_content = '<div style="color: #ff4444; text-align: center; padding: 40px;">Item non trouve</div>'
        return HTML_TEMPLATE.format(page_content=page_content, port=port, version=version, update_banner='',
            nav_dashboard='', nav_search='', nav_trusted='', nav_updates='')
    
    # Secrets
    secrets_html = ""
    for secret_type, values in item.get('secrets_found', {}).items():
        secrets_html += '<div class="secret-block">'
        secrets_html += '<h4 class="tag tag-secret">' + html.escape(secret_type) + '</h4>'
        for val in values[:5]:
            secrets_html += '<code class="secret-value">' + html.escape(str(val)[:100]) + '</code>'
        secrets_html += '</div>'
    
    # Crypto
    crypto_html = ""
    for coin, addrs in item.get('cryptos', {}).items():
        crypto_html += '<div class="crypto-block">'
        crypto_html += '<h4 class="tag tag-crypto">' + html.escape(coin) + ' (' + str(len(addrs)) + ')</h4>'
        for addr in addrs[:5]:
            crypto_html += '<code class="crypto-addr">' + html.escape(addr) + '</code>'
        crypto_html += '</div>'
    
    # Emails
    emails_html = ""
    for email in item.get('emails', [])[:20]:
        emails_html += '<span class="email-item">' + html.escape(email) + '</span>'
    
    # Socials
    socials_html = ""
    for network, handles in item.get('socials', {}).items():
        for handle in handles[:5]:
            socials_html += '<span class="social-item">' + html.escape(network) + ': ' + html.escape(handle) + '</span>'
    
    # Entites
    entities_html = ""
    for entity in item.get('entities', [])[:20]:
        entities_html += '<tr><td>' + html.escape(entity.get('entity_type', '')) + '</td>'
        entities_html += '<td>' + html.escape(str(entity.get('value', ''))[:50]) + '</td></tr>'
    
    important_btn = 'btn-warning' if item.get('marked_important') else 'btn-primary'
    fp_btn = 'btn-danger' if item.get('marked_false_positive') else 'btn-primary'
    url_escaped = html.escape(item.get('url', ''))
    
    page_content = '''
    <div class="control-panel">
        <h2>''' + html.escape(str(item.get('title', 'Sans titre'))[:80]) + '''</h2>
        <p class="url" style="word-break: break-all;">''' + url_escaped + '''</p>
        <p style="color: #888;">Domaine: <strong>''' + html.escape(item.get('domain', '')) + '''</strong> | 
           Risk: <span class="''' + ('risk-high' if item.get('risk_score', 0) >= 70 else '') + '''">''' + str(item.get('risk_score', 0)) + '''</span> |
           Categorie: ''' + html.escape(item.get('category', '-') or '-') + ''' |
           Langue: ''' + html.escape(item.get('language', '-') or '-') + '''</p>
        
        <div class="form-row" style="margin-top: 15px;">
            <button class="btn ''' + important_btn + '''" onclick="markIntel('important')">''' + ('Important &#9733;' if item.get('marked_important') else 'Marquer Important') + '''</button>
            <button class="btn ''' + fp_btn + '''" onclick="markIntel('false_positive')">''' + ('Faux Positif &#10003;' if item.get('marked_false_positive') else 'Faux Positif') + '''</button>
        </div>
    </div>
    
    <div class="grid-2">
        <div class="section">
            <div class="section-header">Secrets Trouves</div>
            <div class="section-content" style="max-height: none;">
                ''' + (secrets_html or '<p style="color: #888;">Aucun secret</p>') + '''
            </div>
        </div>
        
        <div class="section">
            <div class="section-header">Adresses Crypto</div>
            <div class="section-content" style="max-height: none;">
                ''' + (crypto_html or '<p style="color: #888;">Aucune adresse</p>') + '''
            </div>
        </div>
    </div>
    
    <div class="grid-2">
        <div class="section">
            <div class="section-header">Emails (''' + str(len(item.get('emails', []))) + ''')</div>
            <div class="section-content">
                <div class="tags-container">''' + (emails_html or '<p style="color: #888;">Aucun</p>') + '''</div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-header">Liens Sociaux</div>
            <div class="section-content">
                <div class="tags-container">''' + (socials_html or '<p style="color: #888;">Aucun</p>') + '''</div>
            </div>
        </div>
    </div>
    
    <div class="section">
        <div class="section-header">Entites Extraites</div>
        <div class="section-content">
            <table>
                <thead><tr><th>Type</th><th>Valeur</th></tr></thead>
                <tbody>''' + (entities_html or '<tr><td colspan="2" style="color: #888;">Aucune</td></tr>') + '''</tbody>
            </table>
        </div>
    </div>
    
    <div class="section">
        <div class="section-header">Contenu Brut (extrait)</div>
        <div class="section-content">
            <div class="changelog">''' + html.escape(item.get('content_text', '')[:2000] or '') + '''</div>
        </div>
    </div>
    
    <script>
    var currentUrl = "''' + url_escaped + '''";
    function markIntel(type) {
        fetch("/api/mark-intel", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({url: currentUrl, type: type})
        }).then(function() { location.reload(); });
    }
    </script>
    
    <style>
    .secret-block, .crypto-block { margin-bottom: 15px; }
    .secret-value, .crypto-addr { display: block; background: #0a0a0a; padding: 5px 10px; margin: 5px 0; border-radius: 3px; word-break: break-all; font-size: 11px; }
    .email-item, .social-item { display: inline-block; background: #1a1a1a; padding: 3px 8px; margin: 3px; border-radius: 3px; font-size: 11px; }
    .tags-container { display: flex; flex-wrap: wrap; gap: 5px; }
    </style>'''
    
    return HTML_TEMPLATE.format(page_content=page_content, port=port, version=version, update_banner='',
        nav_dashboard='', nav_search='', nav_trusted='', nav_updates='')


def render_queue(queue: List[Dict], sort: str, port: int) -> str:
    """Page de gestion de la queue."""
    version = "7.0.0"
    
    rows_html = ""
    for item in queue[:100]:
        status_class = 'frozen' if item.get('domain_status') == 'frozen' else ''
        rows_html += '<tr class="' + status_class + '">'
        rows_html += '<td class="url">' + html.escape(str(item.get('url', ''))[:60]) + '</td>'
        rows_html += '<td class="domain">' + html.escape(str(item.get('domain', ''))[:25]) + '</td>'
        rows_html += '<td>' + str(item.get('depth', 0)) + '</td>'
        rows_html += '<td>' + str(item.get('priority_score', 50)) + '</td>'
        rows_html += '<td>' + html.escape(str(item.get('found_at', ''))[:10]) + '</td>'
        rows_html += '</tr>'
    
    if not rows_html:
        rows_html = '<tr><td colspan="5" style="color: #888;">Queue vide</td></tr>'
    
    page_content = '''
    <div class="stats-grid">
        <div class="stat-card"><h3>EN QUEUE</h3><div class="value">''' + str(len(queue)) + '''</div></div>
    </div>
    
    <div class="control-panel">
        <h2>Controles Queue</h2>
        <div class="form-row">
            <div class="form-group">
                <label>Trier par</label>
                <select onchange="window.location='?sort='+this.value">
                    <option value="priority" ''' + ('selected' if sort == 'priority' else '') + '''>Priorite</option>
                    <option value="depth" ''' + ('selected' if sort == 'depth' else '') + '''>Profondeur</option>
                    <option value="recent" ''' + ('selected' if sort == 'recent' else '') + '''>Recent</option>
                </select>
            </div>
        </div>
    </div>
    
    <div class="section">
        <div class="section-header">Queue (''' + str(len(queue)) + ''' URLs)</div>
        <div class="section-content" style="max-height: 600px;">
            <table>
                <thead><tr><th>URL</th><th>Domaine</th><th>Depth</th><th>Prio</th><th>Date</th></tr></thead>
                <tbody>''' + rows_html + '''</tbody>
            </table>
        </div>
    </div>
    
    <style>
    .frozen { opacity: 0.5; background: #1a1a2a; }
    </style>'''
    
    return HTML_TEMPLATE.format(page_content=page_content, port=port, version=version, update_banner='',
        nav_dashboard='', nav_search='', nav_trusted='', nav_updates='')


def render_domains_list(domains: List[Dict], status_filter: str, port: int) -> str:
    """Liste des domaines avec leurs profils."""
    version = "7.0.0"
    
    rows_html = ""
    for d in domains:
        status_badge = ''
        if d.get('status') == 'frozen':
            status_badge = '<span class="tag" style="background:#00aaff;">GELE</span>'
        elif d.get('status') == 'priority':
            status_badge = '<span class="tag" style="background:#ffaa00;">PRIO</span>'
        
        trust_class = 'trust-' + d.get('trust_level', 'unknown')
        
        rows_html += '<tr onclick="showDomain(\'' + html.escape(d.get('domain', '')) + '\')" style="cursor:pointer;">'
        rows_html += '<td class="domain">' + html.escape(d.get('domain', '')[:35]) + ' ' + status_badge + '</td>'
        rows_html += '<td>' + str(d.get('total_pages', 0)) + '</td>'
        rows_html += '<td style="color:#00ff00;">' + str(d.get('success_pages', 0)) + '</td>'
        rows_html += '<td>' + str(d.get('intel_count', 0)) + '</td>'
        rows_html += '<td class="' + trust_class + '">' + html.escape(d.get('trust_level', '-')) + '</td>'
        rows_html += '<td>' + str(d.get('priority_boost', 0)) + '</td>'
        rows_html += '</tr>'
    
    if not rows_html:
        rows_html = '<tr><td colspan="6" style="color: #888;">Aucun domaine</td></tr>'
    
    page_content = '''
    <div class="control-panel">
        <h2>Gestion des Domaines</h2>
        <div class="form-row">
            <div class="form-group">
                <label>Filtrer par statut</label>
                <select onchange="window.location='?status='+this.value">
                    <option value="">Tous</option>
                    <option value="normal" ''' + ('selected' if status_filter == 'normal' else '') + '''>Normal</option>
                    <option value="frozen" ''' + ('selected' if status_filter == 'frozen' else '') + '''>Gele</option>
                    <option value="priority" ''' + ('selected' if status_filter == 'priority' else '') + '''>Prioritaire</option>
                </select>
            </div>
        </div>
    </div>
    
    <div class="section">
        <div class="section-header">Domaines (''' + str(len(domains)) + ''')</div>
        <div class="section-content" style="max-height: 600px;">
            <table>
                <thead><tr><th>Domaine</th><th>Pages</th><th>Succes</th><th>Intel</th><th>Trust</th><th>Boost</th></tr></thead>
                <tbody>''' + rows_html + '''</tbody>
            </table>
        </div>
    </div>
    
    <script>
    function showDomain(domain) {
        window.location.href = '/domain/detail?d=' + encodeURIComponent(domain);
    }
    </script>
    
    <style>
    .trust-high { color: #00ff00; }
    .trust-medium { color: #ffaa00; }
    .trust-low { color: #ff4444; }
    .trust-unknown { color: #888; }
    </style>'''
    
    return HTML_TEMPLATE.format(page_content=page_content, port=port, version=version, update_banner='',
        nav_dashboard='', nav_search='', nav_trusted='', nav_updates='')


def render_domain_detail(profile: Optional[Dict], port: int) -> str:
    """Detail d'un domaine."""
    version = "7.0.0"
    
    if not profile:
        page_content = '<div style="color: #ff4444; text-align: center;">Domaine non trouve</div>'
        return HTML_TEMPLATE.format(page_content=page_content, port=port, version=version, update_banner='',
            nav_dashboard='', nav_search='', nav_trusted='', nav_updates='')
    
    domain = profile.get('domain', '')
    
    page_content = '''
    <div class="control-panel">
        <h2>''' + html.escape(domain) + '''</h2>
        <div class="stats-grid">
            <div class="stat-card"><h3>PAGES</h3><div class="value">''' + str(profile.get('total_pages', 0)) + '''</div></div>
            <div class="stat-card"><h3>SUCCES</h3><div class="value">''' + str(profile.get('success_pages', 0)) + '''</div></div>
            <div class="stat-card"><h3>RISQUE MOY</h3><div class="value">''' + str(round(profile.get('avg_risk', 0) or 0, 1)) + '''</div></div>
        </div>
    </div>
    
    <div class="control-panel">
        <h2>Profil de Crawl</h2>
        <div class="form-row">
            <div class="form-group">
                <label>Statut</label>
                <select id="domainStatus">
                    <option value="normal" ''' + ('selected' if profile.get('status') == 'normal' else '') + '''>Normal</option>
                    <option value="frozen" ''' + ('selected' if profile.get('status') == 'frozen' else '') + '''>Gele</option>
                    <option value="priority" ''' + ('selected' if profile.get('status') == 'priority' else '') + '''>Prioritaire</option>
                </select>
            </div>
            <div class="form-group">
                <label>Trust Level</label>
                <select id="trustLevel">
                    <option value="unknown" ''' + ('selected' if profile.get('trust_level') == 'unknown' else '') + '''>Inconnu</option>
                    <option value="high" ''' + ('selected' if profile.get('trust_level') == 'high' else '') + '''>Haute</option>
                    <option value="medium" ''' + ('selected' if profile.get('trust_level') == 'medium' else '') + '''>Moyenne</option>
                    <option value="low" ''' + ('selected' if profile.get('trust_level') == 'low' else '') + '''>Basse</option>
                </select>
            </div>
            <div class="form-group">
                <label>Profondeur Max</label>
                <input type="number" id="maxDepth" value="''' + str(profile.get('max_depth', 5)) + '''" min="1" max="20">
            </div>
            <div class="form-group">
                <label>Delai (ms)</label>
                <input type="number" id="delayMs" value="''' + str(profile.get('delay_ms', 1000)) + '''" min="100" max="10000">
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>Priority Boost</label>
                <input type="number" id="priorityBoost" value="''' + str(profile.get('priority_boost', 0)) + '''" min="-100" max="100">
            </div>
            <div class="form-group" style="flex: 2;">
                <label>Notes</label>
                <input type="text" id="notes" value="''' + html.escape(profile.get('notes', '')) + '''">
            </div>
        </div>
        <div class="form-row">
            <button class="btn btn-primary" onclick="saveDomain()">Sauvegarder</button>
            <button class="btn btn-warning" onclick="boostDomain(10)">Boost +10</button>
            <button class="btn btn-danger" onclick="freezeDomain()">Geler</button>
        </div>
        <div id="domainResult" style="margin-top: 10px;"></div>
    </div>
    
    <script>
    var currentDomain = "''' + html.escape(domain) + '''";
    
    function saveDomain() {
        fetch('/api/update-domain', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                domain: currentDomain,
                status: document.getElementById('domainStatus').value,
                trust_level: document.getElementById('trustLevel').value,
                max_depth: parseInt(document.getElementById('maxDepth').value),
                delay_ms: parseInt(document.getElementById('delayMs').value),
                priority_boost: parseInt(document.getElementById('priorityBoost').value),
                notes: document.getElementById('notes').value
            })
        }).then(function(r) { return r.json(); })
        .then(function(data) {
            document.getElementById('domainResult').innerHTML = '<span style="color:' + (data.success ? '#00ff00' : '#ff4444') + ';">' + data.message + '</span>';
        });
    }
    
    function boostDomain(boost) {
        fetch('/api/boost-domain', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({domain: currentDomain, boost: boost})
        }).then(function() { location.reload(); });
    }
    
    function freezeDomain() {
        fetch('/api/freeze-domain', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({domain: currentDomain, freeze: true})
        }).then(function() { location.reload(); });
    }
    </script>'''
    
    return HTML_TEMPLATE.format(page_content=page_content, port=port, version=version, update_banner='',
        nav_dashboard='', nav_search='', nav_trusted='', nav_updates='')


def render_monitoring(data: Dict, workers: Dict, port: int) -> str:
    """Page monitoring avec graphs."""
    version = "7.0.0"
    
    # Timeline chart
    timeline = data.get('timeline', [])
    timeline_html = _render_simple_chart(
        [t['date'][-5:] for t in reversed(timeline)] if timeline else [],
        [t['success'] for t in reversed(timeline)] if timeline else []
    )
    
    # Hourly stats
    hourly = data.get('hourly', [])[:12]
    hourly_html = ""
    for h in hourly:
        hourly_html += '<tr>'
        hourly_html += '<td>' + html.escape(str(h.get('hour', ''))[-8:-3]) + '</td>'
        hourly_html += '<td>' + str(h.get('urls_crawled', 0)) + '</td>'
        hourly_html += '<td style="color:#00ff00;">' + str(h.get('success_count', 0)) + '</td>'
        hourly_html += '<td style="color:#ff4444;">' + str(h.get('error_count', 0)) + '</td>'
        hourly_html += '<td>' + str(h.get('intel_found', 0)) + '</td>'
        hourly_html += '</tr>'
    
    # Errors
    errors = data.get('errors', {})
    errors_html = ""
    for code, count in errors.get('by_code', {}).items():
        errors_html += '<tr><td>' + str(code) + '</td><td>' + str(count) + '</td></tr>'
    
    # Sanity checks
    sanity = data.get('sanity', {})
    disk_class = 'alert' if sanity.get('disk_percent', 0) > 80 else ('warning' if sanity.get('disk_percent', 0) > 60 else 'info')
    ram_class = 'alert' if sanity.get('ram_percent', 0) > 80 else ('warning' if sanity.get('ram_percent', 0) > 60 else 'info')
    tor_class = 'info' if sanity.get('tor_status') == 'active' else 'alert'
    
    page_content = '''
    <div class="stats-grid">
        <div class="stat-card"><h3>WORKERS</h3><div class="value">''' + str(workers.get('workers', 0)) + '''</div></div>
        <div class="stat-card"><h3>ACTIFS</h3><div class="value">''' + str(workers.get('active', 0)) + '''</div></div>
        <div class="stat-card"><h3>TEMPS MOY</h3><div class="value">''' + str(round(workers.get('avg_time', 0), 1)) + '''s</div></div>
        <div class="stat-card"><h3>REQUETES</h3><div class="value">''' + str(workers.get('total_requests', 0)) + '''</div></div>
    </div>
    
    <div class="control-panel">
        <h2>Controle du Moteur</h2>
        <div class="form-row">
            <button class="btn btn-warning" onclick="controlCrawler('pause')">Pause</button>
            <button class="btn btn-primary" onclick="controlCrawler('resume')">Reprendre</button>
            <button class="btn btn-danger" onclick="controlCrawler('drain')">Drain (finir queue)</button>
        </div>
        <div id="controlResult" style="margin-top: 10px;"></div>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card ''' + disk_class + '''"><h3>DISQUE</h3><div class="value">''' + str(sanity.get('disk_percent', 0)) + '''%</div><small>''' + str(sanity.get('disk_free_gb', 0)) + ''' GB libre</small></div>
        <div class="stat-card ''' + ram_class + '''"><h3>RAM</h3><div class="value">''' + str(sanity.get('ram_percent', 0)) + '''%</div></div>
        <div class="stat-card ''' + tor_class + '''"><h3>TOR</h3><div class="value" style="font-size:16px;">''' + html.escape(str(sanity.get('tor_status', '-'))) + '''</div></div>
        <div class="stat-card"><h3>DB</h3><div class="value">''' + str(sanity.get('db_size_mb', 0)) + '''MB</div></div>
    </div>
    
    <div class="grid-2">
        <div class="section">
            <div class="section-header">Activite (7 jours)</div>
            <div class="section-content" style="max-height: none;">
                <div style="padding: 20px;">''' + timeline_html + '''</div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-header">Stats Horaires</div>
            <div class="section-content">
                <table>
                    <thead><tr><th>Heure</th><th>Crawl</th><th>OK</th><th>Err</th><th>Intel</th></tr></thead>
                    <tbody>''' + (hourly_html or '<tr><td colspan="5">Pas de donnees</td></tr>') + '''</tbody>
                </table>
            </div>
        </div>
    </div>
    
    <div class="section">
        <div class="section-header">Erreurs par Code HTTP</div>
        <div class="section-content">
            <p style="color:#888; margin-bottom:10px;">Total erreurs: ''' + str(errors.get('total_errors', 0)) + ''' (serveur: ''' + str(errors.get('server_errors', 0)) + ''', client: ''' + str(errors.get('client_errors', 0)) + ''')</p>
            <table>
                <thead><tr><th>Code</th><th>Count</th></tr></thead>
                <tbody>''' + (errors_html or '<tr><td colspan="2">Aucune erreur</td></tr>') + '''</tbody>
            </table>
        </div>
    </div>
    
    <script>
    function controlCrawler(action) {
        fetch('/api/control-crawler', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({action: action})
        }).then(function(r) { return r.json(); })
        .then(function(data) {
            document.getElementById('controlResult').innerHTML = '<span style="color:' + (data.success ? '#00ff00' : '#ff4444') + ';">' + data.message + '</span>';
        });
    }
    </script>'''
    
    return HTML_TEMPLATE.format(page_content=page_content, port=port, version=version, update_banner='',
        nav_dashboard='', nav_search='', nav_trusted='', nav_updates='')


def render_entities(data: Dict, entity_type: str, port: int) -> str:
    """Page des entites OSINT."""
    version = "7.0.0"
    
    entities = data.get('entities', [])
    stats = data.get('stats', {})
    
    # Stats cards
    stats_html = ""
    for etype, count in sorted(stats.items(), key=lambda x: -x[1])[:8]:
        stats_html += '<div class="stat-card"><h3>' + html.escape(etype.upper()) + '</h3><div class="value">' + str(count) + '</div></div>'
    
    # Entities table
    rows_html = ""
    for e in entities:
        rows_html += '<tr>'
        rows_html += '<td>' + html.escape(e.get('entity_type', '')) + '</td>'
        rows_html += '<td class="url">' + html.escape(str(e.get('value', ''))[:60]) + '</td>'
        rows_html += '<td class="domain">' + html.escape(str(e.get('source_domain', ''))[:30]) + '</td>'
        rows_html += '<td>' + html.escape(str(e.get('first_seen', ''))[:10]) + '</td>'
        rows_html += '</tr>'
    
    if not rows_html:
        rows_html = '<tr><td colspan="4" style="color: #888;">Aucune entite</td></tr>'
    
    # Filter options
    type_options = '<option value="">Tous</option>'
    for etype in sorted(stats.keys()):
        selected = 'selected' if etype == entity_type else ''
        type_options += '<option value="' + html.escape(etype) + '" ' + selected + '>' + html.escape(etype) + '</option>'
    
    page_content = '''
    <div class="stats-grid">
        ''' + stats_html + '''
    </div>
    
    <div class="control-panel">
        <h2>Filtrer les Entites</h2>
        <div class="form-row">
            <div class="form-group">
                <label>Type</label>
                <select onchange="window.location='?type='+this.value">
                    ''' + type_options + '''
                </select>
            </div>
        </div>
    </div>
    
    <div class="section">
        <div class="section-header">Entites OSINT (''' + str(len(entities)) + ''')</div>
        <div class="section-content" style="max-height: 600px;">
            <table>
                <thead><tr><th>Type</th><th>Valeur</th><th>Source</th><th>Vu</th></tr></thead>
                <tbody>''' + rows_html + '''</tbody>
            </table>
        </div>
    </div>'''
    
    return HTML_TEMPLATE.format(page_content=page_content, port=port, version=version, update_banner='',
        nav_dashboard='', nav_search='', nav_trusted='', nav_updates='')


def render_login(port: int) -> str:
    """Page de login."""
    return '''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Darknet Crawler - Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Courier New', monospace; background: #0a0a0a; color: #00ff00; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .login-container { background: #111; border: 2px solid #00ff00; border-radius: 8px; padding: 40px; width: 350px; box-shadow: 0 0 30px rgba(0, 255, 0, 0.2); }
        h1 { text-align: center; margin-bottom: 30px; font-size: 20px; text-shadow: 0 0 10px #00ff00; }
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; margin-bottom: 8px; color: #888; font-size: 12px; }
        .form-group input { width: 100%; padding: 12px; background: #0a0a0a; border: 1px solid #333; color: #00ff00; font-family: 'Courier New', monospace; font-size: 14px; border-radius: 4px; }
        .form-group input:focus { border-color: #00ff00; outline: none; }
        .btn { width: 100%; padding: 12px; background: #00ff00; color: #000; border: none; font-family: 'Courier New', monospace; font-weight: bold; font-size: 14px; cursor: pointer; border-radius: 4px; }
        .btn:hover { background: #00cc00; }
        .error { background: #3a1a1a; border: 1px solid #ff4444; color: #ff4444; padding: 10px; border-radius: 4px; margin-bottom: 20px; font-size: 12px; display: none; }
        .info { color: #666; font-size: 10px; text-align: center; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>DARKNET CRAWLER</h1>
        <div id="error" class="error"></div>
        <form onsubmit="login(event)">
            <div class="form-group">
                <label>Username</label>
                <input type="text" id="username" autocomplete="username" required>
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" id="password" autocomplete="current-password" required>
            </div>
            <button type="submit" class="btn">LOGIN</button>
        </form>
        <p class="info">Protected access - Authorized users only</p>
    </div>
    <script>
    function login(e) {
        e.preventDefault();
        var username = document.getElementById("username").value;
        var password = document.getElementById("password").value;
        var errorDiv = document.getElementById("error");
        
        fetch("/api/login", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({username: username, password: password})
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.success && data.token) {
                document.cookie = "token=" + data.token + "; path=/; max-age=86400";
                window.location.href = "/";
            } else {
                errorDiv.textContent = data.message || "Login failed";
                errorDiv.style.display = "block";
            }
        })
        .catch(function(err) {
            errorDiv.textContent = "Connection error";
            errorDiv.style.display = "block";
        });
    }
    </script>
</body>
</html>'''


def render_security(security_status: Dict, audit_data: Dict, port: int) -> str:
    """Page de configuration securite."""
    version = "7.1.0"
    
    auth_status = 'Activee' if security_status.get('auth_enabled') else 'Desactivee'
    auth_class = 'info' if security_status.get('auth_enabled') else 'warning'
    
    ip_status = 'Activee' if security_status.get('ip_whitelist_enabled') else 'Desactivee'
    ip_class = 'info' if security_status.get('ip_whitelist_enabled') else ''
    
    rate_status = 'Active' if security_status.get('rate_limit_enabled') else 'Desactive'
    
    # IP Whitelist
    ip_list_html = ""
    for ip in security_status.get('ip_whitelist', []):
        ip_list_html += '<tr><td>' + html.escape(ip) + '</td>'
        ip_list_html += '<td><button class="btn btn-danger btn-small" onclick="removeIP(\'' + html.escape(ip) + '\')">Retirer</button></td></tr>'
    
    if not ip_list_html:
        ip_list_html = '<tr><td colspan="2" style="color:#888;">Aucune IP</td></tr>'
    
    # Rate limit stats
    rate_stats = security_status.get('rate_limit_stats', {})
    
    # Audit logs
    audit_html = ""
    for log in audit_data.get('logs', [])[:30]:
        event_class = ''
        if 'FAILED' in log.get('event', '') or 'BLOCKED' in log.get('event', ''):
            event_class = 'style="color:#ff4444;"'
        elif 'SUCCESS' in log.get('event', ''):
            event_class = 'style="color:#00ff00;"'
        
        audit_html += '<tr>'
        audit_html += '<td>' + html.escape(str(log.get('timestamp', ''))[-19:-7]) + '</td>'
        audit_html += '<td ' + event_class + '>' + html.escape(log.get('event', '')) + '</td>'
        audit_html += '<td>' + html.escape(str(log.get('ip', ''))) + '</td>'
        audit_html += '<td>' + html.escape(str(log.get('details', {}))[:50]) + '</td>'
        audit_html += '</tr>'
    
    if not audit_html:
        audit_html = '<tr><td colspan="4" style="color:#888;">Aucun log</td></tr>'
    
    page_content = '''
    <div class="stats-grid">
        <div class="stat-card ''' + auth_class + '''"><h3>AUTH JWT</h3><div class="value" style="font-size:14px;">''' + auth_status + '''</div></div>
        <div class="stat-card ''' + ip_class + '''"><h3>IP WHITELIST</h3><div class="value" style="font-size:14px;">''' + ip_status + '''</div></div>
        <div class="stat-card"><h3>RATE LIMIT</h3><div class="value" style="font-size:14px;">''' + rate_status + '''</div></div>
        <div class="stat-card"><h3>IPS BLOQUEES</h3><div class="value">''' + str(len(rate_stats.get('blocked_ips', []))) + '''</div></div>
    </div>
    
    <div class="info-box">
        <p><strong>Variables d'environnement pour activer la securite:</strong></p>
        <p><code>CRAWLER_AUTH_ENABLED=true</code> - Active l'authentification JWT</p>
        <p><code>CRAWLER_AUTH_USERNAME=admin</code> - Username (defaut: admin)</p>
        <p><code>CRAWLER_AUTH_PASSWORD=xxx</code> - Password (defaut: changeme)</p>
        <p><code>CRAWLER_IP_WHITELIST=true</code> - Active la whitelist IP</p>
        <p><code>CRAWLER_ALLOWED_IPS=1.2.3.4,5.6.7.8</code> - IPs autorisees</p>
    </div>
    
    <div class="grid-2">
        <div class="section">
            <div class="section-header">IP Whitelist</div>
            <div class="section-content">
                <div class="form-row" style="margin-bottom:10px;">
                    <input type="text" id="newIP" placeholder="IP a ajouter" style="flex:2;">
                    <button class="btn btn-danger" onclick="addIP()">Ajouter</button>
                </div>
                <table>
                    <thead><tr><th>IP</th><th>Action</th></tr></thead>
                    <tbody>''' + ip_list_html + '''</tbody>
                </table>
            </div>
        </div>
        
        <div class="section">
            <div class="section-header">Rate Limiting</div>
            <div class="section-content">
                <p style="margin-bottom:10px;">100 requetes/min par IP, 10 recherches/sec</p>
                <p>IPs actives: <strong>''' + str(rate_stats.get('active_ips', 0)) + '''</strong></p>
                <p>Requetes trackees: <strong>''' + str(rate_stats.get('total_requests_tracked', 0)) + '''</strong></p>
                <p style="margin-top:10px;">IPs bloquees:</p>
                <div class="changelog" style="max-height:100px;">''' + ', '.join(rate_stats.get('blocked_ips', [])) or 'Aucune' + '''</div>
            </div>
        </div>
    </div>
    
    <div class="section">
        <div class="section-header">Audit Logs (''' + str(len(audit_data.get('logs', []))) + ''')</div>
        <div class="section-content" style="max-height:400px;">
            <table>
                <thead><tr><th>Date</th><th>Event</th><th>IP</th><th>Details</th></tr></thead>
                <tbody>''' + audit_html + '''</tbody>
            </table>
        </div>
    </div>
    
    <script>
    function addIP() {
        var ip = document.getElementById("newIP").value.trim();
        if (!ip) return;
        
        fetch("/api/ip-whitelist", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({action: "add", ip: ip})
        }).then(function() { location.reload(); });
    }
    
    function removeIP(ip) {
        if (!confirm("Retirer " + ip + "?")) return;
        
        fetch("/api/ip-whitelist", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({action: "remove", ip: ip})
        }).then(function() { location.reload(); });
    }
    </script>'''
    
    return HTML_TEMPLATE.format(page_content=page_content, port=port, version=version, update_banner='',
        nav_dashboard='', nav_search='', nav_trusted='', nav_updates='')


def render_graph(graph_data: Dict, port: int) -> str:
    """Page de visualisation du graphe d'entites."""
    version = "8.0.0"
    
    nodes = graph_data.get('nodes', [])
    edges = graph_data.get('edges', [])
    stats = graph_data.get('stats', {})
    
    # Preparer nodes pour vis.js
    nodes_js = []
    for n in nodes[:200]:
        color = {
            'email': '#ff6b6b',
            'crypto': '#feca57',
            'social': '#48dbfb',
            'username': '#ff9ff3',
            'phone': '#1dd1a1',
        }.get(n.get('entity_type', ''), '#888888')
        
        nodes_js.append({
            'id': n['id'],
            'label': n['value'][:20] + ('...' if len(n['value']) > 20 else ''),
            'title': n['entity_type'] + ': ' + n['value'] + '\nOccurrences: ' + str(n.get('occurrence_count', 1)),
            'color': color,
            'size': min(10 + n.get('occurrence_count', 1) * 2, 40)
        })
    
    edges_js = []
    for e in edges[:500]:
        edges_js.append({
            'from': e['source_entity_id'],
            'to': e['target_entity_id'],
            'width': min(e.get('weight', 1), 5)
        })
    
    page_content = '''
    <div class="stats-grid">
        <div class="stat-card"><h3>NOEUDS</h3><div class="value">''' + str(stats.get('total_nodes', 0)) + '''</div></div>
        <div class="stat-card"><h3>LIENS</h3><div class="value">''' + str(stats.get('total_edges', 0)) + '''</div></div>
        <div class="stat-card info"><h3>EMAILS</h3><div class="value">''' + str(len([n for n in nodes if n.get('entity_type') == 'email'])) + '''</div></div>
        <div class="stat-card warning"><h3>CRYPTO</h3><div class="value">''' + str(len([n for n in nodes if 'crypto' in n.get('entity_type', '')])) + '''</div></div>
    </div>
    
    <div class="section">
        <div class="section-header">Graphe d'Entites (''' + str(len(nodes_js)) + ''' noeuds)</div>
        <div class="section-content" style="height:500px;">
            <div id="graph" style="width:100%;height:100%;background:#0a0a0a;border:1px solid #333;"></div>
        </div>
    </div>
    
    <div class="legend" style="margin-top:10px;">
        <span style="color:#ff6b6b;">Email</span>
        <span style="color:#feca57;">Crypto</span>
        <span style="color:#48dbfb;">Social</span>
        <span style="color:#ff9ff3;">Username</span>
        <span style="color:#1dd1a1;">Phone</span>
    </div>
    
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <script>
    var nodes = new vis.DataSet(''' + json.dumps(nodes_js) + ''');
    var edges = new vis.DataSet(''' + json.dumps(edges_js) + ''');
    
    var container = document.getElementById("graph");
    var data = { nodes: nodes, edges: edges };
    var options = {
        nodes: { shape: "dot", font: { color: "#00ff00", size: 10 } },
        edges: { color: { color: "#444", highlight: "#00ff00" }, smooth: { type: "continuous" } },
        physics: { stabilization: { iterations: 100 }, barnesHut: { gravitationalConstant: -3000 } },
        interaction: { hover: true, tooltipDelay: 100 }
    };
    
    var network = new vis.Network(container, data, options);
    
    network.on("click", function(params) {
        if (params.nodes.length > 0) {
            var nodeId = params.nodes[0];
            window.location.href = "/entity/detail?id=" + nodeId;
        }
    });
    </script>'''
    
    return HTML_TEMPLATE.format(page_content=page_content, port=port, version=version, update_banner='',
        nav_dashboard='', nav_search='', nav_trusted='', nav_updates='')


def render_correlations(corr_data: Dict, port: int) -> str:
    """Page des correlations."""
    version = "8.0.0"
    
    correlations = corr_data.get('correlations', [])
    cross_domain = corr_data.get('cross_domain', [])
    
    # Stats
    total_corr = len(correlations)
    avg_score = sum(c.get('correlation_score', 0) for c in correlations) / max(total_corr, 1)
    
    # Table correlations
    corr_html = ""
    for c in correlations[:50]:
        score_class = 'danger' if c.get('correlation_score', 0) >= 0.9 else ('warning' if c.get('correlation_score', 0) >= 0.7 else '')
        corr_html += '<tr class="' + score_class + '">'
        corr_html += '<td>' + html.escape(str(c.get('entity1_type', ''))) + ': ' + html.escape(str(c.get('entity1_value', ''))[:30]) + '</td>'
        corr_html += '<td>' + html.escape(str(c.get('entity2_type', ''))) + ': ' + html.escape(str(c.get('entity2_value', ''))[:30]) + '</td>'
        corr_html += '<td><strong>' + str(round(c.get('correlation_score', 0), 2)) + '</strong></td>'
        corr_html += '<td>' + html.escape(str(c.get('relationship_type', ''))) + '</td>'
        corr_html += '<td>' + html.escape(str(c.get('interpretation', ''))[:50]) + '</td>'
        corr_html += '</tr>'
    
    if not corr_html:
        corr_html = '<tr><td colspan="5" style="color:#888;">Aucune correlation</td></tr>'
    
    # Table cross-domain
    cross_html = ""
    for cd in cross_domain[:30]:
        cross_html += '<tr>'
        cross_html += '<td>' + html.escape(str(cd.get('entity_type', ''))) + '</td>'
        cross_html += '<td>' + html.escape(str(cd.get('value', ''))[:40]) + '</td>'
        cross_html += '<td><strong>' + str(cd.get('domain_count', 0)) + '</strong></td>'
        cross_html += '<td>' + str(cd.get('total_occurrences', 0)) + '</td>'
        cross_html += '<td style="font-size:10px;">' + html.escape(str(cd.get('domains', ''))[:60]) + '</td>'
        cross_html += '</tr>'
    
    if not cross_html:
        cross_html = '<tr><td colspan="5" style="color:#888;">Aucune entite cross-domain</td></tr>'
    
    page_content = '''
    <div class="stats-grid">
        <div class="stat-card"><h3>CORRELATIONS</h3><div class="value">''' + str(total_corr) + '''</div></div>
        <div class="stat-card"><h3>CROSS-DOMAIN</h3><div class="value">''' + str(len(cross_domain)) + '''</div></div>
        <div class="stat-card"><h3>SCORE MOYEN</h3><div class="value">''' + str(round(avg_score, 2)) + '''</div></div>
    </div>
    
    <div class="section">
        <div class="section-header">Correlations Elevees (score >= 0.7)</div>
        <div class="section-content" style="max-height:400px;">
            <table>
                <thead><tr><th>Entite 1</th><th>Entite 2</th><th>Score</th><th>Type</th><th>Interpretation</th></tr></thead>
                <tbody>''' + corr_html + '''</tbody>
            </table>
        </div>
    </div>
    
    <div class="section">
        <div class="section-header">Entites Cross-Domain (2+ domaines)</div>
        <div class="section-content" style="max-height:400px;">
            <table>
                <thead><tr><th>Type</th><th>Valeur</th><th>Domaines</th><th>Occurrences</th><th>Sources</th></tr></thead>
                <tbody>''' + cross_html + '''</tbody>
            </table>
        </div>
    </div>
    
    <div class="info-box" style="margin-top:20px;">
        <p><strong>Interpretation des scores:</strong></p>
        <p>0.9+ = CRITICAL - Meme acteur probable</p>
        <p>0.7-0.9 = HIGH - Forte correlation</p>
        <p>0.4-0.7 = MEDIUM - Correlation moderee</p>
    </div>'''
    
    return HTML_TEMPLATE.format(page_content=page_content, port=port, version=version, update_banner='',
        nav_dashboard='', nav_search='', nav_trusted='', nav_updates='')


def render_alerts(alerts: List[Dict], port: int) -> str:
    """Page des alertes simple."""
    version = "7.0.0"
    
    alerts_html = ""
    for a in alerts[:50]:
        severity = a.get('severity', 'info')
        sev_class = 'danger' if severity == 'danger' else ('warning' if severity == 'warning' else '')
        
        alerts_html += '<tr class="' + sev_class + '">'
        alerts_html += '<td>' + html.escape(str(a.get('severity', 'info'))) + '</td>'
        alerts_html += '<td>' + html.escape(str(a.get('title', ''))[:60]) + '</td>'
        alerts_html += '<td>' + html.escape(str(a.get('domain', '') or '-')) + '</td>'
        alerts_html += '<td>' + html.escape(str(a.get('created_at', ''))[:16]) + '</td>'
        alerts_html += '</tr>'
    
    if not alerts_html:
        alerts_html = '<tr><td colspan="4" style="color: #888;">Aucune alerte</td></tr>'
    
    page_content = '''
    <div class="section">
        <div class="section-header">
            Alertes (''' + str(len(alerts)) + ''')
            <button class="btn btn-small btn-warning" onclick="markAllRead()">Tout marquer lu</button>
            <button class="btn btn-small btn-danger" onclick="clearAlerts()">Supprimer</button>
        </div>
        <div class="section-content" style="max-height:600px;">
            <table>
                <thead><tr><th>Severite</th><th>Message</th><th>Domaine</th><th>Date</th></tr></thead>
                <tbody>''' + alerts_html + '''</tbody>
            </table>
        </div>
    </div>
    
    <script>
    function markAllRead() {
        fetch("/api/mark-alerts-read", {
            method: "POST"
        }).then(function() { location.reload(); });
    }
    function clearAlerts() {
        if (confirm("Supprimer toutes les alertes?")) {
            fetch("/api/clear-alerts", {
                method: "POST"
            }).then(function() { location.reload(); });
        }
    }
    </script>'''
    
    return HTML_TEMPLATE.format(page_content=page_content, port=port, version=version, update_banner='',
        nav_dashboard='', nav_search='', nav_trusted='', nav_updates='')


def render_export(stats: Dict, port: int) -> str:
    """Page d'export."""
    version = "7.0.0"
    
    page_content = '''
    <div class="stats-grid">
        <div class="stat-card"><h3>TOTAL</h3><div class="value">''' + str(stats.get('total', 0)) + '''</div></div>
        <div class="stat-card"><h3>EMAILS</h3><div class="value">''' + str(stats.get('with_emails', 0)) + '''</div></div>
        <div class="stat-card"><h3>CRYPTO</h3><div class="value">''' + str(stats.get('with_crypto', 0)) + '''</div></div>
        <div class="stat-card"><h3>SECRETS</h3><div class="value">''' + str(stats.get('with_secrets', 0)) + '''</div></div>
    </div>
    
    <div class="control-panel">
        <h2>Exporter les Donnees</h2>
        <div class="form-row">
            <button class="btn btn-primary" onclick="exportData('json')">Export JSON</button>
            <button class="btn btn-primary" onclick="exportData('csv')">Export CSV</button>
            <button class="btn btn-warning" onclick="exportData('emails')">Export Emails</button>
            <button class="btn btn-purple" onclick="exportData('crypto')">Export Crypto</button>
        </div>
        <div id="exportResult" style="margin-top:15px;"></div>
    </div>
    
    <div class="control-panel">
        <h2>Maintenance Base de Donnees</h2>
        <div class="form-row">
            <div class="form-group">
                <label>Purger les donnees de plus de X jours</label>
                <input type="number" id="purgeDays" value="30" min="1" max="365">
            </div>
            <div class="form-group" style="flex:0;">
                <button class="btn btn-danger" onclick="purgeData(false)">Supprimer</button>
                <button class="btn btn-warning" onclick="purgeData(true)">Anonymiser</button>
            </div>
        </div>
        <div class="form-row">
            <button class="btn btn-primary" onclick="vacuumDb()">Optimiser DB (VACUUM)</button>
        </div>
        <div id="maintenanceResult" style="margin-top:15px;"></div>
    </div>
    
    <script>
    function exportData(type) {
        var result = document.getElementById("exportResult");
        result.innerHTML = '<span class="loading"></span> Export en cours...';
        fetch("/api/export", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({type: type})
        }).then(function(r) { return r.json(); })
        .then(function(data) {
            result.innerHTML = '<span style="color:' + (data.success ? '#00ff00' : '#ff4444') + ';">' + data.message + '</span>';
        });
    }
    function purgeData(anonymize) {
        var days = document.getElementById("purgeDays").value;
        if (!confirm((anonymize ? "Anonymiser" : "Supprimer") + " les donnees de plus de " + days + " jours?")) return;
        var result = document.getElementById("maintenanceResult");
        fetch("/api/purge", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({days: parseInt(days), anonymize: anonymize})
        }).then(function(r) { return r.json(); })
        .then(function(data) {
            result.innerHTML = '<span style="color:' + (data.success ? '#00ff00' : '#ff4444') + ';">' + data.message + '</span>';
        });
    }
    function vacuumDb() {
        var result = document.getElementById("maintenanceResult");
        result.innerHTML = '<span class="loading"></span>';
        fetch("/api/vacuum", {method: "POST"}).then(function(r) { return r.json(); })
        .then(function(data) {
            result.innerHTML = '<span style="color:#00ff00;">' + data.message + '</span>';
        });
    }
    </script>'''
    
    return HTML_TEMPLATE.format(page_content=page_content, port=port, version=version, update_banner='',
        nav_dashboard='', nav_search='', nav_trusted='', nav_updates='')


def render_settings(domain_lists: Dict, port: int) -> str:
    """Page des settings."""
    version = "7.0.0"
    
    blacklist_html = ""
    for item in domain_lists.get('blacklist', []):
        blacklist_html += '<tr><td>' + html.escape(item.get('domain', '')) + '</td>'
        blacklist_html += '<td>' + html.escape(item.get('reason', '')) + '</td>'
        blacklist_html += '<td><button class="btn btn-danger btn-small" onclick="removeFromList(\'' + html.escape(item.get('domain', '')) + '\')">X</button></td></tr>'
    
    if not blacklist_html:
        blacklist_html = '<tr><td colspan="3" style="color:#888;">Vide</td></tr>'
    
    whitelist_html = ""
    for item in domain_lists.get('whitelist', []):
        whitelist_html += '<tr><td>' + html.escape(item.get('domain', '')) + '</td>'
        whitelist_html += '<td>' + html.escape(item.get('reason', '')) + '</td>'
        whitelist_html += '<td><button class="btn btn-danger btn-small" onclick="removeFromList(\'' + html.escape(item.get('domain', '')) + '\')">X</button></td></tr>'
    
    if not whitelist_html:
        whitelist_html = '<tr><td colspan="3" style="color:#888;">Vide</td></tr>'
    
    page_content = '''
    <div class="grid-2">
        <div class="section">
            <div class="section-header">Blacklist</div>
            <div class="section-content">
                <div class="form-row" style="margin-bottom:10px;">
                    <input type="text" id="blacklistDomain" placeholder="domaine.onion">
                    <input type="text" id="blacklistReason" placeholder="Raison">
                    <button class="btn btn-danger" onclick="addToList('blacklist')">+</button>
                </div>
                <table>
                    <thead><tr><th>Domaine</th><th>Raison</th><th></th></tr></thead>
                    <tbody>''' + blacklist_html + '''</tbody>
                </table>
            </div>
        </div>
        
        <div class="section">
            <div class="section-header">Whitelist</div>
            <div class="section-content">
                <div class="form-row" style="margin-bottom:10px;">
                    <input type="text" id="whitelistDomain" placeholder="domaine.onion">
                    <input type="text" id="whitelistReason" placeholder="Raison">
                    <button class="btn btn-primary" onclick="addToList('whitelist')">+</button>
                </div>
                <table>
                    <thead><tr><th>Domaine</th><th>Raison</th><th></th></tr></thead>
                    <tbody>''' + whitelist_html + '''</tbody>
                </table>
            </div>
        </div>
    </div>
    
    <script>
    function addToList(listType) {
        var domain = document.getElementById(listType + "Domain").value.trim();
        var reason = document.getElementById(listType + "Reason").value.trim();
        if (!domain) return;
        fetch("/api/add-to-list", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({domain: domain, list_type: listType, reason: reason})
        }).then(function() { location.reload(); });
    }
    function removeFromList(domain) {
        if (!confirm("Retirer " + domain + "?")) return;
        fetch("/api/remove-from-list", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({domain: domain})
        }).then(function() { location.reload(); });
    }
    </script>'''
    
    return HTML_TEMPLATE.format(page_content=page_content, port=port, version=version, update_banner='',
        nav_dashboard='', nav_search='', nav_trusted='', nav_updates='')
