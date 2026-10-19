#!/usr/bin/env python3
"""
Generate a self-contained HTML benchmark report from a results JSON file.

Usage:
    python generate_artifact.py                            # latest results file
    python generate_artifact.py results/results_XYZ.json  # specific file
    python generate_artifact.py --out report.html          # custom output path
"""
import json
import sys
import glob
import argparse
from pathlib import Path
from datetime import datetime

RESULTS_DIR = Path(__file__).parent / "results"

QUERY_LABELS = {
    "full_agg":     "Full Scan — Multi-column SUM",
    "grouped_agg":  "Group By — Entity & Scenario",
    "filtered_agg": "Filtered Agg — Partition Range",
    "join_entity":  "JOIN — Entity Hierarchy",
    "join_desk":    "JOIN — Trading Desk",
    "join_calendar":"JOIN — Fiscal Quarter",
}
QUERY_ORDER = list(QUERY_LABELS.keys())

CHART_JS = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"


def load_results(path=None):
    if path:
        return json.loads(Path(path).read_text()), Path(path).name
    files = sorted(glob.glob(str(RESULTS_DIR / "results_*.json")), reverse=True)
    if not files:
        print("No results files found in results/. Run bench_cluster.py first.", file=sys.stderr)
        sys.exit(1)
    return json.loads(Path(files[0]).read_text()), Path(files[0]).name


def parse_timestamp(filename):
    stem = Path(filename).stem
    parts = stem.split("_")
    if len(parts) >= 3:
        try:
            return datetime.strptime(f"{parts[1]}_{parts[2]}", "%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
    return ""


def generate(data, filename):
    ts = parse_timestamp(filename)
    sail_data  = json.dumps(data.get("sail",  {}))
    spark_data = json.dumps(data.get("spark", {}))
    query_order = json.dumps(QUERY_ORDER)
    query_labels = json.dumps(QUERY_LABELS)
    has_sail  = "sail"  in data
    has_spark = "spark" in data

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sail vs Spark — Cluster Benchmark</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap">
<script src="{CHART_JS}"></script>
<style>
:root {{
  --bg:#0d0d0f; --surface:#17171a; --border:#2a2a30;
  --fg:#e8e8f0; --muted:#7a7a8c;
  --sail:#00d4aa; --spark:#ff6b6b; --good:#00d4aa; --warn:#ffc94d;
  color-scheme: dark;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: var(--bg); color: var(--fg);
  font-family: 'IBM Plex Sans', system-ui, sans-serif;
  font-size: 14px;
  padding: max(28px, env(safe-area-inset-top, 0px)) max(32px, env(safe-area-inset-right, 0px))
           max(28px, env(safe-area-inset-bottom, 0px)) max(32px, env(safe-area-inset-left, 0px));
  max-width: 1100px; margin: 0 auto;
}}
h1 {{ font-size: 22px; font-weight: 600; letter-spacing: -.01em; margin-bottom: 6px; }}
.subtitle {{ font-size: 13px; color: var(--muted); margin-bottom: 28px; }}
.badge {{
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-size: 11px; font-weight: 600; letter-spacing: .04em; margin-right: 6px;
}}
.badge-sail  {{ background: rgba(0,212,170,.15); color: var(--sail); }}
.badge-spark {{ background: rgba(255,107,107,.15); color: var(--spark); }}
.card {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 8px; overflow: hidden; margin-bottom: 28px;
}}
.card-title {{
  padding: 12px 20px;
  font-size: 11px; font-weight: 600; letter-spacing: .08em;
  text-transform: uppercase; color: var(--muted);
  border-bottom: 1px solid var(--border);
}}
table {{ width: 100%; border-collapse: collapse; }}
thead th {{
  padding: 10px 20px;
  font-size: 11px; font-weight: 600; letter-spacing: .06em;
  text-transform: uppercase; color: var(--muted);
  text-align: right; border-bottom: 1px solid var(--border);
}}
thead th:first-child {{ text-align: left; }}
tbody tr {{ border-bottom: 1px solid rgba(255,255,255,.04); }}
tbody tr:last-child {{ border-bottom: none; }}
tbody td {{
  padding: 11px 20px;
  font-family: 'IBM Plex Mono', monospace; font-size: 13px; text-align: right;
}}
tbody td:first-child {{
  font-family: 'IBM Plex Sans', sans-serif; font-weight: 500; color: var(--fg); text-align: left;
}}
.sail-val  {{ color: var(--sail); }}
.spark-val {{ color: var(--spark); }}
.good {{ color: var(--good); font-weight: 600; }}
.warn {{ color: var(--warn); }}
.charts-grid {{
  display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 28px;
}}
@media (max-width: 700px) {{ .charts-grid {{ grid-template-columns: 1fr; }} }}
.chart-card {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 8px; padding: 16px 20px;
}}
.chart-card h3 {{
  font-size: 11px; font-weight: 600; letter-spacing: .06em;
  text-transform: uppercase; color: var(--muted); margin-bottom: 14px;
}}
.chart-wrap {{ position: relative; height: 200px; }}
.runs-wrap  {{ position: relative; height: 260px; padding: 16px 20px; }}
.legend {{ display: flex; gap: 20px; margin-bottom: 20px; align-items: center; }}
.dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 6px; }}
.legend-item {{ font-size: 12px; color: var(--muted); display: flex; align-items: center; }}
.footer {{ font-size: 11px; color: var(--muted); margin-top: 28px; padding-top: 16px; border-top: 1px solid var(--border); }}
</style>
</head>
<body>
<h1>Sail vs Spark — Local Cluster Benchmark</h1>
<div class="subtitle">
  <span class="badge badge-sail">Sail local-cluster (3 workers, 1 Rust process)</span>
  <span class="badge badge-spark">Spark local-cluster[3,1,1024] (3 executor JVMs)</span>
  &nbsp;{ts}
