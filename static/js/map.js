// map.js - Leaflet map, click handlers, markers, route drawing, delivery simulation

const CHENNAI = [13.0827, 80.2707];
const map = L.map("map", { center: CHENNAI, zoom: 12, zoomControl: true });
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "OpenStreetMap", maxZoom: 19
}).addTo(map);

const MAP_ROUTE_COLORS = ["#00f5ff", "#ff00e5", "#00ff88"];

window.mapState = {
  startLatLng: null, endLatLng: null,
  startMarker: null, endMarker: null,
  routeLines: [], deliveryMarker: null, simFrameId: null
};

function makeIcon(label, color) {
  return L.divIcon({
    html: `<div style="width:30px;height:30px;border-radius:50%;background:${color}22;border:2px solid ${color};display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;color:${color};box-shadow:0 0 12px ${color}88;font-family:Inter,sans-serif">${label}</div>`,
    className: "", iconSize: [30,30], iconAnchor: [15,15]
  });
}

function makeDeliveryIcon() {
  return L.divIcon({
    html: `<div style="width:22px;height:22px;border-radius:50%;background:#00f5ff33;border:2px solid #00f5ff;display:flex;align-items:center;justify-content:center;font-size:11px;box-shadow:0 0 16px #00f5ffaa">&#128682;</div>`,
    className: "", iconSize: [22,22], iconAnchor: [11,11]
  });
}

map.on("click", (e) => {
  const { lat, lng } = e.latlng;
  if (!window.mapState.startLatLng) {
    window.mapState.startLatLng = [lat, lng];
    if (window.mapState.startMarker) window.mapState.startMarker.remove();
    window.mapState.startMarker = L.marker([lat,lng], {icon: makeIcon("S","#00ff88")})
      .bindPopup(`<b style="color:#00ff88">Start</b><br>${lat.toFixed(5)}, ${lng.toFixed(5)}`).addTo(map);
    const el = document.getElementById("start-display");
    el.textContent = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
    el.classList.remove("empty");
    setClickMode("end-mode","SET DESTINATION");
    setStatus("ready","Now click to set destination");
  } else if (!window.mapState.endLatLng) {
    window.mapState.endLatLng = [lat, lng];
    if (window.mapState.endMarker) window.mapState.endMarker.remove();
    window.mapState.endMarker = L.marker([lat,lng], {icon: makeIcon("D","#ff00e5")})
      .bindPopup(`<b style="color:#ff00e5">Destination</b><br>${lat.toFixed(5)}, ${lng.toFixed(5)}`).addTo(map);
    const el = document.getElementById("end-display");
    el.textContent = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
    el.classList.remove("empty");
    setClickMode("done-mode","READY");
    setStatus("ready","Both points set, click Solve");
    document.getElementById("solve-btn").disabled = false;
  }
});

document.getElementById("clear-btn").addEventListener("click", clearAll);

function clearAll() {
  const ms = window.mapState;
  if (ms.startMarker)    { ms.startMarker.remove();    ms.startMarker = null; }
  if (ms.endMarker)      { ms.endMarker.remove();      ms.endMarker = null; }
  if (ms.deliveryMarker) { ms.deliveryMarker.remove(); ms.deliveryMarker = null; }
  ms.routeLines.forEach(l => l.remove()); ms.routeLines = [];
  ms.startLatLng = null; ms.endLatLng = null;
  if (ms.simFrameId) { clearTimeout(ms.simFrameId); ms.simFrameId = null; }
  document.getElementById("start-display").textContent = "Click on map...";
  document.getElementById("start-display").classList.add("empty");
  document.getElementById("end-display").textContent = "Click on map...";
  document.getElementById("end-display").classList.add("empty");
  document.getElementById("solve-btn").disabled = true;
  document.getElementById("sim-btn").disabled = true;
  document.getElementById("sim-stop-btn").disabled = true;
  setClickMode("start-mode","SET START");
  setStatus("ready","Click map to set start point");
}

window.drawRoutes = function(allRoutes, selectedIndex) {
  window.mapState.routeLines.forEach(l => l.remove());
  window.mapState.routeLines = [];
  allRoutes.forEach((route, i) => {
    const latlngs = route.geometry.map(p => [p[0], p[1]]);
    const color   = MAP_ROUTE_COLORS[i % MAP_ROUTE_COLORS.length];
    const isSelected = (i === selectedIndex);
    const line = L.polyline(latlngs, {
      color, weight: isSelected ? 5 : 2.5, opacity: isSelected ? 1 : 0.45,
      dashArray: isSelected ? null : "6 8"
    }).addTo(map);
    line.bindPopup(`<div style="font-family:Inter,sans-serif;min-width:160px"><div style="font-weight:700;color:${color};margin-bottom:6px">Route ${i}${isSelected?" SELECTED":""}</div><div style="font-size:11px;color:#aaa">Distance: ${route.distance_km} km</div><div style="font-size:11px;color:#aaa">ETA: ${route.eta_min} min</div></div>`);
    window.mapState.routeLines.push(line);
  });
  if (allRoutes[0] && allRoutes[0].geometry.length) {
    const allPoints = allRoutes.flatMap(r => r.geometry.map(p => [p[0],p[1]]));
    map.fitBounds(L.latLngBounds(allPoints).pad(0.1));
  }
};

window.startSimulation = function(geometry) {
  const ms = window.mapState;
  if (ms.simFrameId) clearTimeout(ms.simFrameId);
  if (ms.deliveryMarker) ms.deliveryMarker.remove();
  const pts = geometry.map(p => [p[0],p[1]]);
  if (pts.length < 2) return;
  ms.deliveryMarker = L.marker(pts[0], {icon: makeDeliveryIcon(), zIndexOffset: 1000}).addTo(map);
  let stepIndex = 0;
  function animate() {
    stepIndex++;
    if (stepIndex > pts.length - 1) {
      setStatus("ready","Delivery complete!");
      showTooltip("Delivery complete!", 2500);
      document.getElementById("sim-btn").disabled = false;
      return;
    }
    ms.deliveryMarker.setLatLng(pts[stepIndex]);
    ms.simFrameId = setTimeout(() => requestAnimationFrame(animate), 40);
  }
  showTooltip("Simulating delivery...");
  requestAnimationFrame(animate);
};

window.stopSimulation = function() {
  const ms = window.mapState;
  if (ms.simFrameId) { clearTimeout(ms.simFrameId); ms.simFrameId = null; }
  if (ms.deliveryMarker) { ms.deliveryMarker.remove(); ms.deliveryMarker = null; }
};

function setClickMode(cls, text) {
  const el = document.getElementById("click-mode");
  el.className = cls; el.textContent = text;
}

function setStatus(type, text) {
  document.getElementById("status-dot").className = `status-dot${type==="busy"?" busy":type==="error"?" error":""}`;
  document.getElementById("status-text").textContent = text;
}

let tooltipTimer = null;
function showTooltip(text, autoHideMs = 0) {
  const el = document.getElementById("tooltip");
  el.textContent = text; el.classList.add("show");
  if (tooltipTimer) clearTimeout(tooltipTimer);
  if (autoHideMs > 0) tooltipTimer = setTimeout(() => el.classList.remove("show"), autoHideMs);
}

window.showTooltip = showTooltip;
window.setStatus   = setStatus;
