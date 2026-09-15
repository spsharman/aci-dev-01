#!/usr/bin/env python3
"""ACI tenant / VRF / ESG diagrams.  Cross-platform (Linux / macOS / Windows).

Run these from the repo root (aci-dev-01), not from diagrams/.
Default tenant is common. There is no default NAC file.

Four ways to run
================

1. Retrieve tenant.json from APIC
   python3 diagrams/render_v9_tenant_diagram.py --no-prompt --tenant common --from-apic

2. Path to a downloaded tenant.json
   python3 diagrams/render_v9_tenant_diagram.py --no-prompt --tenant common --tenant-json diagrams/tn-common/tenant.json

3. Retrieve tenant.json from APIC + path to NAC configuration
   python3 diagrams/render_v9_tenant_diagram.py --no-prompt --tenant common --from-apic --nac path/to/configuration.nac.yaml

4. Path to a downloaded tenant.json + path to NAC configuration
   python3 diagrams/render_v9_tenant_diagram.py --no-prompt --tenant common --tenant-json diagrams/tn-common/tenant.json --nac path/to/configuration.nac.yaml

Outputs land in diagrams/tn-<tenant>/. APIC login writes tenant.json there.
Copy diagrams/.env.example to diagrams/.env for host and user (gitignored).
Password is taken from the dialog or APIC_PASS and is never stored in this file.

Fonts
=====
No font paths are hardcoded to one OS. Resolution order:
  1. --font-regular / --font-bold flags
  2. DIAGRAM_FONT_REG / DIAGRAM_FONT_BOLD environment variables
  3. Per-OS candidate list (Arial, Helvetica, Liberation Sans, DejaVu Sans, ...)
  4. Pillow's built-in font (last resort; layout will look rough)
Liberation Sans is metric-compatible with Arial and is the preferred Linux pick.

Layout
======
Every y coordinate is measured before anything is drawn (see _layout()).
No hardcoded canvas heights, no fixed row positions: BD rows wrap, AP columns
are packed by height, and all text is clipped to its container. This is what
stops large tenants from overlapping.

Output formats
==============
--format png | svg | both.  SVG scales without loss, is far smaller for big
tenants, is text-searchable in a browser, and carries hover tooltips with the
untruncated value wherever a label had to be clipped.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import ssl
import sys
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from http.cookiejar import CookieJar
from pathlib import Path
from xml.sax.saxutils import escape as _xesc

import yaml
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DEFAULT_TENANT = "common"


def load_local_env() -> None:
    """Load APIC_HOST / APIC_USER / APIC_PASS from a gitignored .env if present."""
    for path in (HERE / ".env", REPO / ".env"):
        if not path.is_file():
            continue

        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            # Explicit environment variables take priority over .env values.
            if key and key not in os.environ:
                os.environ[key] = value


load_local_env()

# Host and user come from the environment or dialog — never from this file.
DEFAULT_APIC_HOST = os.environ.get("APIC_HOST", "")
DEFAULT_APIC_USER = os.environ.get("APIC_USER", "")

# macOS ships a deprecated system Tk; silence that warning before any Tk import.
os.environ.setdefault("TK_SILENCE_DEPRECATION", "1")

W, H = 3400, 2180

# --------------------------------------------------------------------------- #
# Fonts                                                                       #
# --------------------------------------------------------------------------- #

_FONT_CANDIDATES: dict[str, list[str]] = {
    "regular": [
        # macOS
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
        # Linux — Debian / Ubuntu
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
        # Linux — RHEL / Rocky / Fedora / SUSE
        "/usr/share/fonts/liberation-sans/LiberationSans-Regular.ttf",
        "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
        # Linux — Arch / Alpine
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/LiberationSans-Regular.ttf",
        "/usr/share/fonts/noto/NotoSans-Regular.ttf",
        # Windows
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
    ],
    "bold": [
        # macOS
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        # Linux — Debian / Ubuntu
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf",
        # Linux — RHEL / Rocky / Fedora / SUSE
        "/usr/share/fonts/liberation-sans/LiberationSans-Bold.ttf",
        "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
        # Linux — Arch / Alpine
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/LiberationSans-Bold.ttf",
        "/usr/share/fonts/noto/NotoSans-Bold.ttf",
        # Windows
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "C:/Windows/Fonts/tahomabd.ttf",
    ],
}



# Bare names so Pillow can search the OS font path (helps on Windows and on
# Linux boxes with fonts in non-standard locations).
_FONT_BY_NAME = {
    "regular": ["LiberationSans-Regular.ttf", "DejaVuSans.ttf", "Arial.ttf", "arial.ttf"],
    "bold": ["LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"],
}

# --------------------------------------------------------------------------- #
# Interactive viewer (d3 v7). Self-contained: data is inlined, so the file    #
# opens by double-clicking — no web server and no CORS problem.               #
# --------------------------------------------------------------------------- #

_VIEWER_HTML = r"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TENANT__ — contract relationships</title>
__D3_TAGS__
<style>
  /* ---------- light (default) ---------- */
  :root {
    color-scheme: light;
    --bg:#f7f8f9; --panel:#ffffff; --ink:#212529; --muted:#6c757d;
    --line:#e2e2e2; --hair:#f2f2f2; --row:#fafafa; --head:#ecf5e4;
    --green:#7ab548; --orange:#f47b20; --red:#c41e3a;
    --kind-epg:#0091d6; --kind-esg:#66a636; --kind-vzany:#3d4348; --kind-other:#8a9199;
    --kind-contract:#f47b20;
    --consumer:#0091ad; --provider:#66a636; --both:#f47b20;
    --link:#0091ad; --faint:#c2c8ce;
    --cell-lo:#eaf4dd; --cell-hi:#c41e3a; --cell-bg:#fcfcfc; --grid:#eef0f2;
    --pill-bg:#eef6e7; --pill-fg:#4b7a2a;
    --pill-c-bg:#fdecef; --pill-c-fg:#8c1024;
    --pill-w-bg:#fff6d8; --pill-w-fg:#7a5c00; --pill-w-bd:#f5c018;
    --pill-f-bg:#eaf4fb; --pill-f-fg:#0b5f8a;
    --dim-node:.34; --dim-label:.30; --dim-link:.28;
    --shadow:0 1px 2px rgba(0,0,0,.05);
    accent-color:#7ab548;
  }
  /* ---------- dark ---------- */
  html[data-theme="dark"] {
    color-scheme: dark;
    --bg:#14171a; --panel:#1c2024; --ink:#e6e9ec; --muted:#8b949e;
    --line:#2c3238; --hair:#23282d; --row:#20252a; --head:#233021;
    --green:#8fce5c; --orange:#ff9542; --red:#ff5f74;
    --kind-epg:#3fb6f0; --kind-esg:#7fd155; --kind-vzany:#aab3bb; --kind-other:#79828b;
    --kind-contract:#ff9542;
    --consumer:#35bed3; --provider:#8fce5c; --both:#ffab5c;
    --link:#35bed3; --faint:#3a424a;
    --cell-lo:#24352a; --cell-hi:#ff5f74; --cell-bg:#1a1e22; --grid:#262c32;
    --pill-bg:#22301d; --pill-fg:#a5d97a;
    --pill-c-bg:#331a1f; --pill-c-fg:#ff8fa0;
    --pill-w-bg:#332a12; --pill-w-fg:#f0cf7a; --pill-w-bd:#8a6d1c;
    --pill-f-bg:#14293a; --pill-f-fg:#7fc4f0;
    --dim-node:.30; --dim-label:.28; --dim-link:.26;
    --shadow:0 1px 2px rgba(0,0,0,.4);
    accent-color:#8fce5c;
  }

  * { box-sizing:border-box; }
  body { margin:0; font:13px/1.45 "Liberation Sans",Arial,Helvetica,sans-serif;
         color:var(--ink); background:var(--bg); }

  header { background:var(--panel); border-bottom:3px solid var(--green);
           padding:9px 16px; display:flex; align-items:center; gap:14px;
           flex-wrap:wrap; position:sticky; top:0; z-index:20; box-shadow:var(--shadow); }
  header h1 { margin:0; font-size:19px; }
  header .sub { color:var(--muted); font-size:12px; }
  header .stats { margin-left:auto; color:var(--muted); font-size:12px; }
  header .stats b { color:var(--ink); }
  .warn { color:var(--red); font-weight:bold; }
  .tbtn { font:inherit; font-size:15px; line-height:1; padding:5px 10px; cursor:pointer;
          background:var(--panel); color:var(--ink);
          border:1px solid var(--line); border-radius:4px; }
  .tbtn:hover { border-color:var(--green); }

  #layout { display:flex; align-items:flex-start; }
  aside { width:270px; flex:0 0 270px; padding:12px; background:var(--panel);
          border-right:1px solid var(--line); height:calc(100vh - 54px);
          overflow-y:auto; position:sticky; top:54px; }
  aside h3 { font-size:11px; text-transform:uppercase; letter-spacing:.06em;
             color:var(--green); margin:16px 0 6px; display:flex; align-items:baseline; }
  aside h3:first-of-type { margin-top:0; }
  aside label { display:flex; align-items:center; gap:5px; padding:1px 0; cursor:pointer; }
  aside label span.txt { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  aside label.all { border-bottom:1px solid var(--hair); padding-bottom:4px;
                    margin-bottom:3px; }
  .count { margin-left:auto; color:var(--muted); font-size:11px; }
  a.only { margin-left:auto; font-size:10px; color:var(--muted); cursor:pointer;
           text-decoration:none; opacity:0; flex:0 0 auto; }
  aside label:hover a.only { opacity:1; }
  a.only:hover { color:var(--green); text-decoration:underline; }
  aside input[type=search] { width:100%; padding:5px 7px; border:1px solid var(--line);
                             border-radius:3px; font:inherit;
                             background:var(--bg); color:var(--ink); }
  #reset { width:100%; margin-top:14px; }

  main { flex:1; padding:12px 16px 40px; min-width:0; }
  .tabs { display:flex; gap:6px; margin-bottom:10px; flex-wrap:wrap; }
  .tabs button { font:inherit; padding:6px 14px; cursor:pointer;
                 border:1px solid var(--line); border-radius:4px;
                 background:var(--panel); color:var(--ink); }
  .tabs button:hover { border-color:var(--green); }
  .tabs button.on { background:var(--green); border-color:var(--green);
                    color:#10240a; font-weight:bold; }

  #canvas { background:var(--panel); border:1px solid var(--line); border-radius:6px;
            overflow:auto; box-shadow:var(--shadow); }
  svg { display:block; }
  .hint { color:var(--muted); font-size:12px; margin:8px 0 0; }

  .lbl { font-size:11px; fill:var(--ink); pointer-events:none; }
  .lbl-sm { font-size:10px; fill:var(--muted); pointer-events:none; }
  .link { fill:none; }
  .cell { stroke:var(--panel); stroke-width:1px; cursor:pointer; }
  .sankey-node rect { cursor:pointer; }
  .sankey-link { fill:none; }
  .chord-ribbon { stroke:var(--panel); stroke-width:.4px; }
  .dim      { opacity:var(--dim-node) !important; }
  .dim-lbl  { opacity:var(--dim-label) !important; }

  #tip { position:fixed; pointer-events:none; background:rgba(16,18,20,.95);
         color:#f3f5f7; padding:6px 9px; border-radius:4px; font-size:12px;
         max-width:360px; opacity:0; transition:opacity .1s; z-index:60;
         box-shadow:0 2px 8px rgba(0,0,0,.35); }
  #detail { margin-top:12px; background:var(--panel); border:1px solid var(--line);
            border-radius:6px; padding:12px; box-shadow:var(--shadow); }
  #detail h2 { margin:0 0 6px; font-size:15px; }
  #detail table { border-collapse:collapse; width:100%; margin-top:8px; }
  #detail th { text-align:left; font-size:11px; text-transform:uppercase;
               color:var(--green); border-bottom:1px solid var(--line);
               padding:4px 8px 4px 0; }
  #detail td { padding:3px 8px 3px 0; border-bottom:1px solid var(--hair);
               vertical-align:top; }
  .pill { display:inline-block; padding:1px 7px; border-radius:9px; font-size:11px;
          background:var(--pill-bg); color:var(--pill-fg);
          border:1px solid var(--kind-esg); }
  .pill.c { background:var(--pill-c-bg); color:var(--pill-c-fg); border-color:var(--red); }
  .pill.w { background:var(--pill-w-bg); color:var(--pill-w-fg);
            border-color:var(--pill-w-bd); }
  .pill.f { background:var(--pill-f-bg); color:var(--pill-f-fg);
            border-color:var(--kind-epg);
            font-family:ui-monospace,Menlo,Consolas,monospace; font-size:10.5px; }
  a.obj { color:var(--kind-epg); cursor:pointer; text-decoration:none; }
  a.obj:hover { text-decoration:underline; }
</style>
</head>
<body>
<header>
  <h1>__TENANT__</h1>
  <span class="sub">__SUBTITLE__</span>
  <span class="stats" id="stats"></span>
  <button class="tbtn" id="theme" title="Toggle dark mode (d)">◐</button>
</header>

<div id="layout">
  <aside>
    <h3>Search</h3>
    <input type="search" id="q" placeholder="object, contract or port…">
    <h3>Object type</h3><div id="f-kind"></div>
    <h3>Application profile</h3><div id="f-ap"></div>
    <h3>Contract</h3><div id="f-contract"></div>
    <h3>Audit</h3><div id="audit"></div>
    <button class="tbtn" id="reset">Reset filters</button>
  </aside>

  <main>
    <div class="tabs" id="tabs"></div>
    <div id="canvas"></div>
    <p class="hint" id="hint"></p>
    <div id="detail"></div>
  </main>
</div>

<div id="tip"></div>
<script type="application/json" id="graph-data">__GRAPH_DATA__</script>
<script>
window.addEventListener('error', function (e) {
  var box = document.getElementById('canvas');
  if (!box) return;
  box.innerHTML = '<div style="padding:22px;color:#c41e3a">' +
    '<b>Viewer script error \u2014 nothing rendered.</b><br><br><code>' +
    String(e.message || e.error) + '</code><br><span style="opacity:.7">line ' +
    (e.lineno || '?') + ', column ' + (e.colno || '?') + ' of this file</span></div>';
});
</script>
<script>
"use strict";
__VIEWER_JS__
</script>
</body>
</html>
"""

