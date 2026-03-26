"""
Flask application - AI Logistics CSP Optimizer
"""

import os
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from csp.osrm import fetch_routes
from csp.weather import get_weather
from csp.solver import solve_csp
from csp.algorithms import bfs_solve, dfs_solve, greedy_solve, branch_and_bound_solve

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

_logs = []


def _log(level, message, data=None):
    entry = {
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "level":     level,
        "message":   message,
        "data":      data or {},
    }
    _logs.append(entry)
    if len(_logs) > 200:
        _logs.pop(0)
    return entry


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/routes", methods=["POST"])
def api_routes():
    body  = request.get_json(force=True) or {}
    start = body.get("start")
    end   = body.get("end")
    if not start or not end:
        return jsonify({"error": "start and end required"}), 400
    _log("INFO", "Fetching OSRM routes", {"start": start, "end": end})
    routes, err = fetch_routes(start, end, alternatives=3)
    if err:
        _log("WARN", f"OSRM error: {err}")
    route_dicts = [r.to_dict() for r in routes]
    _log("INFO", f"Retrieved {len(routes)} routes")
    return jsonify({"routes": route_dicts, "osrm_error": err})


@app.route("/api/weather", methods=["GET"])
def api_weather():
    try:
        lat = float(request.args.get("lat", 13.0827))
        lng = float(request.args.get("lng", 80.2707))
    except ValueError:
        return jsonify({"error": "invalid lat/lng"}), 400
    api_key = request.args.get("api_key") or os.environ.get("OPENWEATHER_API_KEY", "")
    weather = get_weather(lat, lng, api_key)
    _log("INFO", "Weather fetched", weather)
    return jsonify(weather)


ALGORITHM_MAP = {
    "csp_backtrack": None,
    "csp_mrv":       None,
    "csp_lcv":       None,
    "csp_full":      None,
    "bfs":           bfs_solve,
    "dfs":           dfs_solve,
    "greedy":        greedy_solve,
    "branch_bound":  branch_and_bound_solve,
}


@app.route("/api/solve", methods=["POST"])
def api_solve():
    body      = request.get_json(force=True) or {}
    start     = body.get("start")
    end       = body.get("end")
    algorithm = body.get("algorithm", "csp_full")
    cfg       = body.get("cfg", {})
    api_key   = body.get("weather_api_key") or os.environ.get("OPENWEATHER_API_KEY", "")

    if not start or not end:
        return jsonify({"error": "start and end required"}), 400
    if algorithm not in ALGORITHM_MAP:
        return jsonify({"error": f"Unknown algorithm: {algorithm}"}), 400

    _log("INFO", f"Solve: {algorithm}", {"start": start, "end": end})

    routes, osrm_err = fetch_routes(start, end, alternatives=3)
    if not routes:
        return jsonify({"error": "No routes available"}), 500

    mid_lat = (start[0] + end[0]) / 2
    mid_lng = (start[1] + end[1]) / 2
    weather = get_weather(mid_lat, mid_lng, api_key)
    weather_factor = weather["factor"]

    for r in routes:
        r.weather_factor = weather_factor

    solver_fn = ALGORITHM_MAP.get(algorithm)
    if solver_fn is None:
        use_mrv  = algorithm in ("csp_mrv",  "csp_full")
        use_lcv  = algorithm in ("csp_lcv",  "csp_full")
        use_fc   = algorithm in ("csp_full",)
        use_prop = algorithm in ("csp_full",)
        result = solve_csp(routes, weather_factor=weather_factor, cfg=cfg,
                           use_mrv=use_mrv, use_lcv=use_lcv,
                           use_fc=use_fc, use_propagation=use_prop)
    else:
        result = solver_fn(routes, weather_factor=weather_factor, cfg=cfg)

    result["weather"]    = weather
    result["osrm_error"] = osrm_err

    _log("INFO", f"Solved: {algorithm}", {
        "selected_route": result.get("selected_route"),
        "distance_km":    result.get("distance_km"),
        "eta_min":        result.get("effective_eta_min"),
        "nodes_explored": result.get("nodes_explored"),
    })
    return jsonify(result)


@app.route("/api/logs", methods=["GET"])
def api_logs():
    limit = min(int(request.args.get("limit", 50)), 200)
    return jsonify({"logs": _logs[-limit:][::-1]})


@app.route("/api/logs/clear", methods=["POST"])
def api_logs_clear():
    _logs.clear()
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    _log("INFO", f"Starting CSP Logistics server on port {port}")
    app.run(host="0.0.0.0", port=port)
