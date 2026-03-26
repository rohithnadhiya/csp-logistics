// logs.js - Poll backend logs and display

let _logsLastCount = 0;

function renderLogs(logs) {
  const container = document.getElementById("log-container");
  if (!container || !logs.length) return;
  container.innerHTML = logs.slice(0, 40).map(e => `
    <div class="log-entry ${e.level}">
      <span class="log-ts">${(e.timestamp||"").slice(11,19)}</span>
      <span class="log-level">${e.level}</span>
      <span class="log-msg">${e.message}</span>
    </div>`).join("");
}

async function fetchLogs() {
  try {
    const resp = await fetch("/api/logs?limit=40");
    if (!resp.ok) return;
    const data = await resp.json();
    renderLogs(data.logs || []);
  } catch {}
}

document.getElementById("clear-logs-btn").addEventListener("click", async () => {
  await fetch("/api/logs/clear", { method: "POST" });
  fetchLogs();
});

fetchLogs();
setInterval(fetchLogs, 5000);