_VIEWER_JS = r"""
/* ===================================================== data + small helpers */
const DATA  = JSON.parse(document.getElementById('graph-data').textContent);
const NODES = new Map(DATA.nodes.map(n => [n.id, n]));
const CONTRACT = new Map(DATA.contracts.map(c => [c.name, c]));

const $   = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"]/g,
  ch => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;' }[ch]));
const fmt = n => String(n);
const pairKey = (a, b) => a + '\u0001' + b;

const cFilters  = name => (CONTRACT.get(name) || {}).filters || [];
const filtPills = name => cFilters(name)
  .map(f => '<span class="pill f">' + esc(f) + '</span>').join(' ');
const filtLines = name => cFilters(name).map(f => esc(f)).join('<br>');
const contractText = name => name + ' ' + cFilters(name).join(' ');

const KIND_LABEL = { epg: 'EPG', esg: 'ESG', vzany: 'vzAny', other: 'other' };
const SYMBOL = {
  consumer: d3.symbolCircle,
  provider: d3.symbolSquare,
  both:     d3.symbolDiamond
};

/* ===================================================== theme */
const THEME_KEY = 'aci-diagram-theme';
let P = {};

function palette() {
  const cs = getComputedStyle(document.documentElement);
  const v  = n => cs.getPropertyValue(n).trim();
  return {
    epg:v('--kind-epg'), esg:v('--kind-esg'), vzany:v('--kind-vzany'),
    other:v('--kind-other'), contract:v('--kind-contract'),
    consumer:v('--consumer'), provider:v('--provider'), both:v('--both'),
    link:v('--link'), faint:v('--faint'), ink:v('--ink'), muted:v('--muted'),
    panel:v('--panel'), cellLo:v('--cell-lo'), cellHi:v('--cell-hi'),
    cellBg:v('--cell-bg'), grid:v('--grid')
  };
}
const kindColor = k => P[k] || P.other;
const roleColor = r => r === 'both' ? P.both : r === 'provider' ? P.provider : P.consumer;

function applyTheme(t) {
  document.documentElement.dataset.theme = t;
  try { localStorage.setItem(THEME_KEY, t); } catch (e) { /* file:// */ }
  P = palette();
}
(function initTheme() {
  let t = null;
  try { t = localStorage.getItem(THEME_KEY); } catch (e) { /* ignore */ }
  if (!t) {
    t = window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark' : 'light';
  }
  applyTheme(t);
})();

/* ===================================================== tooltip */
const tip = $('#tip');
function showTip(html, ev) {
  tip.innerHTML = html;
  tip.style.opacity = 1;
  tip.style.left = Math.min(ev.clientX + 14, innerWidth  - 372) + 'px';
  tip.style.top  = Math.min(ev.clientY + 16, innerHeight - 110) + 'px';
}
const hideTip = () => { tip.style.opacity = 0; };

/* ===================================================== filter state
   state.sel is one of:
     null
     { t:'node',     id:<nodeId>, role:'consumer'|'provider' }
     { t:'contract', name:<contractName> }
   A node selection is DIRECTIONAL: one object on its own axis, n on the other. */
const state = {
  view: 'force',
  kinds:     new Set(DATA.nodes.map(n => n.kind)),
  aps:       new Set(DATA.nodes.map(n => n.ap)),
  contracts: new Set(DATA.contracts.map(c => c.name)),
  q: '',
  sel: null
};

const matches = t => !state.q || String(t).toLowerCase().includes(state.q);

function nodeVisible(id) {
  const n = NODES.get(id);
  return !!n && state.kinds.has(n.kind) && state.aps.has(n.ap);
}
function visibleLinks() {
  return DATA.links.filter(l =>
    state.contracts.has(l.contract) &&
    nodeVisible(l.source) && nodeVisible(l.target) &&
    (!state.q || matches(contractText(l.contract)) ||
     matches(NODES.get(l.source).label) || matches(NODES.get(l.target).label)));
}
function visibleNodeIds(links) {
  const s = new Set();
  links.forEach(l => { s.add(l.source); s.add(l.target); });
  return [...s];
}

/* ---- selection ---------------------------------------------------------- */
function globalRoles(id) {
  return {
    consumes: DATA.links.some(l => l.source === id),
    provides: DATA.links.some(l => l.target === id)
  };
}

/* role omitted  -> auto-pick, and flip on a repeat click of the same node.
   role supplied -> honour it (Sankey column, Matrix axis). */
function selectNode(id, role) {
  const r = globalRoles(id);
  let use = role || null;
  if (!use) {
    const same = state.sel && state.sel.t === 'node' && state.sel.id === id;
    if (same && r.consumes && r.provides) {
      use = state.sel.role === 'consumer' ? 'provider' : 'consumer';
    } else {
      use = r.consumes ? 'consumer' : 'provider';
    }
  }
  if (use === 'consumer' && !r.consumes) use = 'provider';
  if (use === 'provider' && !r.provides) use = 'consumer';
  state.sel = { t: 'node', id: id, role: use };
}
const selectContract = name => { state.sel = { t: 'contract', name: name }; };
const flipSelection = () => {
  if (state.sel && state.sel.t === 'node') {
    selectNode(state.sel.id,
      state.sel.role === 'consumer' ? 'provider' : 'consumer');
  }
};

function selection() {
  if (!state.sel) return null;

  if (state.sel.t === 'contract') {
    const name = state.sel.name;
    const links = DATA.links.filter(l => l.contract === name);
    const cons = new Set(), prov = new Set(), pairs = new Set();
    links.forEach(l => {
      cons.add(l.source); prov.add(l.target); pairs.add(pairKey(l.source, l.target));
    });
    return {
      contract: name, focus: null, role: null,
      cons: cons, prov: prov, contracts: new Set([name]), pairs: pairs,
      any: new Set([...cons, ...prov])
    };
  }

  /* Directional: only ONE direction is collected, so the focus object is the
     sole member of its own axis. This is what makes it strictly 1:n. */
  const id = state.sel.id, role = state.sel.role;
  const links = role === 'consumer'
    ? DATA.links.filter(l => l.source === id)
    : DATA.links.filter(l => l.target === id);

  const cons = new Set(), prov = new Set(), contracts = new Set(), pairs = new Set();
  links.forEach(l => {
    cons.add(l.source); prov.add(l.target);
    contracts.add(l.contract); pairs.add(pairKey(l.source, l.target));
  });
  if (role === 'consumer') { cons.clear(); cons.add(id); }
  else                     { prov.clear(); prov.add(id); }

  return {
    contract: null, focus: id, role: role,
    cons: cons, prov: prov, contracts: contracts, pairs: pairs,
    any: new Set([...cons, ...prov])
  };
}

function linkSelected(l, S) {
  if (!S) return true;
  if (S.contract) return l.contract === S.contract;
  return S.role === 'consumer' ? (l.source === S.focus) : (l.target === S.focus);
}

/* Role within the currently visible sub-graph (drives shape / arc colour). */
function roleMap(links) {
  const cons = new Set(links.map(l => l.source));
  const prov = new Set(links.map(l => l.target));
  const m = new Map();
  visibleNodeIds(links).forEach(id => {
    const c = cons.has(id), p = prov.has(id);
    m.set(id, c && p ? 'both' : p ? 'provider' : 'consumer');
  });
  return m;
}

/* ===================================================== legend */
function kindsPresent(ids) {
  const out = [];
  ids.forEach(id => {
    const k = (NODES.get(id) || {}).kind || 'other';
    if (out.indexOf(k) < 0) out.push(k);
  });
  return out.sort();
}

function drawLegend(svg, x, y, ids, showShapes) {
  const kinds = kindsPresent(ids);
  const rows = (showShapes ? 4 : 0) + 1 + kinds.length;
  const g = svg.append('g')
    .attr('transform', 'translate(' + x + ',' + y + ')')
    .style('pointer-events', 'none');
  g.append('rect')
    .attr('width', 196).attr('height', 16 * rows + 12).attr('rx', 4)
    .attr('fill', P.panel).attr('fill-opacity', .93)
    .attr('stroke', P.grid);

  let cy = 15;
  const head = t => {
    g.append('text').attr('class', 'lbl-sm').attr('x', 9).attr('y', cy)
      .attr('font-weight', 'bold').attr('fill', P.muted).text(t);
    cy += 16;
  };

  if (showShapes) {
    head('SHAPE = role');
    [['consumer', 'consumes only'], ['provider', 'provides only'],
     ['both', 'consumes + provides']].forEach(it => {
      g.append('path')
        .attr('d', d3.symbol().type(SYMBOL[it[0]]).size(118)())
        .attr('transform', 'translate(18,' + (cy - 4) + ')')
        .attr('fill', 'none').attr('stroke', roleColor(it[0])).attr('stroke-width', 2.2);
      g.append('text').attr('class', 'lbl-sm').attr('x', 32).attr('y', cy).text(it[1]);
      cy += 16;
    });
  }

  head(showShapes ? 'FILL = object type' : 'COLOUR = object type');
  kinds.forEach(k => {
    g.append('rect')
      .attr('x', 12).attr('y', cy - 9).attr('width', 12).attr('height', 12).attr('rx', 2)
      .attr('fill', kindColor(k)).attr('stroke', P.panel);
    g.append('text').attr('class', 'lbl-sm').attr('x', 32).attr('y', cy)
      .text(KIND_LABEL[k] || k);
    cy += 16;
  });
  return g;
}

/* Caption naming the current focus + direction. */
function focusCaption(svg, S, x, y) {
  if (!S) return;
  let txt;
  if (S.contract) {
    txt = 'contract ' + S.contract + '  ·  ' + S.cons.size + ' consumer(s) → ' +
          S.prov.size + ' provider(s)';
  } else {
    const n = NODES.get(S.focus) || { label: S.focus };
    txt = S.role === 'consumer'
      ? n.label + '  consumes →  ' + S.prov.size + ' provider(s)'
      : S.prov.size + ' ← ' + S.cons.size + ' consumer(s)  →  provides  ' + n.label;
    txt = S.role === 'consumer'
      ? n.label + '  →  ' + S.prov.size + ' provider(s)'
      : S.cons.size + ' consumer(s)  →  ' + n.label;
  }
  svg.append('text').attr('class', 'lbl-sm')
    .attr('x', x).attr('y', y)
    .attr('font-weight', 'bold')
    .attr('fill', S.contract ? P.contract : roleColor(S.role))
    .text('focus: ' + txt);
}

/* ===================================================== sidebar */
function checkboxGroup(host, values, set, onchange) {
  host.innerHTML = '';
  const boxes = new Map();

  const all   = document.createElement('label');
  all.className = 'all';
  const allCb = document.createElement('input');
  allCb.type = 'checkbox';
  const allTx = document.createElement('span');
  allTx.className = 'txt';
  allTx.innerHTML = '<b>all</b>';
  const count = document.createElement('span');
  count.className = 'count';
  all.append(allCb, allTx, count);
  host.appendChild(all);

  function sync() {
    const n = values.reduce((a, v) => a + (set.has(v) ? 1 : 0), 0);
    allCb.checked = n === values.length && n > 0;
    allCb.indeterminate = n > 0 && n < values.length;
    count.textContent = n + '/' + values.length;
    boxes.forEach((cb, v) => { cb.checked = set.has(v); });
  }

  /* Toggle from the SET, never from the checkbox's own state. */
  allCb.addEventListener('click', () => {
    const full = values.every(v => set.has(v));
    values.forEach(v => full ? set.delete(v) : set.add(v));
    sync(); onchange();
  });

  values.forEach(v => {
    const l  = document.createElement('label');
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.addEventListener('change', () => {
      if (cb.checked) set.add(v); else set.delete(v);
      sync(); onchange();
    });
    const tx = document.createElement('span');
    tx.className = 'txt';
    tx.textContent = v;
    const only = document.createElement('a');
    only.className = 'only';
    only.textContent = 'only';
    only.title = 'Show only this';
    only.addEventListener('click', e => {
      e.preventDefault(); e.stopPropagation();
      set.clear(); set.add(v); sync(); onchange();
    });
    l.append(cb, tx, only);
    host.appendChild(l);
    boxes.set(v, cb);
  });

  sync();
  return sync;
}

const SYNC = [];

function buildSidebar() {
  const kinds = [...new Set(DATA.nodes.map(n => n.kind))].sort();
  const aps   = [...new Set(DATA.nodes.map(n => n.ap))].sort();
  const cons  = DATA.contracts.map(c => c.name).sort();
  SYNC.length = 0;
  SYNC.push(checkboxGroup($('#f-kind'),     kinds, state.kinds,     render));
  SYNC.push(checkboxGroup($('#f-ap'),       aps,   state.aps,       render));
  SYNC.push(checkboxGroup($('#f-contract'), cons,  state.contracts, render));
  buildAudit();
  buildStats();
}
const syncSidebar = () => SYNC.forEach(f => f());

function buildAudit() {
  const bad = DATA.contracts.filter(c => c.dangling);
  const nof = DATA.contracts.filter(c => !c.dangling && !(c.filters || []).length);
  const row = (cls, txt, name) =>
    '<div><span class="pill ' + cls + '">' + txt + '</span> ' +
    '<a class="obj" data-contract="' + esc(name) + '">' + esc(name) + '</a></div>';
  $('#audit').innerHTML =
    (bad.length
      ? bad.map(c => row('w', c.consumers.length ? 'no provider' : 'no consumer', c.name)).join('')
      : '<span class="pill">all contracts have both ends</span>') +
    (nof.length
      ? '<div style="margin-top:6px"></div>' + nof.map(c => row('w', 'no filters', c.name)).join('')
      : '');
  $('#audit').querySelectorAll('[data-contract]').forEach(a => {
    a.onclick = () => { selectContract(a.dataset.contract); render(); };
  });
}

function buildStats() {
  const s = DATA.stats;
  $('#stats').innerHTML =
    '<b>' + s.nodes + '</b> objects · <b>' + s.contracts + '</b> contracts · <b>' +
    s.links + '</b> relationships' +
    (s.dangling   ? ' · <span class="warn">' + s.dangling   + ' incomplete</span>' : '') +
    (s.unfiltered ? ' · <span class="warn">' + s.unfiltered + ' unfiltered</span>' : '');
}

/* ===================================================== detail panel */
function objLink(id, role) {
  const n = NODES.get(id);
  return '<a class="obj" data-node="' + esc(id) + '"' +
         (role ? ' data-role="' + role + '"' : '') + '>' +
         esc(n ? n.label : id) + '</a>';
}

function detail() {
  const host = $('#detail');
  if (!state.sel) {
    host.innerHTML = '<h2>Nothing selected</h2><p class="hint">' +
      'Click an object or a contract in any view. Selecting an object is ' +
      'directional — one consumer to many providers, or one provider to many ' +
      'consumers. Press Esc to clear, f to flip direction.</p>';
    return;
  }

  if (state.sel.t === 'contract') {
    const ct = CONTRACT.get(state.sel.name);
    if (!ct) { state.sel = null; return detail(); }
    host.innerHTML =
      '<h2>Contract ' + esc(ct.name) + '</h2>' +
      (ct.scope ? '<span class="pill">' + esc(ct.scope) + '</span> ' : '') +
      ((ct.filters || []).length ? filtPills(ct.name)
        : '<span class="pill w">no filters resolved</span>') +
      '<table><tr><th>Consumers (' + ct.consumers.length + ')</th>' +
      '<th>Providers (' + ct.providers.length + ')</th></tr><tr><td>' +
      (ct.consumers.map(id => objLink(id, 'consumer')).join('<br>') || '<i>none</i>') +
      '</td><td>' +
      (ct.providers.map(id => objLink(id, 'provider')).join('<br>') || '<i>none</i>') +
      '</td></tr></table>';
  } else {
    const n = NODES.get(state.sel.id);
    if (!n) { state.sel = null; return detail(); }
    const role = state.sel.role;
    const r = globalRoles(n.id);
    const consumed = DATA.contracts.filter(x => x.consumers.includes(n.id));
    const provided = DATA.contracts.filter(x => x.providers.includes(n.id));
    const list = role === 'consumer' ? consumed : provided;

    host.innerHTML =
      '<h2>' + (KIND_LABEL[n.kind] || n.kind) + ' ' + esc(n.label) + '</h2>' +
      '<span class="pill">AP ' + esc(n.ap) + '</span> ' +
      '<span class="pill">VRF ' + esc(n.vrf || '—') + '</span> ' +
      '<span class="pill ' + (role === 'consumer' ? 'c' : '') + '">viewing as ' +
        role + '</span> ' +
      ((r.consumes && r.provides)
        ? ' <a class="obj" id="flip">flip to ' +
          (role === 'consumer' ? 'provider' : 'consumer') + ' →</a>'
        : '') +
      '<table><tr><th>' +
      (role === 'consumer'
        ? 'Consumes (' + consumed.length + ') → providers'
        : 'Provides (' + provided.length + ') ← consumers') +
      '</th></tr><tr><td>' +
      (list.map(x =>
        role === 'consumer'
          ? '<a class="obj" data-contract="' + esc(x.name) + '">' + esc(x.name) +
            '</a> ' + filtPills(x.name) + ' → ' +
            (x.providers.map(id => objLink(id, 'provider')).join(', ')
              || '<i>no provider</i>')
          : (x.consumers.map(id => objLink(id, 'consumer')).join(', ')
              || '<i>no consumer</i>') +
            ' → <a class="obj" data-contract="' + esc(x.name) + '">' + esc(x.name) +
            '</a> ' + filtPills(x.name)
      ).join('<br>') || '<i>none</i>') +
      '</td></tr></table>' +
      '<p class="hint">Also ' + (role === 'consumer'
        ? 'provides ' + provided.length + ' contract(s)'
        : 'consumes ' + consumed.length + ' contract(s)') +
      ' — not shown in this direction.</p>';

    const fl = document.getElementById('flip');
    if (fl) fl.onclick = () => { flipSelection(); render(); };
  }

  host.querySelectorAll('[data-node]').forEach(a => {
    a.onclick = () => { selectNode(a.dataset.node, a.dataset.role || null); render(); };
  });
  host.querySelectorAll('[data-contract]').forEach(a => {
    a.onclick = () => { selectContract(a.dataset.contract); render(); };
  });
}

/* ===================================================== view: force */
function drawForce() {
  const links = visibleLinks();
  if (!links.length) return empty();
  const roles = roleMap(links);
  const ids   = visibleNodeIds(links);
  const S     = selection();

  const w = Math.max(680, ($('#canvas').clientWidth || 1100) - 4);
  const h = Math.max(560, Math.min(920, 300 + ids.length * 13));

  const nodes = ids.map(id => {
    const n = NODES.get(id);
    const rad = 7 + Math.min(9, (n.degree || 1) * 1.3);
    return Object.assign({}, n,
      { role: roles.get(id), rad: rad, area: Math.PI * rad * rad });
  });
  const byId = new Map(nodes.map(n => [n.id, n]));
  const ls = links.map(l => Object.assign({}, l,
    { source: byId.get(l.source), target: byId.get(l.target) }));

  const svg = d3.create('svg').attr('width', w).attr('height', h);
  const defs = svg.append('defs');
  [['arrow', P.faint], ['arrow-hot', P.link]].forEach(a => {
    defs.append('marker').attr('id', a[0]).attr('viewBox', '0 -5 10 10')
      .attr('refX', 19).attr('refY', 0)
      .attr('markerWidth', 5).attr('markerHeight', 5).attr('orient', 'auto')
      .append('path').attr('d', 'M0,-4L9,0L0,4').attr('fill', a[1]);
  });
  svg.on('click', () => { state.sel = null; render(); });

  const g = svg.append('g');
  svg.call(d3.zoom().scaleExtent([0.35, 3])
      .on('zoom', e => g.attr('transform', e.transform)))
     .on('dblclick.zoom', null);

  const link = g.append('g').selectAll('path').data(ls).join('path')
    .attr('class', 'link')
    .attr('stroke', d => linkSelected(d, S) ? P.link : P.faint)
    .attr('stroke-width', d => linkSelected(d, S) ? 2.4 : 1.3)
    .attr('stroke-opacity', d => !S ? .55 : (linkSelected(d, S) ? .95 : .16))
    .attr('marker-end', d => linkSelected(d, S) ? 'url(#arrow-hot)' : 'url(#arrow)')
    .style('cursor', 'pointer')
    .on('mouseover', (e, d) => showTip(
      '<b>' + esc(d.contract) + '</b>' + (d.scope ? ' · ' + esc(d.scope) : '') + '<br>' +
      esc(d.source.label) + ' → ' + esc(d.target.label) +
      (cFilters(d.contract).length ? '<br>' + filtLines(d.contract) : ''), e))
    .on('mouseout', hideTip)
    .on('click', (e, d) => {
      e.stopPropagation(); selectContract(d.contract); render();
    });

  const node = g.append('g').selectAll('g.n').data(nodes).join('g').attr('class', 'n')
    .classed('dim', d => !!(S && !S.any.has(d.id)))
    .style('cursor', 'pointer')
    .on('click', (e, d) => { e.stopPropagation(); selectNode(d.id, null); render(); })
    .on('mouseover', (e, d) => showTip(
      '<b>' + esc(d.label) + '</b><br>' +
      (KIND_LABEL[d.kind] || d.kind) + ' · AP ' + esc(d.ap) +
      '<br>here: ' + d.role +
      '<br>overall: consumes ' + d.consumes + ' · provides ' + d.provides +
      ((d.consumes && d.provides) ? '<br><i>click twice to flip direction</i>' : ''), e))
    .on('mouseout', hideTip)
    .call(d3.drag()
      .on('start', (e, d) => {
        if (!e.active) sim.alphaTarget(.25).restart(); d.fx = d.x; d.fy = d.y;
      })
      .on('drag',  (e, d) => { d.fx = e.x; d.fy = e.y; })
      .on('end',   (e, d) => {
        if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null;
      }));

  node.append('path')
    .attr('d', d => d3.symbol()
      .type(SYMBOL[d.role] || d3.symbolCircle).size(d.area * 1.25)())
    .attr('fill', d => kindColor(d.kind))
    .attr('stroke', d => (S && S.focus === d.id)
      ? roleColor(S.role) : roleColor(d.role))
    .attr('stroke-width', d => (S && S.focus === d.id) ? 4.5 : 2.5);
  node.append('text').attr('class', 'lbl')
    .attr('x', d => d.rad + 7).attr('y', 4)
    .text(d => d.label);

  const sim = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(ls).id(d => d.id).distance(155).strength(.35))
    .force('charge', d3.forceManyBody().strength(-390))
    .force('center', d3.forceCenter(w / 2, h / 2))
    .force('collide', d3.forceCollide(d => d.rad + 17))
    .on('tick', () => {
      link.attr('d', d => {
        const dx = d.target.x - d.source.x, dy = d.target.y - d.source.y;
        const r = Math.hypot(dx, dy) * 1.6;
        return 'M' + d.source.x + ',' + d.source.y + 'A' + r + ',' + r +
               ' 0 0,1 ' + d.target.x + ',' + d.target.y;
      });
      node.attr('transform', d => 'translate(' + d.x + ',' + d.y + ')');
    });

  drawLegend(svg, 12, 12, ids, true);
  focusCaption(svg, S, 220, 24);
  $('#hint').textContent =
    'Shape = role in this view, fill = object type. Selecting an object is ' +
    'directional: click it again (or press f) to flip between its consumer and ' +
    'provider side. Drag to rearrange, scroll to zoom.';
  return svg.node();
}

/* ===================================================== view: sankey */
function drawSankey() {
  const links = visibleLinks();
  if (!links.length) return empty();
  const S = selection();

  /* An object can consume AND provide, so left and right copies must be
     separate nodes: d3-sankey needs an acyclic graph. */
  const names = [];
  const seen  = new Set();
  const add = k => { if (!seen.has(k)) { seen.add(k); names.push(k); } return k; };
  const agg = new Map();
  links.forEach(l => {
    const a = 'c\u0000' + l.source, m = 'k\u0000' + l.contract, b = 'p\u0000' + l.target;
    add(a); add(m); add(b);
    [[a, m], [m, b]].forEach(pair => {
      const key = pair[0] + '\u0001' + pair[1];
      agg.set(key, (agg.get(key) || 0) + 1);
    });
  });
  const index = new Map(names.map((n, i) => [n, i]));
  const sLinks = [...agg].map(kv => {
    const parts = kv[0].split('\u0001');
    return { source: index.get(parts[0]), target: index.get(parts[1]), value: kv[1] };
  });

  const w = Math.max(760, ($('#canvas').clientWidth || 1100) - 4);
  const h = Math.max(430, 52 + names.length * 15);
  const svg = d3.create('svg').attr('width', w).attr('height', h);
  svg.on('click', () => { state.sel = null; render(); });

  const graph = d3.sankey().nodeWidth(16).nodePadding(11)
    .extent([[172, 34], [w - 172, h - 16]])
    ({ nodes: names.map(n => ({ name: n })), links: sLinks });

  const label = n => n.name.slice(n.name.indexOf('\u0000') + 1);
  const side  = n => n.name.charAt(0);   /* c consumer | k contract | p provider */

  /* Strict 1:n — S.cons holds exactly one id when a consumer is focused,
     S.prov exactly one when a provider is focused. */
  const hot = n => {
    if (!S) return true;
    if (side(n) === 'k') return S.contracts.has(label(n));
    return side(n) === 'c' ? S.cons.has(label(n)) : S.prov.has(label(n));
  };
  const nodeFill = n => {
    if (!hot(n)) return P.faint;
    if (side(n) === 'k') return P.contract;
    return side(n) === 'c' ? P.consumer : P.provider;
  };
  const linkOn = d => {
    if (!S) return true;
    if (!(hot(d.source) && hot(d.target))) return false;
    /* Also require the underlying relationship to involve the focus, so a
       shared contract does not pull in unrelated ends. */
    if (S.contract) return true;
    if (side(d.source) === 'c') return S.cons.has(label(d.source));
    return S.prov.has(label(d.target));
  };
  const isFocus = n => !!(S && S.focus && label(n) === S.focus &&
    ((S.role === 'consumer' && side(n) === 'c') ||
     (S.role === 'provider' && side(n) === 'p')));

  svg.append('g').selectAll('path').data(graph.links).join('path')
    .attr('class', 'sankey-link')
    .attr('d', d3.sankeyLinkHorizontal())
    .attr('stroke-width', d => Math.max(1.3, d.width))
    .attr('stroke', d => linkOn(d) ? P.link : P.faint)
    .attr('stroke-opacity', d => !S ? .30 : (linkOn(d) ? .74 : .14))
    .on('mouseover', function (e, d) {
      d3.select(this).attr('stroke-opacity', .9);
      showTip(esc(label(d.source)) + ' → ' + esc(label(d.target)) +
              ' · ' + fmt(d.value) + ' link(s)', e);
    })
    .on('mouseout', function (e, d) {
      d3.select(this).attr('stroke-opacity', !S ? .30 : (linkOn(d) ? .74 : .14));
      hideTip();
    });

  const gn = svg.append('g').selectAll('g').data(graph.nodes).join('g')
    .attr('class', 'sankey-node');
  gn.append('rect')
    .attr('x', d => d.x0).attr('y', d => d.y0)
    .attr('width', d => d.x1 - d.x0)
    .attr('height', d => Math.max(2, d.y1 - d.y0))
    .attr('rx', 2)
    .attr('fill', nodeFill)
    .attr('fill-opacity', d => hot(d) ? 1 : .5)
    .attr('stroke', d => isFocus(d) ? P.ink : 'none')
    .attr('stroke-width', 2)
    .on('click', (e, d) => {
      e.stopPropagation();
      if (side(d) === 'k') selectContract(label(d));
      else if (NODES.has(label(d)))
        selectNode(label(d), side(d) === 'c' ? 'consumer' : 'provider');
      else state.sel = null;
      render();
    })
    .on('mouseover', (e, d) => {
      const n = NODES.get(label(d));
      showTip('<b>' + esc(label(d)) + '</b><br>' +
        (side(d) === 'k'
          ? 'contract' + (cFilters(label(d)).length ? '<br>' + filtLines(label(d)) : '')
          : (n ? (KIND_LABEL[n.kind] || n.kind) + ' · AP ' + esc(n.ap) + '<br>' : '') +
            (side(d) === 'c' ? 'click: show its providers'
                             : 'click: show its consumers')), e);
    })
    .on('mouseout', hideTip);

  gn.filter(d => side(d) !== 'k').append('rect')
    .attr('width', 9).attr('height', 9).attr('rx', 2)
    .attr('x', d => side(d) === 'p' ? d.x1 + 6 : d.x0 - 15)
    .attr('y', d => (d.y0 + d.y1) / 2 - 4.5)
    .attr('fill', d => {
      const n = NODES.get(label(d));
      return hot(d) ? kindColor(n ? n.kind : 'other') : P.faint;
    })
    .attr('opacity', d => hot(d) ? 1 : .5);

  gn.append('text')
    .attr('class', 'lbl')
    .attr('fill', d => hot(d) ? P.ink : P.muted)
    .attr('opacity', d => hot(d) ? 1 : .58)
    .attr('font-weight', d => isFocus(d) ? 'bold' : 'normal')
    .attr('x', d => side(d) === 'p' ? d.x1 + (side(d) === 'k' ? 6 : 19)
                                    : d.x0 - (side(d) === 'k' ? 6 : 19))
    .attr('y', d => (d.y0 + d.y1) / 2 + 4)
    .attr('text-anchor', d => side(d) === 'p' ? 'start' : 'end')
    .text(d => label(d));

  svg.append('text').attr('class', 'lbl-sm').attr('x', 168).attr('y', 14)
     .attr('text-anchor', 'end').attr('font-weight', 'bold')
     .attr('fill', P.consumer).text('CONSUMER');
  svg.append('text').attr('class', 'lbl-sm').attr('x', w / 2).attr('y', 14)
     .attr('text-anchor', 'middle').attr('font-weight', 'bold')
     .attr('fill', P.contract).text('CONTRACT');
  svg.append('text').attr('class', 'lbl-sm').attr('x', w - 168).attr('y', 14)
     .attr('font-weight', 'bold').attr('fill', P.provider).text('PROVIDER');
  focusCaption(svg, S, 12, 28);

  $('#hint').textContent =
    'Click a left-hand block to see that one consumer and all of its providers; ' +
    'click a right-hand block for one provider and all of its consumers. The same ' +
    'object on the other side stays grey — press f to flip.';
  return svg.node();
}

/* ===================================================== view: matrix */
function cmpNode(a, b) {
  const x = NODES.get(a), y = NODES.get(b);
  return (x.ap || '').localeCompare(y.ap || '') || x.label.localeCompare(y.label);
}

function drawMatrix() {
  const links = visibleLinks();
  if (!links.length) return empty();
  const S = selection();

  const rows = [...new Set(links.map(l => l.source))].sort(cmpNode);
  const cols = [...new Set(links.map(l => l.target))].sort(cmpNode);

  const cells = new Map();
  links.forEach(l => {
    const k = pairKey(l.source, l.target);
    if (!cells.has(k)) cells.set(k, []);
    cells.get(k).push(l.contract);
  });

  const cs   = Math.max(17, Math.min(30, Math.floor(780 / Math.max(cols.length, 1))));
  const padL = 250, padT = 250;
  const w = padL + cols.length * cs + 26;
  const h = padT + rows.length * cs + 26;
  const svg = d3.create('svg').attr('width', w).attr('height', h);
  svg.on('click', () => { state.sel = null; render(); });

  const maxN  = d3.max([...cells.values()], v => v.length) || 1;
  const scale = d3.scaleSequential(d3.interpolateRgb(P.cellLo, P.cellHi)).domain([0, maxN]);

  const rowHot = r => !S || S.cons.has(r);   /* consumer axis — 1 when focused */
  const colHot = c => !S || S.prov.has(c);   /* provider axis — 1 when focused */

  rows.forEach((r, i) => {
    const n = NODES.get(r);
    const on = rowHot(r);
    const cy = padT + i * cs + cs / 2;
    svg.append('rect')
      .attr('x', padL - 17).attr('y', cy - 5.5)
      .attr('width', 11).attr('height', 11).attr('rx', 2)
      .attr('fill', on ? kindColor(n.kind) : P.faint)
      .attr('opacity', on ? 1 : .5);
    svg.append('text').attr('class', 'lbl')
      .attr('x', padL - 23).attr('y', cy + 4)
      .attr('text-anchor', 'end')
      .attr('fill', on ? P.consumer : P.muted)
      .attr('font-weight', (S && S.focus === r && S.role === 'consumer')
        ? 'bold' : 'normal')
      .classed('dim-lbl', !on)
      .style('cursor', 'pointer')
      .text(n.label)
      .on('click', e => { e.stopPropagation(); selectNode(r, 'consumer'); render(); })
      .on('mouseover', e => showTip('<b>' + esc(n.label) + '</b><br>' +
        (KIND_LABEL[n.kind] || n.kind) + ' · AP ' + esc(n.ap) +
        '<br>click: show its providers', e))
      .on('mouseout', hideTip);
  });

  cols.forEach((c, j) => {
    const n = NODES.get(c);
    const on = colHot(c);
    const cx = padL + j * cs + cs / 2;
    svg.append('rect')
      .attr('x', cx - 5.5).attr('y', padT - 17)
      .attr('width', 11).attr('height', 11).attr('rx', 2)
      .attr('fill', on ? kindColor(n.kind) : P.faint)
      .attr('opacity', on ? 1 : .5);
    svg.append('text').attr('class', 'lbl')
      .attr('transform', 'translate(' + (cx + 4) + ',' + (padT - 23) + ') rotate(-90)')
      .attr('fill', on ? P.provider : P.muted)
      .attr('font-weight', (S && S.focus === c && S.role === 'provider')
        ? 'bold' : 'normal')
      .classed('dim-lbl', !on)
      .style('cursor', 'pointer')
      .text(n.label)
      .on('click', e => { e.stopPropagation(); selectNode(c, 'provider'); render(); })
      .on('mouseover', e => showTip('<b>' + esc(n.label) + '</b><br>' +
        (KIND_LABEL[n.kind] || n.kind) + ' · AP ' + esc(n.ap) +
        '<br>click: show its consumers', e))
      .on('mouseout', hideTip);
  });

  const g = svg.append('g');
  rows.forEach((r, i) => cols.forEach((c, j) => {
    const list = cells.get(pairKey(r, c));
    const on   = !S ? true : S.pairs.has(pairKey(r, c));
    g.append('rect')
      .attr('class', list ? 'cell' : '')
      .attr('x', padL + j * cs).attr('y', padT + i * cs)
      .attr('width', cs - 1).attr('height', cs - 1)
      .attr('fill', list ? (on ? scale(list.length) : P.faint) : P.cellBg)
      .attr('fill-opacity', list ? (on ? 1 : .4) : 1)
      .attr('stroke', list ? P.panel : P.grid)
      .on('mouseover', e => showTip(
        '<b>' + esc(NODES.get(r).label) + '</b> <span style="opacity:.7">consumes</span>' +
        ' → <b>' + esc(NODES.get(c).label) + '</b> <span style="opacity:.7">provides</span>' +
        '<br>' + (list
          ? list.map(x => esc(x) + (cFilters(x).length
              ? ' <i>' + esc(cFilters(x).join(', ')) + '</i>' : '')).join('<br>')
          : '<i>no contract</i>'), e))
      .on('mouseout', hideTip)
      .on('click', e => {
        e.stopPropagation();
        if (list) {
          if (list.length === 1) selectContract(list[0]);
          else selectNode(r, 'consumer');
        }
        render();
      });
  }));

  svg.append('text').attr('class', 'lbl-sm').attr('x', 12).attr('y', 20)
     .attr('font-weight', 'bold').attr('fill', P.consumer)
     .text('↓  ROWS = consuming object');
  svg.append('text').attr('class', 'lbl-sm').attr('x', 12).attr('y', 36)
     .attr('font-weight', 'bold').attr('fill', P.provider)
     .text('→  COLUMNS = providing object');
  svg.append('text').attr('class', 'lbl-sm').attr('x', 12).attr('y', 54)
     .attr('fill', P.muted).text('cell = contract(s) permitting that direction');
  focusCaption(svg, S, 12, 72);

  drawLegend(svg, 12, 84, rows.concat(cols), false);

  $('#hint').textContent =
    'Rows consume, columns provide — the same object can appear on both axes. ' +
    'Clicking a row label shows only that consumer and its providers; a column ' +
    'label shows only that provider and its consumers.';
  return svg.node();
}

/* ===================================================== view: chord */
function drawChord() {
  const links = visibleLinks();
  const ids = visibleNodeIds(links);
  if (ids.length < 2) return empty();
  if (ids.length > 40) {
    const d = document.createElement('div');
    d.style.padding = '28px';
    d.innerHTML = '<b>Too many objects for a readable chord diagram (' + ids.length +
      ').</b><br><span class="hint">Chord works up to roughly 25–30 objects. ' +
      'Filter by application profile or contract, or use the Matrix view.</span>';
    $('#hint').textContent = '';
    return d;
  }
  const S = selection();
  ids.sort(cmpNode);
  const idx = new Map(ids.map((d, i) => [d, i]));
  const m = ids.map(() => ids.map(() => 0));
  links.forEach(l => { m[idx.get(l.source)][idx.get(l.target)] += 1; });

  const size  = Math.min(830, Math.max(560, ($('#canvas').clientWidth || 900) - 40));
  const outer = size / 2 - 138, inner = outer - 14;
  const root  = d3.create('svg').attr('width', size).attr('height', size);
  const svg   = root.append('g')
    .attr('transform', 'translate(' + size / 2 + ',' + size / 2 + ')');
  root.on('click', () => { state.sel = null; render(); });

  const chord = (d3.chordDirected ? d3.chordDirected() : d3.chord())
    .padAngle(.035).sortSubgroups(d3.descending)(m);
  const arc    = d3.arc().innerRadius(inner).outerRadius(outer);
  const ribbon = (d3.ribbonArrow ? d3.ribbonArrow() : d3.ribbon()).radius(inner - 1);
  const roles  = roleMap(links);
  const groupOn = i => !S || S.any.has(ids[i]);
  const ribOn = d => !S || S.pairs.has(pairKey(ids[d.source.index], ids[d.target.index]));

  svg.append('g').selectAll('path').data(chord.groups).join('path')
    .attr('d', arc)
    .attr('fill', d => groupOn(d.index) ? roleColor(roles.get(ids[d.index])) : P.faint)
    .attr('fill-opacity', d => groupOn(d.index) ? .95 : .4)
    .attr('stroke', d => (S && S.focus === ids[d.index]) ? P.ink : P.panel)
    .attr('stroke-width', d => (S && S.focus === ids[d.index]) ? 2 : 1)
    .style('cursor', 'pointer')
    .on('click', (e, d) => {
      e.stopPropagation(); selectNode(ids[d.index], null); render();
    })
    .on('mouseover', (e, d) => {
      const n = NODES.get(ids[d.index]);
      showTip('<b>' + esc(n.label) + '</b><br>' + (KIND_LABEL[n.kind] || n.kind) +
              ' · AP ' + esc(n.ap) + '<br>role here: ' + roles.get(ids[d.index]) +
              '<br><i>click twice to flip direction</i>', e);
    })
    .on('mouseout', hideTip);

  const kindArc = d3.arc().innerRadius(outer + 3).outerRadius(outer + 8);
  svg.append('g').selectAll('path').data(chord.groups).join('path')
    .attr('d', kindArc)
    .attr('fill', d => groupOn(d.index)
      ? kindColor(NODES.get(ids[d.index]).kind) : P.faint)
    .attr('fill-opacity', d => groupOn(d.index) ? .95 : .4)
    .style('pointer-events', 'none');

  svg.append('g').selectAll('path').data(chord).join('path')
    .attr('class', 'chord-ribbon')
    .attr('d', ribbon)
    .attr('fill', d => ribOn(d) ? roleColor(roles.get(ids[d.source.index])) : P.faint)
    .attr('fill-opacity', d => ribOn(d) ? .62 : .12)
    .on('mouseover', (e, d) => {
      const cs = [...new Set(links
        .filter(l => l.source === ids[d.source.index] && l.target === ids[d.target.index])
        .map(l => l.contract))];
      showTip('<b>' + esc(NODES.get(ids[d.source.index]).label) + '</b> → <b>' +
              esc(NODES.get(ids[d.target.index]).label) + '</b><br>' +
              cs.map(esc).join('<br>'), e);
    })
    .on('mouseout', hideTip);

  svg.append('g').selectAll('text').data(chord.groups).join('text')
    .attr('class', 'lbl')
    .attr('transform', d => {
      const a = (d.startAngle + d.endAngle) / 2 - Math.PI / 2;
      return 'rotate(' + (a * 180 / Math.PI) + ') translate(' + (outer + 13) + ') ' +
             (a > Math.PI / 2 || a < -Math.PI / 2 ? 'rotate(180)' : '');
    })
    .attr('text-anchor', d => {
      const a = (d.startAngle + d.endAngle) / 2 - Math.PI / 2;
      return (a > Math.PI / 2 || a < -Math.PI / 2) ? 'end' : 'start';
    })
    .attr('dy', '.32em')
    .attr('font-weight', d => (S && S.focus === ids[d.index]) ? 'bold' : 'normal')
    .classed('dim-lbl', d => !groupOn(d.index))
    .text(d => NODES.get(ids[d.index]).label);

  drawLegend(root, 10, 10, ids, false);
  focusCaption(root, S, 216, 24);
  $('#hint').textContent =
    'Inner arc colour = role, thin outer band = object type. Ribbons run ' +
    'consumer → provider. Selecting an arc is directional — click it again to flip.';
  return root.node();
}

/* ===================================================== shell */
function empty() {
  const d = document.createElement('div');
  d.style.padding = '28px';
  d.className = 'hint';
  d.textContent = 'No relationships match the current filters.';
  $('#hint').textContent = '';
  return d;
}

const VIEWS = {
  force:  { label:'Force graph', fn: drawForce  },
  sankey: { label:'Sankey flow', fn: drawSankey },
  matrix: { label:'Matrix',      fn: drawMatrix },
  chord:  { label:'Chord',       fn: drawChord  }
};

function render() {
  const tabs = $('#tabs');
  tabs.innerHTML = '';
  Object.keys(VIEWS).forEach(k => {
    const b = document.createElement('button');
    b.textContent = VIEWS[k].label;
    b.className = state.view === k ? 'on' : '';
    b.onclick = () => { state.view = k; render(); };
    tabs.appendChild(b);
  });
  const c = $('#canvas');
  c.innerHTML = '';
  c.appendChild(VIEWS[state.view].fn());
  detail();
}

$('#q').oninput = e => { state.q = e.target.value.trim().toLowerCase(); render(); };

$('#theme').onclick = () => {
  applyTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
  render();
};

$('#reset').onclick = () => {
  DATA.nodes.forEach(n => { state.kinds.add(n.kind); state.aps.add(n.ap); });
  DATA.contracts.forEach(c => state.contracts.add(c.name));
  state.q = ''; $('#q').value = ''; state.sel = null;
  syncSidebar(); render();
};

addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT') return;
  if (e.key === 'Escape') { state.sel = null; render(); }
  if (e.key === 'f' || e.key === 'F') { flipSelection(); render(); }
  if (e.key === 'd' || e.key === 'D') $('#theme').click();
});

let rt;
addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(render, 180); });

buildSidebar();
render();
"""

