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

function _el(tag, attrs = {}, text = null) {
  const node = document.createElement(tag);
  Object.entries(attrs || {}).forEach(([k, v]) => {
    if (v === null || v === undefined) return;
    if (k === "className") node.className = String(v);
    else if (k === "title") node.title = String(v);
    else node.setAttribute(k, String(v));
  });
  if (text !== null && text !== undefined) node.textContent = String(text);
  return node;
}

function setStatus(state) {
  runStatus.className = `badge ${state}`;
  runStatus.textContent = state;
}

function isAvailableInTier(widget, tier) {
  return widget.available_in.includes(tier);
}

function renderWidgets() {
  const tier = tierSelect.value;
  widgetGrid.textContent = "";

  widgetModel.widgets.forEach((widget) => {
    const available = isAvailableInTier(widget, tier);
    const node = document.createElement("article");
    node.className = `widget ${available ? "" : "unavailable"}`;
    const head = _el("div", { className: "widget-head" });
    head.appendChild(_el("strong", {}, widget.title || ""));
    head.appendChild(
      _el(
        "span",
        {
          className: `checkbox ${available ? "checked" : ""}`,
          title: available ? "enabled" : "disabled"
        },
        ""
      )
    );
    node.appendChild(head);
    node.appendChild(_el("p", {}, widget.description || ""));
    node.appendChild(_el("small", {}, widget.hardened_only ? "Hardened-only behavior" : "Available behavior"));
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
  daemonList.textContent = "";
  list.forEach((d) => {
    const node = document.createElement("div");
    node.className = "daemon-item";
    const pid = d.pid || "";
    const row = _el("div", { className: "row" });
    row.appendChild(_el("strong", {}, d.widget_id || "daemon"));
    row.appendChild(_el("span", { className: "muted" }, `pid=${pid}`));
    node.appendChild(row);

    const cwd = _el("div", { className: "muted" });
    cwd.appendChild(document.createTextNode("cwd: "));
    cwd.appendChild(_el("code", {}, d.cwd || ""));
    node.appendChild(cwd);

    const log = _el("div", { className: "muted" });
    log.appendChild(document.createTextNode("log: "));
    log.appendChild(_el("code", {}, d.log_file || ""));
    node.appendChild(log);

    const cmd = _el("div", { className: "muted" });
    cmd.appendChild(document.createTextNode("cmd: "));
    cmd.appendChild(_el("code", {}, String(d.command || "").slice(0, 220)));
    node.appendChild(cmd);
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
