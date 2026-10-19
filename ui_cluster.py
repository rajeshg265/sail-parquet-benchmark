#!/usr/bin/env python3
"""
Cluster benchmark UI server — Sail vs Spark local-cluster results viewer.
Serves at http://localhost:5053/

Reads pre-computed results from results/results_*.json files produced by
bench_cluster.py. No live query execution — just result visualisation.

Usage:
    python ui_cluster.py
    python ui_cluster.py --results results/results_20261019_121351.json
"""
import json
import os
import glob
import argparse
from pathlib import Path

from flask import Flask, jsonify, send_from_directory, request

RESULTS_DIR = Path(__file__).parent / "results"
STATIC      = Path(__file__).parent / "ui_cluster_static"

app = Flask(__name__, static_folder=str(STATIC))


def _result_files():
    files = sorted(glob.glob(str(RESULTS_DIR / "results_*.json")), reverse=True)
    return files


@app.route("/api/results/list")
def api_list():
    files = _result_files()
    out = []
    for f in files:
        name = Path(f).name
        try:
            data = json.loads(Path(f).read_text())
            engines = list(data.keys())
        except Exception:
            engines = []
        out.append({"filename": name, "path": f, "engines": engines})
    return jsonify(out)


@app.route("/api/results/latest")
def api_latest():
    files = _result_files()
    if not files:
        return jsonify({"error": "no results found in results/"}), 404
    return _serve_file(files[0])


@app.route("/api/results/<filename>")
def api_result(filename):
    path = RESULTS_DIR / filename
    if not path.exists():
        return jsonify({"error": "not found"}), 404
    return _serve_file(str(path))


def _serve_file(path):
    data = json.loads(Path(path).read_text())
    data["_filename"] = Path(path).name
    # Pull timestamp from filename if present (results_YYYYMMDD_HHMMSS.json)
    stem = Path(path).stem
    parts = stem.split("_")
    if len(parts) >= 3:
        try:
            from datetime import datetime
            ts = datetime.strptime(f"{parts[1]}_{parts[2]}", "%Y%m%d_%H%M%S")
            data["_timestamp"] = ts.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
    return jsonify(data)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_static(path):
    from flask import make_response
    if path and (STATIC / path).exists():
        resp = make_response(send_from_directory(str(STATIC), path))
    else:
        resp = make_response(send_from_directory(str(STATIC), "index.html"))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp


if __name__ == "__main__":
    import logging
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    print("Cluster Benchmark UI: http://localhost:5053/")
    app.run(host="0.0.0.0", port=5053, threaded=True)