_D3_CDN = (
    '<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>\n'
    '<script src="https://cdn.jsdelivr.net/npm/d3-sankey@0.12.3/dist/d3-sankey.min.js"></script>'
)


def _d3_tags(local_dir: Path | None) -> str:
    """CDN by default; inline the libraries when --d3-dir is given (airgapped labs)."""
    if not local_dir:
        return _D3_CDN
    tags = []
    for fname in ("d3.min.js", "d3-sankey.min.js"):
        p = local_dir / fname
        if not p.is_file():
            raise SystemExit(
                f"--d3-dir: {p} not found. Download once with:\n"
                f"  curl -Lo {local_dir / 'd3.min.js'} https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js\n"
                f"  curl -Lo {local_dir / 'd3-sankey.min.js'} "
                f"https://cdn.jsdelivr.net/npm/d3-sankey@0.12.3/dist/d3-sankey.min.js"
            )
        tags.append("<script>\n" + p.read_text(encoding="utf-8") + "\n</script>")
    return "\n".join(tags)


def build_viewer_html(model: Model, d3_dir: Path | None = None) -> str:
    graph = build_graph(model)
    # A literal </script> inside the JSON would close the tag early.
    # r"<\/" is a backslash + slash: valid JSON escape, inert to the HTML parser.
    payload = json.dumps(graph).replace("</", r"<\/")
    return (
        _VIEWER_HTML
        .replace("__D3_TAGS__", _d3_tags(d3_dir))
        .replace("__VIEWER_JS__", _VIEWER_JS)
        .replace("__GRAPH_DATA__", payload)
        .replace("__TENANT__", _xesc(str(model.title)))
        .replace("__SUBTITLE__", _xesc(str(model.subtitle)))
    )


