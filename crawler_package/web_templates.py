"""
Templates HTML pour le serveur web.
Separe pour une meilleure lisibilite du code.
"""

import html
import json
import math
from datetime import datetime
from typing import Dict, List, Any


# Template HTML principal
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
        .nav-tabs {{ display: flex; gap: 10px; margin-bottom: 20px; justify-content: center; }}
        .nav-tab {{ padding: 10px 25px; background: #111; border: 1px solid #333; color: #888; cursor: pointer; border-radius: 5px; font-size: 14px; text-decoration: none; }}
        .nav-tab:hover, .nav-tab.active {{ background: #00ff00; color: #000; border-color: #00ff00; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .stat-card {{ background: #111; border: 1px solid #00ff00; padding: 15px; text-align: center; border-radius: 5px; }}
        .stat-card h3 {{ color: #888; font-size: 12px; margin-bottom: 8px; }}
        .stat-card .value {{ font-size: 28px; color: #00ff00; }}
        .stat-card.alert .value {{ color: #ff4444; }}
        .stat-card.warning .value {{ color: #ffaa00; }}
        .stat-card.info .value {{ color: #00aaff; }}
        .section {{ background: #111; border: 1px solid #333; margin-bottom: 20px; border-radius: 5px; }}
        .section-header {{ background: #1a1a1a; padding: 12px 15px; border-bottom: 1px solid #333; font-weight: bold; }}
        .section-content {{ padding: 15px; max-height: 350px; overflow-y: auto; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 8px 10px; text-align: left; border-bottom: 1px solid #222; font-size: 13px; }}
        th {{ color: #888; }}
        tr:hover {{ background: #1a1a1a; }}
        .tag {{ display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 11px; margin: 1px; }}
        .tag-secret {{ background: #ff4444; color: #fff; }}
        .tag-crypto {{ background: #9933ff; color: #fff; }}
        .tag-social {{ background: #00aaff; color: #fff; }}
        .tag-email {{ background: #ffaa00; color: #000; }}
        .url {{ color: #00ff00; word-break: break-all; font-size: 12px; }}
        .domain {{ color: #888; }}
        .title {{ color: #fff; }}
        .footer {{ text-align: center; padding: 20px; color: #444; font-size: 12px; }}
        .status-running {{ color: #00ff00; animation: blink 1s infinite; }}
        .status-stopped {{ color: #ff4444; }}
        @keyframes blink {{ 50% {{ opacity: 0.5; }} }}
        .control-panel {{ background: #111; border: 1px solid #00ff00; border-radius: 5px; padding: 15px; margin-bottom: 20px; }}
        .control-panel h2 {{ color: #00ff00; margin-bottom: 12px; font-size: 14px; }}
        .form-row {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: flex-end; }}
        .form-group {{ flex: 1; min-width: 200px; margin-bottom: 10px; }}
        .form-group label {{ display: block; color: #888; margin-bottom: 5px; font-size: 11px; }}
        .form-group input, .form-group textarea, .form-group select {{ width: 100%; padding: 8px; background: #0a0a0a; border: 1px solid #333; color: #00ff00; font-family: 'Courier New', monospace; border-radius: 3px; font-size: 12px; }}
        .form-group textarea {{ height: 60px; resize: vertical; }}
        .btn {{ padding: 8px 15px; border: none; border-radius: 3px; cursor: pointer; font-family: 'Courier New', monospace; font-weight: bold; font-size: 12px; margin-right: 5px; }}
        .btn-primary {{ background: #00ff00; color: #000; }}
        .btn-primary:hover {{ background: #00cc00; }}
        .btn-warning {{ background: #ffaa00; color: #000; }}
        .btn-small {{ padding: 4px 8px; font-size: 10px; }}
        .btn-copy {{ background: #333; color: #00ff00; border: 1px solid #00ff00; }}
        .message {{ padding: 8px; border-radius: 3px; margin-bottom: 10px; display: none; font-size: 12px; }}
        .message.success {{ background: #1a3a1a; border: 1px solid #00ff00; color: #00ff00; display: block; }}
        .message.error {{ background: #3a1a1a; border: 1px solid #ff4444; color: #ff4444; display: block; }}
        .grid-2 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }}
        .trust-score {{ display: inline-block; padding: 3px 8px; border-radius: 10px; font-size: 11px; font-weight: bold; }}
        .trust-high {{ background: #00ff00; color: #000; }}
        .trust-medium {{ background: #ffaa00; color: #000; }}
        .trust-low {{ background: #ff4444; color: #fff; }}
        .search-result {{ background: #1a1a1a; border: 1px solid #333; border-radius: 5px; padding: 15px; margin-bottom: 10px; }}
        .search-result:hover {{ border-color: #00ff00; }}
        .search-result-title {{ color: #00ff00; font-size: 14px; margin-bottom: 5px; }}
        .search-result-url {{ color: #888; font-size: 11px; word-break: break-all; }}
        .search-result-meta {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 8px; }}
        .refresh-info {{ text-align: center; color: #444; margin-bottom: 15px; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Darknet Crawler v6.4</h1>
        <div class="nav-tabs">
            <a href="/" class="nav-tab {nav_dashboard}">Dashboard</a>
            <a href="/search" class="nav-tab {nav_search}">Recherche</a>
            <a href="/trusted" class="nav-tab {nav_trusted}">Sites Fiables</a>
        </div>
        {page_content}
        <div class="footer">Darknet Omniscient Crawler v6.4 | Port {port}</div>
    </div>
    <script>
        function copyToClipboard(text) {{
            navigator.clipboard.writeText(text);
        }}
        function showMessage(text, type) {{
            const msg = document.getElementById('message');
            if (msg) {{
                msg.textContent = text;
                msg.className = 'message ' + type;
                setTimeout(() => {{ msg.className = 'message'; }}, 5000);
            }}
        }}
        function addSeeds() {{
            const urls = document.getElementById('seedUrls').value.trim().split('\\n').filter(u => u.trim());
            if (urls.length === 0) {{ showMessage('Entrez au moins une URL', 'error'); return; }}
            fetch('/api/add-seeds', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
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
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>'''


def render_dashboard(data: Dict[str, Any], port: int) -> str:
    """Genere la page dashboard."""
    # Intel rows
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
    <div class="control-panel">
        <h2>Ajouter des Sites a Explorer</h2>
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
    </div>
    '''
    
    return HTML_TEMPLATE.format(
        page_content=page_content, port=port,
        nav_dashboard='active', nav_search='', nav_trusted=''
    )


def render_search(results: List[Dict], query: str, filter_type: str, port: int) -> str:
    """Genere la page de recherche."""
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
        
        search_results_html += f'''
        <div class="search-result">
            <div class="search-result-title">{html.escape(str(r.get("title", "Sans titre"))[:100])}</div>
            <div class="search-result-url">{html.escape(str(r.get("url", ""))[:100])}</div>
            <div class="search-result-meta">
                <span class="domain">{html.escape(str(r.get("domain", ""))[:40])}</span>
                {"".join(tags)}
                <button class="btn btn-copy btn-small" onclick="copyToClipboard('{html.escape(r.get("url", ""))}')">Copier</button>
            </div>
        </div>'''
    
    if not search_results_html:
        search_results_html = '<div style="color: #888; text-align: center; padding: 40px;">Entrez une recherche ou selectionnez un filtre</div>'
    
    page_content = f'''
    <div class="control-panel">
        <h2>Rechercher dans la Base de Donnees</h2>
        <form method="GET" action="/search">
            <div class="form-row">
                <div class="form-group" style="flex: 3;">
                    <label>Recherche (titre, domaine, URL)</label>
                    <input type="text" name="q" value="{html.escape(query)}" placeholder="Entrez votre recherche...">
                </div>
                <div class="form-group" style="flex: 1;">
                    <label>Filtrer par</label>
                    <select name="filter">
                        <option value="all" {'selected' if filter_type == 'all' else ''}>Tout</option>
                        <option value="crypto" {'selected' if filter_type == 'crypto' else ''}>Crypto</option>
                        <option value="social" {'selected' if filter_type == 'social' else ''}>Social</option>
                        <option value="email" {'selected' if filter_type == 'email' else ''}>Emails</option>
                        <option value="secret" {'selected' if filter_type == 'secret' else ''}>Secrets</option>
                    </select>
                </div>
                <div class="form-group" style="flex: 0;">
                    <button type="submit" class="btn btn-primary">Rechercher</button>
                </div>
            </div>
        </form>
    </div>
    <div class="section">
        <div class="section-header">Resultats ({len(results)})</div>
        <div class="section-content" style="max-height: none;">{search_results_html}</div>
    </div>
    '''
    
    return HTML_TEMPLATE.format(
        page_content=page_content, port=port,
        nav_dashboard='', nav_search='active', nav_trusted=''
    )


def render_trusted(data: Dict[str, Any], port: int) -> str:
    """Genere la page des sites fiables."""
    trusted_html = ""
    for site in data['sites'][:12]:
        trust_class = f"trust-{site['trust_level']}"
        trusted_html += f'''
        <div class="search-result">
            <div class="search-result-title">
                <span class="trust-score {trust_class}">{site["score"]}</span>
                {html.escape(str(site.get("domain", ""))[:50])}
            </div>
            <div class="search-result-url">{html.escape(str(site.get("title", ""))[:80])}</div>
            <div class="search-result-meta">
                <span>{site["total_pages"]} pages</span>
                <span style="color: #00ff00">{site["success_rate"]}% succes</span>
                {"<span class='tag tag-secret'>INTEL</span>" if site["has_intel"] else ""}
                <button class="btn btn-copy btn-small" onclick="copyToClipboard('http://{html.escape(site.get("domain", ""))}/')">Copier</button>
            </div>
        </div>'''
    
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
    <div class="section">
        <div class="section-header">Sites les Plus Fiables</div>
        <div class="section-content" style="max-height: none;">
            <p style="color: #888; margin-bottom: 15px; font-size: 12px;">Score calcule selon: pages crawlees, taux de succes, presence de donnees structurees.</p>
            {trusted_html or '<div style="color:#888;">Aucun site analyse</div>'}
        </div>
    </div>
    <div class="section">
        <div class="section-header">Tous les Domaines Classes</div>
        <div class="section-content" style="max-height: 500px;">
            <table>
                <thead><tr><th>Domaine</th><th>Score</th><th>Pages</th><th>Succes</th><th>Intel</th></tr></thead>
                <tbody>{domain_table_html or '<tr><td colspan="5">Aucune donnee</td></tr>'}</tbody>
            </table>
        </div>
    </div>
    '''
    
    return HTML_TEMPLATE.format(
        page_content=page_content, port=port,
        nav_dashboard='', nav_search='', nav_trusted='active'
    )