</div>
<div class="legend">
  <span class="legend-item"><span class="dot" style="background:var(--sail)"></span>Sail</span>
  <span class="legend-item"><span class="dot" style="background:var(--spark)"></span>Spark</span>
  <span style="font-size:11px;color:var(--muted)">54.88M rows · 9.71 GB · 6 FRTB queries · 10 runs each</span>
</div>

<!-- Summary table injected by JS -->
<div id="summaryTable"></div>

<!-- Per-query bar charts -->
<div class="charts-grid" id="chartsGrid"></div>

<!-- All runs scatter -->
<div class="card" id="runsCard" style="display:none">
  <div class="card-title">All Run Times — 10 Runs per Query (ms)</div>
  <div class="runs-wrap"><canvas id="runsChart"></canvas></div>
</div>

<div class="footer">
  Dataset: 54.88M rows, 9.71 GB, 2 Parquet files, 32 float64 columns of synthetic FRTB SA capital output.
  Sail uses DataFusion/Rust via SparkConnect. Spark uses JVM local-cluster with Netty RPC.
  File: {filename}
</div>

<script>
const SAIL  = {sail_data};
const SPARK = {spark_data};
const QUERY_ORDER  = {query_order};
const QUERY_LABELS = {query_labels};

function buildSummaryTable() {{
  const rows = QUERY_ORDER.map(qid => {{
    const s = SAIL[qid];
    const k = SPARK[qid];
    const sp = s?.p99_ms, kp = k?.p99_ms;
    const ratio = (sp && kp) ? (kp / sp).toFixed(2) : null;
    const faster = ratio ? (parseFloat(ratio) >= 1 ? 'Sail' : 'Spark') : '';
    return `<tr>
      <td>${{QUERY_LABELS[qid]||qid}}</td>
      <td>${{sp != null ? `<span class="sail-val">${{sp.toLocaleString()}} ms</span>` : '—'}}</td>
      <td>${{kp != null ? `<span class="spark-val">${{kp.toLocaleString()}} ms</span>` : '—'}}</td>
      <td>${{ratio ? `<span class="${{parseFloat(ratio)>=1?'good':'warn'}}">${{ratio}}× ${{faster}} faster</span>` : '—'}}</td>
    </tr>`;
  }}).join('');
  document.getElementById('summaryTable').innerHTML = `
    <div class="card">
      <div class="card-title">P99 Latency — 10-Run Benchmark</div>
      <table>
        <thead><tr><th>Query</th><th>Sail P99</th><th>Spark P99</th><th>Speedup</th></tr></thead>
        <tbody>${{rows}}</tbody>
      </table>
    </div>`;
}}