def write_viewer_html(model: Model, outfile: Path, d3_dir: Path | None = None) -> Path:
    if outfile.suffix.lower() != ".html":
        outfile = outfile.parent / (outfile.name + ".html")
    outfile.parent.mkdir(parents=True, exist_ok=True)
    outfile.write_text(build_viewer_html(model, d3_dir), encoding="utf-8")
    g = build_graph(model)["stats"]
    print(
        f"wrote {outfile}  ({g['nodes']} objects, {g['contracts']} contracts, "
        f"{g['links']} relationships)"
    )
    return outfile


def serve_viewer(job: Job, port: int, d3_dir: Path | None = None) -> None:
    """Tiny dev server: re-parses the source on every request, so editing the
    NAC file and hitting refresh shows the new topology."""
    import http.server
    import socketserver

    def current_model() -> Model:
        if job.from_apic:
            password = job.apic_pass or os.environ.get("APIC_PASS")
            if not password:
                raise RuntimeError("APIC_PASS is not set; --serve cannot prompt per request")
            data = fetch_apic(job.tenant, job.apic_host, job.apic_user, password)
            return load_tenant_model(data, job.tenant, job.apic_host)
        if job.tenant_json:
            data = json.loads(job.tenant_json.read_text(encoding="utf-8"))
            return load_tenant_model(data, job.tenant, str(job.tenant_json))
        return parse_yaml(job.nac, job.tenant)

    class Handler(http.server.BaseHTTPRequestHandler):
        def _send(self, body: bytes, ctype: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            try:
                model = current_model()
                if self.path.startswith("/data.json"):
                    self._send(
                        json.dumps(build_graph(model), indent=2).encode(),
                        "application/json; charset=utf-8",
                    )
                else:
                    self._send(
                        build_viewer_html(model, d3_dir).encode(),
                        "text/html; charset=utf-8",
                    )
            except Exception as exc:  # keep the server alive on a bad edit
                msg = f"<pre style='color:#c41e3a'>{_xesc(str(exc))}</pre>".encode()
                self.send_response(500)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(msg)))
                self.end_headers()
                self.wfile.write(msg)

        def log_message(self, fmt, *a):
            print(f"  {self.address_string()} {fmt % a}")

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    with Server(("127.0.0.1", port), Handler) as httpd:
        print(f"serving http://127.0.0.1:{port}/   (Ctrl-C to stop)")
        print("  /            interactive viewer, re-parsed on every request")
        print("  /data.json   raw graph JSON")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")


def _loadable(path: str | None) -> str | None:
    """Return path if Pillow/FreeType can actually open it, else None."""
    if not path:
        return None
    try:
        ImageFont.truetype(path, 12)
        return path
    except Exception:
        return None


def _resolve_font(kind: str, override: str | None = None) -> str | None:
    env = os.environ.get("DIAGRAM_FONT_BOLD" if kind == "bold" else "DIAGRAM_FONT_REG")
    for cand in (override, env):
        if cand:
            resolved = _loadable(str(Path(cand).expanduser()))
            if resolved:
                return resolved
            print(f"warning: requested font not usable, ignoring: {cand}", file=sys.stderr)
    for cand in _FONT_CANDIDATES[kind]:
        if Path(cand).is_file():
            resolved = _loadable(cand)
            if resolved:
                return resolved
    for name in _FONT_BY_NAME[kind]:
        resolved = _loadable(name)
        if resolved:
            return resolved
    return None


FONT_REG: str | None = None
FONT_BOLD: str | None = None
_FONT_WARNED = False


def set_fonts(regular: str | None = None, bold: str | None = None) -> None:
    """Resolve the regular/bold faces and reset the font cache."""
    global FONT_REG, FONT_BOLD, _FONT_WARNED
    FONT_REG = _resolve_font("regular", regular)
    FONT_BOLD = _resolve_font("bold", bold) or FONT_REG
    if FONT_REG is None and not _FONT_WARNED:
        _FONT_WARNED = True
        hint = {
            "linux": "sudo apt-get install -y fonts-liberation   (or: dnf install liberation-sans-fonts)",
            "darwin": "install any .ttf, or pass --font-regular /path/to/font.ttf",
            "win32": "unexpected on Windows — pass --font-regular C:/Windows/Fonts/arial.ttf",
        }.get(sys.platform, "install a TrueType font or pass --font-regular")
        print(
            "warning: no TrueType font found — falling back to Pillow's built-in font.\n"
            f"         {hint}\n"
            "         Alternatively set DIAGRAM_FONT_REG / DIAGRAM_FONT_BOLD.",
            file=sys.stderr,
        )
    F.cache_clear()


@lru_cache(maxsize=None)
def F(size: int, bold: bool = False):
    """Cached font accessor. Never raises — degrades to the built-in font.

    The returned object is tagged with .diagram_bold / .diagram_size so the SVG
    backend can emit the right font-weight without re-deriving it from a path.
    """
    path = FONT_BOLD if bold else FONT_REG
    font = None
    if path:
        try:
            font = ImageFont.truetype(path, size)
        except OSError:
            font = None
    if font is None:
        try:
            font = ImageFont.load_default(size=size)  # Pillow >= 10.1
        except TypeError:
            font = ImageFont.load_default()           # older Pillow: bitmap
    try:
        font.diagram_bold = bold
        font.diagram_size = size
    except Exception:
        pass
    return font


set_fonts()  # resolve at import so F() is always safe

# --------------------------------------------------------------------------- #
# Measurement — everything is measured before it is drawn                      #
# --------------------------------------------------------------------------- #

_MEASURE_IMG = Image.new("RGB", (1, 1))
MEASURE = ImageDraw.Draw(_MEASURE_IMG)


def tw(text, font) -> float:
    """Text width, usable before the canvas exists. Always PIL/FreeType, so
    PNG and SVG geometry are identical."""
    try:
        return MEASURE.textlength(str(text), font=font)
    except Exception:
        return len(str(text)) * getattr(font, "diagram_size", 12) * 0.55


def fit_text(text, font, max_w: float | None, ellipsis: str = "…") -> str:
    """Truncate with an ellipsis so text never exceeds max_w."""
    text = str(text)
    if max_w is None or max_w <= 0 or tw(text, font) <= max_w:
        return text
    ew = tw(ellipsis, font)
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if tw(text[:mid], font) + ew <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return (text[:lo].rstrip() + ellipsis) if lo else ellipsis


def wrap_items(items: list[str], font, max_w: float, sep: str = ",  ") -> list[str]:
    """Pack a list of labels into as few lines as fit max_w. Never returns []."""
    if not items:
        return [""]
    lines, cur = [], ""
    for it in items:
        it = str(it)
        cand = it if not cur else cur + sep + it
        if tw(cand, font) <= max_w or not cur:
            cur = cand
        else:
            lines.append(cur + sep.rstrip())
            cur = it
    if cur:
        lines.append(cur)
    return [fit_text(ln, font, max_w) for ln in lines]


def pack_columns(heights: list[int], n_cols: int, gap: int = 12) -> tuple[list[int], int]:
    """Greedy shortest-column packing. Returns (column index per item, tallest column)."""
    col_h = [0] * max(1, n_cols)
    assign = []
    for h in heights:
        i = col_h.index(min(col_h))
        assign.append(i)
        col_h[i] += h + gap
    tallest = max(col_h) if col_h else 0
    return assign, (tallest - gap if heights else 0)

def tenant_dir(tenant: str) -> Path:
    slug = tenant if tenant.startswith("tn-") else f"tn-{tenant}"
    return HERE / slug


def resolve_path(raw: str | Path) -> Path:
    p = Path(raw).expanduser()
    if not p.is_file() and not p.is_absolute():
        alt = (REPO / p).resolve()
        if alt.is_file():
            return alt
        here = (HERE / p).resolve()
        if here.is_file():
            return here
    return p.resolve()


resolve_nac = resolve_path


@dataclass
class Job:
    tenant: str
    nac: Path | None = None
    tenant_json: Path | None = None
    from_apic: bool = False
    apic_host: str = DEFAULT_APIC_HOST
    apic_user: str = DEFAULT_APIC_USER
    apic_pass: str | None = None


TENANT_GREEN = (122, 181, 72)
VRF_ORANGE = (244, 123, 32)
NAVY = (33, 37, 41)
GRAY = (95, 95, 95)
LINE = (168, 168, 168)
BOX = (255, 255, 255)
AP_RED = (196, 30, 58)
ESG_GREEN = (102, 166, 54)
BD_BLUE = (0, 145, 214)
EPG_DARK = (52, 52, 52)
L3 = (0, 112, 186)
RED = (196, 30, 58)

# Contract roles — steel-cyan consume, green provide.
# Cyan sits next to green on the wheel, avoiding the previous
# royal-blue / grass-green clash.
CONS = (0, 145, 173)
PROV = ESG_GREEN

GOLD = (245, 192, 24)
MUTED = (120, 120, 120)
FOOTER = (80, 80, 80)

# --- layout constants (replace the old magic numbers) ---------------------- #
PAD = 20
FRAME_L, FRAME_R = 32, W - 32
LEFT_X, LEFT_W = 52, 828
DUAL_SPLIT = 900          # right edge of the outside-VRF frame
DUAL_RIGHT_X = 940        # left edge of the inside-VRF content
BD_W, BD_GAP = 360, 20
VZ_W = 964
AP_GAP = 12
AP_MIN_W = 900            # never make an AP column narrower than this
BAND_TOP = 128            # first L3Out box in the header band
VZ_TOP = 86               # vzAny box top
LEGEND_X = 1180


def rr(draw, xy, r=5, fill=BOX, outline=LINE, width=1):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)


@dataclass
class ESG:
    name: str
    selectors: list[str] = field(default_factory=list)
    consumers: list[str] = field(default_factory=list)
    providers: list[str] = field(default_factory=list)


@dataclass
class AP:
    name: str
    esgs: list[ESG] = field(default_factory=list)
    epgs: list[tuple[str, tuple]] = field(default_factory=list)


@dataclass
class BD:
    name: str
    gw: str


@dataclass
class Model:
    title: str
    subtitle: str
    l3_vrf02: str
    l3_vrf01: str
    vz_consumers: list[str]
    aps_vrf02: list[AP]
    aps_vrf01_center: list[AP]
    aps_vrf01_right: list[AP]
    bds: list[BD]
    # (contract, scope, [consumers], [providers]) — lists so the table can wrap
    table_rows: list[tuple[str, str, list[str], list[str]]]
    notes: str
    l3outs_vrf01: list[str] = field(default_factory=list)
    l3outs_vrf02: list[str] = field(default_factory=list)
    # Real VRF names so the drawing is not hardcoded to vrf-01 / vrf-02.
    vrf_primary: str = "vrf-01"
    vrf_secondary: str = ""
    contract_filters: dict[str, list[str]] = field(default_factory=dict)



def choose_vrfs(names: list[str]) -> tuple[str, str | None]:
    """Pick the inside (primary) and outside (secondary) VRF to draw.

    Keeps the historical vrf-01 / vrf-02 behaviour when those names exist,
    otherwise falls back to the first (and second) VRF found.
    """
    seen = [n for n in dict.fromkeys(names) if n]
    if not seen:
        return "vrf-01", None
    primary = "vrf-01" if "vrf-01" in seen else seen[0]
    secondary = None
    if "vrf-02" in seen and primary != "vrf-02":
        secondary = "vrf-02"
    elif primary != "vrf-01" and len(seen) > 1:
        secondary = next((n for n in seen if n != primary), None)
    return primary, secondary

def _hex(c) -> str:
    if c is None:
        return "none"
    if isinstance(c, str):
        return c
    return "#%02x%02x%02x" % tuple(int(v) for v in c[:3])


