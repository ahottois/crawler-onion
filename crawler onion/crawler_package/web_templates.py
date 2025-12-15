"""
Templates HTML pour le serveur web.
Séparé pour une meilleure lisibilité du code.
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
    <title>??? Darknet Crawler Dashboard</title>
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
        .section-header {{ background: #1a1a1a; padding: 12px 15px; border-bottom: 1px solid #333; font-weight: bold; display: flex; justify-content: space-between; align-items: center; }}
        .section-content {{ padding: 15px; max-height: 350px; overflow-y: auto; }}
        .tabs {{ display: flex; gap: 5px; }}
        .tab {{ padding: 5px 15px; background: #222; border: 1px solid #333; color: #888; cursor: pointer; border-radius: 3px; font-size: 12px; }}
        .tab.active {{ background: #00ff00; color: #000; border-color: #00ff00; }}
        .tab:hover {{ border-color: #00ff00; }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
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
        .form-group input[type="text"], .form-group textarea, .form-group select {{ width: 100%; padding: 8px; background: #0a0a0a; border: 1px solid #333; color: #00ff00; font-family: 'Courier New', monospace; border-radius: 3px; font-size: 12px; }}
        .form-group textarea {{ height: 60px; resize: vertical; }}
        .form-group input:focus, .form-group textarea:focus, .form-group select:focus {{ border-color: #00ff00; outline: none; }}
        .btn {{ padding: 8px 15px; border: none; border-radius: 3px; cursor: pointer; font-family: 'Courier New', monospace; font-weight: bold; font-size: 12px; margin-right: 5px; }}
        .btn-primary {{ background: #00ff00; color: #000; }}
        .btn-primary:hover {{ background: #00cc00; }}
        .btn-warning {{ background: #ffaa00; color: #000; }}
        .btn-warning:hover {{ background: #cc8800; }}
        .btn-small {{ padding: 4px 8px; font-size: 10px; }}
        .btn-copy {{ background: #333; color: #00ff00; border: 1px solid #00ff00; }}
        .btn-copy:hover {{ background: #00ff00; color: #000; }}
        .message {{ padding: 8px; border-radius: 3px; margin-bottom: 10px; display: none; font-size: 12px; }}
        .message.success {{ background: #1a3a1a; border: 1px solid #00ff00; color: #00ff00; display: block; }}
        .message.error {{ background: #3a1a1a; border: 1px solid #ff4444; color: #ff4444; display: block; }}
        .quick-seeds {{ display: flex; flex-wrap: wrap; gap: 5px; }}
        .quick-seed {{ background: #1a1a1a; border: 1px solid #333; padding: 4px 8px; border-radius: 3px; font-size: 10px; color: #888; cursor: pointer; }}
        .quick-seed:hover {{ border-color: #00ff00; color: #00ff00; }}
        .graph-container {{ background: #0a0a0a; border: 1px solid #333; border-radius: 5px; padding: 20px; min-height: 400px; position: relative; }}
        .network-map {{ width: 100%; height: 500px; position: relative; overflow: hidden; }}
        .node {{ position: absolute; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; font-size: 10px; text-align: center; overflow: hidden; }}
        .node:hover {{ transform: scale(1.2); z-index: 100; }}
        .node-seed {{ background: #00ff00; color: #000; border: 2px solid #00ff00; box-shadow: 0 0 15px #00ff00; }}
        .node-intel {{ background: #ff4444; color: #fff; border: 2px solid #ff4444; box-shadow: 0 0 10px #ff4444; }}
        .node-crypto {{ background: #9933ff; color: #fff; border: 2px solid #9933ff; box-shadow: 0 0 10px #9933ff; }}
        .node-social {{ background: #00aaff; color: #fff; border: 2px solid #00aaff; box-shadow: 0 0 10px #00aaff; }}
        .node-normal {{ background: #333; color: #888; border: 1px solid #555; }}
        .node-tooltip {{ position: absolute; background: #111; border: 1px solid #00ff00; padding: 10px; border-radius: 5px; font-size: 11px; max-width: 300px; z-index: 1000; display: none; word-break: break-all; }}
        .node-tooltip.visible {{ display: block; }}
        .legend {{ display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 15px; padding: 10px; background: #111; border-radius: 5px; }}
        .legend-item {{ display: flex; align-items: center; gap: 5px; font-size: 11px; color: #888; }}
        .legend-dot {{ width: 12px; height: 12px; border-radius: 50%; }}
        .chart-bar {{ display: flex; align-items: flex-end; gap: 3px; height: 150px; padding: 10px 0; }}
        .bar {{ flex: 1; background: linear-gradient(to top, #00ff00, #004400); border-radius: 2px 2px 0 0; min-width: 20px; max-width: 40px; position: relative; cursor: pointer; }}
        .bar:hover {{ background: linear-gradient(to top, #00ff00, #00aa00); }}
        .bar-label {{ position: absolute; bottom: -20px; left: 50%; transform: translateX(-50%); font-size: 9px; color: #888; white-space: nowrap; }}
        .bar-value {{ position: absolute; top: -18px; left: 50%; transform: translateX(-50%); font-size: 10px; color: #00ff00; }}
        .timeline {{ display: flex; flex-direction: column; gap: 10px; max-height: 400px; overflow-y: auto; }}
        .timeline-item {{ display: flex; gap: 10px; padding: 8px; background: #1a1a1a; border-radius: 5px; border-left: 3px solid #00ff00; }}
        .timeline-item.intel {{ border-left-color: #ff4444; }}
        .timeline-item.crypto {{ border-left-color: #9933ff; }}
        .timeline-time {{ color: #888; font-size: 10px; min-width: 60px; }}
        .timeline-content {{ flex: 1; font-size: 12px; }}
        .grid-2 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }}
        .trust-score {{ display: inline-block; padding: 3px 8px; border-radius: 10px; font-size: 11px; font-weight: bold; }}
        .trust-high {{ background: #00ff00; color: #000; }}
        .trust-medium {{ background: #ffaa00; color: #000; }}
        .trust-low {{ background: #ff4444; color: #fff; }}
        .search-result {{ background: #1a1a1a; border: 1px solid #333; border-radius: 5px; padding: 15px; margin-bottom: 10px; }}
        .search-result:hover {{ border-color: #00ff00; }}
        .search-result-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }}
        .search-result-title {{ color: #00ff00; font-size: 14px; margin-bottom: 5px; }}
        .search-result-url {{ color: #888; font-size: 11px; word-break: break-all; }}
        .search-result-meta {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 8px; }}
        .copied-toast {{ position: fixed; bottom: 20px; right: 20px; background: #00ff00; color: #000; padding: 10px 20px; border-radius: 5px; display: none; z-index: 9999; font-weight: bold; }}
        .copied-toast.show {{ display: block; animation: fadeInOut 2s; }}
        @keyframes fadeInOut {{ 0%, 100% {{ opacity: 0; }} 10%, 90% {{ opacity: 1; }} }}
        .refresh-info {{ text-align: center; color: #444; margin-bottom: 15px; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>??? Darknet Crawler</h1>
        <div class="nav-tabs">
            <a href="/" class="nav-tab {nav_dashboard}">?? Dashboard</a>
            <a href="/search" class="nav-tab {nav_search}">?? Recherche</a>
            <a href="/trusted" class="nav-tab {nav_trusted}">? Sites Fiables</a>
        </div>
        {page_content}
        <div class="footer">Darknet Omniscient Crawler v6.4 | Port {port}</div>
    </div>
    <div class="copied-toast" id="copiedToast">? Copié!</div>
    <script>
        function copyToClipboard(text) {{
            navigator.clipboard.writeText(text).then(() => {{
                const toast = document.getElementById('copiedToast');
                toast.classList.add('show');
                setTimeout(() => toast.classList.remove('show'), 2000);
            }});
        }}
        let autoRefresh = true;
        let refreshTimer = null;
        function startAutoRefresh() {{
            if (refreshTimer) clearTimeout(refreshTimer);
            if (autoRefresh && window.location.pathname === '/') {{
                refreshTimer = setTimeout(() => location.reload(), 30000);
            }}
        }}
        function toggleAutoRefresh() {{
            autoRefresh = !autoRefresh;
            const el = document.getElementById('autoRefreshStatus');
            if (el) el.textContent = 'Auto-refresh: ' + (autoRefresh ? 'ON' : 'OFF');
            startAutoRefresh();
        }}
        function showMessage(text, type) {{
            const msg = document.getElementById('message');
            if (msg) {{
                msg.textContent = text;
                msg.className = 'message ' + type;
                setTimeout(() => {{ msg.className = 'message'; }}, 5000);
            }}
        }}
        function showTab(tabId) {{
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelector(`[onclick="showTab('${{tabId}}')"]`).classList.add('active');
            document.getElementById('tab-' + tabId).classList.add('active');
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
            }})
            .catch(e => showMessage('Erreur: ' + e, 'error'));
        }}
        function addQuickSeed(url) {{
            const ta = document.getElementById('seedUrls');
            if (ta && !ta.value.includes(url)) ta.value += (ta.value ? '\\n' : '') + url;
        }}
        function refreshLinks() {{
            fetch('/api/refresh-links', {{ method: 'POST' }})
            .then(r => r.json())
            .then(data => showMessage(data.message, data.success ? 'success' : 'error'))
            .catch(e => showMessage('Erreur: ' + e, 'error'));
        }}
        document.querySelectorAll('.node').forEach(node => {{
            node.addEventListener('mouseenter', (e) => {{
                const tooltip = document.getElementById('nodeTooltip');
                if (tooltip) {{
                    tooltip.innerHTML = `<strong>${{node.dataset.domain}}</strong><br>${{node.dataset.title || 'N/A'}}<br><span style="color:#888">${{node.dataset.tags || ''}}</span>`;
                    tooltip.style.left = (e.pageX + 10) + 'px';
                    tooltip.style.top = (e.pageY + 10) + 'px';
                    tooltip.classList.add('visible');
                }}
            }});
            node.addEventListener('mouseleave', () => {{
                const tooltip = document.getElementById('nodeTooltip');
                if (tooltip) tooltip.classList.remove('visible');
            }});
        }});
        startAutoRefresh();
    </script>
</body>
</html>'''


def render_dashboard(data: Dict[str, Any], port: int) -> str:
    """Génère la page dashboard."""
    # Network nodes
    network_nodes_html = ""
    node_count = len(data['graph_nodes'])
    center_x, center_y = 400, 250
    for i, node in enumerate(data['graph_nodes'][:40]):
        angle = (i / max(node_count, 1)) * 4 * math.pi
        radius = 80 + (i * 8)
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle) * 0.6
        has_secrets = node.get('secrets_found', '{}') != '{}'
        has_crypto = node.get('cryptos', '{}') != '{}'
        has_social = node.get('socials', '{}') != '{}'
        if has_secrets: node_class, size = 'node-intel', 45
        elif has_crypto: node_class, size = 'node-crypto', 40
        elif has_social: node_class, size = 'node-social', 35
        else: node_class, size = 'node-normal', 25
        domain = node.get('domain', '')[:15]
        title = html.escape(str(node.get('title', ''))[:50])
        tags = [t for t, c in [('SECRET', has_secrets), ('CRYPTO', has_crypto), ('SOCIAL', has_social)] if c]
        network_nodes_html += f'<div class="node {node_class}" style="left: {x}px; top: {y}px; width: {size}px; height: {size}px;" data-domain="{html.escape(node.get("domain", ""))}" data-title="{title}" data-tags="{", ".join(tags)}">{domain[:6]}</div>'
    
    # Charts
    domain_chart_html = ""
    max_pages = max((d.get('pages', 0) for d in data['domain_rows']), default=1)
    for d in data['domain_rows'][:10]:
        height = (d.get('pages', 0) / max_pages) * 130 if max_pages > 0 else 0
        domain_chart_html += f'<div class="bar" style="height: {max(height, 5)}px;" title="{d.get("domain", "")}"><span class="bar-value">{d.get("pages", 0)}</span><span class="bar-label">{html.escape(str(d.get("domain", ""))[:8])}</span></div>'
    
    intel_chart_html = ""
    intel_types = [('Emails', data['total_emails'], '#ffaa00'), ('Crypto', data['total_cryptos'], '#9933ff'), ('Social', data['total_socials'], '#00aaff'), ('Intel', data['intel_count'], '#ff4444')]
    max_intel = max((v for _, v, _ in intel_types), default=1)
    for name, value, color in intel_types:
        height = (value / max_intel) * 130 if max_intel > 0 else 0
        intel_chart_html += f'<div class="bar" style="height: {max(height, 5)}px; background: linear-gradient(to top, {color}, #111);"><span class="bar-value">{value}</span><span class="bar-label">{name}</span></div>'
    
    # Timeline
    timeline_html = "".join([f'<div class="timeline-item {"intel" if item.get("secrets_found", "{}") != "{}" else ("crypto" if item.get("cryptos", "{}") != "{}" else "")}"><span class="timeline-time">{str(item.get("found_at", ""))[-8:-3] if item.get("found_at") else ""}</span><span class="timeline-content"><strong>{html.escape(str(item.get("domain", ""))[:30])}</strong><br><span style="color: #888;">{html.escape(str(item.get("title", ""))[:50])}</span></span></div>' for item in data['timeline'][:20]]) or '<div style="color:#888;">Pas de données</div>'
    
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
    
    recent_rows_html = "".join([f'<tr><td style="color: {"#00ff00" if row.get("status", 0) == 200 else "#ff4444" if row.get("status", 0) >= 400 else "#ffaa00"}">{row.get("status", 0)}</td><td class="url">{html.escape(str(row.get("url", ""))[:70])}</td><td class="title">{html.escape(str(row.get("title", ""))[:30])}</td></tr>' for row in data['recent_rows']])
    domain_rows_html = "".join([f'<tr><td class="domain">{html.escape(str(row.get("domain", ""))[:35])}</td><td>{row.get("pages", 0)}</td><td style="color: #00ff00">{row.get("success", 0)}</td></tr>' for row in data['domain_rows']])
    
    success_rate = round((data['success_urls'] / data['total_urls'] * 100) if data['total_urls'] > 0 else 0, 1)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    page_content = f'''
    <p class="refresh-info">
        <span id="autoRefreshStatus">Auto-refresh: ON</span> | {timestamp} |
        <button class="btn btn-primary" onclick="location.reload()" style="padding: 3px 10px;">?? Refresh</button>
        <button class="btn" onclick="toggleAutoRefresh()" style="padding: 3px 10px; background: #333; color: #888;">Toggle Auto</button>
    </p>
    <div id="message" class="message"></div>
    <div class="stats-grid">
        <div class="stat-card"><h3>STATUS</h3><div class="value {"status-running" if data["status"] == "RUNNING" else "status-stopped"}">{data["status"]}</div></div>
        <div class="stat-card"><h3>URLS CRAWLÉES</h3><div class="value">{data["total_urls"]}</div></div>
        <div class="stat-card info"><h3>SUCCÈS (200)</h3><div class="value">{data["success_urls"]}</div></div>
        <div class="stat-card"><h3>DOMAINES</h3><div class="value">{data["domains"]}</div></div>
        <div class="stat-card warning"><h3>EN QUEUE</h3><div class="value">{data["queue_size"]}</div></div>
        <div class="stat-card alert"><h3>INTEL</h3><div class="value">{data["intel_count"]}</div></div>
    </div>
    <div class="control-panel">
        <h2>?? Ajouter des Sites à Explorer</h2>
        <div class="form-row">
            <div class="form-group" style="flex: 2;"><label>URLs .onion (une par ligne)</label><textarea id="seedUrls" placeholder="http://exemple.onion/"></textarea></div>
            <div class="form-group" style="flex: 1;"><button class="btn btn-primary" onclick="addSeeds()">? Ajouter</button><button class="btn btn-warning" onclick="refreshLinks()">?? Extraire liens</button></div>
        </div>
        <div class="quick-seeds">
            <span class="quick-seed" onclick="addQuickSeed('http://darkfailenbsdla5mal2mxn2uz66od5vtzd5qozslagrfzachha3f3id.onion/')">Dark.fail</span>
            <span class="quick-seed" onclick="addQuickSeed('http://torlinksge6enmcyyuxjpjkoouw4oorgdgeo7ftnq3zodj7g2zxi3kyd.onion/')">TorLinks</span>
            <span class="quick-seed" onclick="addQuickSeed('http://jaz45aabn5vkemy4jkg4mi4syheztb75ki6f5yzd5v7mreqxgpkrv5qd.onion/')">OnionLinks</span>
        </div>
    </div>
    <div class="section">
        <div class="section-header"><span>?? Visualisations</span>
            <div class="tabs">
                <span class="tab active" onclick="showTab('map')">??? Carte</span>
                <span class="tab" onclick="showTab('chart')">?? Stats</span>
                <span class="tab" onclick="showTab('timeline')">?? Timeline</span>
            </div>
        </div>
        <div class="section-content" style="max-height: none;">
            <div id="tab-map" class="tab-content active">
                <div class="legend">
                    <div class="legend-item"><div class="legend-dot" style="background: #00ff00;"></div> Normal</div>
                    <div class="legend-item"><div class="legend-dot" style="background: #ff4444;"></div> Secrets</div>
                    <div class="legend-item"><div class="legend-dot" style="background: #9933ff;"></div> Crypto</div>
                    <div class="legend-item"><div class="legend-dot" style="background: #00aaff;"></div> Social</div>
                </div>
                <div class="graph-container"><div class="network-map" id="networkMap">{network_nodes_html}</div><div class="node-tooltip" id="nodeTooltip"></div></div>
            </div>
            <div id="tab-chart" class="tab-content">
                <div class="grid-2">
                    <div><h3 style="color: #888; margin-bottom: 10px; font-size: 13px;">?? Top Domaines</h3><div class="chart-bar">{domain_chart_html or "<div>Pas de données</div>"}</div></div>
                    <div><h3 style="color: #888; margin-bottom: 10px; font-size: 13px;">?? Types Intel</h3><div class="chart-bar">{intel_chart_html}</div></div>
                </div>
                <div style="margin-top: 20px;"><h3 style="color: #888; margin-bottom: 10px; font-size: 13px;">?? Stats Globales</h3>
                    <div class="stats-grid">
                        <div class="stat-card"><h3>Taux Succès</h3><div class="value" style="font-size: 24px;">{success_rate}%</div></div>
                        <div class="stat-card"><h3>Emails</h3><div class="value" style="font-size: 24px;">{data["total_emails"]}</div></div>
                        <div class="stat-card"><h3>Crypto</h3><div class="value" style="font-size: 24px;">{data["total_cryptos"]}</div></div>
                        <div class="stat-card"><h3>Social</h3><div class="value" style="font-size: 24px;">{data["total_socials"]}</div></div>
                    </div>
                </div>
            </div>
            <div id="tab-timeline" class="tab-content"><div class="timeline">{timeline_html}</div></div>
        </div>
    </div>
    <div class="grid-2">
        <div class="section"><div class="section-header">?? Dernières Intel</div><div class="section-content"><table><thead><tr><th>Domaine</th><th>Titre</th><th>Tags</th></tr></thead><tbody>{intel_rows_html or "<tr><td colspan='3'>Aucune donnée</td></tr>"}</tbody></table></div></div>
        <div class="section"><div class="section-header">?? Top Domaines</div><div class="section-content"><table><thead><tr><th>Domaine</th><th>Pages</th><th>OK</th></tr></thead><tbody>{domain_rows_html or "<tr><td colspan='3'>Aucune donnée</td></tr>"}</tbody></table></div></div>
    </div>
    <div class="section"><div class="section-header">?? Dernières URLs</div><div class="section-content"><table><thead><tr><th>Status</th><th>URL</th><th>Titre</th></tr></thead><tbody>{recent_rows_html or "<tr><td colspan='3'>Aucune donnée</td></tr>"}</tbody></table></div></div>
    '''
    
    return HTML_TEMPLATE.format(
        page_content=page_content, port=port,
        nav_dashboard='active', nav_search='', nav_trusted=''
    )


def render_search(results: List[Dict], query: str, filter_type: str, port: int) -> str:
    """Génère la page de recherche."""
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
            <div class="search-result-header">
                <div>
                    <div class="search-result-title">{html.escape(str(r.get("title", "Sans titre"))[:100])}</div>
                    <div class="search-result-url">{html.escape(str(r.get("url", ""))[:100])}</div>
                </div>
                <button class="btn btn-copy btn-small" onclick="copyToClipboard('{html.escape(r.get("url", ""))}')">?? Copier</button>
            </div>
            <div class="search-result-meta">
                <span class="domain">?? {html.escape(str(r.get("domain", ""))[:40])}</span>
                {"".join(tags)}
            </div>
        </div>'''
    
    if not search_results_html:
        search_results_html = '<div style="color: #888; text-align: center; padding: 40px;">Entrez une recherche ou sélectionnez un filtre</div>'
    
    page_content = f'''
    <div class="control-panel">
        <h2>?? Rechercher dans la Base de Données</h2>
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
                    <button type="submit" class="btn btn-primary">?? Rechercher</button>
                </div>
            </div>
        </form>
    </div>
    <div class="section">
        <div class="section-header">
            <span>?? Résultats ({len(results)})</span>
        </div>
        <div class="section-content" style="max-height: none;">
            {search_results_html}
        </div>
    </div>
    '''
    
    return HTML_TEMPLATE.format(
        page_content=page_content, port=port,
        nav_dashboard='', nav_search='active', nav_trusted=''
    )


def render_trusted(data: Dict[str, Any], port: int) -> str:
    """Génère la page des sites fiables."""
    # Top trusted sites cards
    trusted_html = ""
    for site in data['sites'][:12]:
        trust_class = f"trust-{site['trust_level']}"
        trusted_html += f'''
        <div class="search-result">
            <div class="search-result-header">
                <div>
                    <div class="search-result-title">
                        <span class="trust-score {trust_class}">{site["score"]}</span>
                        {html.escape(str(site.get("domain", ""))[:50])}
                    </div>
                    <div class="search-result-url">{html.escape(str(site.get("title", ""))[:80])}</div>
                </div>
                <button class="btn btn-copy btn-small" onclick="copyToClipboard('http://{html.escape(site.get("domain", ""))}/')">?? Copier</button>
            </div>
            <div class="search-result-meta">
                <span>?? {site["total_pages"]} pages</span>
                <span style="color: #00ff00">? {site["success_rate"]}% succès</span>
                {"<span class='tag tag-secret'>INTEL</span>" if site["has_intel"] else ""}
            </div>
        </div>'''
    
    # Domain table
    domain_table_html = ""
    for site in data['sites']:
        trust_class = f"trust-{site['trust_level']}"
        domain_table_html += f'''
        <tr>
            <td class="domain">{html.escape(str(site.get("domain", ""))[:40])}</td>
            <td><span class="trust-score {trust_class}">{site["score"]}</span></td>
            <td>{site["total_pages"]}</td>
            <td style="color: #00ff00">{site["success_rate"]}%</td>
            <td>{"?" if site["has_intel"] else "-"}</td>
            <td><button class="btn btn-copy btn-small" onclick="copyToClipboard('http://{html.escape(site.get("domain", ""))}/')">??</button></td>
        </tr>'''
    
    page_content = f'''
    <div class="stats-grid">
        <div class="stat-card"><h3>SITES ANALYSÉS</h3><div class="value">{data['total']}</div></div>
        <div class="stat-card info"><h3>HAUTE CONFIANCE</h3><div class="value">{data['high_trust']}</div></div>
        <div class="stat-card warning"><h3>CONFIANCE MOYENNE</h3><div class="value">{data['medium_trust']}</div></div>
        <div class="stat-card alert"><h3>FAIBLE CONFIANCE</h3><div class="value">{data['low_trust']}</div></div>
    </div>
    <div class="section">
        <div class="section-header"><span>? Sites les Plus Fiables (Score de Confiance)</span></div>
        <div class="section-content" style="max-height: none;">
            <p style="color: #888; margin-bottom: 15px; font-size: 12px;">
                Le score de confiance est calculé selon: pages crawlées, taux de succès, présence de données structurées.
            </p>
            {trusted_html or '<div style="color:#888;">Aucun site analysé</div>'}
        </div>
    </div>
    <div class="section">
        <div class="section-header"><span>?? Tous les Domaines Classés</span></div>
        <div class="section-content" style="max-height: 500px;">
            <table>
                <thead><tr><th>Domaine</th><th>Score</th><th>Pages</th><th>Succès</th><th>Intel</th><th>Actions</th></tr></thead>
                <tbody>{domain_table_html or '<tr><td colspan="6">Aucune donnée</td></tr>'}</tbody>
            </table>
        </div>
    </div>
    '''
    
    return HTML_TEMPLATE.format(
        page_content=page_content, port=port,
        nav_dashboard='', nav_search='', nav_trusted='active'
    )