function buildBarCharts() {{
  const grid = document.getElementById('chartsGrid');
  QUERY_ORDER.forEach(qid => {{
    const s = SAIL[qid], k = SPARK[qid];
    if (!s && !k) return;
    const div = document.createElement('div');
    div.className = 'chart-card';
    div.innerHTML = `<h3>${{QUERY_LABELS[qid]||qid}}</h3><div class="chart-wrap"><canvas id="b_${{qid}}"></canvas></div>`;
    grid.appendChild(div);
    const labels = [], vals = [], colors = [];
    if (s) {{ labels.push('Sail');  vals.push(s.median_ms); colors.push('rgba(0,212,170,0.8)'); }}
    if (k) {{ labels.push('Spark'); vals.push(k.median_ms); colors.push('rgba(255,107,107,0.8)'); }}
    new Chart(document.getElementById(`b_${{qid}}`), {{
      type: 'bar',
      data: {{ labels, datasets: [{{ data: vals, backgroundColor: colors, borderRadius: 4, borderSkipped: false }}] }},
      options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          x: {{ ticks: {{ color: '#7a7a8c' }}, grid: {{ color: 'rgba(255,255,255,.04)' }} }},
          y: {{ ticks: {{ color: '#7a7a8c', callback: v => v.toLocaleString()+'ms' }},
               grid: {{ color: 'rgba(255,255,255,.06)' }} }}
        }}
      }}
    }});
  }});
}}

function buildRunsChart() {{
  const sailPts = [], sparkPts = [];
  let x = 0;
  let hasData = false;
  QUERY_ORDER.forEach(qid => {{
    const s = SAIL[qid]?.times_ms || [], k = SPARK[qid]?.times_ms || [];
    const n = Math.max(s.length, k.length, 0);
    if (!n) return;
    hasData = true;
    s.forEach((v,i) => sailPts.push({{x: x+i, y: v}}));
    k.forEach((v,i) => sparkPts.push({{x: x+i, y: v}}));
    x += n;
  }});
  if (!hasData) return;
  document.getElementById('runsCard').style.display = '';
  new Chart(document.getElementById('runsChart'), {{
    type: 'scatter',
    data: {{
      datasets: [
        {{ label:'Sail',  data:sailPts,  backgroundColor:'rgba(0,212,170,0.7)', pointRadius:5 }},
        {{ label:'Spark', data:sparkPts, backgroundColor:'rgba(255,107,107,0.7)', pointRadius:5 }},
      ]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{
        legend: {{ labels: {{ color:'#e8e8f0' }} }},
        tooltip: {{ callbacks: {{ label: c => `${{c.dataset.label}}: ${{c.parsed.y.toLocaleString()}}ms` }} }}
      }},
      scales: {{
        x: {{ ticks: {{ color:'#7a7a8c', maxTicksLimit:6 }}, grid: {{ color:'rgba(255,255,255,.04)' }} }},
        y: {{ ticks: {{ color:'#7a7a8c', callback: v => v.toLocaleString()+'ms' }},
             grid: {{ color:'rgba(255,255,255,.06)' }} }}
      }}
    }}
  }});
}}

buildSummaryTable();
buildBarCharts();
buildRunsChart();
</script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results_file", nargs="?", help="Path to results JSON file (default: latest)")
    parser.add_argument("--out", default=None, help="Output HTML file (default: results/<name>.html)")
    args = parser.parse_args()

    data, filename = load_results(args.results_file)
    html = generate(data, filename)

    if args.out:
        out = Path(args.out)
    else:
        stem = Path(filename).stem
        out  = RESULTS_DIR / f"{stem}.html"

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"Artifact written to: {out}")


if __name__ == "__main__":
    main()
