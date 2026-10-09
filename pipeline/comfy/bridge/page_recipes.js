// Studio bridge recipes for the studio's own ComfyUI tab (never the user's tab).
// Evaluate this whole file once per page load with the Claude in Chrome JavaScript tool,
// then call e.g. `await studio.convertTemplate("H3regenrunsTest", {profile: {...}})`.
// Read-only by design: nothing here queues a job. Queuing is added only behind the guardrail hooks.
window.studio = {
  version: 1,

  ready() {
    return !!(window.app && app.rootGraph && typeof app.graphToPrompt === "function");
  },

  frontendVersion() {
    return window.__COMFYUI_FRONTEND_VERSION__ || null;
  },

  // Paths of open workflows with unsaved changes in THIS tab. Stop before any reload if non-empty.
  unsaved() {
    const ws = app.extensionManager && app.extensionManager.workflow;
    return ((ws && ws.openWorkflows) || []).filter((w) => w.isModified).map((w) => w.path);
  },

  // The user's saved workflow file, exactly as saved, without opening it.
  async fetchSaved(name) {
    const r = await fetch("/api/userdata/" + encodeURIComponent("workflows/" + name + ".json"));
    if (!r.ok) throw new Error(`cannot read workflows/${name}.json: HTTP ${r.status}`);
    return await r.json();
  },

  // Load the saved workflow into this tab's graph. Dialogs for missing nodes or models are suppressed;
  // the conversion result is checked against the saved file on the shell side (manifest_tool.py).
  async load(name) {
    const wf = await this.fetchSaved(name);
    await app.loadGraphData(wf, true, true, null, {
      showMissingNodesDialog: false,
      showMissingModelsDialog: false,
    });
    return { name, nodes: app.rootGraph.nodes.length };
  },

  // Node modes as currently loaded: {id: mode}. 0 = on, 2 = muted, 4 = bypass.
  modes() {
    const out = {};
    for (const n of app.rootGraph.nodes) out[String(n.id)] = n.mode;
    return out;
  },

  // Apply an attention profile, e.g. {"187": 0, "190": 0, "153": 4, "155": 4, "158": 4, "159": 4}.
  // Returns the previous modes so they can be restored. The saved file is never touched.
  setModes(modes) {
    const before = {};
    for (const [id, mode] of Object.entries(modes || {})) {
      const n = app.rootGraph.getNodeById(Number(id));
      if (!n) throw new Error(`node ${id} not found`);
      before[id] = n.mode;
      n.mode = mode;
    }
    return before;
  },

  // graphToPrompt with an optional profile; modes are restored afterwards.
  async convert({ profile = null } = {}) {
    const before = profile ? this.setModes(profile) : null;
    try {
      const p = await app.graphToPrompt();
      return { output: p.output };
    } finally {
      if (before) this.setModes(before);
    }
  },

  async convertTemplate(name, { profile = null, label = null } = {}) {
    const loaded = await this.load(name);
    const { output } = await this.convert({ profile });
    return {
      template: name,
      label: label || (profile ? "profile" : "as_saved"),
      profile,
      frontend_version: this.frontendVersion(),
      converted_at: new Date().toISOString(),
      loaded_nodes: loaded.nodes,
      ui_modes: this.modes(),
      api_prompt: output,
    };
  },

  // Hand a JSON object to the shell through receiver.py (loopback only).
  async send(name, data, port = 8199) {
    const r = await fetch(`http://127.0.0.1:${port}/put/${name}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    const body = await r.json();
    if (!r.ok) throw new Error(`receiver: ${r.status} ${JSON.stringify(body)}`);
    return body;
  },
};
"studio bridge v" + window.studio.version + (window.studio.ready() ? " ready" : " loaded, ComfyUI app not ready yet");
