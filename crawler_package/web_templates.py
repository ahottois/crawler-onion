"""
Templates HTML pour le serveur web.
Separe pour une meilleure lisibilite du code.
"""

import html
import json
import math
from datetime import datetime
from typing import Dict, List, Any


# Template HTML principal avec scripts daemon ajoutes
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Darknet Crawler Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Courier New', monospace; background: #0a0a0a; color: #00ff00; padding: 20px; min-height: 100vh; }}
        .container {{ max-width: 1600px; margin: 0 auto; }}
        h1 {{ color: #00ff00; text-align: center; margin-bottom: 30px; text-shadow: 0 0 10px #00ff00; }}
        .nav-tabs {{ display: flex; gap: 8px; margin-bottom: 20px; justify-content: center; flex-wrap: wrap; }}
        .nav-tab {{ padding: 8px 16px; background: #111; border: 1px solid #333; color: #888; cursor: pointer; border-radius: 5px; font-size: 13px; text-decoration: none; }}
        .nav-tab:hover, .nav-tab.active {{ background: #00ff00; color: #000; border-color: #00ff00; }}
        .nav-tab.update-available {{ background: #ff4444; color: #fff; border-color: #ff4444; animation: pulse 2s infinite; }}
        .nav-tab.alerts {{ position: relative; }}
        .nav-tab .badge {{ position: absolute; top: -5px; right: -5px; background: #ff4444; color: #fff; border-radius: 50%; padding: 2px 6px; font-size: 10px; }}
        @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.7; }} }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 20px; }}
        .stat-card {{ background: #111; border: 1px solid #00ff00; padding: 12px; text-align: center; border-radius: 5px; }}
        .stat-card h3 {{ color: #888; font-size: 11px; margin-bottom: 6px; }}
        .stat-card .value {{ font-size: 24px; color: #00ff00; }}
        .stat-card.alert .value {{ color: #ff4444; }}
        .stat-card.warning .value {{ color: #ffaa00; }}
        .stat-card.info .value {{ color: #00aaff; }}
        .section {{ background: #111; border: 1px solid #333; margin-bottom: 20px; border-radius: 5px; }}
        .section-header {{ background: #1a1a1a; padding: 12px 15px; border-bottom: 1px solid #333; font-weight: bold; display: flex; justify-content: space-between; align-items: center; }}
        .section-content {{ padding: 15px; max-height: 350px; overflow-y: auto; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 8px 10px; text-align: left; border-bottom: 1px solid #222; font-size: 12px; }}
        th {{ color: #888; }}
        tr:hover {{ background: #1a1a1a; }}
        .tag {{ display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 10px; margin: 1px; }}
        .tag-secret {{ background: #ff4444; color: #fff; }}
        .tag-crypto {{ background: #9933ff; color: #fff; }}
        .tag-social {{ background: #00aaff; color: #fff; }}
        .tag-email {{ background: #ffaa00; color: #000; }}
        .url {{ color: #00ff00; word-break: break-all; font-size: 11px; }}
        .domain {{ color: #888; }}
        .title {{ color: #fff; }}
        .footer {{ text-align: center; padding: 20px; color: #444; font-size: 11px; }}
        .status-running {{ color: #00ff00; animation: blink 1s infinite; }}
        .status-stopped {{ color: #ff4444; }}
        @keyframes blink {{ 50% {{ opacity: 0.5; }} }}
        .control-panel {{ background: #111; border: 1px solid #00ff00; border-radius: 5px; padding: 15px; margin-bottom: 20px; }}
        .control-panel h2 {{ color: #00ff00; margin-bottom: 12px; font-size: 14px; }}
        .control-panel.daemon {{ border-color: #9933ff; }}
        .control-panel.daemon h2 {{ color: #9933ff; }}
        .form-row {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: flex-end; }}
        .form-group {{ flex: 1; min-width: 150px; margin-bottom: 10px; }}
        .form-group label {{ display: block; color: #888; margin-bottom: 5px; font-size: 11px; }}
        .form-group input, .form-group textarea, .form-group select {{ width: 100%; padding: 8px; background: #0a0a0a; border: 1px solid #333; color: #00ff00; font-family: 'Courier New', monospace; border-radius: 3px; font-size: 12px; }}
        .form-group textarea {{ height: 60px; resize: vertical; }}
        .btn {{ padding: 8px 15px; border: none; border-radius: 3px; cursor: pointer; font-family: 'Courier New', monospace; font-weight: bold; font-size: 11px; margin-right: 5px; margin-bottom: 5px; }}
        .btn-primary {{ background: #00ff00; color: #000; }}
        .btn-primary:hover {{ background: #00cc00; }}
        .btn-warning {{ background: #ffaa00; color: #000; }}
        .btn-danger {{ background: #ff4444; color: #fff; }}
        .btn-danger:hover {{ background: #cc3333; }}
        .btn-purple {{ background: #9933ff; color: #fff; }}
        .btn-purple:hover {{ background: #7722cc; }}
        .btn-small {{ padding: 4px 8px; font-size: 10px; }}
        .btn-copy {{ background: #333; color: #00ff00; border: 1px solid #00ff00; }}
        .btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
        .message {{ padding: 8px; border-radius: 3px; margin-bottom: 10px; display: none; font-size: 12px; }}
        .message.success {{ background: #1a3a1a; border: 1px solid #00ff00; color: #00ff00; display: block; }}
        .message.error {{ background: #3a1a1a; border: 1px solid #ff4444; color: #ff4444; display: block; }}
        .grid-2 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; }}
        .trust-score {{ display: inline-block; padding: 3px 8px; border-radius: 10px; font-size: 11px; font-weight: bold; }}
        .trust-high {{ background: #00ff00; color: #000; }}
        .trust-medium {{ background: #ffaa00; color: #000; }}
        .trust-low {{ background: #ff4444; color: #fff; }}
        .search-result {{ background: #1a1a1a; border: 1px solid #333; border-radius: 5px; padding: 12px; margin-bottom: 10px; }}
        .search-result:hover {{ border-color: #00ff00; }}
        .search-result-title {{ color: #00ff00; font-size: 13px; margin-bottom: 5px; }}
        .search-result-url {{ color: #888; font-size: 10px; word-break: break-all; }}
        .search-result-meta {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }}
        .refresh-info {{ text-align: center; color: #444; margin-bottom: 15px; font-size: 11px; }}
        .update-banner {{ background: linear-gradient(90deg, #ff4444, #ff6666); color: #fff; padding: 10px 20px; border-radius: 5px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }}
        .changelog {{ background: #0a0a0a; border: 1px solid #333; border-radius: 5px; padding: 15px; margin-top: 15px; white-space: pre-wrap; font-size: 11px; color: #888; max-height: 200px; overflow-y: auto; }}
        .commit-list {{ list-style: none; }}
        .commit-list li {{ padding: 8px 0; border-bottom: 1px solid #222; }}
        .commit-list li:last-child {{ border-bottom: none; }}
        .commit-sha {{ color: #00aaff; font-family: monospace; }}
        .commit-date {{ color: #666; font-size: 10px; }}
        .loading {{ display: inline-block; width: 16px; height: 16px; border: 2px solid #333; border-top-color: #00ff00; border-radius: 50%; animation: spin 1s linear infinite; }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
        .daemon-status {{ display: inline-block; padding: 4px 12px; border-radius: 15px; font-size: 11px; font-weight: bold; }}
        .daemon-status.active {{ background: #00ff00; color: #000; }}
        .daemon-status.inactive {{ background: #ff4444; color: #fff; }}
        .daemon-status.not-installed {{ background: #666; color: #fff; }}
        .log-viewer {{ background: #000; border: 1px solid #333; border-radius: 5px; padding: 15px; font-family: monospace; font-size: 10px; color: #00ff00; max-height: 250px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; }}
        .info-box {{ background: #1a1a2a; border: 1px solid #9933ff; border-radius: 5px; padding: 12px; margin-bottom: 15px; }}
        .info-box p {{ color: #888; font-size: 11px; margin-bottom: 6px; }}
        .info-box code {{ background: #0a0a0a; padding: 2px 6px; border-radius: 3px; color: #00ff00; font-size: 11px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Darknet Crawler v{version}</h1>
        <div class="nav-tabs">
            <a href="/" class="nav-tab {nav_dashboard}">Dashboard</a>
            <a href="/search" class="nav-tab {nav_search}">Recherche</a>
            <a href="/trusted" class="nav-tab {nav_trusted}">Sites</a>
            <a href="/alerts" class="nav-tab">Alertes</a>
            <a href="/export" class="nav-tab">Export</a>
            <a href="/settings" class="nav-tab">Parametres</a>
            <a href="/updates" class="nav-tab {nav_updates}">Systeme</a>
        </div>
        {update_banner}
        {page_content}
        <div class="footer">Darknet Omniscient Crawler v{version} | Port {port}</div>
    </div>
    <script>
        function copyToClipboard(text) {{ navigator.clipboard.writeText(text); }}
        function showMessage(text, type) {{
            const msg = document.getElementById('message');
            if (msg) {{ msg.textContent = text; msg.className = 'message ' + type; setTimeout(() => {{ msg.className = 'message'; }}, 5000); }}
        }}
        function addSeeds() {{
            const urls = document.getElementById('seedUrls').value.trim().split('\\n').filter(u => u.trim());
            if (urls.length === 0) {{ showMessage('Entrez au moins une URL', 'error'); return; }}
            fetch('/api/add-seeds', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ urls: urls }})
            }})
            .then(r => r.json())
            .then(data => {{
                showMessage(data.message, data.success ? 'success' : 'error');
                if (data.success) document.getElementById('seedUrls').value = '';
            }});
        }}
        function refreshLinks() {{
            fetch('/api/refresh-links', {{ method: 'POST' }})
            .then(r => r.json())
            .then(data => showMessage(data.message, data.success ? 'success' : 'error'));
        }}
        function checkUpdates() {{
            const btn = document.getElementById('checkUpdateBtn');
            const status = document.getElementById('updateStatus');
            if (btn) btn.disabled = true;
            if (status) status.innerHTML = '<span class="loading"></span> Verification...';
            
            fetch('/api/check-updates', {{ method: 'POST' }})
            .then(r => r.json())
            .then(data => {{
                if (btn) btn.disabled = false;
                if (status) {{
                    if (data.update_available) {{
                        status.innerHTML = '<span style="color: #ff4444;">Mise a jour disponible: v' + data.latest_version + '</span>';
                    }} else if (data.error) {{
                        status.innerHTML = '<span style="color: #ff4444;">Erreur: ' + data.error + '</span>';
                    }} else {{
                        status.innerHTML = '<span style="color: #00ff00;">Vous etes a jour!</span>';
                    }}
                }}
            }})
            .catch(e => {{
                if (btn) btn.disabled = false;
                if (status) status.innerHTML = '<span style="color: #ff4444;">Erreur</span>';
            }});
        }}
        function performUpdate() {{
            if (!confirm('Mettre a jour maintenant?')) return;
            
            const btn = document.getElementById('updateBtn');
            const status = document.getElementById('updateResult');
            if (btn) btn.disabled = true;
            if (status) status.innerHTML = '<span class="loading"></span> Mise a jour...';
            
            fetch('/api/perform-update', {{ method: 'POST' }})
            .then(r => r.json())
            .then(data => {{
                if (btn) btn.disabled = false;
                if (status) {{ status.innerHTML = '<span style="color: ' + (data.success ? '#00ff00' : '#ff4444') + ';">' + data.message + '</span><pre style="color: #888; font-size: 10px;">' + (data.details || '') + '</pre>'; }}
            }})
            .catch(e => {{ if (btn) btn.disabled = false; if (status) status.innerHTML = '<span style="color: #ff4444;">Erreur</span>'; }});
        }}
        function installDaemon() {{
            const port = document.getElementById('daemonPort').value || 4587;
            const workers = document.getElementById('daemonWorkers').value || 15;
            if (!confirm('Installer le crawler comme service systemd?')) return;
            const btn = document.getElementById('installDaemonBtn'); const status = document.getElementById('daemonResult');
            if (btn) btn.disabled = true; if (status) status.innerHTML = '<span class="loading"></span> Installation...';
            fetch('/api/daemon-install', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ web_port: parseInt(port), workers: parseInt(workers) }}) }})
            .then(r => r.json()).then(data => {{
                if (btn) btn.disabled = false;
                if (status) {{ status.innerHTML = '<span style="color: ' + (data.success ? '#00ff00' : '#ff4444') + ';">' + data.message + '</span>'; }}
                if (data.success) setTimeout(() => location.reload(), 2000);
            }}).catch(e => {{ if (btn) btn.disabled = false; if (status) status.innerHTML = '<span style="color: #ff4444;">Erreur</span>'; }});
        }}
        function uninstallDaemon() {{ if (!confirm('Desinstaller?')) return; fetch('/api/daemon-uninstall', {{ method: 'POST' }}).then(r => r.json()).then(data => {{ document.getElementById('daemonResult').innerHTML = '<span style="color: ' + (data.success ? '#00ff00' : '#ff4444') + ';">' + data.message + '</span>'; if (data.success) setTimeout(() => location.reload(), 2000); }}); }}
        function controlDaemon(action) {{ const status = document.getElementById('daemonResult'); if (status) status.innerHTML = '<span class="loading"></span>'; fetch('/api/daemon-control', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ action: action }}) }}).then(r => r.json()).then(data => {{ if (status) status.innerHTML = '<span style="color: ' + (data.success ? '#00ff00' : '#ff4444') + ';">' + data.message + '</span>'; setTimeout(() => location.reload(), 1500); }}); }}
        function refreshLogs() {{ const log = document.getElementById('daemonLogs'); if (!log) return; fetch('/api/daemon-logs?lines=50').then(r => r.json()).then(data => {{ if (data.logs) log.textContent = data.logs; }}); }}
        if (window.location.pathname === '/') setTimeout(() => location.reload(), 30000);
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
        <div class="stat-card info"><h3>SUCCES (200)</h3><div class="value">{data["success_urls"]}</div></div>
        <div class="stat-card"><h3>DOMAINES</h3><div class="value">{data["domains"]}</div></div>
        <div class="stat-card warning"><h3>EN QUEUE</h3><div class="value">{data["queue_size"]}</div></div>
        <div class="stat-card alert"><h3>INTEL</h3><div class="value">{data["intel_count"]}</div></div>
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
        <div class="stat-card alert"><h3>FAIBLE CONFIANCE</h3><div class="value">{data['low_trust']}</div></div>
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
            update_status_html = '<div class="stat-card alert"><h3>MISE A JOUR</h3><div class="value" style="font-size: 18px;">Disponible</div></div>'
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


def render_alerts(alerts: List[Dict], port: int) -> str:
    """Genere la page des alertes."""
    version = "6.5.0"
    
    alerts_html = ""
    unread_count = 0
    for alert in alerts:
        severity_class = 'alert' if alert.get('severity') == 'danger' else ('warning' if alert.get('severity') == 'warning' else 'info')
        read_class = '' if alert.get('read') else 'unread'
        if not alert.get('read'):
            unread_count += 1
        
        alerts_html += '''
        <div class="alert-item ''' + read_class + '''">
            <div class="alert-header">
                <span class="alert-type tag tag-''' + alert.get('severity', 'info') + '''">''' + html.escape(str(alert.get('type', ''))) + '''</span>
                <span class="alert-date">''' + html.escape(str(alert.get('created_at', ''))[:19]) + '''</span>
            </div>
            <div class="alert-message">''' + html.escape(str(alert.get('message', ''))) + '''</div>
            <div class="alert-url">''' + html.escape(str(alert.get('url', ''))[:80]) + '''</div>
        </div>'''
    
    if not alerts_html:
        alerts_html = '<div style="color: #888; text-align: center; padding: 40px;">Aucune alerte</div>'
    
    page_content = '''
    <div id="message" class="message"></div>
    
    <div class="stats-grid">
        <div class="stat-card"><h3>TOTAL ALERTES</h3><div class="value">''' + str(len(alerts)) + '''</div></div>
        <div class="stat-card alert"><h3>NON LUES</h3><div class="value">''' + str(unread_count) + '''</div></div>
    </div>
    
    <div class="control-panel">
        <h2>Gestion des Alertes</h2>
        <div class="form-row">
            <div class="form-group">
                <button class="btn btn-primary" onclick="markAlertsRead()">Marquer tout comme lu</button>
                <button class="btn btn-danger" onclick="clearAlerts()">Supprimer tout</button>
            </div>
        </div>
    </div>
    
    <div class="section">
        <div class="section-header">Alertes Recentes</div>
        <div class="section-content" style="max-height: none;">
            ''' + alerts_html + '''
        </div>
    </div>
    
    <script>
    function markAlertsRead() {
        fetch('/api/mark-alerts-read', {method: 'POST'})
        .then(r => r.json())
        .then(data => { showMessage(data.message, data.success ? 'success' : 'error'); setTimeout(() => location.reload(), 1000); });
    }
    function clearAlerts() {
        if (!confirm('Supprimer toutes les alertes?')) return;
        fetch('/api/clear-alerts', {method: 'POST'})
        .then(r => r.json())
        .then(data => { showMessage(data.message, data.success ? 'success' : 'error'); setTimeout(() => location.reload(), 1000); });
    }
    </script>
    
    <style>
    .alert-item { background: #1a1a1a; border: 1px solid #333; border-radius: 5px; padding: 15px; margin-bottom: 10px; }
    .alert-item.unread { border-left: 3px solid #ff4444; }
    .alert-header { display: flex; justify-content: space-between; margin-bottom: 8px; }
    .alert-type { text-transform: uppercase; }
    .alert-date { color: #666; font-size: 10px; }
    .alert-message { color: #fff; margin-bottom: 5px; }
    .alert-url { color: #888; font-size: 10px; word-break: break-all; }
    .tag-danger { background: #ff4444; color: #fff; }
    .tag-warning { background: #ffaa00; color: #000; }
    .tag-info { background: #00aaff; color: #fff; }
    </style>'''
    
    return HTML_TEMPLATE.format(page_content=page_content, port=port, version=version, update_banner='',
        nav_dashboard='', nav_search='', nav_trusted='', nav_updates='')


def render_export(stats: Dict[str, Any], port: int) -> str:
    """Genere la page d'export."""
    version = "6.5.0"
    
    # Timeline chart data
    timeline = stats.get('timeline', [])
    timeline_labels = [t['date'] for t in reversed(timeline)]
    timeline_values = [t['success'] for t in reversed(timeline)]
    
    # High risk sites
    high_risk = stats.get('high_risk', [])
    high_risk_html = ""
    for site in high_risk[:10]:
        high_risk_html += '''
        <tr>
            <td class="domain">''' + html.escape(str(site.get('domain', ''))[:30]) + '''</td>
            <td>''' + html.escape(str(site.get('title', ''))[:40]) + '''</td>
            <td class="risk-score">''' + str(site.get('risk_score', 0)) + '''</td>
        </tr>'''
    
    if not high_risk_html:
        high_risk_html = '<tr><td colspan="3" style="color: #888;">Aucun site a haut risque</td></tr>'
    
    page_content = '''
    <div id="message" class="message"></div>
    
    <div class="stats-grid">
        <div class="stat-card"><h3>URLS TOTALES</h3><div class="value">''' + str(stats.get('total', 0)) + '''</div></div>
        <div class="stat-card info"><h3>AVEC INTEL</h3><div class="value">''' + str(stats.get('with_secrets', 0) + stats.get('with_crypto', 0)) + '''</div></div>
        <div class="stat-card warning"><h3>EMAILS</h3><div class="value">''' + str(stats.get('with_emails', 0)) + '''</div></div>
        <div class="stat-card alert"><h3>RISQUE MOY.</h3><div class="value">''' + str(stats.get('avg_risk', 0)) + '''</div></div>
    </div>
    
    <div class="control-panel">
        <h2>Exporter les Donnees</h2>
        <div class="info-box">
            <p>Exportez les resultats du crawl dans differents formats pour analyse externe.</p>
        </div>
        <div class="form-row">
            <div class="form-group">
                <button class="btn btn-primary" onclick="exportData('json')">Export JSON</button>
                <button class="btn btn-primary" onclick="exportData('csv')">Export CSV</button>
                <button class="btn btn-warning" onclick="exportData('emails')">Export Emails</button>
                <button class="btn btn-purple" onclick="exportData('crypto')">Export Crypto</button>
            </div>
        </div>
        <div id="exportResult" style="margin-top: 15px;"></div>
    </div>
    
    <div class="grid-2">
        <div class="section">
            <div class="section-header">Sites a Haut Risque (Score >= 50)</div>
            <div class="section-content" style="max-height: none;">
                <table>
                    <thead><tr><th>Domaine</th><th>Titre</th><th>Risk</th></tr></thead>
                    <tbody>''' + high_risk_html + '''</tbody>
                </table>
            </div>
        </div>
        
        <div class="section">
            <div class="section-header">Activite (7 derniers jours)</div>
            <div class="section-content" style="max-height: none;">
                <div class="chart-container">
                    ''' + _render_simple_chart(timeline_labels, timeline_values) + '''
                </div>
            </div>
        </div>
    </div>
    
    <script>
    function exportData(type) {
        const status = document.getElementById('exportResult');
        status.innerHTML = '<span class="loading"></span> Export en cours...';
        
        fetch('/api/export', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({type: type})
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                status.innerHTML = '<span style="color: #00ff00;">' + data.message + '</span><br><code>' + (data.file || '') + '</code>';
            } else {
                status.innerHTML = '<span style="color: #ff4444;">' + data.message + '</span>';
            }
        })
        .catch(e => {
            status.innerHTML = '<span style="color: #ff4444;">Erreur</span>';
        });
    }
    </script>
    
    <style>
    .risk-score { color: #ff4444; font-weight: bold; }
    .chart-container { padding: 20px; }
    .chart-bar { display: inline-block; width: 30px; margin: 0 5px; background: #00ff00; vertical-align: bottom; }
    .chart-label { font-size: 10px; color: #888; text-align: center; }
    </style>'''
    
    return HTML_TEMPLATE.format(page_content=page_content, port=port, version=version, update_banner='',
        nav_dashboard='', nav_search='', nav_trusted='', nav_updates='')


def _render_simple_chart(labels: List[str], values: List[int]) -> str:
    """Genere un graphique simple en HTML/CSS."""
    if not values:
        return '<p style="color: #888;">Pas de donnees</p>'
    
    max_val = max(values) if values else 1
    chart_html = '<div style="display: flex; align-items: flex-end; height: 150px; gap: 5px;">'
    
    for i, (label, value) in enumerate(zip(labels, values)):
        height = int((value / max_val) * 120) if max_val > 0 else 0
        chart_html += '<div style="text-align: center;">'
        chart_html += '<div style="color: #00ff00; font-size: 10px;">' + str(value) + '</div>'
        chart_html += '<div style="width: 30px; height: ' + str(height) + 'px; background: linear-gradient(to top, #00ff00, #00aa00); border-radius: 3px 3px 0 0;"></div>'
        chart_html += '<div style="font-size: 9px; color: #666; margin-top: 5px;">' + html.escape(label[-5:]) + '</div>'
        chart_html += '</div>'
    
    chart_html += '</div>'
    return chart_html


def render_settings(domain_lists: Dict, port: int) -> str:
    """Genere la page des parametres."""
    version = "6.5.0"
    
    blacklist_html = ""
    for item in domain_lists.get('blacklist', [])[:20]:
        domain_escaped = html.escape(str(item.get('domain', '')))
        reason_escaped = html.escape(str(item.get('reason', ''))[:50])
        blacklist_html += '<tr>'
        blacklist_html += '<td class="domain">' + domain_escaped + '</td>'
        blacklist_html += '<td>' + reason_escaped + '</td>'
        blacklist_html += '<td><button class="btn btn-danger btn-small" onclick="removeFromList(\'' + domain_escaped + '\')">X</button></td>'
        blacklist_html += '</tr>'
    
    whitelist_html = ""
    for item in domain_lists.get('whitelist', [])[:20]:
        domain_escaped = html.escape(str(item.get('domain', '')))
        reason_escaped = html.escape(str(item.get('reason', ''))[:50])
        whitelist_html += '<tr>'
        whitelist_html += '<td class="domain">' + domain_escaped + '</td>'
        whitelist_html += '<td>' + reason_escaped + '</td>'
        whitelist_html += '<td><button class="btn btn-danger btn-small" onclick="removeFromList(\'' + domain_escaped + '\')">X</button></td>'
        whitelist_html += '</tr>'
    
    blacklist_count = str(len(domain_lists.get('blacklist', [])))
    whitelist_count = str(len(domain_lists.get('whitelist', [])))
    
    page_content = '''
    <div id="message" class="message"></div>
    
    <div class="control-panel">
        <h2>Ajouter un Domaine</h2>
        <div class="form-row">
            <div class="form-group" style="flex: 2;">
                <label>Domaine (.onion)</label>
                <input type="text" id="domainInput" placeholder="exemple.onion">
            </div>
            <div class="form-group" style="flex: 1;">
                <label>Liste</label>
                <select id="listType">
                    <option value="blacklist">Blacklist</option>
                    <option value="whitelist">Whitelist</option>
                </select>
            </div>
            <div class="form-group" style="flex: 2;">
                <label>Raison (optionnel)</label>
                <input type="text" id="reasonInput" placeholder="Raison...">
            </div>
            <div class="form-group" style="flex: 0;">
                <button class="btn btn-primary" onclick="addToList()">Ajouter</button>
            </div>
        </div>
    </div>
    
    <div class="grid-2">
        <div class="section">
            <div class="section-header">Blacklist (''' + blacklist_count + ''')</div>
            <div class="section-content" style="max-height: 400px;">
                <p style="color: #888; font-size: 11px; margin-bottom: 10px;">Les domaines blacklistes seront ignores.</p>
                <table>
                    <thead><tr><th>Domaine</th><th>Raison</th><th></th></tr></thead>
                    <tbody>''' + (blacklist_html or '<tr><td colspan="3" style="color: #888;">Aucun domaine</td></tr>') + '''</tbody>
                </table>
            </div>
        </div>
        
        <div class="section">
            <div class="section-header">Whitelist (''' + whitelist_count + ''')</div>
            <div class="section-content" style="max-height: 400px;">
                <p style="color: #888; font-size: 11px; margin-bottom: 10px;">Les domaines whitelistes seront priorises.</p>
                <table>
                    <thead><tr><th>Domaine</th><th>Raison</th><th></th></tr></thead>
                    <tbody>''' + (whitelist_html or '<tr><td colspan="3" style="color: #888;">Aucun domaine</td></tr>') + '''</tbody>
                </table>
            </div>
        </div>
    </div>
    
    <script>
    function addToList() {
        var domain = document.getElementById("domainInput").value.trim();
        var listType = document.getElementById("listType").value;
        var reason = document.getElementById("reasonInput").value.trim();
        
        if (!domain) { showMessage("Domaine requis", "error"); return; }
        
        fetch("/api/add-to-list", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({domain: domain, list_type: listType, reason: reason})
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            showMessage(data.message, data.success ? "success" : "error");
            if (data.success) {
                document.getElementById("domainInput").value = "";
                document.getElementById("reasonInput").value = "";
                setTimeout(function() { location.reload(); }, 1000);
            }
        });
    }
    
    function removeFromList(domain) {
        fetch("/api/remove-from-list", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({domain: domain})
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            showMessage(data.message, data.success ? "success" : "error");
            if (data.success) setTimeout(function() { location.reload(); }, 1000);
        });
    }
    </script>'''
    
    return HTML_TEMPLATE.format(page_content=page_content, port=port, version=version, update_banner='',
        nav_dashboard='', nav_search='', nav_trusted='', nav_updates='')
