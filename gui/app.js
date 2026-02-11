const tierSelect = document.getElementById("tier");
const widgetGrid = document.getElementById("widgetGrid");
const widgetIdInput = document.getElementById("widgetIdInput");
const argsInput = document.getElementById("argsInput");
const commandInput = document.getElementById("commandInput");
const runBtn = document.getElementById("runBtn");
const behaviorOutput = document.getElementById("behaviorOutput");
const logsOutput = document.getElementById("logsOutput");
const runStatus = document.getElementById("runStatus");
const daemonList = document.getElementById("daemonList");
const daemonsEmpty = document.getElementById("daemonsEmpty");
const daemonPidInput = document.getElementById("daemonPidInput");
const stopDaemonBtn = document.getElementById("stopDaemonBtn");
const viewDaemonLogBtn = document.getElementById("viewDaemonLogBtn");
const daemonLogOutput = document.getElementById("daemonLogOutput");

let widgetModel = { widgets: [] };
let selectedWidget = null;

function setStatus(state) {
  runStatus.className = `badge ${state}`;
  runStatus.textContent = state;
}

function isAvailableInTier(widget, tier) {
  return widget.available_in.includes(tier);
}

function renderWidgets() {
  const tier = tierSelect.value;
  widgetGrid.innerHTML = "";

  widgetModel.widgets.forEach((widget) => {
    const available = isAvailableInTier(widget, tier);
    const node = document.createElement("article");
    node.className = `widget ${available ? "" : "unavailable"}`;
    node.innerHTML = `
      <div class="widget-head">
        <strong>${widget.title}</strong>
        <span class="checkbox ${available ? "checked" : ""}" title="${available ? "enabled" : "disabled"}"></span>
      </div>
      <p>${widget.description}</p>
      <small>${widget.hardened_only ? "Hardened-only behavior" : "Available behavior"}</small>
    `;
    node.addEventListener("click", () => {
      selectedWidget = widget;
      widgetIdInput.value = widget.id;
      argsInput.value = "";
      commandInput.value = widget.template;
      behaviorOutput.textContent = [
        `Widget: ${widget.title}`,
        `Tier: ${tier}`,
        `Available: ${available ? "yes" : "no"}`,
        `Command: ${widget.template}`,
        widget.args_hint ? `Args hint: ${widget.args_hint}` : "Args hint: none"
      ].join("\n");
    });
    widgetGrid.appendChild(node);
  });
}

async function loadModel() {
  const response = await fetch("/api/widgets");
  const data = await response.json();
  widgetModel.widgets = data.widgets || [];
  renderWidgets();
}

async function loadLogs() {
  try {
    const response = await fetch("/api/logs");
    if (!response.ok) {
      logsOutput.textContent = "No API logs available yet.";
      return;
    }
    const data = await response.json();
    logsOutput.textContent = (data.logs || [])
      .slice(-25)
      .map((row) => `[${row.timestamp || "n/a"}] ${row.message || ""}`)
      .join("\n") || "No logs available.";
  } catch {
    logsOutput.textContent = "No API logs available yet.";
  }
}

function renderDaemons(daemons) {
  const list = Array.isArray(daemons) ? daemons : [];
  if (list.length === 0) {
    daemonList.hidden = true;
    daemonsEmpty.hidden = false;
    return;
  }
  daemonsEmpty.hidden = true;
  daemonList.hidden = false;
  daemonList.innerHTML = "";
  list.forEach((d) => {
    const node = document.createElement("div");
    node.className = "daemon-item";
    const pid = d.pid || "";
    node.innerHTML = `
      <div class="row">
        <strong>${d.widget_id || "daemon"}</strong>
        <span class="muted">pid=${pid}</span>
      </div>
      <div class="muted">cwd: <code>${d.cwd || ""}</code></div>
      <div class="muted">log: <code>${d.log_file || ""}</code></div>
      <div class="muted">cmd: <code>${(d.command || "").slice(0, 220)}</code></div>
    `;
    node.addEventListener("click", () => {
      daemonPidInput.value = String(pid);
      daemonLogOutput.hidden = true;
    });
    daemonList.appendChild(node);
  });
}

async function loadDaemons() {
  try {
    const response = await fetch("/api/daemons");
    const data = await response.json();
    renderDaemons(data.daemons || []);
  } catch {
    renderDaemons([]);
  }
}

async function stopDaemon(pid) {
  const res = await fetch("/api/stop", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pid })
  });
  return res.json();
}

async function viewDaemonLog(pid) {
  const response = await fetch(`/api/daemon-log?pid=${encodeURIComponent(String(pid))}`);
  return response.json();
}

function runCommandScaffold() {
  const tier = tierSelect.value;
  const widgetId = widgetIdInput.value.trim();
  if (!widgetId) {
    behaviorOutput.textContent = "Select a widget first.";
    return;
  }
  const widget = widgetModel.widgets.find((w) => w.id === widgetId);
  if (!widget) {
    behaviorOutput.textContent = `Unknown widget id: ${widgetId}`;
    return;
  }
  const available = isAvailableInTier(widget, tier);
  commandInput.value = widget.template;
  if (!available) {
    setStatus("failed");
    behaviorOutput.textContent = `Widget is unchecked in ${tier} mode and cannot run.`;
    return;
  }

  setStatus("idle");
  fetch("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      widget_id: widgetId,
      args: argsInput.value.trim()
    })
  })
    .then((response) => response.json())
    .then((result) => {
      const ok = Boolean(result.ok);
      setStatus(ok ? "success" : "failed");
      behaviorOutput.textContent = [
        `widget=${widgetId}`,
        `command=${result.command || widget.template}`,
        `cwd=${result.cwd || "n/a"}`,
        `exit=${result.exit_code}`,
        `duration=${result.duration_sec || "n/a"}s`,
        "",
        "STDOUT:",
        (result.stdout || "").trim() || "(empty)",
        "",
        "STDERR:",
        (result.stderr || "").trim() || "(empty)"
      ].join("\n");
      loadLogs();
      loadDaemons();
    })
    .catch((error) => {
      setStatus("failed");
      behaviorOutput.textContent = `Failed to run command: ${error.message}`;
    });
}

tierSelect.addEventListener("change", renderWidgets);
runBtn.addEventListener("click", runCommandScaffold);
stopDaemonBtn.addEventListener("click", async () => {
  const pid = Number(daemonPidInput.value);
  if (!pid) {
    daemonLogOutput.hidden = false;
    daemonLogOutput.textContent = "Enter a pid to stop.";
    return;
  }
  try {
    const result = await stopDaemon(pid);
    daemonLogOutput.hidden = false;
    daemonLogOutput.textContent = JSON.stringify(result, null, 2);
  } catch (e) {
    daemonLogOutput.hidden = false;
    daemonLogOutput.textContent = `Stop failed: ${e.message || e}`;
  } finally {
    loadDaemons();
  }
});
viewDaemonLogBtn.addEventListener("click", async () => {
  const pid = Number(daemonPidInput.value);
  if (!pid) {
    daemonLogOutput.hidden = false;
    daemonLogOutput.textContent = "Enter a pid to view log.";
    return;
  }
  try {
    const result = await viewDaemonLog(pid);
    daemonLogOutput.hidden = false;
    daemonLogOutput.textContent = result.log || JSON.stringify(result, null, 2);
  } catch (e) {
    daemonLogOutput.hidden = false;
    daemonLogOutput.textContent = `Log fetch failed: ${e.message || e}`;
  }
});

loadModel();
loadLogs();
loadDaemons();
setInterval(loadLogs, 5000);
setInterval(loadDaemons, 5000);
