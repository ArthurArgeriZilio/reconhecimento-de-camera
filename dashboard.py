"""
DEMI Dashboard - Painel de KPIs e Seguranca Industrial
======================================================
Servidor web Flask que le dados do banco SQLite do DEMI
e exibe KPIs, graficos e alertas de seguranca no navegador.

Uso:
  python dashboard.py
  Acessar: http://localhost:5000
"""

from flask import Flask, render_template_string, jsonify
import sqlite3
import os

app = Flask(__name__)
DB_PATH = "demi_data.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DEMI Dashboard - Seguranca Industrial</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: #0f0f1a;
            color: #e0e0e0;
            min-height: 100vh;
        }
        .header {
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            padding: 20px 30px;
            border-bottom: 2px solid #e94560;
            display: flex; justify-content: space-between; align-items: center;
        }
        .header h1 { font-size: 1.8em; color: #e94560; }
        .header .subtitle { color: #888; font-size: 0.9em; }
        .header .status { display: flex; align-items: center; gap: 8px; }
        .status-dot {
            width: 12px; height: 12px; background: #00ff88;
            border-radius: 50%; animation: pulse 2s infinite;
        }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
        .container { padding: 20px 30px; }

        /* Tabs */
        .tabs { display: flex; gap: 4px; margin-bottom: 20px; }
        .tab {
            padding: 10px 24px; border: 1px solid #2a2a4a; border-bottom: none;
            border-radius: 8px 8px 0 0; cursor: pointer; background: #1a1a2e;
            color: #888; font-size: 0.9em; transition: all 0.2s;
        }
        .tab.active { background: #16213e; color: #e94560; border-color: #e94560; }
        .tab:hover { color: #e94560; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }

        /* KPI Cards */
        .kpis {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px; margin-bottom: 24px;
        }
        .kpi-card {
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            border: 1px solid #2a2a4a; border-radius: 12px;
            padding: 18px; text-align: center;
            transition: transform 0.2s, border-color 0.2s;
        }
        .kpi-card:hover { transform: translateY(-3px); border-color: #e94560; }
        .kpi-card.danger { border-color: #e94560; }
        .kpi-card.warning { border-color: #ffa500; }
        .kpi-card.safe { border-color: #00ff88; }
        .kpi-value { font-size: 2.2em; font-weight: bold; color: #e94560; margin: 6px 0; }
        .kpi-value.green { color: #00ff88; }
        .kpi-value.orange { color: #ffa500; }
        .kpi-label { font-size: 0.8em; color: #888; text-transform: uppercase; letter-spacing: 1px; }
        .kpi-detail { font-size: 0.72em; color: #555; margin-top: 4px; }

        /* Charts */
        .charts {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
            gap: 18px; margin-bottom: 24px;
        }
        .chart-card {
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            border: 1px solid #2a2a4a; border-radius: 12px; padding: 18px;
        }
        .chart-card h3 { color: #e94560; margin-bottom: 10px; font-size: 0.95em; text-transform: uppercase; letter-spacing: 1px; }

        /* Tables */
        .table-card {
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            border: 1px solid #2a2a4a; border-radius: 12px;
            padding: 18px; overflow-x: auto; margin-bottom: 20px;
        }
        .table-card h3 { color: #e94560; margin-bottom: 10px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #2a2a4a; }
        th { color: #e94560; font-size: 0.78em; text-transform: uppercase; letter-spacing: 1px; }
        td { font-size: 0.85em; }
        tr:hover td { background: rgba(233,69,96,0.05); }
        .badge {
            display: inline-block; padding: 2px 8px; border-radius: 4px;
            font-size: 0.75em; font-weight: bold;
        }
        .badge-danger { background: rgba(233,69,96,0.3); color: #ff6b81; }
        .badge-warning { background: rgba(255,165,0,0.3); color: #ffa500; }
        .badge-safe { background: rgba(0,255,136,0.2); color: #00ff88; }

        .refresh-btn {
            background: #e94560; color: white; border: none;
            padding: 8px 20px; border-radius: 6px; cursor: pointer; font-size: 0.9em;
        }
        .refresh-btn:hover { background: #c73652; }
        .auto-refresh { color: #888; font-size: 0.8em; }

        /* Safety Score */
        .safety-score {
            display: flex; align-items: center; justify-content: center;
            gap: 12px; padding: 16px; background: linear-gradient(135deg, #1a1a2e, #16213e);
            border: 1px solid #2a2a4a; border-radius: 12px; margin-bottom: 20px;
        }
        .score-circle {
            width: 100px; height: 100px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-size: 2em; font-weight: bold;
        }
        .score-high { border: 4px solid #00ff88; color: #00ff88; }
        .score-mid { border: 4px solid #ffa500; color: #ffa500; }
        .score-low { border: 4px solid #e94560; color: #e94560; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>DEMI Dashboard</h1>
            <div class="subtitle">Monitoramento de Seguranca Industrial — Industria 4.0</div>
        </div>
        <div class="status">
            <div class="status-dot"></div>
            <span class="auto-refresh">Atualiza a cada 3s</span>
            <button class="refresh-btn" onclick="loadData()">Atualizar</button>
        </div>
    </div>

    <div class="container">
        <!-- Tabs -->
        <div class="tabs">
            <div class="tab active" onclick="switchTab('detections')">Deteccoes</div>
            <div class="tab" onclick="switchTab('safety')">Seguranca Industrial</div>
        </div>

        <!-- TAB: Deteccoes -->
        <div id="tab-detections" class="tab-content active">
            <div class="kpis" id="kpiContainer"></div>
            <div class="charts">
                <div class="chart-card">
                    <h3>Deteccoes ao Longo do Tempo</h3>
                    <canvas id="timelineChart"></canvas>
                </div>
                <div class="chart-card">
                    <h3>Distribuicao de Deteccoes</h3>
                    <canvas id="pieChart"></canvas>
                </div>
                <div class="chart-card">
                    <h3>FPS ao Longo do Tempo</h3>
                    <canvas id="fpsChart"></canvas>
                </div>
                <div class="chart-card">
                    <h3>Maos e Dedos Detectados</h3>
                    <canvas id="handsChart"></canvas>
                </div>
            </div>
            <div class="table-card">
                <h3>Ultimos Registros</h3>
                <table>
                    <thead><tr>
                        <th>Horario</th><th>Pose</th><th>Maos</th>
                        <th>Dedos</th><th>Rosto</th><th>FPS</th><th>Sessao</th>
                    </tr></thead>
                    <tbody id="tableBody"></tbody>
                </table>
            </div>
        </div>

        <!-- TAB: Seguranca -->
        <div id="tab-safety" class="tab-content">
            <div class="safety-score" id="safetyScoreContainer">
                <div class="score-circle score-high" id="scoreCircle">--</div>
                <div>
                    <div style="font-size:1.3em;font-weight:bold;">Indice de Seguranca</div>
                    <div style="color:#888;font-size:0.85em;" id="scoreDesc">Coletando dados...</div>
                </div>
            </div>
            <div class="kpis" id="safetyKpis"></div>
            <div class="charts">
                <div class="chart-card">
                    <h3>Alertas por Tipo</h3>
                    <canvas id="alertTypeChart"></canvas>
                </div>
                <div class="chart-card">
                    <h3>Alertas ao Longo do Tempo</h3>
                    <canvas id="alertTimelineChart"></canvas>
                </div>
            </div>
            <div class="table-card">
                <h3>Ultimos Alertas de Seguranca</h3>
                <table>
                    <thead><tr>
                        <th>Horario</th><th>Tipo</th><th>Descricao</th>
                        <th>Severidade</th><th>Sessao</th>
                    </tr></thead>
                    <tbody id="alertTableBody"></tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        let timelineChart, pieChart, fpsChart, handsChart, alertTypeChart, alertTimelineChart;

        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.getElementById('tab-' + tab).classList.add('active');
            event.target.classList.add('active');
        }

        function initCharts() {
            const gc = 'rgba(255,255,255,0.05)', tc = '#888';
            const opts = {
                responsive: true,
                plugins: { legend: { labels: { color: tc } } },
                scales: {
                    x: { grid: { color: gc }, ticks: { color: tc, maxTicksLimit: 15 } },
                    y: { grid: { color: gc }, ticks: { color: tc }, beginAtZero: true }
                }
            };

            timelineChart = new Chart(document.getElementById('timelineChart'), {
                type: 'line', data: { labels: [], datasets: [] },
                options: { ...opts, interaction: { intersect: false, mode: 'index' } }
            });
            pieChart = new Chart(document.getElementById('pieChart'), {
                type: 'doughnut', data: { labels: [], datasets: [] },
                options: { responsive: true, plugins: { legend: { position: 'bottom', labels: { color: tc, padding: 14 } } } }
            });
            fpsChart = new Chart(document.getElementById('fpsChart'), {
                type: 'line', data: { labels: [], datasets: [] },
                options: { ...opts, interaction: { intersect: false } }
            });
            handsChart = new Chart(document.getElementById('handsChart'), {
                type: 'bar', data: { labels: [], datasets: [] }, options: opts
            });
            alertTypeChart = new Chart(document.getElementById('alertTypeChart'), {
                type: 'doughnut', data: { labels: [], datasets: [] },
                options: { responsive: true, plugins: { legend: { position: 'bottom', labels: { color: tc, padding: 14 } } } }
            });
            alertTimelineChart = new Chart(document.getElementById('alertTimelineChart'), {
                type: 'bar', data: { labels: [], datasets: [] }, options: opts
            });
        }

        const typeLabels = {
            'drowsiness': 'Sonolencia',
            'yawn': 'Bocejo',
            'distraction': 'Distracao',
            'inactivity': 'Inatividade',
            'blink_rate': 'Piscadas/Fadiga',
            'head_down': 'Cabeca Baixa',
            'posture': 'Postura Ombros',
            'trunk_lean': 'Incl. Tronco',
            'arms_up': 'Bracos Elevados',
            'squat': 'Agachamento',
            'fall': 'Queda',
            'hand_speed': 'Veloc. Maos'
        };
        const typeColors = {
            'drowsiness': '#e94560',
            'yawn': '#ff6b9d',
            'distraction': '#4ecdc4',
            'inactivity': '#a855f7',
            'blink_rate': '#ffd700',
            'head_down': '#ff8c42',
            'posture': '#ffa500',
            'trunk_lean': '#20b2aa',
            'arms_up': '#6a5acd',
            'squat': '#2ecc71',
            'fall': '#ff0000',
            'hand_speed': '#00bfff'
        };

        function renderKPIs(kpis) {
            document.getElementById('kpiContainer').innerHTML = `
                <div class="kpi-card"><div class="kpi-label">Total Registros</div><div class="kpi-value">${kpis.total_records}</div><div class="kpi-detail">${kpis.total_sessions} sessao(oes)</div></div>
                <div class="kpi-card"><div class="kpi-label">Deteccao Pose</div><div class="kpi-value">${kpis.pose_rate}%</div><div class="kpi-detail">${kpis.pose_count} deteccoes</div></div>
                <div class="kpi-card"><div class="kpi-label">Deteccao Rosto</div><div class="kpi-value">${kpis.face_rate}%</div><div class="kpi-detail">${kpis.face_count} deteccoes</div></div>
                <div class="kpi-card"><div class="kpi-label">Media Maos</div><div class="kpi-value">${kpis.avg_hands}</div><div class="kpi-detail">por leitura</div></div>
                <div class="kpi-card"><div class="kpi-label">Media Dedos</div><div class="kpi-value">${kpis.avg_fingers}</div><div class="kpi-detail">quando detectado</div></div>
                <div class="kpi-card"><div class="kpi-label">FPS Medio</div><div class="kpi-value">${kpis.avg_fps}</div><div class="kpi-detail">min: ${kpis.min_fps} / max: ${kpis.max_fps}</div></div>
                <div class="kpi-card"><div class="kpi-label">Tempo Coleta</div><div class="kpi-value">${kpis.collection_time}</div><div class="kpi-detail">${kpis.first_record} - ${kpis.last_record}</div></div>
                <div class="kpi-card"><div class="kpi-label">Max Dedos</div><div class="kpi-value">${kpis.max_fingers}</div><div class="kpi-detail">simultaneos</div></div>
            `;
        }

        function renderSafetyKPIs(safety) {
            const score = safety.safety_score;
            const el = document.getElementById('scoreCircle');
            el.textContent = score + '%';
            el.className = 'score-circle ' + (score >= 80 ? 'score-high' : score >= 50 ? 'score-mid' : 'score-low');
            document.getElementById('scoreDesc').textContent =
                score >= 80 ? 'Ambiente seguro — poucos alertas' :
                score >= 50 ? 'Atencao — alertas frequentes' : 'Critico — muitos alertas de seguranca';

            document.getElementById('safetyKpis').innerHTML = `
                <div class="kpi-card danger"><div class="kpi-label">Total Alertas</div><div class="kpi-value">${safety.total_alerts}</div><div class="kpi-detail">nesta coleta</div></div>
                <div class="kpi-card safe"><div class="kpi-label">Alertas/Hora</div><div class="kpi-value green">${safety.alerts_per_hour}</div><div class="kpi-detail">taxa media</div></div>
                <div class="kpi-card warning"><div class="kpi-label">Sonolencia</div><div class="kpi-value orange">${safety.drowsiness_count}</div><div class="kpi-detail">EAR olhos fechados</div></div>
                <div class="kpi-card warning"><div class="kpi-label">Bocejo</div><div class="kpi-value orange">${safety.yawn_count}</div><div class="kpi-detail">MAR boca aberta</div></div>
                <div class="kpi-card"><div class="kpi-label">Distracao</div><div class="kpi-value">${safety.distraction_count}</div><div class="kpi-detail">cabeca virada</div></div>
                <div class="kpi-card"><div class="kpi-label">Piscadas</div><div class="kpi-value">${safety.blink_count}</div><div class="kpi-detail">freq. anormal</div></div>
                <div class="kpi-card"><div class="kpi-label">Cab. Baixa</div><div class="kpi-value">${safety.head_down_count}</div><div class="kpi-detail">olhando p/ baixo</div></div>
                <div class="kpi-card warning"><div class="kpi-label">Postura</div><div class="kpi-value orange">${safety.posture_count}</div><div class="kpi-detail">ombros inclinados</div></div>
                <div class="kpi-card"><div class="kpi-label">Tronco</div><div class="kpi-value">${safety.trunk_count}</div><div class="kpi-detail">inclinacao frontal</div></div>
                <div class="kpi-card"><div class="kpi-label">Bracos</div><div class="kpi-value">${safety.arms_count}</div><div class="kpi-detail">elevados demais</div></div>
                <div class="kpi-card"><div class="kpi-label">Agachamento</div><div class="kpi-value">${safety.squat_count}</div><div class="kpi-detail">joelhos flexionados</div></div>
                <div class="kpi-card danger"><div class="kpi-label">Queda</div><div class="kpi-value">${safety.fall_count}</div><div class="kpi-detail">pose perdida</div></div>
                <div class="kpi-card"><div class="kpi-label">Inatividade</div><div class="kpi-value">${safety.inactivity_count}</div><div class="kpi-detail">maos paradas</div></div>
                <div class="kpi-card"><div class="kpi-label">Veloc. Maos</div><div class="kpi-value">${safety.hand_speed_count}</div><div class="kpi-detail">velocidade excessiva</div></div>
            `;
        }

        function updateCharts(d) {
            timelineChart.data.labels = d.timeline.labels;
            timelineChart.data.datasets = [
                { label: 'Pose', data: d.timeline.pose, borderColor: '#e94560', backgroundColor: 'rgba(233,69,96,0.1)', fill: true, tension: 0.3 },
                { label: 'Rosto', data: d.timeline.face, borderColor: '#00ff88', backgroundColor: 'rgba(0,255,136,0.1)', fill: true, tension: 0.3 },
                { label: 'Maos', data: d.timeline.hands, borderColor: '#4ecdc4', backgroundColor: 'rgba(78,205,196,0.1)', fill: true, tension: 0.3 }
            ];
            timelineChart.update();

            pieChart.data.labels = ['Pose', 'Rosto', 'Maos', 'Nenhuma'];
            pieChart.data.datasets = [{ data: [d.distribution.pose, d.distribution.face, d.distribution.hands, d.distribution.none], backgroundColor: ['#e94560','#00ff88','#4ecdc4','#333'] }];
            pieChart.update();

            fpsChart.data.labels = d.fps_data.labels;
            fpsChart.data.datasets = [{ label: 'FPS', data: d.fps_data.values, borderColor: '#ffd700', backgroundColor: 'rgba(255,215,0,0.1)', fill: true, tension: 0.3 }];
            fpsChart.update();

            handsChart.data.labels = d.hands_data.labels;
            handsChart.data.datasets = [
                { label: 'Maos', data: d.hands_data.hands, backgroundColor: 'rgba(78,205,196,0.6)' },
                { label: 'Dedos', data: d.hands_data.fingers, backgroundColor: 'rgba(233,69,96,0.6)' }
            ];
            handsChart.update();
        }

        function updateSafetyCharts(safety) {
            const types = safety.alert_types || {};
            const labels = Object.keys(types).map(k => typeLabels[k] || k);
            const values = Object.values(types);
            const colors = Object.keys(types).map(k => typeColors[k] || '#888');

            alertTypeChart.data.labels = labels;
            alertTypeChart.data.datasets = [{ data: values, backgroundColor: colors }];
            alertTypeChart.update();

            const tl = safety.alert_timeline || {};
            alertTimelineChart.data.labels = tl.labels || [];
            alertTimelineChart.data.datasets = [{ label: 'Alertas', data: tl.values || [], backgroundColor: 'rgba(233,69,96,0.6)' }];
            alertTimelineChart.update();
        }

        function renderTable(rows) {
            document.getElementById('tableBody').innerHTML = rows.map(r => `<tr>
                <td>${r.timestamp}</td><td>${r.pose_detected ? '\\u2705' : '\\u274c'}</td>
                <td>${r.hands_count}</td><td>${r.fingers_count}</td>
                <td>${r.face_detected ? '\\u2705' : '\\u274c'}</td><td>${r.fps}</td><td>${r.session_id}</td>
            </tr>`).join('');
        }

        function renderAlertTable(rows) {
            document.getElementById('alertTableBody').innerHTML = rows.map(r => {
                const sev = r.severity === 'danger' ? 'badge-danger' : 'badge-warning';
                return `<tr>
                    <td>${r.timestamp}</td>
                    <td>${typeLabels[r.alert_type] || r.alert_type}</td>
                    <td>${r.description}</td>
                    <td><span class="badge ${sev}">${r.severity.toUpperCase()}</span></td>
                    <td>${r.session_id}</td>
                </tr>`;
            }).join('');
        }

        async function loadData() {
            try {
                const res = await fetch('/api/data');
                const data = await res.json();
                if (data.error) return;
                renderKPIs(data.kpis);
                updateCharts(data);
                renderTable(data.recent);
                renderSafetyKPIs(data.safety);
                updateSafetyCharts(data.safety);
                renderAlertTable(data.recent_alerts);
            } catch (e) { console.error('Erro:', e); }
        }

        initCharts();
        loadData();
        setInterval(loadData, 3000);
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(DASHBOARD_HTML)


@app.route("/api/data")
def api_data():
    if not os.path.exists(DB_PATH):
        return jsonify({"error": "Banco de dados nao encontrado. Execute o DEMI primeiro."})

    conn = get_db()

    # --- Detection KPIs ---
    stats = conn.execute("""
        SELECT COUNT(*) as total, SUM(pose_detected) as pose_count,
            SUM(face_detected) as face_count,
            ROUND(AVG(hands_count),1) as avg_hands,
            ROUND(AVG(CASE WHEN hands_count>0 THEN fingers_count END),1) as avg_fingers,
            MAX(fingers_count) as max_fingers,
            ROUND(AVG(fps),1) as avg_fps, ROUND(MIN(fps),1) as min_fps,
            ROUND(MAX(fps),1) as max_fps,
            MIN(timestamp) as first_ts, MAX(timestamp) as last_ts
        FROM detections
    """).fetchone()

    total = stats["total"] or 0
    total_sessions = conn.execute("SELECT COUNT(*) as c FROM sessions").fetchone()["c"]

    if total > 0:
        first_epoch = conn.execute("SELECT MIN(epoch) FROM detections").fetchone()[0]
        last_epoch = conn.execute("SELECT MAX(epoch) FROM detections").fetchone()[0]
        diff = (last_epoch or 0) - (first_epoch or 0)
        h, m, s = int(diff//3600), int((diff%3600)//60), int(diff%60)
        collection_time = f"{h}h {m}m" if h else f"{m}m {s}s" if m else f"{s}s"
    else:
        diff = 0
        collection_time = "0s"

    kpis = {
        "total_records": total, "total_sessions": total_sessions,
        "pose_count": stats["pose_count"] or 0,
        "pose_rate": round((stats["pose_count"] or 0)/total*100, 1) if total else 0,
        "face_count": stats["face_count"] or 0,
        "face_rate": round((stats["face_count"] or 0)/total*100, 1) if total else 0,
        "avg_hands": stats["avg_hands"] or 0, "avg_fingers": stats["avg_fingers"] or 0,
        "max_fingers": stats["max_fingers"] or 0,
        "avg_fps": stats["avg_fps"] or 0, "min_fps": stats["min_fps"] or 0, "max_fps": stats["max_fps"] or 0,
        "collection_time": collection_time,
        "first_record": (stats["first_ts"] or "")[:19].replace("T"," "),
        "last_record": (stats["last_ts"] or "")[:19].replace("T"," "),
    }

    # --- Timeline ---
    tl = conn.execute("SELECT timestamp, pose_detected, hands_count, face_detected FROM detections ORDER BY epoch DESC LIMIT 100").fetchall()
    tl.reverse()
    timeline = {"labels": [r["timestamp"][11:19] for r in tl],
                "pose": [r["pose_detected"] for r in tl],
                "hands": [r["hands_count"] for r in tl],
                "face": [r["face_detected"] for r in tl]}

    distribution = {
        "pose": kpis["pose_count"], "face": kpis["face_count"],
        "hands": conn.execute("SELECT COUNT(*) FROM detections WHERE hands_count>0").fetchone()[0],
        "none": conn.execute("SELECT COUNT(*) FROM detections WHERE pose_detected=0 AND hands_count=0 AND face_detected=0").fetchone()[0],
    }

    fr = conn.execute("SELECT timestamp, fps FROM detections ORDER BY epoch DESC LIMIT 100").fetchall()
    fr.reverse()
    fps_data = {"labels": [r["timestamp"][11:19] for r in fr], "values": [r["fps"] for r in fr]}

    hr = conn.execute("SELECT timestamp, hands_count, fingers_count FROM detections ORDER BY epoch DESC LIMIT 50").fetchall()
    hr.reverse()
    hands_data = {"labels": [r["timestamp"][11:19] for r in hr],
                  "hands": [r["hands_count"] for r in hr], "fingers": [r["fingers_count"] for r in hr]}

    recent = [{
        "timestamp": r["timestamp"][:19].replace("T"," "),
        "pose_detected": r["pose_detected"], "hands_count": r["hands_count"],
        "fingers_count": r["fingers_count"], "face_detected": r["face_detected"],
        "fps": r["fps"], "session_id": r["session_id"],
    } for r in conn.execute("SELECT * FROM detections ORDER BY epoch DESC LIMIT 20").fetchall()]

    # --- Safety Alerts ---
    # Check if alerts table exists
    has_alerts = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alerts'").fetchone()

    if has_alerts:
        total_alerts = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        drowsiness_count = conn.execute("SELECT COUNT(*) FROM alerts WHERE alert_type='drowsiness'").fetchone()[0]
        yawn_count = conn.execute("SELECT COUNT(*) FROM alerts WHERE alert_type='yawn'").fetchone()[0]
        distraction_count = conn.execute("SELECT COUNT(*) FROM alerts WHERE alert_type='distraction'").fetchone()[0]
        inactivity_count = conn.execute("SELECT COUNT(*) FROM alerts WHERE alert_type='inactivity'").fetchone()[0]
        blink_count = conn.execute("SELECT COUNT(*) FROM alerts WHERE alert_type='blink_rate'").fetchone()[0]
        head_down_count = conn.execute("SELECT COUNT(*) FROM alerts WHERE alert_type='head_down'").fetchone()[0]
        posture_count = conn.execute("SELECT COUNT(*) FROM alerts WHERE alert_type='posture'").fetchone()[0]
        trunk_count = conn.execute("SELECT COUNT(*) FROM alerts WHERE alert_type='trunk_lean'").fetchone()[0]
        arms_count = conn.execute("SELECT COUNT(*) FROM alerts WHERE alert_type='arms_up'").fetchone()[0]
        squat_count = conn.execute("SELECT COUNT(*) FROM alerts WHERE alert_type='squat'").fetchone()[0]
        fall_count = conn.execute("SELECT COUNT(*) FROM alerts WHERE alert_type='fall'").fetchone()[0]
        hand_speed_count = conn.execute("SELECT COUNT(*) FROM alerts WHERE alert_type='hand_speed'").fetchone()[0]

        hours_elapsed = max(diff / 3600, 0.01)
        alerts_per_hour = round(total_alerts / hours_elapsed, 1) if total_alerts else 0

        # Safety score: 100 - (alerts_per_hour * 10), clamped 0-100
        raw_score = 100 - (alerts_per_hour * 10)
        safety_score = max(0, min(100, round(raw_score)))

        # Alert types distribution
        alert_types_rows = conn.execute(
            "SELECT alert_type, COUNT(*) as cnt FROM alerts GROUP BY alert_type ORDER BY cnt DESC"
        ).fetchall()
        alert_types = {r["alert_type"]: r["cnt"] for r in alert_types_rows}

        # Alert timeline (per minute buckets for last 60 entries)
        at_rows = conn.execute("""
            SELECT substr(timestamp, 1, 16) as minute, COUNT(*) as cnt
            FROM alerts GROUP BY minute ORDER BY minute DESC LIMIT 60
        """).fetchall()
        at_rows.reverse()
        alert_timeline = {"labels": [r["minute"][11:16] for r in at_rows],
                          "values": [r["cnt"] for r in at_rows]}

        # Recent alerts
        recent_alerts = [{
            "timestamp": r["timestamp"][:19].replace("T", " "),
            "alert_type": r["alert_type"], "description": r["description"],
            "severity": r["severity"], "session_id": r["session_id"],
        } for r in conn.execute("SELECT * FROM alerts ORDER BY epoch DESC LIMIT 30").fetchall()]
    else:
        total_alerts = 0
        drowsiness_count = yawn_count = distraction_count = inactivity_count = 0
        blink_count = head_down_count = posture_count = trunk_count = 0
        arms_count = squat_count = fall_count = hand_speed_count = 0
        alerts_per_hour = 0
        safety_score = 100
        alert_types = {}
        alert_timeline = {"labels": [], "values": []}
        recent_alerts = []

    safety = {
        "total_alerts": total_alerts,
        "drowsiness_count": drowsiness_count,
        "posture_count": posture_count,
        "yawn_count": yawn_count,
        "distraction_count": distraction_count,
        "inactivity_count": inactivity_count,
        "blink_count": blink_count,
        "head_down_count": head_down_count,
        "trunk_count": trunk_count,
        "arms_count": arms_count,
        "squat_count": squat_count,
        "fall_count": fall_count,
        "hand_speed_count": hand_speed_count,
        "alerts_per_hour": alerts_per_hour,
        "safety_score": safety_score,
        "alert_types": alert_types,
        "alert_timeline": alert_timeline,
    }

    conn.close()

    return jsonify({
        "kpis": kpis, "timeline": timeline, "distribution": distribution,
        "fps_data": fps_data, "hands_data": hands_data, "recent": recent,
        "safety": safety, "recent_alerts": recent_alerts,
    })


if __name__ == "__main__":
    print("=" * 55)
    print("  DEMI Dashboard - Seguranca Industrial")
    print("=" * 55)
    print("Acesse: http://localhost:5000")
    print("Ctrl+C para parar\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
