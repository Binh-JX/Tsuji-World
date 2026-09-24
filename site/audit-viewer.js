(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.TsujiAuditViewer = api;
})(typeof window !== "undefined" ? window : globalThis, function () {
  "use strict";

  function requireObject(value, name) {
    if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(name + " must be an object");
    return value;
  }

  function parseArtifacts(input) {
    const audit = requireObject(input.audit, "audit.json");
    const proof = requireObject(input.proof, "proof.json");
    const signoff = requireObject(input.signoff, "signoff.json");
    const routes = requireObject(input.routes, "routes.json");
    if (audit.schema_version !== "v1" || proof.schema_version !== "v1" || signoff.schema_version !== "v1") throw new Error("unsupported artifact schema version");
    if (typeof audit.status !== "string" || !Array.isArray(audit.stages) || !audit.counts || !audit.fixity) throw new Error("audit.json is incomplete");
    if (!Array.isArray(proof.records) || !proof.signoffs || !proof.proof_sha256) throw new Error("proof.json is incomplete");
    if (!signoff.signoff_sha256 || signoff.proof_sha256 !== proof.proof_sha256) throw new Error("sign-off does not bind to proof");
    return { audit: audit, proof: proof, signoff: signoff, routes: routes };
  }

  function buildViewModel(artifacts) {
    const parsed = parseArtifacts(artifacts);
    const fixityEntries = Object.keys(parsed.audit.fixity).map(function (name) {
      const item = parsed.audit.fixity[name] || {};
      return { name: name, checked: Number(item.checked || 0), failures: Array.isArray(item.failures) ? item.failures.slice() : ["malformed fixity state"] };
    });
    const failures = fixityEntries.reduce(function (count, item) { return count + item.failures.length; }, 0);
    const signoffs = Object.keys(parsed.signoff.signoffs || {}).map(function (role) {
      const item = parsed.signoff.signoffs[role] || {};
      return { role: role, name: item.name || "Pending", date: item.date || "", status: item.status || "pending" };
    });
    return {
      project: parsed.audit.project || "TSUJI WORLD",
      edition: parsed.audit.edition || "",
      release: parsed.audit.release || "",
      status: parsed.audit.status,
      stages: parsed.audit.stages.slice(),
      counts: Object.assign({}, parsed.audit.counts),
      fixity: fixityEntries,
      fixityHealthy: failures === 0,
      proofHash: parsed.proof.proof_sha256,
      signoffHash: parsed.signoff.signoff_sha256,
      signoffs: signoffs,
      recordCount: parsed.proof.records.length,
      routeCount: Object.keys(parsed.routes).length,
      artifacts: parsed
    };
  }

  function createLocalMetrics(storage) {
    const target = storage || (typeof sessionStorage !== "undefined" ? sessionStorage : null);
    let views = Number(target && target.getItem("tsuji-local-views") || 0) + 1;
    if (target) target.setItem("tsuji-local-views", String(views));
    return { views: views, active: 1, label: "This browser session" };
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>\"']/g, function (character) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[character]; });
  }

  function render(container, model, metrics) {
    const fixityClass = model.fixityHealthy ? "ok" : "bad";
    const stageMarkup = model.stages.map(function (stage) { return '<li class="stage"><span class="dot ok"></span>' + escapeHtml(stage) + '</li>'; }).join("");
    const fixityMarkup = model.fixity.map(function (item) { return '<li><span>' + escapeHtml(item.name) + '</span><strong class="' + (item.failures.length ? "bad" : "ok") + '">' + item.checked + ' checked</strong></li>'; }).join("");
    const signoffMarkup = model.signoffs.map(function (item) { return '<li><span>' + escapeHtml(item.role) + '</span><strong class="' + (item.status === "signed" ? "ok" : "pending") + '">' + escapeHtml(item.status) + '</strong><small>' + escapeHtml(item.name) + '</small></li>'; }).join("");
    container.innerHTML = '<header class="topbar"><div><p class="kicker">CORE REVIEW / ' + escapeHtml(model.edition) + '</p><h1>' + escapeHtml(model.project) + '</h1><p class="subline">Release ' + escapeHtml(model.release) + ' · cryptographic pipeline view</p></div><span class="status ' + (model.status === "passed" ? "ok" : "bad") + '">' + escapeHtml(model.status) + '</span></header>' +
      '<main><section class="hero"><div><p class="eyebrow">AUDIT READOUT</p><h2>Quiet proof, visible custody.</h2><p>Published artifacts only. This viewer never reads archive data or sends analytics.</p></div><div class="hero-seal"><span>SHA-256</span><code>' + escapeHtml(model.proofHash.slice(0, 18)) + '...</code></div></section>' +
      '<section class="metrics"><article><span>Records</span><strong>' + model.recordCount + '</strong><small>proof sheet</small></article><article><span>Routes</span><strong>' + model.routeCount + '</strong><small>Core generated</small></article><article><span>Fixity</span><strong class="' + fixityClass + '">' + (model.fixityHealthy ? "Clear" : "Review") + '</strong><small>' + model.counts.fixity_checks + ' checks</small></article><article><span>Local views</span><strong>' + metrics.views + '</strong><small>' + escapeHtml(metrics.label) + '</small></article></section>' +
      '<section class="grid"><article class="panel wide"><div class="panel-heading"><div><p class="eyebrow">PIPELINE</p><h3>Release stages</h3></div><span class="caption">fail-closed</span></div><ol class="stages">' + stageMarkup + '</ol></article><article class="panel"><div class="panel-heading"><div><p class="eyebrow">FIXITY</p><h3>Integrity health</h3></div></div><ul class="list">' + fixityMarkup + '</ul></article><article class="panel"><div class="panel-heading"><div><p class="eyebrow">SIGN-OFF</p><h3>Review custody</h3></div></div><ul class="list">' + signoffMarkup + '</ul></article></section>' +
      '<section class="panel hashes"><div class="panel-heading"><div><p class="eyebrow">SEALS</p><h3>Independent verification</h3></div></div><dl><dt>Proof</dt><dd>' + escapeHtml(model.proofHash) + '</dd><dt>Sign-off</dt><dd>' + escapeHtml(model.signoffHash) + '</dd></dl></section></main><footer>Local review surface · no credentials · no external requests</footer>';
  }

  return { parseArtifacts: parseArtifacts, buildViewModel: buildViewModel, createLocalMetrics: createLocalMetrics, render: render };
});
