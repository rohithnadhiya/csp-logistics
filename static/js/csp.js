// csp.js - Main orchestration: fetch routes, call solver, update all UI panels

let _selectedAlgo    = "csp_full";
let _lastSolveResult = null;

// ── Algorithm selector ─────────────────────────────────────────────────────
document.querySelectorAll(".algo-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".algo-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    _selectedAlgo = btn.dataset.algo;
  });
});

// ── Solve button ───────────────────────────────────────────────────────────
document.getElementById("solve-btn").addEventListener("click", runSolve);
document.getElementById("sim-btn").addEventListener("click", () => {
  if (!_lastSolveResult) return;
  document.getElementById("sim-btn").disabled = true;
  window.setStatus("busy","Simulating delivery...");
  window.startSimulation(_lastSolveResult.geometry || []);
});
document.getElementById("sim-stop-btn").addEventListener("click", () => {
  window.stopSimulation();
  window.setStatus("ready","Simulation stopped");
});

async function runSolve() {
  const ms = window.mapState;
  if (!ms.startLatLng || !ms.endLatLng) { alert("Set both start and destination"); return; }

  showLoading("Running CSP Solver...");
  window.setStatus("busy","Solving...");

  const cfg = {
    max_km:     parseFloat(document.getElementById("cfg-max-km").value)  || 200,
    max_eta_min:parseFloat(document.getElementById("cfg-max-eta").value) || 180,
    energy_budget: parseFloat(document.getElementById("cfg-energy").value) || 100,
  };
  const weatherApiKey = document.getElementById("weather-api-key").value.trim();

  try {
    const resp = await fetch("/api/solve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        start: ms.startLatLng,
        end:   ms.endLatLng,
        algorithm: _selectedAlgo,
        cfg,
        weather_api_key: weatherApiKey,
      })
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ error: "Unknown error" }));
      throw new Error(err.error || `HTTP ${resp.status}`);
    }

    const result = await resp.json();
    _lastSolveResult = result;
    showAlgoReason(result.algorithm);
    // Draw map routes
    if (result.all_routes && result.all_routes.length) {
      window.drawRoutes(result.all_routes, result.selected_route);
    }

    // Update analytics
    window.Analytics.updateStats(result);
    if (result.weather) window.Analytics.updateWeather(result.weather);
    if (result.all_routes) {
      window.Analytics.updateChart(result.all_routes, result.selected_route);
      window.Analytics.updateRouteLegend(result.all_routes, result.selected_route);
    }
    if (result.constraint_details) window.Analytics.updateConstraints(result.constraint_details);
    if (result.rationale)          window.Analytics.updateRationale(result.rationale);
    if (result.steps)              window.Analytics.updateSteps(result.steps);

    // Enable simulation buttons
    document.getElementById("sim-btn").disabled = false;
    document.getElementById("sim-stop-btn").disabled = false;

    window.setStatus("ready","Solved!");
    window.showTooltip(`Route #${result.selected_route} selected | ${result.distance_km} km | ${result.effective_eta_min} min`, 4000);

  } catch (err) {
    window.setStatus("error","Solver error: " + err.message);
    document.getElementById("status-text").textContent = "Solver error: " + err.message;
    console.error("Solve error:", err);
  } finally {
    hideLoading();
  }
}

function showLoading(text) {
  const overlay = document.getElementById("loading-overlay");
  document.getElementById("loading-text").textContent = text;
  overlay.style.display = "flex";
}

function hideLoading() {
  document.getElementById("loading-overlay").style.display = "none";
}
function showAlgoReason(algo) {
    const text = (algo || "").toUpperCase();

    let reason = "Advanced AI optimization algorithm";

    if (text.includes("CSP")) {
        reason = "Uses Constraint Satisfaction to handle time, capacity, and delivery constraints efficiently";
    } else if (text.includes("BACKTRACK")) {
        reason = "Explores all possibilities ensuring optimal solution";
    } else if (text.includes("BFS")) {
        reason = "Finds shortest path quickly but ignores constraints";
    } else if (text.includes("DFS")) {
        reason = "Explores deep paths but not always optimal";
    } else if (text.includes("GREEDY")) {
        reason = "Fast decision-making but may not give best solution";
    } else if (text.includes("BRANCH")) {
        reason = "Optimized search using pruning techniques";
    }

    document.getElementById("algoReason").innerText = reason;
}