class SvgCanvas:
    """Minimal drop-in for the ImageDraw.Draw subset this script uses.

    Measurement is delegated to PIL/FreeType (see tw()), so SVG and PNG
    geometry are identical. Only 7 primitives are needed: rectangle,
    rounded_rectangle, ellipse, polygon, line, text, textlength.
    """

    FAMILY = "Liberation Sans, Arial, Helvetica, sans-serif"

    def __init__(self, width: int, height: int, bg=(255, 255, 255)):
        self.size = (width, height)
        self.p: list[str] = [
            f'<rect x="0" y="0" width="{width}" height="{height}" fill="{_hex(bg)}"/>'
        ]

    # --- measurement -------------------------------------------------------
    @staticmethod
    def textlength(text, font=None, **_kw) -> float:
        return tw(text, font) if font is not None else 0.0

    # --- helpers -----------------------------------------------------------
    @staticmethod
    def _stroke(outline, width) -> str:
        if outline is None or not width:
            return ' stroke="none"'
        return f' stroke="{_hex(outline)}" stroke-width="{width}"'

    @staticmethod
    def _n(v) -> str:
        return f"{float(v):.2f}".rstrip("0").rstrip(".")

    # --- primitives --------------------------------------------------------
    def rectangle(self, xy, fill=None, outline=None, width=1):
        x0, y0, x1, y1 = xy
        n = self._n
        self.p.append(
            f'<rect x="{n(x0)}" y="{n(y0)}" width="{n(max(0, x1 - x0))}" '
            f'height="{n(max(0, y1 - y0))}" fill="{_hex(fill)}"'
            f'{self._stroke(outline, width)}/>'
        )

    def rounded_rectangle(self, xy, radius=0, fill=None, outline=None, width=1):
        x0, y0, x1, y1 = xy
        n = self._n
        self.p.append(
            f'<rect x="{n(x0)}" y="{n(y0)}" width="{n(max(0, x1 - x0))}" '
            f'height="{n(max(0, y1 - y0))}" rx="{n(radius)}" ry="{n(radius)}" '
            f'fill="{_hex(fill)}"{self._stroke(outline, width)}/>'
        )

    def ellipse(self, xy, fill=None, outline=None, width=1):
        x0, y0, x1, y1 = xy
        n = self._n
        self.p.append(
            f'<ellipse cx="{n((x0 + x1) / 2)}" cy="{n((y0 + y1) / 2)}" '
            f'rx="{n(abs(x1 - x0) / 2)}" ry="{n(abs(y1 - y0) / 2)}" '
            f'fill="{_hex(fill)}"{self._stroke(outline, width)}/>'
        )

    def polygon(self, pts, fill=None, outline=None, width=1):
        n = self._n
        pt = " ".join(f"{n(x)},{n(y)}" for x, y in pts)
        self.p.append(
            f'<polygon points="{pt}" fill="{_hex(fill)}"{self._stroke(outline, width)}/>'
        )

    def line(self, xy, fill=None, width=1):
        x0, y0, x1, y1 = xy
        n = self._n
        self.p.append(
            f'<line x1="{n(x0)}" y1="{n(y0)}" x2="{n(x1)}" y2="{n(y1)}" '
            f'stroke="{_hex(fill)}" stroke-width="{width}"/>'
        )

    def text(self, xy, text, font=None, fill=None, full=None, **_kw):
        x, y = xy
        size = getattr(font, "diagram_size", getattr(font, "size", 12))
        try:
            ascent = font.getmetrics()[0]   # PIL anchors top-left, SVG baseline
        except Exception:
            ascent = int(size * 0.8)
        weight = ' font-weight="bold"' if getattr(font, "diagram_bold", False) else ""
        title = ""
        if full is not None and str(full) != str(text):
            title = f"<title>{_xesc(str(full))}</title>"
        n = self._n
        self.p.append(
            f'<text x="{n(x)}" y="{n(y + ascent)}" font-family="{self.FAMILY}" '
            f'font-size="{size}"{weight} fill="{_hex(fill)}" '
            f'xml:space="preserve">{title}{_xesc(str(text))}</text>'
        )

    # --- output ------------------------------------------------------------
    def save(self, outfile: Path, *_a, **_kw):
        w, h = self.size
        body = "\n".join(self.p)
        outfile.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            'shape-rendering="geometricPrecision">\n'
            f"{body}\n</svg>\n",
            encoding="utf-8",
        )


def dtext(draw, xy, text, font, fill, max_w=None):
    """Draw text clipped to max_w. On SVG the full value becomes a tooltip."""
    raw = str(text)
    shown = fit_text(raw, font, max_w)
    if isinstance(draw, SvgCanvas):
        draw.text(xy, shown, font=font, fill=fill, full=raw)
    else:
        draw.text(xy, shown, font=font, fill=fill)
    return shown


def _new_canvas(width: int, height: int, fmt: str):
    """Returns (image_like, draw_like). Both have .size and .save()."""
    if fmt == "svg":
        c = SvgCanvas(width, height)
        return c, c
    img = Image.new("RGB", (width, height), (255, 255, 255))
    return img, ImageDraw.Draw(img)

def contract_bar(
    draw,
    x,
    y,
    consume=False,
    provide=False,
    cci=False,
    intra=False,
):
    """C / CCI / I / P handles. They are independent ports."""
    slots = [
        ("C", consume, CONS),
        ("CCI", cci, GOLD),
        ("I", intra, GOLD),
        ("P", provide, PROV),
    ]

    bw, bh, gap = 36, 18, 10
    bx = x

    for label, active, col in slots:
        fill = col if active else (255, 255, 255)
        text = (255, 255, 255) if active else col

        rr(
            draw,
            (bx, y, bx + bw, y + bh),
            r=3,
            fill=fill,
            outline=col,
            width=1,
        )  # noqa: port chrome

        fnt = F(10, bold=True)
        draw.text(
            (bx + (bw - tw(label, fnt)) / 2, y + 3),
            label,
            font=fnt,
            fill=text,
        )

        bx += bw + gap


def tagged_line(draw, x, y, kind, text, max_w=None):
    """One row inside an ESG box: selector, consumer, or provider."""
    if kind == "sel":
        dtext(draw, (x, y), text, F(12), GRAY, max_w)
        return

    col = CONS if kind == "C" else PROV

    rr(
        draw,
        (x, y + 1, x + 16, y + 15),
        r=2,
        fill=col,
        outline=col,
    )

    draw.text(
        (x + 3, y + 1),
        kind,
        font=F(10, bold=True),
        fill=(255, 255, 255),
    )

    dtext(
        draw,
        (x + 22, y),
        text,
        F(12),
        NAVY,
        (max_w - 22) if max_w else None,
    )


def esg_height(esg: ESG) -> int:
    rows = len(esg.selectors) + len(esg.consumers) + len(esg.providers)
    return 38 + 17 * max(rows, 1) + 30


def draw_esg(draw, x, y, w, esg: ESG) -> int:
    h = esg_height(esg)
    inner = w - 20
    rr(draw, (x, y, x + w, y + h), r=5, fill=BOX, outline=ESG_GREEN, width=2)
    draw.rectangle((x + 1, y + 1, x + w - 1, y + 7), fill=ESG_GREEN)
    dtext(draw, (x + 10, y + 11), f"ESG  {esg.name}", F(13, bold=True), NAVY, inner)
    yy = y + 32
    for s in esg.selectors:
        tagged_line(draw, x + 10, yy, "sel", s, inner)
        yy += 17
    for c in esg.consumers:
        tagged_line(draw, x + 10, yy, "C", c, inner)
        yy += 17
    for p in esg.providers:
        tagged_line(draw, x + 10, yy, "P", p, inner)
        yy += 17
    contract_bar(draw, x + 10, y + h - 26, bool(esg.consumers), bool(esg.providers))
    return h


def ap_height(ap: AP) -> int:
    title, pad, gap = 28, 12, 8
    kids = [esg_height(e) for e in ap.esgs]
    kids += [88] * len(ap.epgs)
    if not kids:
        return title + pad * 2
    return title + pad + sum(kids) + gap * (len(kids) - 1) + pad


def draw_ap(draw, x, y, w, ap: AP) -> int:
    """Red AP container that owns its EPGs / ESGs."""
    h = ap_height(ap)
    inner_w = w - 20
    rr(draw, (x, y, x + w, y + h), r=5, fill=BOX, outline=AP_RED, width=2)
    draw.rectangle((x + 1, y + 1, x + w - 1, y + 7), fill=AP_RED)
    dtext(draw, (x + 10, y + 10), f"AP  {ap.name}", F(13, bold=True), NAVY, inner_w)
    yy = y + 32
    for name, color in ap.epgs:
        draw_epg(draw, x + 10, yy, inner_w, name, color)
        yy += 88 + 8
    for esg in ap.esgs:
        yy += draw_esg(draw, x + 10, yy, inner_w, esg) + 8
    return h


def l3out_box(draw, x, y, w, name):
    h = 34
    rr(draw, (x, y, x + w, y + h), r=4, fill=BOX, outline=(160, 160, 160))
    dtext(draw, (x + 12, y + 8), f"L3out  {name}", F(13, bold=True), NAVY, w - 24)
    return h


def bd_box(draw, x, y, w, bd: BD):
    h = 46
    rr(draw, (x, y, x + w, y + h), r=4, fill=BOX, outline=BD_BLUE, width=2)
    draw.rectangle((x + 1, y + 1, x + w - 1, y + 6), fill=BD_BLUE)
    dtext(draw, (x + 10, y + 10), f"BD  {bd.name}", F(13, bold=True), NAVY, w - 20)
    dtext(draw, (x + 10, y + 26), bd.gw, F(12), GRAY, w - 20)
    return h


def draw_epg(draw, x, y, w, name, color):
    h = 88
    rr(draw, (x, y, x + w, y + h), r=4, fill=BOX, outline=EPG_DARK, width=1)
    draw.rectangle((x + 1, y + 1, x + w - 1, y + 6), fill=EPG_DARK)
    dtext(draw, (x + 10, y + 10), f"EPG  {name}", F(13, bold=True), NAVY, w - 20)
    draw.rounded_rectangle(
        (x + 8, y + 32, x + w - 8, y + h - 8), radius=3,
        fill=(246, 246, 246), outline=(210, 210, 210),
    )
    for i in range(4):
        sx = x + 16 + i * 26
        sy = y + 46
        rr(draw, (sx, sy, sx + 16, sy + 22), r=2, fill=color, outline=(90, 90, 90))
        draw.rectangle((sx + 3, sy + 5, sx + 13, sy + 8), fill=(255, 255, 255))
    return h


def vzany_height(consumers) -> int:
    return 36 + 17 * max(len(consumers), 1) + 28


def vzany_box(draw, x, y, w, consumers, vrf_label: str = ""):
    h = vzany_height(consumers)
    rr(draw, (x, y, x + w, y + h), r=5, fill=BOX, outline=EPG_DARK, width=1)
    draw.rectangle((x + 1, y + 1, x + w - 1, y + 7), fill=EPG_DARK)
    title = f"EPG  vzAny  ({vrf_label})" if vrf_label else "EPG  vzAny"
    dtext(draw, (x + 10, y + 11), title, F(13, bold=True), NAVY, w - 20)
    yy = y + 32
    if not consumers:
        draw.text((x + 10, yy), "no contracts attached", font=F(12), fill=MUTED)
    for c in consumers:
        tagged_line(draw, x + 10, yy, "C", c, w - 20)
        yy += 17
    contract_bar(draw, x + 10, y + h - 24, bool(consumers), False)
    return h


