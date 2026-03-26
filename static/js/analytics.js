// analytics.js - Chart.js ETA chart, stat cards, constraint display

let etaChart = null;

function initChart() {
  const ctx = document.getElementById("eta-chart").getContext("2d");
  etaChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Route 0","Route 1","Route 2"],
      datasets: [
        { label: "ETA (min)", data: [0,0,0],
          backgroundColor: ["#00f5ff33","#ff00e533","#00ff8833"],
          borderColor:      ["#00f5ff","#ff00e5","#00ff88"],
          borderWidth: 2, borderRadius: 4 },
        { label: "Distance (km)", data: [0,0,0],
          backgroundColor: ["#00f5ff11","#ff00e511","#00ff8811"],
          borderColor:      ["#00f5ff88","#ff00e588","#00ff8888"],
          borderWidth: 1, borderRadius: 4 }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: true, labels: { color: "#7a9bbf", font: { family: "'Inter'", size: 10 }, boxWidth: 10 } },
        tooltip: {
          backgroundColor: "#121e2e", borderColor: "#1e3a52", borderWidth: 1,
          titleColor: "#e0eeff", bodyColor: "#7a9bbf",
          callbacks: { label: (c) => ` ${c.dataset.label}: ${c.parsed.y}` }
        }
      },
      scales: {
        x: { ticks: { color: "#7a9bbf", font: { size: 10 } }, grid: { color: "#1e3a52" } },
        y: { ticks: { color: "#7a9bbf", font: { size: 10 } }, grid: { color: "#1e3a52" }, beginAtZero: true }
      }
    }
  });
}

function updateChart(allRoutes, selectedIndex) {
  if (!etaChart) return;
  const labels = allRoutes.map((_,i) => i===selectedIndex ? `Route ${i} *` : `Route ${i}`);
  const etas   = allRoutes.map(r => r.eta_min);
  const dists  = allRoutes.map(r => r.distance_km);
  const bgEta = allRoutes.map((_,i) => i===selectedIndex ? "#00f5ff55" : ["#00f5ff33","#ff00e533","#00ff8833"][i%3]);
  const bdEta = allRoutes.map((_,i) => i===selectedIndex ? "#00f5ff" : ["#00f5ff88","#ff00e588","#00ff8888"][i%3]);
  etaChart.data.labels = labels;
  etaChart.data.datasets[0].data = etas;
  etaChart.data.datasets[0].backgroundColor = bgEta;
  etaChart.data.datasets[0].borderColor = bdEta;
  etaChart.data.datasets[0].borderWidth = allRoutes.map((_,i) => i===selectedIndex ? 3 : 1);
  etaChart.data.datasets[1].data = dists;
  etaChart.update("active");
}

function updateStats(result) {
  document.getElementById("stat-distance").textContent = result.distance_km ?? "--";
  document.getElementById("stat-eta").textContent      = result.effective_eta_min ?? "--";
  document.getElementById("stat-nodes").textContent    = result.nodes_explored ?? "--";
  document.getElementById("stat-checks").textContent   = result.constraint_checks ?? "--";
  document.getElementById("stat-algo").textContent     = result.algorithm ?? "--";
  document.getElementById("stat-time").textContent     = result.execution_time_ms != null
    ? `${result.execution_time_ms} ms` : "--";
}

const WEATHER_ICONS = { clear:"[sun]",sunny:"[sun]",cloud:"[cloud]",rain:"[rain]",drizzle:"[rain]",storm:"[storm]",snow:"[snow]",mist:"[fog]",fog:"[fog]",haze:"[fog]" };
function getWeatherIcon(desc="") {
  const d = desc.toLowerCase();
  for (const [k,v] of Object.entries(WEATHER_ICONS)) if (d.includes(k)) return v;
  return "[sky]";
}

function updateWeather(weather) {
  if (!weather) return;
  document.getElementById("weather-icon").textContent = getWeatherIcon(weather.description);
  document.getElementById("weather-desc").textContent = weather.description || "--";
  document.getElementById("weather-sub").textContent  =
    `${weather.temp_c ?? "--"}C | Wind ${weather.wind_ms ?? "--"} m/s | Rain ${weather.rain_1h ?? 0} mm/h`;
  const fEl = document.getElementById("weather-factor-val");
  const f = weather.factor ?? 1;
  fEl.textContent = `x${f.toFixed(2)}`;
  fEl.style.color = f <= 1.1 ? "var(--neon-g)" : f <= 1.35 ? "var(--neon-y)" : "var(--neon-r)";
}

const ANALYTICS_ROUTE_COLORS = ["#00f5ff","#ff00e5","#00ff88"];
function updateRouteLegend(allRoutes, selectedIndex) {
  const el = document.getElementById("route-legend");
  el.innerHTML = "";
  allRoutes.forEach((r,i) => {
    const item = document.createElement("div");
    item.className = `route-item${i===selectedIndex?" selected":""}`;
    item.innerHTML = `<div class="route-dot" style="background:${ANALYTICS_ROUTE_COLORS[i%3]};box-shadow:0 0 6px ${ANALYTICS_ROUTE_COLORS[i%3]}"></div>
      <div class="route-info"><div class="route-name">Route ${i}${i===selectedIndex?" *":""}</div>
      <div class="route-stats">${r.distance_km} km · ${r.eta_min} min · x${r.traffic_factor}</div></div>
      ${i===selectedIndex?'<span class="route-badge">SELECTED</span>':""}`;
    el.appendChild(item);
  });
}

const CONSTRAINT_ICONS = { distance:"[dist]",eta:"[eta]",weather:"[weather]",traffic:"[traffic]",energy:"[energy]" };
function updateConstraints(details) {
  const el = document.getElementById("constraint-list");
  if (!details || !details.length) {
    el.innerHTML = `<div style="font-size:11px;color:var(--text-3);text-align:center;padding:8px 0">No data</div>`;
    return;
  }
  el.innerHTML = details.map(c => `
    <div class="constraint-item">
      <span class="constraint-icon">${CONSTRAINT_ICONS[c.name]||"[?]"}</span>
      <span class="constraint-text">${c.msg||c.name}</span>
      <span class="constraint-status ${c.satisfied?"ok":"fail"}">${c.satisfied?"OK":"FAIL"}</span>
    </div>`).join("");
}

function updateRationale(text) {
  document.getElementById("rationale-box").textContent = text || "--";
}

function updateSteps(steps) {
  const el = document.getElementById("steps-list");
  if (!steps || !steps.length) {
    el.innerHTML = `<div style="font-size:11px;color:var(--text-3);padding:4px 0">No steps.</div>`;
    return;
  }
  el.innerHTML = steps.map(s => `<div class="step-item">${s}</div>`).join("");
  el.scrollTop = el.scrollHeight;
}

document.addEventListener("DOMContentLoaded", initChart);

window.Analytics = { updateChart, updateStats, updateWeather, updateRouteLegend, updateConstraints, updateRationale, updateSteps };
