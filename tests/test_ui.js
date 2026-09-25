const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const html = fs.readFileSync("BhoomiLens.dc.html", "utf8");
const script = html.match(/<script type="text\/x-dc"[^>]*>([\s\S]*?)<\/script>/);
assert.ok(script, "DC component script exists");
assert.ok(html.includes("Edit OCR details here"), "review screen prominently identifies editable OCR details");
assert.ok(html.includes('<sc-if value="{{ showAlerts }}"'), "header alerts are conditionally rendered");
assert.ok(html.includes("<title>BhoomiLens - Dashboard</title>"), "initial browser title stays fixed");
assert.ok(html.includes('rel="icon" type="image/svg+xml" href="./favicon.svg"'), "BhoomiLens favicon is linked");
assert.ok(script[1].includes('document.title = "BhoomiLens - Dashboard";'), "route changes keep the dashboard title");
assert.ok(html.includes("#ocr-preview-panel{grid-column:1;grid-row:1}"), "desktop review keeps the document preview on the left");
assert.ok(html.includes("#ocr-edit-fields{grid-column:2;grid-row:1}"), "desktop review places OCR fields on the right");
assert.ok(html.includes("#ocr-edit-fields{grid-column:1;grid-row:1}"), "mobile review places editable OCR fields first");
assert.ok(html.includes("#ocr-preview-panel{grid-column:1;grid-row:2}"), "mobile review places the document preview after the fields");

const requests = [];
const context = {
  DCLogic: class {
    constructor() { this.props = {}; }
    setState(patch, callback) {
      this.state = { ...this.state, ...patch };
      if (callback) callback();
    }
  },
  document: {
    querySelectorAll: () => [],
    head: { querySelector: () => null, appendChild: () => {} },
    documentElement: { setAttribute: () => {} },
    createElement: tag => ({ tag, setAttribute(name, value) { this[name] = value; } }),
  },
  fetch: async (url, options) => {
    requests.push({ url, body: JSON.parse(options.body) });
    return { ok: true, json: async () => ({ analysis: { summary: "Reviewed" } }) };
  },
  React: { createElement: () => ({}) },
  console,
};
const Component = vm.runInNewContext(script[1] + "\nComponent", context);
const app = new Component();

assert.equal(app.renderVals().showAlerts, false, "alerts stay hidden while signed out");
app.go("collector");
assert.equal(app.state.route, "login");
assert.equal(app.state.loginMode, "officer");
assert.equal(context.document.title, "BhoomiLens - Dashboard", "route navigation keeps the fixed browser title");
app.renderVals().submitLogin({ preventDefault() {} });
assert.equal(app.state.role, "District Collector");
assert.equal(app.state.route, "collector");
assert.equal(app.renderVals().showAlerts, false, "officer sessions do not show citizen alerts");
for (const route of ["parcel", "case", "objection", "compensation", "upload", "mediation", "notifications", "audit"]) {
  app.go(route);
  assert.equal(app.state.route, route, `officer can open ${route}`);
  assert.equal(app.state.role, "District Collector", `officer role retained on ${route}`);
}
app.renderVals().signOut();
app.go("parcel");
assert.equal(app.state.route, "login");
assert.equal(app.state.loginMode, "citizen");
app.renderVals().submitLogin({ preventDefault() {} });
assert.equal(app.state.role, "Citizen");
assert.equal(app.renderVals().showAlerts, true, "citizen alerts appear after citizen login");
app.go("collector");
assert.equal(app.state.route, "login");
assert.equal(app.state.loginMode, "officer");

app.renderVals().useDemoDocument();
assert.equal(app.state.upStep, 3);
app.renderVals().extracted[3].onChange({ target: { value: "Corrected buyer" } });
assert.equal(app.state.extractedFields[3].value, "Corrected buyer");
assert.equal(app.state.extractedFields[2].value, "Om Prakash (fictional)");
(async () => {
  await app.renderVals().runAiAnalysis();
  assert.equal(requests[0].url, "/api/analyze-document");
  assert.equal(requests[0].body.correctedFields[3].value, "Corrected buyer");
  app.renderVals().confirmUpload();
  assert.equal(app.state.upStep, 4);
  assert.equal(app.renderVals().extracted[3].value, "Corrected buyer");
  app.renderVals().editConfirmedDetails();
  assert.equal(app.state.upStep, 3);
  assert.equal(app.renderVals().extracted[3].value, "Corrected buyer");
  app.renderVals().resetUpload();
  assert.equal(app.state.extractedFields.length, 0);
  app.renderVals().useDemoDocument();
  app.state.uploadPreview = "data:image/jpeg;base64,private-document";
  app.renderVals().signOut();
  assert.equal(app.renderVals().showAlerts, false, "signing out hides citizen alerts");
  assert.equal(app.state.upStep, 1);
  assert.equal(app.state.uploadPreview, "");
  assert.equal(app.state.documentText, "");
  assert.equal(app.state.extractedFields.length, 0);

  app.renderVals().useDemoDocument();
  let finishAnalysis;
  context.fetch = () => new Promise(resolve => { finishAnalysis = resolve; });
  const pending = app.renderVals().runAiAnalysis();
  app.renderVals().extracted[3].onChange({ target: { value: "Updated after request" } });
  finishAnalysis({ ok: true, json: async () => ({ analysis: { summary: "Outdated result" } }) });
  await pending;
  assert.equal(app.state.aiAnalysis, null);
  assert.equal(app.state.aiBusy, false);
  console.log("UI route and correction checks passed");
})().catch(error => { console.error(error); process.exitCode = 1; });