def k8s_stack(draw, x, y, w):
    h = 156
    for i, off in enumerate((10, 5, 0)):
        shade = 255 - i * 5
        rr(
            draw,
            (x + off, y + off, x + w - (10 - off), y + h - 6 + off // 2),
            r=7, fill=(shade, shade, shade), outline=(170, 170, 170),
        )
    dtext(draw, (x + 14, y + 8), "K8s nodes   BGP AS65252", F(13, bold=True), NAVY, w - 28)
    hx, hy, r = x + 32, y + 52, 14
    pts = [
        (hx, hy - r),
        (hx + r * 0.87, hy - r * 0.5),
        (hx + r * 0.87, hy + r * 0.5),
        (hx, hy + r),
        (hx - r * 0.87, hy + r * 0.5),
        (hx - r * 0.87, hy - r * 0.5),
    ]
    draw.polygon(pts, fill=(50, 108, 166), outline=(30, 70, 120))
    dtext(draw, (x + 52, y + 36), "Cilium CNI  +  eBPF", F(13, bold=True), NAVY, w - 66)
    dtext(draw, (x + 52, y + 54), "Node subnets", F(12), GRAY, w - 66)
    dtext(draw, (x + 52, y + 70), "10.237.101.0/27    10.100.0.0/23", F(12), NAVY, w - 66)
    dtext(draw, (x + 14, y + 100), "Pod routes imported on floating SVI L3out", F(12), GRAY, w - 28)
    dtext(draw, (x + 14, y + 116), "match-rule  pod-subnets   0.0.0.0/0 aggregate", F(12), GRAY, w - 28)
    return h


def cloud(draw, x, y):
    fill, out = (226, 233, 240), (130, 146, 162)
    draw.ellipse((x + 6, y + 18, x + 46, y + 52), fill=fill, outline=out)
    draw.ellipse((x + 26, y + 4, x + 80, y + 52), fill=fill, outline=out)
    draw.ellipse((x + 62, y + 16, x + 108, y + 52), fill=fill, outline=out)
    draw.rectangle((x + 20, y + 32, x + 92, y + 51), fill=fill)
    draw.line((x + 20, y + 51, x + 92, y + 51), fill=out, width=1)


def router(draw, x, y):
    draw.ellipse((x, y, x + 34, y + 13), fill=(0, 145, 214), outline=(0, 100, 160))
    draw.rectangle((x, y + 6, x + 34, y + 20), fill=(0, 145, 214))
    draw.ellipse((x, y + 14, x + 34, y + 27), fill=(0, 120, 186), outline=(0, 90, 140))
    for i in range(3):
        draw.ellipse((x + 6 + i * 9, y + 4, x + 12 + i * 9, y + 10), fill=(180, 230, 255))


def chip(draw, x, y, text, fill, outline, fg):
    fnt = F(11, bold=True)
    ww = tw(text, fnt) + 12
    rr(draw, (x, y, x + ww, y + 18), r=3, fill=fill, outline=outline)
    draw.text((x + 6, y + 2), str(text), font=fnt, fill=fg)
    return ww

def table_from_attachments(
    contracts_meta: dict, attachments: list[tuple[str, str, str]]
) -> list[tuple[str, str, list[str], list[str]]]:
    """attachments: (object_label, role, contract) with role in {C,P}.

    Returns lists (not joined strings) so the table can wrap them.
    """
    cons, provs = defaultdict(list), defaultdict(list)
    for obj, role, contract in attachments:
        (cons if role == "C" else provs)[contract].append(obj)
    rows = []
    for name in sorted(set(cons) | set(provs) | set(contracts_meta)):
        rows.append(
            (
                name,
                contracts_meta.get(name, ""),
                sorted(dict.fromkeys(cons.get(name) or [])),
                sorted(dict.fromkeys(provs.get(name) or [])),
            )
        )
    return rows


def layout_aps(
    aps_by_vrf: dict[str, list[AP]],
    primary: str = "vrf-01",
    secondary: str | None = "vrf-02",
) -> tuple[list[AP], list[AP], list[AP]]:
    """Split APs into (outside, inside-center, inside-right) buckets.

    The center/right split is only cosmetic now — the renderer packs both
    lists into height-balanced columns — but it is preserved so the historical
    ordering of the isovalent-style tenants is unchanged.
    """
    aps_v2 = list(aps_by_vrf.get(secondary) or []) if secondary else []
    aps_v1 = list(aps_by_vrf.get(primary) or [])
    for name, aps in aps_by_vrf.items():
        if name != primary and name != secondary:
            aps_v1.extend(aps)
    isovalent_layout = any(a.name == "external-subnets-esgs" for a in aps_v2) or any(
        a.name in ("network-segments", "network-segments-esgs", "node-subnets-esgs")
        for a in aps_v1
    )
    if isovalent_layout:
        center, right = [], []
        for ap in aps_v1:
            if ap.name in ("network-segments", "network-segments-esgs", "node-subnets-esgs"):
                center.append(ap)
            else:
                right.append(ap)
        return aps_v2, center, right
    return aps_v2, aps_v1, []


def infer_tenant_from_json(data: dict, fallback: str) -> str:
    if data.get("tenant"):
        return str(data["tenant"])
    for item in data.get("imdata") or []:
        cls, body = next(iter(item.items()))
        attrs = body.get("attributes", {})
        if cls == "fvTenant" and attrs.get("name"):
            return attrs["name"]
        dn = attrs.get("dn") or ""
        if "tn-" in dn:
            return dn.split("tn-", 1)[1].split("/")[0]
    return fallback


# --------------------------------------------------------------------------- #
# Filter / port formatting — shared by the NAC and APIC parsers               #
# --------------------------------------------------------------------------- #

_PORT_UNSET = {"", "unspecified", "none", "0"}


def _port(v) -> str:
    s = str(v).strip() if v is not None else ""
    return "" if s.lower() in _PORT_UNSET else s


def _fmt_ports(frm, to) -> str:
    """(80, 443) -> '80-443'   (443, 443) -> '443'   (None, None) -> ''"""
    a, b = _port(frm), _port(to)
    if not a and not b:
        return ""
    if a and b and a != b:
        return f"{a}-{b}"
    return a or b


def _fmt_nac_entry(e) -> str:
    """NAC filter entry dict -> 'tcp 80-443' / 'icmp' / 'arp'."""
    if not isinstance(e, dict):
        return str(e)
    proto = str(e.get("protocol") or "").strip()
    ether = str(e.get("ethertype") or "").strip()
    dports = _fmt_ports(e.get("destination_from_port"), e.get("destination_to_port"))
    sports = _fmt_ports(e.get("source_from_port"), e.get("source_to_port"))
    bits = []
    if ether and ether not in ("ip", "unspecified") and ether != proto:
        bits.append(ether)
    bits.append(proto or ether or "any")
    if sports:
        bits.append(f"src {sports}")
    if dports:
        bits.append(dports)
    return " ".join(dict.fromkeys(b for b in bits if b))


def _fmt_apic_entry(a: dict) -> str:
    """vzEntry attributes -> 'tcp 80-443'. APIC uses 'unspecified' for unset."""
    prot = str(a.get("prot") or "").strip()
    ether = str(a.get("etherT") or "").strip()
    dports = _fmt_ports(a.get("dFromPort"), a.get("dToPort"))
    sports = _fmt_ports(a.get("sFromPort"), a.get("sToPort"))
    bits = []
    if ether and ether not in ("ip", "unspecified") and ether != prot:
        bits.append(ether)
    bits.append(prot if prot and prot != "unspecified"
                else (ether if ether and ether != "unspecified" else "any"))
    if sports:
        bits.append(f"src {sports}")
    if dports:
        bits.append(dports)
    return " ".join(dict.fromkeys(b for b in bits if b))


def _label_filter(fname: str, entries: list[str]) -> str:
    return f"{fname}: {', '.join(entries)}" if entries else str(fname)

def parse_yaml(path: Path, tenant: str) -> Model:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    tenants = [t for t in data.get("apic", {}).get("tenants", []) if t.get("name") == tenant]
    if not tenants:
        names = [t.get("name") for t in data.get("apic", {}).get("tenants", []) if t.get("name")]
        raise SystemExit(f"tenant '{tenant}' not found in {path}. Tenants in file: {names or '(none)'}")
    tn = tenants[0]
    contracts_meta = {c["name"]: c.get("scope", "") for c in tn.get("contracts", [])}

    # --- contract -> filter -> port ranges ------------------------------- #
    filter_entries = {f["name"]: (f.get("entries") or []) for f in tn.get("filters") or []}
    contract_filters: dict[str, list[str]] = {}
    for c in tn.get("contracts") or []:
        labels: list[str] = []
        for subj in c.get("subjects") or []:
            refs = list(subj.get("filters") or [])
            # A subject may also carry direction-specific filter lists.
            for term in ("consumer_to_provider", "provider_to_consumer"):
                refs += list((subj.get(term) or {}).get("filters") or [])
            for fr in refs:
                fname = fr.get("filter") if isinstance(fr, dict) else fr
                if not fname:
                    continue
                entries = [s for s in (_fmt_nac_entry(e)
                                       for e in filter_entries.get(fname, [])) if s]
                label = _label_filter(fname, entries)
                if label not in labels:
                    labels.append(label)
        if labels:
            contract_filters[c["name"]] = labels
    
    # Collect every VRF this tenant references, not just the declared ones.
    vrf_names = [v["name"] for v in tn.get("vrfs") or [] if v.get("name")]
    for bd in tn.get("bridge_domains") or []:
        if bd.get("vrf"):
            vrf_names.append(bd["vrf"])
    for o in tn.get("l3outs") or []:
        if o.get("vrf"):
            vrf_names.append(o["vrf"])
    primary, secondary = choose_vrfs(vrf_names)

    def l3_labels(vrf_name: str | None) -> list[str]:
        labels = []
        if not vrf_name:
            return labels
        for o in tn.get("l3outs") or []:
            if o.get("vrf") == vrf_name:
                labels.append(f"{o.get('alias') or o['name']}    {o['name']}")
        return labels

    l3_01 = l3_labels(primary)
    l3_02 = l3_labels(secondary)

    vz = []
    for vrf in tn.get("vrfs", []):
        if vrf.get("name") == primary:
            vz = list((vrf.get("contracts") or {}).get("consumers") or [])

    bds = []
    for bd in tn.get("bridge_domains", []):
        if bd["name"] == "6.6.6.0_24":
            continue
        subs = bd.get("subnets") or [{}]
        sub = subs[0] if subs else {}
        flags = []
        if sub.get("public"):
            flags.append("public")
        if sub.get("shared"):
            flags.append("shared")
        bds.append(BD(bd["name"].replace("_", "/"),
                      f"GW  {sub.get('ip','')}   {' + '.join(flags)}".rstrip()))

    attachments = [(f"vzAny ({primary})", "C", c) for c in vz]
    aps_by_vrf: dict[str, list[AP]] = defaultdict(list)
    epg_colors = [RED, L3, BD_BLUE, ESG_GREEN]
    bd_vrf = {bd["name"]: bd.get("vrf") for bd in tn.get("bridge_domains") or []}
    for ap in tn.get("application_profiles", []):
        epgs = []
        epg_vrf = None
        for i, epg in enumerate(ap.get("endpoint_groups") or []):
            epgs.append((epg["name"].replace("_", "/"), epg_colors[i % len(epg_colors)]))
            epg_vrf = bd_vrf.get(epg.get("bridge_domain")) or epg_vrf
            cons = list((epg.get("contracts") or {}).get("consumers") or [])
            provs = list((epg.get("contracts") or {}).get("providers") or [])
            for c in cons:
                attachments.append((f"EPG {epg['name']}", "C", c))
            for p in provs:
                attachments.append((f"EPG {epg['name']}", "P", p))
        esgs = []
        vrf = None
        for e in ap.get("endpoint_security_groups") or []:
            vrf = e.get("vrf") or vrf
            sels = []
            for sel in e.get("epg_selectors") or []:
                sels.append(
                    f"EPG selector  {sel.get('application_profile')} / {sel.get('endpoint_group')}"
                )
            for sel in e.get("ip_external_subnet_selectors") or []:
                shared = "   shared" if sel.get("shared") else ""
                sels.append(f"IP selector  {sel.get('ip')}{shared}")
            cons = list((e.get("contracts") or {}).get("consumers") or [])
            provs = list((e.get("contracts") or {}).get("providers") or [])
            esgs.append(ESG(e["name"], sels, cons, provs))
            for c in cons:
                attachments.append((f"ESG {e['name']}", "C", c))
            for p in provs:
                attachments.append((f"ESG {e['name']}", "P", p))
        if not epgs and not esgs:
            continue
        aps_by_vrf[vrf or epg_vrf or primary].append(AP(ap["name"], esgs, epgs))

    aps_v2, center, right = layout_aps(aps_by_vrf, primary, secondary)

    rows = table_from_attachments(contracts_meta, attachments)
    attached = {c for _obj, _role, c in attachments}
    unattached = [n for n in contracts_meta if n not in attached]
    notes = (
        "Defined but not attached in NAC:  " + "  ·  ".join(unattached)
        if unattached
        else "All defined contracts are attached to at least one object."
    )
    return Model(
        title=tenant,
        subtitle=f"INTENT   ·   {path.name}   ·   desired VRF / AP / ESG / contracts",
        l3_vrf02=l3_02[0] if l3_02 else "",
        l3_vrf01=l3_01[0] if l3_01 else "",
        vz_consumers=vz,
        aps_vrf02=aps_v2,
        aps_vrf01_center=center,
        aps_vrf01_right=right,
        bds=bds,
        table_rows=rows,
        notes=notes,
        l3outs_vrf01=l3_01,
        l3outs_vrf02=l3_02,
        vrf_primary=primary,
        vrf_secondary=secondary or "",
        contract_filters=contract_filters, 
    )

def fetch_apic(tenant: str, host: str, user: str, password: str) -> dict:
    if not password:
        raise RuntimeError("APIC password is not set")
    host = host.rstrip("/")
    # Lab APIC presents a self-signed certificate. Verification is skipped for
    # this lab only — do not copy this pattern to production.
    ctx = ssl._create_unverified_context()
    cj = CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ctx),
        urllib.request.HTTPCookieProcessor(cj),
    )

    def post(path, payload):
        req = urllib.request.Request(
            host + path,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with opener.open(req, timeout=30) as resp:
            return json.load(resp)

    def get(path):
        req = urllib.request.Request(host + path)
        with opener.open(req, timeout=90) as resp:
            return json.load(resp)

    post("/api/aaaLogin.json", {"aaaUser": {"attributes": {"name": user, "pwd": password}}})
    subtree = get(
        f"/api/node/mo/uni/tn-{tenant}.json?query-target=subtree"
        "&target-subtree-class=fvTenant,fvCtx,fvAp,fvESg,fvAEPg,fvBD,fvSubnet,l3extOut,"
        "vzBrCP,vzAny,fvRsCons,fvRsProv,vzRsAnyToCons,fvExternalSubnetSelector,"
        "fvEPgSelector,fvRsMatchEPg,l3extRsEctx,fvRsScope,"
        "vzSubj,vzRsSubjFiltAtt,vzRsFiltAtt,vzFilter,vzEntry"
    )
    return subtree


def parse_apic(subtree: dict, tenant: str, apic_host: str) -> Model:
    by = defaultdict(list)
    for item in subtree.get("imdata", []):
        cls = next(iter(item))
        by[cls].append(item[cls]["attributes"])

    tenant = infer_tenant_from_json(subtree, tenant)
    contracts_meta = {a["name"]: a.get("scope", "") for a in by.get("vzBrCP", [])}

    # --- filter entries, then contract -> filter labels ------------------- #
    filt_entries: dict[str, list[str]] = defaultdict(list)
    for e in by.get("vzEntry", []):
        dn = e.get("dn") or ""
        if "/flt-" not in dn:
            continue
        flt = dn.split("/flt-")[1].split("/")[0]
        s = _fmt_apic_entry(e)
        if s and s not in filt_entries[flt]:
            filt_entries[flt].append(s)

    contract_filters: dict[str, list[str]] = defaultdict(list)
    # vzRsSubjFiltAtt = filter on a subject; vzRsFiltAtt = filter on an in/out term.
    for r in list(by.get("vzRsSubjFiltAtt", [])) + list(by.get("vzRsFiltAtt", [])):
        dn = r.get("dn") or ""
        if "/brc-" not in dn:
            continue
        brc = dn.split("/brc-")[1].split("/")[0]
        fname = r.get("tnVzFilterName") or (r.get("tDn") or "").rsplit("/flt-", 1)[-1]
        if not fname:
            continue
        label = _label_filter(fname, filt_entries.get(fname, []))
        if label not in contract_filters[brc]:
            contract_filters[brc].append(label)
    contract_filters = dict(contract_filters)

    primary, secondary = choose_vrfs([a.get("name", "") for a in by.get("fvCtx", [])])

    l3_alias = {}
    for o in by.get("l3extOut", []):
        l3_alias[o["name"]] = o.get("nameAlias") or o["name"]
    l3_vrf = {}
    for r in by.get("l3extRsEctx", []):
        out = r["dn"].split("/out-")[1].split("/")[0]
        l3_vrf[out] = r.get("tnFvCtxName")
    l3_01 = [f"{l3_alias.get(n, n)}    {n}" for n, v in l3_vrf.items() if v == primary]
    l3_02 = [
        f"{l3_alias.get(n, n)}    {n}" for n, v in l3_vrf.items() if secondary and v == secondary
    ]
    if not l3_01:
        l3_01 = [f"{l3_alias.get(n, n)}    {n}" for n in l3_alias if primary in n]
    if not l3_02 and secondary:
        l3_02 = [f"{l3_alias.get(n, n)}    {n}" for n in l3_alias if secondary in n]
    # Single-VRF tenant: any remaining L3Outs belong to the one VRF we have.
    if not l3_01 and not l3_02 and l3_alias and not secondary:
        l3_01 = [f"{l3_alias.get(n, n)}    {n}" for n in sorted(l3_alias)]

    vz = []
    for r in by.get("vzRsAnyToCons", []):
        if f"/ctx-{primary}/" in r["dn"]:
            vz.append(r["tnVzBrCPName"])
    vz = sorted(set(vz))

    bd_gw = {}
    for s in by.get("fvSubnet", []):
        if "/BD-" not in s["dn"]:
            continue
        bd = s["dn"].split("/BD-")[1].split("/")[0]
        bd_gw[bd] = (s.get("ip", ""), s.get("scope", ""))
    bds = []
    for b in by.get("fvBD", []):
        if b["name"] == "6.6.6.0_24":
            continue
        ip, scope = bd_gw.get(b["name"], ("", ""))
        flags = " + ".join(x for x in ("public", "shared") if x in scope)
        bds.append(BD(b["name"].replace("_", "/"), f"GW  {ip}   {flags}".rstrip()))

    selectors = defaultdict(list)
    for s in by.get("fvExternalSubnetSelector", []):
        if "/esg-" not in s["dn"]:
            continue
        esg = s["dn"].split("/esg-")[1].split("/")[0]
        selectors[esg].append(f"IP selector  {s.get('ip')}")
    for s in by.get("fvRsMatchEPg", []):
        if "/esg-" not in s["dn"]:
            continue
        esg = s["dn"].split("/esg-")[1].split("/")[0]
        epg = s["tDn"].rsplit("/epg-", 1)[-1]
        ap = s["tDn"].split("/ap-")[1].split("/")[0] if "/ap-" in s["tDn"] else ""
        selectors[esg].append(f"EPG selector  {ap} / {epg}")

    esg_cons, esg_provs = defaultdict(list), defaultdict(list)
    epg_cons, epg_provs = defaultdict(list), defaultdict(list)
    for r in by.get("fvRsCons", []):
        name = r.get("tnVzBrCPName")
        if "/esg-" in r["dn"]:
            esg_cons[r["dn"].split("/esg-")[1].split("/")[0]].append(name)
        elif "/epg-" in r["dn"]:
            epg_cons[r["dn"].split("/epg-")[1].split("/")[0]].append(name)
    for r in by.get("fvRsProv", []):
        name = r.get("tnVzBrCPName")
        if "/esg-" in r["dn"]:
            esg_provs[r["dn"].split("/esg-")[1].split("/")[0]].append(name)
        elif "/epg-" in r["dn"]:
            epg_provs[r["dn"].split("/epg-")[1].split("/")[0]].append(name)

    esg_vrf = {}
    for r in by.get("fvRsScope", []):
        if "/esg-" not in r["dn"]:
            continue
        esg = r["dn"].split("/esg-")[1].split("/")[0]
        esg_vrf[esg] = r.get("tnFvCtxName") or (r.get("tDn") or "").rsplit("/ctx-", 1)[-1]

    def default_vrf_for_ap(ap_name: str) -> str:
        if secondary and "external-subnets" in ap_name:
            return secondary
        return primary

    attachments = [(f"vzAny ({primary})", "C", c) for c in vz]
    ap_esgs: dict[str, list[ESG]] = defaultdict(list)
    ap_vrf: dict[str, str] = {}
    for e in by.get("fvESg", []):
        ap = e["dn"].split("/ap-")[1].split("/")[0]
        name = e["name"]
        esg = ESG(name, selectors.get(name, []), esg_cons.get(name, []), esg_provs.get(name, []))
        ap_esgs[ap].append(esg)
        ap_vrf[ap] = esg_vrf.get(name) or default_vrf_for_ap(ap)
        for c in esg.consumers:
            attachments.append((f"ESG {name}", "C", c))
        for p in esg.providers:
            attachments.append((f"ESG {name}", "P", p))

    ap_epgs: dict[str, list[tuple[str, tuple]]] = defaultdict(list)
    epg_colors = [RED, L3, BD_BLUE, ESG_GREEN]
    epg_i: dict[str, int] = defaultdict(int)
    for a in by.get("fvAEPg", []):
        if "/ap-" not in a["dn"]:
            continue
        ap = a["dn"].split("/ap-")[1].split("/")[0]
        color = epg_colors[epg_i[ap] % len(epg_colors)]
        epg_i[ap] += 1
        ap_epgs[ap].append((a["name"].replace("_", "/"), color))
        for c in epg_cons.get(a["name"], []):
            attachments.append((f"EPG {a['name']}", "C", c))
        for p in epg_provs.get(a["name"], []):
            attachments.append((f"EPG {a['name']}", "P", p))

    aps_by_vrf: dict[str, list[AP]] = defaultdict(list)
    for name in sorted(set(ap_esgs) | set(ap_epgs)):
        vrf = ap_vrf.get(name, default_vrf_for_ap(name))
        aps_by_vrf[vrf].append(AP(name, ap_esgs.get(name, []), ap_epgs.get(name, [])))
    aps_v2, center, right = layout_aps(aps_by_vrf, primary, secondary)

    host_label = apic_host.replace("https://", "").replace("http://", "")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    rows = table_from_attachments(contracts_meta, attachments)
    return Model(
        title=tenant,
        subtitle=f"ACTUAL   ·   APIC {host_label}   ·   uni/tn-{tenant}   ·   queried {now}",
        l3_vrf02=l3_02[0] if l3_02 else "",
        l3_vrf01=l3_01[0] if l3_01 else "",
        vz_consumers=vz,
        aps_vrf02=aps_v2,
        aps_vrf01_center=center,
        aps_vrf01_right=right,
        bds=bds,
        table_rows=rows,
        notes=(
            "Read-only query of the running tenant. Service-graph / PBR objects exist "
            "on the fabric but are omitted from this ESG view."
        ),
        l3outs_vrf01=l3_01,
        l3outs_vrf02=l3_02,
        vrf_primary=primary,
        vrf_secondary=secondary or "",
        contract_filters=contract_filters,    
    )

def _l3_labels(model: Model, which: str) -> list[str]:
    extras = model.l3outs_vrf01 if which == "01" else model.l3outs_vrf02
    fallback = model.l3_vrf01 if which == "01" else model.l3_vrf02
    if extras:
        return extras
    if fallback and fallback.strip():
        return [fallback]
    return []


# Contract table column origins.
TBL_X = {"contract": 48, "scope": 700, "cons": 830, "prov": 2130}


def _layout_table(model: Model) -> tuple[list, int]:
    """Wrap the consumer/provider lists and measure the table.

    Returns (rows, total_height) where each row is
    (contract, scope, cons_lines, prov_lines, row_height).
    """
    f = F(12)
    cons_w = TBL_X["prov"] - TBL_X["cons"] - 30
    prov_w = (W - 40) - TBL_X["prov"] - 20
    out = []
    total = 80  # header block
    for contract, scope, cons, prov in model.table_rows:
        cl = wrap_items(list(cons) or ["not attached"], f, cons_w)
        pl = wrap_items(list(prov) or ["not attached"], f, prov_w)
        h = 8 + 17 * max(len(cl), len(pl))
        out.append((contract, scope, cl, pl, h))
        total += h
    if not out:
        total += 28
    return out, total + 40  # + notes line


def _layout(model: Model) -> dict:
    """Measure every coordinate before anything is drawn.

    This replaces the old hardcoded topo_bottom=1288 / y=268 / y=328 cascade,
    which is what caused boxes to overlap on large tenants.
    """
    dual = bool(model.aps_vrf02) or bool(_l3_labels(model, "02"))
    inside_x = DUAL_RIGHT_X if dual else LEFT_X
    avail = FRAME_R - inside_x - PAD
    l3_w = 620 if dual else 1600

    # --- header band: inside L3Outs, optional K8s stack, vzAny ------------- #
    l3_in = _l3_labels(model, "01")
    l3_stack_h = 44 * max(len(l3_in), 1)
    vz_h = vzany_height(model.vz_consumers)
    vz_x = FRAME_R - PAD - VZ_W
    k8s_x, k8s_w, k8s_top = inside_x + l3_w + 70, 500, BAND_TOP - 42
    show_k8s = "k8s" in (model.l3_vrf01 or "").lower() and (k8s_x + k8s_w) <= (vz_x - 20)

    header_bottom = max(
        BAND_TOP + l3_stack_h,
        VZ_TOP + vz_h,
        (k8s_top + 156) if show_k8s else 0,
    )
    bd_top = header_bottom + PAD

    # --- BD row: wrap to the available width instead of running off canvas -- #
    per_row = max(1, int((avail + BD_GAP) // (BD_W + BD_GAP)))
    bd_rows = -(-len(model.bds) // per_row) if model.bds else 0
    aps_top = bd_top + ((56 * (bd_rows - 1) + 46 + PAD) if bd_rows else 0)

    # --- AP columns: pick the widest column count that still fits ---------- #
    aps = model.aps_vrf01_center + model.aps_vrf01_right
    n_cols = 1
    for n in (3, 2, 1):
        if (avail - AP_GAP * (n - 1)) / n >= AP_MIN_W:
            n_cols = n
            break
    col_w = int((avail - AP_GAP * (n_cols - 1)) / n_cols)
    assign, tallest = pack_columns([ap_height(a) for a in aps], n_cols, AP_GAP)
    inside_bottom = aps_top + tallest + PAD

    # --- outside VRF column (dual only) ------------------------------------ #
    left_bottom = 0
    if dual:
        y = BAND_TOP + 44 * len(_l3_labels(model, "02")) + 4
        for ap in model.aps_vrf02:
            y += ap_height(ap) + AP_GAP
        left_bottom = y + PAD

    topo_bottom = max(inside_bottom, left_bottom, 640)
    table_rows, table_h = _layout_table(model)

    return {
        "dual": dual,
        "inside_x": inside_x,
        "avail": avail,
        "l3_w": l3_w,
        "l3_in": l3_in,
        "show_k8s": show_k8s,
        "k8s_x": k8s_x,
        "k8s_w": k8s_w,
        "k8s_top": k8s_top,
        "vz_x": vz_x,
        "vz_h": vz_h,
        "bd_top": bd_top,
        "per_row": per_row,
        "bd_rows": bd_rows,
        "aps": aps,
        "aps_top": aps_top,
        "assign": assign,
        "n_cols": n_cols,
        "col_w": col_w,
        "topo_bottom": topo_bottom,
        "table_rows": table_rows,
        "table_h": table_h,
    }

# Contract table column origins (see also TBL_X use in _layout_table).
def _draw_contract_table(draw, model: Model, plan: dict, top: int, canvas_h: int) -> None:
    draw.rounded_rectangle((FRAME_L, top, FRAME_R, canvas_h - 52), radius=6,
                           fill=None, outline=TENANT_GREEN, width=2)
    draw.text((48, top + 12), "Contract relationships", font=F(17, bold=True), fill=NAVY)
    draw.text((300, top + 18), "Consumer  →  contract  →  Provider", font=F(13), fill=GRAY)

    hy = top + 50
    draw.rectangle((40, hy, W - 40, hy + 26), fill=(236, 245, 228))
    for title, key in (("Contract", "contract"), ("Scope", "scope"),
                       ("Consumers", "cons"), ("Providers", "prov")):
        draw.text((TBL_X[key], hy + 5), title, font=F(13, bold=True), fill=TENANT_GREEN)

    rows = plan["table_rows"]
    ry = hy + 30
    name_w = TBL_X["scope"] - TBL_X["contract"] - 20
    for i, (contract, scope, cl, pl, h) in enumerate(rows):
        if i % 2 == 0:
            draw.rectangle((40, ry - 1, W - 40, ry + h - 1), fill=(250, 250, 250))
        dtext(draw, (TBL_X["contract"], ry + 5), contract, F(13, bold=True), NAVY, name_w)
        if scope:
            chip(draw, TBL_X["scope"], ry + 4, scope,
                 (236, 245, 228), TENANT_GREEN, TENANT_GREEN)
        for j, line in enumerate(cl):
            draw.text((TBL_X["cons"], ry + 5 + 17 * j), line, font=F(12), fill=NAVY)
        muted = pl == ["not attached"]
        for j, line in enumerate(pl):
            draw.text((TBL_X["prov"], ry + 5 + 17 * j), line, font=F(12),
                      fill=MUTED if muted else NAVY)
        ry += h
    if not rows:
        draw.text((TBL_X["contract"], ry + 5), "no contracts defined", font=F(12), fill=MUTED)
        ry += 28
    dtext(draw, (48, ry + 8), model.notes, F(12), MUTED, W - 120)


def _out_path(base: Path, fmt: str) -> Path:
    """Append/replace the extension without mangling dots in tenant names."""
    ext = ".svg" if fmt == "svg" else ".png"
    if base.suffix.lower() in (".png", ".svg"):
        return base.with_suffix(ext)
    return base.parent / (base.name + ext)


def render(model: Model, outfile: Path, fmt: str = "png"):
    """Draw the whole diagram. Every coordinate comes from _layout(model)."""
    plan = _layout(model)
    dual = plan["dual"]
    topo_bottom = plan["topo_bottom"]
    canvas_h = max(H, topo_bottom + 20 + plan["table_h"] + 44)

    img, d = _new_canvas(W, canvas_h, fmt)

    inside = model.vrf_primary or "vrf-01"
    outside = model.vrf_secondary or "vrf-02"
    inside_x = plan["inside_x"]
    l3_w = plan["l3_w"]

    # ----------------------------------------------------------------- header
    cloud(d, 22, 8)
    title_f = F(22, bold=True)
    shown = dtext(d, (138, 20), model.title, title_f, NAVY, 700)
    sub_x = 138 + tw(shown, title_f) + 24
    dtext(d, (sub_x, 26), model.subtitle, F(14), GRAY, max(120, LEGEND_X - 20 - sub_x))

    kx = LEGEND_X
    for label, col in (("tenant", TENANT_GREEN), ("VRF", VRF_ORANGE), ("AP", AP_RED),
                       ("ESG", ESG_GREEN), ("BD", BD_BLUE), ("EPG", EPG_DARK)):
        d.rectangle((kx, 28, kx + 14, 40), fill=col)
        d.text((kx + 18, 26), label, font=F(12), fill=GRAY)
        kx += 78
    for kind, col, label in (
        ("C", CONS, "consumer"),
        ("P", PROV, "provider"),
    ):
        rr(
            d,
            (kx, 26, kx + 16, 42),
            r=2,
            fill=col,
            outline=col,
        )

        d.text(
            (kx + 3, 27),
            kind,
            font=F(10, bold=True),
            fill=(255, 255, 255),
        )

        d.text(
            (kx + 20, 26),
            label,
            font=F(12),
            fill=GRAY,
        )

        kx += 88

    d.text(
        (kx + 4, 26),
        "CCI consumed-IF I intra",
        font=F(12),
        fill=GRAY,
    )

    # tenant frame
    d.rounded_rectangle((16, 58, W - 16, canvas_h - 44), radius=8,
                        fill=None, outline=TENANT_GREEN, width=3)

    # ------------------------------------------------------------ VRF frames
    if dual:
        d.rounded_rectangle((FRAME_L, 74, DUAL_SPLIT, topo_bottom), radius=6,
                            fill=None, outline=VRF_ORANGE, width=2)
        d.rounded_rectangle((920, 74, FRAME_R, topo_bottom), radius=6,
                            fill=None, outline=VRF_ORANGE, width=2)
    else:
        d.rounded_rectangle((FRAME_L, 74, FRAME_R, topo_bottom), radius=6,
                            fill=None, outline=VRF_ORANGE, width=2)

    # --------------------------------------------- outside VRF (dual only)
    if dual:
        router(d, LEFT_X, 90)
        dtext(d, (LEFT_X + 46, 92), f"{outside}  (outside)",
              F(17, bold=True), NAVY, LEFT_W - 60)
        y = BAND_TOP
        labels_02 = _l3_labels(model, "02")
        for label in labels_02:
            y += l3out_box(d, LEFT_X, y, LEFT_W, label) + 10
        if not labels_02:
            d.text((LEFT_X, y), "no L3Out attached to this VRF", font=F(13), fill=MUTED)
            y += 34
        y += 4
        for ap in model.aps_vrf02:
            y += draw_ap(d, LEFT_X, y, LEFT_W, ap) + AP_GAP

    # ------------------------------------------------------------ inside VRF
    router(d, inside_x, 90)
    label_in = f"{inside}  (inside)" if dual else inside
    dtext(d, (inside_x + 46, 92), label_in, F(17, bold=True), NAVY, l3_w - 60)

    # header band: L3Out stack (never a single hardcoded box)
    y = BAND_TOP
    for label in plan["l3_in"]:
        y += l3out_box(d, inside_x, y, l3_w, label) + 10
    if not plan["l3_in"]:
        d.text((inside_x, BAND_TOP + 8), "no L3Out attached to this VRF",
               font=F(13), fill=MUTED)

    # optional K8s stack, only drawn when it fits left of the vzAny box
    if plan["show_k8s"]:
        d.line((inside_x + l3_w + 8, BAND_TOP + 17, plan["k8s_x"] - 6, BAND_TOP + 17),
               fill=L3, width=3)
        k8s_stack(d, plan["k8s_x"], plan["k8s_top"], plan["k8s_w"])

    # vzAny — right-aligned in the header band, height driven by contract count
    vzany_box(d, plan["vz_x"], VZ_TOP, VZ_W, model.vz_consumers, inside)

    # bridge domains — wrapped to the available width
    bx, by = inside_x, plan["bd_top"]
    for i, bd in enumerate(model.bds):
        if i and i % plan["per_row"] == 0:
            bx = inside_x
            by += 56
        bd_box(d, bx, by, BD_W, bd)
        bx += BD_W + BD_GAP

    # application profiles — height-balanced columns, y only ever increases
    col_y = [plan["aps_top"]] * plan["n_cols"]
    for ap, col in zip(plan["aps"], plan["assign"]):
        x = inside_x + col * (plan["col_w"] + AP_GAP)
        col_y[col] += draw_ap(d, x, col_y[col], plan["col_w"], ap) + AP_GAP

    # ------------------------------------------------------- table + footer
    _draw_contract_table(d, model, plan, topo_bottom + 20, canvas_h)
    d.text((24, canvas_h - 34), "© 2026 Cisco and/or its affiliates. All rights reserved.",
           font=F(12), fill=FOOTER)
    d.text((W - 110, canvas_h - 36), "cisco", font=F(18, bold=True), fill=NAVY)

    outfile = _out_path(outfile, fmt)
    outfile.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "svg":
        img.save(outfile)
    else:
        img.save(outfile, "PNG", optimize=True)
    print(f"wrote {outfile}  {img.size[0]}x{img.size[1]}")
    return outfile

def load_tenant_model(data: dict, tenant: str, source: str) -> Model:
    """Accept raw APIC subtree JSON (imdata) or a sanitized snapshot."""
    tenant = infer_tenant_from_json(data, tenant)
    if "imdata" in data:
        model = parse_apic(data, tenant, source)
        if source and "://" not in source:
            model.subtitle = f"ACTUAL   ·   {Path(source).name}   ·   uni/tn-{tenant}"
            model.notes = "Rendered from a saved APIC tenant.json (no credentials stored)."
        return model
    return parse_snapshot_data(data, tenant)


def parse_snapshot(path: Path) -> Model:
    return load_tenant_model(
        json.loads(path.read_text(encoding="utf-8")), DEFAULT_TENANT, path.name
    )


def parse_snapshot_data(snap: dict, fallback_tenant: str) -> Model:
    """Sanitized snapshot format: {tenant, host, source, contracts, esgs, epgs,
    bds, l3outs, vz_consumers_vrf01}."""
    tenant = snap.get("tenant", fallback_tenant)
    contracts_meta = snap.get("contracts", {}) or {}
    l3 = snap.get("l3outs", {}) or {}

    # Derive real VRF names where the snapshot records them.
    vrf_names = [v.get("vrf") for v in l3.values() if isinstance(v, dict) and v.get("vrf")]
    vrf_names += [e.get("vrf") for e in snap.get("esgs", []) if e.get("vrf")]
    primary, secondary = choose_vrfs(vrf_names or ["vrf-01", "vrf-02"])

    attachments = [(f"vzAny ({primary})", "C", c) for c in snap.get("vz_consumers_vrf01", [])]

    aps: dict[str, AP] = {}
    for e in snap.get("esgs", []):
        esg = ESG(e["name"], e.get("selectors", []), e.get("consumers", []), e.get("providers", []))
        aps.setdefault(e["ap"], AP(e["ap"])).esgs.append(esg)
        for c in esg.consumers:
            attachments.append((f"ESG {esg.name}", "C", c))
        for p in esg.providers:
            attachments.append((f"ESG {esg.name}", "P", p))

    epg_ap = AP(
        name="network-segments",
        epgs=[
            (e["name"].replace("_", "/"), RED if "96" in e["name"] else L3)
            for e in snap.get("epgs", [])
        ],
    )

    aps_v2 = [aps[n] for n in aps if n == "external-subnets-esgs"]
    center = [epg_ap] if epg_ap.epgs else []
    for n in ("network-segments-esgs", "node-subnets-esgs"):
        if n in aps:
            center.append(aps[n])
    right = [
        aps[n] for n in aps
        if n not in ("external-subnets-esgs", "network-segments-esgs", "node-subnets-esgs")
    ]

    bds = []
    for b in snap.get("bds", []):
        flags = " + ".join(x for x in ("public", "shared") if x in (b.get("scope") or ""))
        bds.append(BD(b["name"].replace("_", "/"), f"GW  {b.get('ip','')}   {flags}".rstrip()))

    def _labels(vrf: str | None) -> list[str]:
        if not vrf:
            return []
        out = []
        for name, meta in l3.items():
            meta = meta if isinstance(meta, dict) else {}
            if meta.get("vrf") == vrf or name.endswith(vrf):
                out.append(f"{meta.get('alias', name)}    {name}")
        return out

    l3_01 = _labels(primary)
    l3_02 = _labels(secondary)
    if not l3_01 and not l3_02 and l3:
        l3_01 = [
            f"{(m if isinstance(m, dict) else {}).get('alias', n)}    {n}"
            for n, m in sorted(l3.items())
        ]

    return Model(
        title=tenant,
        subtitle=(
            f"ACTUAL   ·   APIC {snap.get('host','')}   ·   uni/tn-{tenant}"
            f"   ·   {snap.get('source','')}"
        ),
        l3_vrf02=l3_02[0] if l3_02 else "",
        l3_vrf01=l3_01[0] if l3_01 else "",
        vz_consumers=list(snap.get("vz_consumers_vrf01", [])),
        aps_vrf02=aps_v2,
        aps_vrf01_center=center,
        aps_vrf01_right=right,
        bds=bds,
        table_rows=table_from_attachments(contracts_meta, attachments),
        notes=(
            "Rendered from a sanitized read-only snapshot of the running tenant "
            "(no credentials stored)."
        ),
        l3outs_vrf01=l3_01,
        l3outs_vrf02=l3_02,
        vrf_primary=primary,
        vrf_secondary=secondary or "",
        contract_filters=snap.get("contract_filters", {}) or {},
    )


def suggested_json(tenant: str) -> Path:
    out = tenant_dir(tenant)
    raw = out / "tenant.json"
    if raw.is_file():
        return raw
    snap = out / f"apic-snapshot-tn-{tenant}.json"
    if snap.is_file():
        return snap
    return raw

# --------------------------------------------------------------------------- #
# Graph extraction — consumer -> contract -> provider                         #
# --------------------------------------------------------------------------- #

def _object_index(model: Model) -> dict[str, dict]:
    """Map EPG/ESG name -> {kind, ap, vrf}.

    Registers both the raw name and the '_'->'/' mangled form, because
    parse_yaml() stores mangled names in AP.epgs but unmangled names in the
    contract attachments.
    """
    idx: dict[str, dict] = {}

    def add(name: str, kind: str, ap: str, vrf: str) -> None:
        for key in {name, name.replace("_", "/"), name.replace("/", "_")}:
            idx.setdefault(key, {"kind": kind, "ap": ap, "vrf": vrf, "label": name})

    for ap in model.aps_vrf02:
        for name, _c in ap.epgs:
            add(name, "epg", ap.name, model.vrf_secondary or "")
        for e in ap.esgs:
            add(e.name, "esg", ap.name, model.vrf_secondary or "")
    for ap in model.aps_vrf01_center + model.aps_vrf01_right:
        for name, _c in ap.epgs:
            add(name, "epg", ap.name, model.vrf_primary)
        for e in ap.esgs:
            add(e.name, "esg", ap.name, model.vrf_primary)
    return idx


def _node_from_label(label: str, idx: dict[str, dict]) -> dict:
    """Turn an attachment label ('EPG Web', 'ESG x', 'vzAny (vrf)') into a node."""
    label = str(label).strip()
    if label.startswith("EPG "):
        name, kind = label[4:], "epg"
    elif label.startswith("ESG "):
        name, kind = label[4:], "esg"
    elif label.startswith("vzAny"):
        vrf = label.split("(", 1)[1].rstrip(")").strip() if "(" in label else ""
        return {"id": "vzany", "label": "vzAny", "kind": "vzany", "ap": "—", "vrf": vrf}
    else:
        name, kind = label, "other"
    meta = idx.get(name) or idx.get(name.replace("_", "/")) or {}
    return {
        "id": f"{kind}:{name}",
        "label": name,
        "kind": kind,
        "ap": meta.get("ap", "—"),
        "vrf": meta.get("vrf", model_vrf_hint(meta)),
    }


def model_vrf_hint(meta: dict) -> str:
    return meta.get("vrf", "") if meta else ""


def build_graph(model: Model) -> dict:
    """Emit a viewer-ready graph. Nodes are EPGs / ESGs / vzAny; every link is
    one (consumer, provider) pair carrying its contract name."""
    idx = _object_index(model)
    nodes: dict[str, dict] = {}
    links: list[dict] = []
    contracts: list[dict] = []

    def node(label: str) -> str:
        n = _node_from_label(label, idx)
        nodes.setdefault(n["id"], n)
        return n["id"]

    for name, scope, cons, prov in model.table_rows:
        cids = [node(c) for c in cons]
        pids = [node(p) for p in prov]
        contracts.append(
            {
                "name": name,
                "scope": scope or "",
                "consumers": cids,
                "providers": pids,
                "filters": list(model.contract_filters.get(name, [])),
                "dangling": (not cids) or (not pids),
            }
        )
        for c in cids:
            for p in pids:
                links.append({"source": c, "target": p, "contract": name, "scope": scope or ""})

    # Degree counts make the force layout and the sidebar more informative.
    for n in nodes.values():
        n["consumes"] = sum(1 for c in contracts if n["id"] in c["consumers"])
        n["provides"] = sum(1 for c in contracts if n["id"] in c["providers"])
        n["degree"] = n["consumes"] + n["provides"]

    return {
        "tenant": model.title,
        "subtitle": model.subtitle,
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "vrfs": {"primary": model.vrf_primary, "secondary": model.vrf_secondary},
        "nodes": sorted(nodes.values(), key=lambda n: (n["ap"], n["kind"], n["label"])),
        "contracts": contracts,
        "links": links,
        "bds": [{"name": b.name, "gw": b.gw} for b in model.bds],
        "l3outs": {
            "inside": _l3_labels(model, "01"),
            "outside": _l3_labels(model, "02"),
        },
        "notes": model.notes,
        "stats": {
            "nodes": len(nodes),
            "links": len(links),
            "contracts": len(contracts),
            "dangling": sum(1 for c in contracts if c["dangling"]),
            "unfiltered": sum(1 for c in contracts if not c["filters"]),   # <-- add
        },
    }


def write_graph_json(model: Model, outfile: Path) -> Path:
    outfile = outfile.parent / (outfile.name + ".json") if outfile.suffix.lower() not in (
        ".json",
    ) else outfile
    outfile.parent.mkdir(parents=True, exist_ok=True)
    outfile.write_text(json.dumps(build_graph(model), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {outfile}")
    return outfile

def prompt_cli(job: Job, fmt: str = "png") -> tuple[Job, str]:
    """Text prompts. Used when Tk is missing or there is no display."""
    tenant = input(f"Tenant name [{job.tenant}]: ").strip() or job.tenant
    nac_in = input(f"NAC file (blank to skip) [{job.nac or ''}]: ").strip()
    print("Tenant JSON:  [1] skip  [2] file  [3] log on to APIC and retrieve")
    mode = input("Choice [1]: ").strip() or "1"
    json_path = None
    from_apic = False
    host = job.apic_host
    user = job.apic_user
    password = job.apic_pass
    if mode == "2":
        default_json = suggested_json(tenant)
        raw = input(f"Path to tenant.json [{default_json}]: ").strip() or str(default_json)
        json_path = resolve_path(raw)
    elif mode == "3":
        from_apic = True
        host = input(f"APIC host [{job.apic_host}]: ").strip() or job.apic_host
        user = input(f"APIC user [{job.apic_user}]: ").strip() or job.apic_user
        password = os.environ.get("APIC_PASS") or getpass.getpass("APIC password: ")
    elif mode != "1":
        raise SystemExit("Choose 1, 2, or 3 for tenant JSON")

    fmt_in = input(
        f"Output format — png / svg / both / html / json / all [{fmt}]: "
    ).strip().lower() or fmt
    if fmt_in not in ("png", "svg", "both", "html", "json", "all"):
        raise SystemExit("Format must be png, svg, both, html, json, or all")

    nac = resolve_path(nac_in) if nac_in else None
    if nac and not nac.is_file():
        raise SystemExit(f"NAC file not found: {nac}")
    if json_path and not json_path.is_file():
        raise SystemExit(f"tenant.json not found: {json_path}")
    if not nac and not json_path and not from_apic:
        raise SystemExit("Provide a NAC file, a tenant.json file, or retrieve from APIC.")
    return Job(tenant, nac, json_path, from_apic, host, user, password), fmt_in


def _gui_available() -> bool:
    """Windows/macOS always have a display; on Linux/BSD require DISPLAY or WAYLAND."""
    if sys.platform.startswith(("win", "darwin")):
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def prompt_job(job: Job, fmt: str = "png") -> tuple[Job, str]:
    """Dialog: optional NAC, plus tenant.json from file or APIC login, plus format.

    Falls back to prompt_cli() when Tk is missing or there is no display
    (headless Linux, SSH session, container).
    Password is read into memory only and is never written to disk.
    """
    os.environ.setdefault("TK_SILENCE_DEPRECATION", "1")
    if not _gui_available():
        return prompt_cli(job, fmt)
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox
    except Exception:
        return prompt_cli(job, fmt)

    result: dict = {"ok": False}
    try:
        root = tk.Tk()
    except Exception:  # tkinter.TclError: no display / no Tk runtime
        return prompt_cli(job, fmt)
    root.title("ACI Tenant Diagram")
    root.resizable(False, False)
    pad = {"padx": 12, "pady": 4}
    ui_font = ("TkDefaultFont", 10)          # portable: no hardcoded Arial
    ui_bold = ("TkDefaultFont", 13, "bold")

    tk.Label(root, text="Render tenant / VRF / ESG diagrams", font=ui_bold).grid(
        row=0, column=0, columnspan=3, sticky="w", **pad
    )
    tk.Label(
        root,
        text=(
            "Use NAC, tenant.json, or both. Password is not saved. "
            "Lab APIC uses a self-signed certificate."
        ),
        fg="#555555",
        wraplength=560,
        justify="left",
        font=ui_font,
    ).grid(row=1, column=0, columnspan=3, sticky="w", **pad)

    tk.Label(root, text="Tenant name").grid(row=2, column=0, sticky="e", **pad)
    tenant_var = tk.StringVar(value=job.tenant)
    tenant_entry = tk.Entry(root, textvariable=tenant_var, width=52)
    tenant_entry.grid(row=2, column=1, columnspan=2, sticky="we", **pad)

    tk.Label(root, text="NAC file (optional)").grid(row=3, column=0, sticky="e", **pad)
    nac_var = tk.StringVar(value=str(job.nac) if job.nac else "")
    tk.Entry(root, textvariable=nac_var, width=52).grid(row=3, column=1, sticky="we", **pad)

    def browse_nac():
        chosen = filedialog.askopenfilename(
            title="Select NAC YAML",
            initialdir=str((job.nac.parent if job.nac and Path(job.nac).exists() else REPO)),
            filetypes=[("NAC / YAML", "*.nac.yaml *.yaml *.yml"), ("All files", "*.*")],
        )
        if chosen:
            nac_var.set(chosen)

    tk.Button(root, text="Browse…", command=browse_nac).grid(row=3, column=2, **pad)

    json_mode = tk.StringVar(value="skip")
    tk.Label(root, text="Tenant JSON").grid(row=4, column=0, sticky="ne", **pad)
    modes = tk.Frame(root)
    modes.grid(row=4, column=1, columnspan=2, sticky="w", **pad)
    tk.Radiobutton(modes, text="Skip — NAC only", variable=json_mode, value="skip").pack(anchor="w")
    tk.Radiobutton(modes, text="Load tenant.json from file", variable=json_mode, value="file").pack(anchor="w")
    tk.Radiobutton(
        modes, text="Log on to APIC and retrieve tenant.json", variable=json_mode, value="apic"
    ).pack(anchor="w")

    tk.Label(root, text="tenant.json").grid(row=5, column=0, sticky="e", **pad)
    json_var = tk.StringVar(value=str(suggested_json(job.tenant)))
    tk.Entry(root, textvariable=json_var, width=52).grid(row=5, column=1, sticky="we", **pad)

    def browse_json():
        chosen = filedialog.askopenfilename(
            title="Select tenant JSON",
            initialdir=str(tenant_dir(tenant_var.get().strip() or job.tenant)),
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if chosen:
            json_var.set(chosen)
            json_mode.set("file")

    tk.Button(root, text="Browse…", command=browse_json).grid(row=5, column=2, **pad)

    tk.Label(root, text="Output format").grid(row=6, column=0, sticky="ne", **pad)
    fmt_var = tk.StringVar(value=fmt)
    fmt_frame = tk.Frame(root)
    fmt_frame.grid(row=6, column=1, columnspan=2, sticky="w", **pad)
    _FMT_CHOICES = (
        ("PNG", "png"),
        ("SVG — scales, searchable", "svg"),
        ("PNG + SVG", "both"),
        ("Interactive HTML", "html"),
        ("Graph JSON", "json"),
        ("Everything", "all"),
    )
    # Two rows of three so the dialog does not grow wider than the entries.
    for i, (text, val) in enumerate(_FMT_CHOICES):
        r, c = divmod(i, 3)
        tk.Radiobutton(fmt_frame, text=text, variable=fmt_var, value=val).grid(
            row=r, column=c, sticky="w", padx=(0, 10)
        )

    tk.Label(root, text="APIC host").grid(row=7, column=0, sticky="e", **pad)
    host_var = tk.StringVar(value=job.apic_host)
    tk.Entry(root, textvariable=host_var, width=52).grid(row=7, column=1, columnspan=2, sticky="we", **pad)
    tk.Label(root, text="APIC user").grid(row=8, column=0, sticky="e", **pad)
    user_var = tk.StringVar(value=job.apic_user)
    tk.Entry(root, textvariable=user_var, width=52).grid(row=8, column=1, columnspan=2, sticky="we", **pad)
    tk.Label(root, text="APIC password").grid(row=9, column=0, sticky="e", **pad)
    pass_var = tk.StringVar()
    tk.Entry(root, textvariable=pass_var, width=52, show="*").grid(
        row=9, column=1, columnspan=2, sticky="we", **pad
    )
    tk.Label(
        root,
        text=(
            "Leave password blank to use the APIC_PASS environment variable. "
            "It is never written to disk."
        ),
        fg="#555555",
        wraplength=560,
        justify="left",
        font=ui_font,
    ).grid(row=10, column=1, columnspan=2, sticky="w", **pad)

    def on_tenant_change(*_args):
        t = tenant_var.get().strip() or job.tenant
        current = json_var.get().strip()
        previous = str(suggested_json(job.tenant))
        if not current or current == previous:
            json_var.set(str(suggested_json(t)))

    tenant_var.trace_add("write", on_tenant_change)

    def submit():
        tenant = tenant_var.get().strip()
        if not tenant:
            messagebox.showerror("Required", "Enter a tenant name.")
            return
        nac_raw = nac_var.get().strip()
        nac = resolve_path(nac_raw) if nac_raw else None
        if nac and not nac.is_file():
            messagebox.showerror("Required", f"NAC file not found:\n{nac}")
            return
        mode = json_mode.get()
        json_path = None
        from_apic = mode == "apic"
        if mode == "file":
            raw = json_var.get().strip()
            if not raw:
                messagebox.showerror("Required", "Select a tenant.json file, or choose Skip / APIC.")
                return
            json_path = resolve_path(raw)
            if not json_path.is_file():
                messagebox.showerror("Required", f"tenant.json not found:\n{json_path}")
                return
        if not nac and mode == "skip":
            messagebox.showerror(
                "Required", "Supply a NAC file, a tenant.json file, or retrieve from APIC."
            )
            return
        password = pass_var.get() or os.environ.get("APIC_PASS") or None
        host = host_var.get().strip() or DEFAULT_APIC_HOST
        user = user_var.get().strip() or DEFAULT_APIC_USER

        if from_apic and not host:
            messagebox.showerror(
                "Required",
                "Enter the APIC host or set APIC_HOST in diagrams/.env.",
            )
            return

        if from_apic and not user:
            messagebox.showerror(
                "Required",
                "Enter the APIC user or set APIC_USER in diagrams/.env.",
            )
            return

        if from_apic and not password:
            messagebox.showerror(
                "Required",
                "Enter the APIC password or set APIC_PASS.",
            )
            return

        result["ok"] = True
        result["fmt"] = fmt_var.get()
        result["job"] = Job(
            tenant=tenant,
            nac=nac,
            tenant_json=json_path,
            from_apic=from_apic,
            apic_host=host,
            apic_user=user,
            apic_pass=password,
        )
        root.destroy()

    def cancel():
        root.destroy()

    btns = tk.Frame(root)
    btns.grid(row=11, column=0, columnspan=3, sticky="e", padx=12, pady=10)
    tk.Button(btns, text="Cancel", command=cancel, width=10).pack(side="right", padx=4)
    tk.Button(btns, text="Render", command=submit, width=10, default="active").pack(side="right")
    root.bind("<Return>", lambda _e: submit())
    tenant_entry.focus_set()
    tenant_entry.selection_range(0, "end")
    root.mainloop()
    if not result.get("ok"):
        raise SystemExit("cancelled")
    return result["job"], result.get("fmt", fmt)

def fingerprint(model: Model) -> set[tuple]:
    items = set()
    for ap in model.aps_vrf02 + model.aps_vrf01_center + model.aps_vrf01_right:
        for e in ap.esgs:
            items.add(
                (
                    ap.name,
                    e.name,
                    tuple(sorted(e.consumers)),
                    tuple(sorted(e.providers)),
                    tuple(sorted(e.selectors)),
                )
            )
    items.add(("vzAny", tuple(sorted(model.vz_consumers))))
    return items


def annotate_diff(intent: Model, actual: Model) -> None:
    fi, fa = fingerprint(intent), fingerprint(actual)
    if fi == fa:
        actual.notes = (
            "Live fabric matches NAC intent for AP / ESG membership, selectors, "
            "and C/P attachments.  " + actual.notes
        )
        return
    missing = fi - fa
    extra = fa - fi
    actual.notes = f"DIFF vs intent — missing {len(missing)}  extra {len(extra)}.  " + actual.notes
    for label, items in (("missing", missing), ("extra", extra)):
        for it in sorted(items, key=repr):
            print(f"{label}: {it}")


def run_job(job: Job, fmt: str = "png", d3_dir: Path | None = None) -> None:
    if not job.nac and not job.tenant_json and not job.from_apic:
        raise SystemExit("Provide a NAC file, a tenant.json file, or retrieve from APIC.")

    fmts = ("png", "svg") if fmt == "both" else (fmt,)
    if fmt == "all":
        fmts = ("png", "svg", "html", "json")

    data = None
    if job.from_apic:
        if not job.apic_host:
            raise SystemExit(
                "APIC host is not set. Copy diagrams/.env.example to "
                "diagrams/.env or pass --apic-host."
            )

        if not job.apic_user:
            raise SystemExit(
                "APIC user is not set. Set APIC_USER in diagrams/.env "
                "or pass --apic-user."
            )

        password = job.apic_pass or os.environ.get("APIC_PASS")
        if not password:
            password = getpass.getpass(
                f"Password for {job.apic_user}@{job.apic_host}: "
            )

        data = fetch_apic(
            job.tenant,
            job.apic_host,
            job.apic_user,
            password,
        )
        job.tenant = infer_tenant_from_json(data, job.tenant)
    elif job.tenant_json:
        data = json.loads(job.tenant_json.read_text(encoding="utf-8"))
        job.tenant = infer_tenant_from_json(data, job.tenant)

    outdir = tenant_dir(job.tenant)
    outdir.mkdir(parents=True, exist_ok=True)

    if job.from_apic and data is not None:
        saved = outdir / "tenant.json"
        saved.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {saved}")

    def emit(model: Model, base: Path) -> None:
        for f in fmts:
            if f in ("png", "svg"):
                render(model, base, f)
            elif f == "html":
                write_viewer_html(model, base, d3_dir)
            elif f == "json":
                write_graph_json(model, base)

    intent = None
    if job.nac:
        if not job.nac.is_file():
            raise SystemExit(f"NAC file not found: {job.nac}")
        intent = parse_yaml(job.nac, job.tenant)
        emit(intent, outdir / f"tn-{job.tenant}-intent")

    if data is not None:
        source = job.apic_host if job.from_apic else str(job.tenant_json)
        actual = load_tenant_model(data, job.tenant, source)
        if intent is not None:
            annotate_diff(intent, actual)
        emit(actual, outdir / f"tn-{job.tenant}-actual-apic")


def main():
    parser = argparse.ArgumentParser(
        description="Render ACI tenant diagrams from optional NAC YAML and/or tenant JSON."
    )
    parser.add_argument("--tenant", default=DEFAULT_TENANT, help="Tenant name")
    parser.add_argument("--nac", help="Path to the NAC YAML file (optional)")
    parser.add_argument("--tenant-json", help="Path to tenant.json or a sanitized APIC snapshot")
    parser.add_argument("--from-apic", action="store_true",
                        help="Log on to APIC and retrieve tenant.json")
    parser.add_argument("--apic-host", default=os.environ.get("APIC_HOST", DEFAULT_APIC_HOST))
    parser.add_argument("--apic-user", default=os.environ.get("APIC_USER", DEFAULT_APIC_USER))
    parser.add_argument("--format",
                        choices=("png", "svg", "both", "html", "json", "all"),
                        default=os.environ.get("DIAGRAM_FORMAT", "png"),
                        help="png/svg static, html interactive viewer, json raw graph, "
                             "both = png+svg, all = png+svg+html+json")
    parser.add_argument("--serve", type=int, metavar="PORT", nargs="?", const=8787,
                        help="Serve the interactive viewer on 127.0.0.1:PORT "
                             "(default 8787), re-parsing on every request")
    parser.add_argument("--d3-dir", metavar="DIR",
                        help="Inline d3.min.js / d3-sankey.min.js from DIR instead of "
                             "loading them from the CDN (offline / airgapped labs)")
    parser.add_argument("--font-regular", help="Path to a regular .ttf/.ttc")
    parser.add_argument("--font-bold", help="Path to a bold .ttf/.ttc")
    parser.add_argument("--show-fonts", action="store_true",
                        help="Print the resolved font paths and exit")
    parser.add_argument("--no-prompt", action="store_true",
                        help="Use flags only; do not open the dialog")
    args = parser.parse_args()

    set_fonts(args.font_regular, args.font_bold)
    if args.show_fonts:
        print(f"platform : {sys.platform}")
        print(f"regular  : {FONT_REG or '(Pillow built-in fallback)'}")
        print(f"bold     : {FONT_BOLD or '(Pillow built-in fallback)'}")
        return

    d3_dir = Path(args.d3_dir).expanduser().resolve() if args.d3_dir else None

    job = Job(
        tenant=args.tenant.strip(),
        nac=resolve_path(args.nac) if args.nac else None,
        tenant_json=resolve_path(args.tenant_json) if args.tenant_json else None,
        from_apic=args.from_apic,
        apic_host=args.apic_host,
        apic_user=args.apic_user,
        apic_pass=os.environ.get("APIC_PASS"),
    )

    if args.serve is not None:
        if not job.nac and not job.tenant_json and not job.from_apic:
            raise SystemExit(
                "--serve needs --nac, --tenant-json, or --from-apic"
            )

        if job.nac and not job.nac.is_file():
            raise SystemExit(f"NAC file not found: {job.nac}")

        if job.tenant_json and not job.tenant_json.is_file():
            raise SystemExit(f"tenant.json not found: {job.tenant_json}")

        if job.from_apic and not job.apic_host:
            raise SystemExit(
                "APIC host is not set. Copy diagrams/.env.example to "
                "diagrams/.env or pass --apic-host."
            )

        if job.from_apic and not job.apic_user:
            raise SystemExit(
                "APIC user is not set. Set APIC_USER in diagrams/.env "
                "or pass --apic-user."
            )

        if job.from_apic and not (
            job.apic_pass or os.environ.get("APIC_PASS")
        ):
            raise SystemExit(
                "--serve with --from-apic requires APIC_PASS because the "
                "server cannot prompt for a password on every request."
            )

        serve_viewer(job, args.serve, d3_dir)
        return

    if args.no_prompt or args.nac or args.tenant_json or args.from_apic:
        run_job(job, args.format, d3_dir)
        return
    job, fmt = prompt_job(job, args.format)
    run_job(job, fmt, d3_dir)


if __name__ == "__main__":
    main()