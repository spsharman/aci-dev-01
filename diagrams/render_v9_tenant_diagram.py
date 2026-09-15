#!/usr/bin/env python3
"""ACI tenant / VRF / ESG diagrams.

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
With no flags, a prompt box asks for the same four choices.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import ssl
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http.cookiejar import CookieJar
from pathlib import Path

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
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val


load_local_env()
# Host and user come from the environment or dialog — never from this file.
DEFAULT_APIC_HOST = os.environ.get("APIC_HOST", "")
DEFAULT_APIC_USER = os.environ.get("APIC_USER", "")
# macOS ships a deprecated system Tk; silence that warning before any Tk import.
os.environ.setdefault("TK_SILENCE_DEPRECATION", "1")

W, H = 3400, 2180


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
# Cyan sits next to green on the wheel, so it avoids the old royal-blue / grass-green clash.
CONS = (0, 145, 173)
PROV = ESG_GREEN
GOLD = (245, 192, 24)
MUTED = (120, 120, 120)
FOOTER = (80, 80, 80)

FONT_REG = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def F(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


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
    table_rows: list[tuple[str, str, str, str]]
    notes: str
    l3outs_vrf01: list[str] = field(default_factory=list)
    l3outs_vrf02: list[str] = field(default_factory=list)


def contract_bar(draw, x, y, consume=False, provide=False, cci=False, intra=False):
    """C / CCI / I / P handles. No connecting line — they are independent ports."""
    slots = [("C", consume, CONS), ("CCI", cci, GOLD), ("I", intra, GOLD), ("P", provide, PROV)]
    bw, bh, gap = 36, 18, 10
    bx = x
    for label, active, col in slots:
        fill = col if active else (255, 255, 255)
        text = (255, 255, 255) if active else col
        rr(draw, (bx, y, bx + bw, y + bh), r=3, fill=fill, outline=col, width=1)  # noqa: port chrome
        fnt = F(10, bold=True)
        tw = draw.textlength(label, font=fnt)
        draw.text((bx + (bw - tw) / 2, y + 3), label, font=fnt, fill=text)
        bx += bw + gap


def tagged_line(draw, x, y, kind, text):
    if kind == "sel":
        draw.text((x, y), text, font=F(12), fill=GRAY)
        return
    col = CONS if kind == "C" else PROV
    rr(draw, (x, y + 1, x + 16, y + 15), r=2, fill=col, outline=col)
    draw.text((x + 3, y + 1), kind, font=F(10, bold=True), fill=(255, 255, 255))
    draw.text((x + 22, y), text, font=F(12), fill=NAVY)


def esg_height(esg: ESG) -> int:
    rows = len(esg.selectors) + len(esg.consumers) + len(esg.providers)
    return 38 + 17 * max(rows, 1) + 30


def draw_esg(draw, x, y, w, esg: ESG) -> int:
    h = esg_height(esg)
    rr(draw, (x, y, x + w, y + h), r=5, fill=BOX, outline=ESG_GREEN, width=2)
    draw.rectangle((x + 1, y + 1, x + w - 1, y + 7), fill=ESG_GREEN)
    draw.text((x + 10, y + 11), f"ESG  {esg.name}", font=F(13, bold=True), fill=NAVY)
    yy = y + 32
    for s in esg.selectors:
        tagged_line(draw, x + 10, yy, "sel", s)
        yy += 17
    for c in esg.consumers:
        tagged_line(draw, x + 10, yy, "C", c)
        yy += 17
    for p in esg.providers:
        tagged_line(draw, x + 10, yy, "P", p)
        yy += 17
    contract_bar(draw, x + 10, y + h - 26, bool(esg.consumers), bool(esg.providers))
    return h


def ap_height(ap: AP) -> int:
    title = 28
    pad = 12
    gap = 8
    kids = [esg_height(e) for e in ap.esgs]
    kids += [88] * len(ap.epgs)
    if not kids:
        return title + pad * 2
    return title + pad + sum(kids) + gap * (len(kids) - 1) + pad


def draw_ap(draw, x, y, w, ap: AP) -> int:
    """Red AP container that owns its EPGs / ESGs."""
    h = ap_height(ap)
    rr(draw, (x, y, x + w, y + h), r=5, fill=BOX, outline=AP_RED, width=2)
    draw.rectangle((x + 1, y + 1, x + w - 1, y + 7), fill=AP_RED)
    draw.text((x + 10, y + 10), f"AP  {ap.name}", font=F(13, bold=True), fill=NAVY)
    yy = y + 32
    inner_w = w - 20
    for name, color in ap.epgs:
        draw_epg(draw, x + 10, yy, inner_w, name, color)
        yy += 88 + 8
    for esg in ap.esgs:
        yy += draw_esg(draw, x + 10, yy, inner_w, esg) + 8
    return h


def l3out_box(draw, x, y, w, name):
    h = 34
    rr(draw, (x, y, x + w, y + h), r=4, fill=BOX, outline=(160, 160, 160))
    draw.text((x + 12, y + 8), f"L3out  {name}", font=F(13, bold=True), fill=NAVY)
    return h


def bd_box(draw, x, y, w, bd: BD):
    h = 46
    rr(draw, (x, y, x + w, y + h), r=4, fill=BOX, outline=BD_BLUE, width=2)
    draw.rectangle((x + 1, y + 1, x + w - 1, y + 6), fill=BD_BLUE)
    draw.text((x + 10, y + 10), f"BD  {bd.name}", font=F(13, bold=True), fill=NAVY)
    draw.text((x + 10, y + 26), bd.gw, font=F(12), fill=GRAY)
    return h


def draw_epg(draw, x, y, w, name, color):
    h = 88
    rr(draw, (x, y, x + w, y + h), r=4, fill=BOX, outline=EPG_DARK, width=1)
    draw.rectangle((x + 1, y + 1, x + w - 1, y + 6), fill=EPG_DARK)
    draw.text((x + 10, y + 10), f"EPG  {name}", font=F(13, bold=True), fill=NAVY)
    draw.rounded_rectangle((x + 8, y + 32, x + w - 8, y + h - 8), radius=3, fill=(246, 246, 246), outline=(210, 210, 210))
    for i in range(4):
        sx = x + 16 + i * 26
        sy = y + 46
        rr(draw, (sx, sy, sx + 16, sy + 22), r=2, fill=color, outline=(90, 90, 90))
        draw.rectangle((sx + 3, sy + 5, sx + 13, sy + 8), fill=(255, 255, 255))
    return h


def vzany_box(draw, x, y, w, consumers):
    h = 36 + 17 * max(len(consumers), 1) + 28
    rr(draw, (x, y, x + w, y + h), r=5, fill=BOX, outline=EPG_DARK, width=1)
    draw.rectangle((x + 1, y + 1, x + w - 1, y + 7), fill=EPG_DARK)
    draw.text((x + 10, y + 11), "EPG  vzAny", font=F(13, bold=True), fill=NAVY)
    yy = y + 32
    if not consumers:
        draw.text((x + 10, yy), "no contracts attached", font=F(12), fill=MUTED)
    for c in consumers:
        tagged_line(draw, x + 10, yy, "C", c)
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
            r=7,
            fill=(shade, shade, shade),
            outline=(170, 170, 170),
        )
    draw.text((x + 14, y + 8), "K8s nodes   BGP AS65252", font=F(13, bold=True), fill=NAVY)
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
    draw.text((x + 52, y + 36), "Cilium CNI  +  eBPF", font=F(13, bold=True), fill=NAVY)
    draw.text((x + 52, y + 54), "Node subnets", font=F(12), fill=GRAY)
    draw.text((x + 52, y + 70), "10.237.101.0/27    10.100.0.0/23", font=F(12), fill=NAVY)
    draw.text((x + 14, y + 100), "Pod routes imported on floating SVI L3out", font=F(12), fill=GRAY)
    draw.text((x + 14, y + 116), "match-rule  pod-subnets   0.0.0.0/0 aggregate", font=F(12), fill=GRAY)
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
    tw = draw.textlength(text, font=fnt)
    ww = tw + 12
    rr(draw, (x, y, x + ww, y + 18), r=3, fill=fill, outline=outline)
    draw.text((x + 6, y + 2), text, font=fnt, fill=fg)
    return ww


def table_from_attachments(contracts_meta: dict, attachments: list[tuple[str, str, str]]) -> list[tuple[str, str, str, str]]:
    """attachments: (object_label, role, contract) role in {C,P}."""
    cons = defaultdict(list)
    provs = defaultdict(list)
    for obj, role, contract in attachments:
        (cons if role == "C" else provs)[contract].append(obj)
    rows = []
    names = sorted(set(cons) | set(provs) | set(contracts_meta))
    for name in names:
        scope = contracts_meta.get(name, "")
        c = ",  ".join(cons.get(name) or ["not attached"])
        p = ",  ".join(provs.get(name) or ["not attached"])
        rows.append((name, scope, c, p))
    return rows


def layout_aps(aps_by_vrf: dict[str, list[AP]]) -> tuple[list[AP], list[AP], list[AP]]:
    aps_v2 = list(aps_by_vrf.get("vrf-02") or [])
    aps_v1 = list(aps_by_vrf.get("vrf-01") or [])
    for name, aps in aps_by_vrf.items():
        if name not in ("vrf-01", "vrf-02"):
            aps_v1.extend(aps)
    isovalent_layout = any(a.name == "external-subnets-esgs" for a in aps_v2) or any(
        a.name in ("network-segments", "network-segments-esgs", "node-subnets-esgs") for a in aps_v1
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


def parse_yaml(path: Path, tenant: str) -> Model:
    data = yaml.safe_load(path.read_text())
    tenants = [t for t in data.get("apic", {}).get("tenants", []) if t.get("name") == tenant]
    if not tenants:
        names = [t.get("name") for t in data.get("apic", {}).get("tenants", []) if t.get("name")]
        raise SystemExit(f"tenant '{tenant}' not found in {path}. Tenants in file: {names or '(none)'}")
    tn = tenants[0]
    contracts_meta = {c["name"]: c.get("scope", "") for c in tn.get("contracts", [])}

    def l3_labels(vrf_name: str) -> list[str]:
        labels = []
        for o in tn.get("l3outs") or []:
            if o.get("vrf") == vrf_name:
                labels.append(f"{o.get('alias') or o['name']}    {o['name']}")
        return labels

    l3_01 = l3_labels("vrf-01")
    l3_02 = l3_labels("vrf-02")

    vz = []
    for vrf in tn.get("vrfs", []):
        if vrf["name"] == "vrf-01":
            vz = list(vrf.get("contracts", {}).get("consumers") or [])

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
        bds.append(BD(bd["name"].replace("_", "/"), f"GW  {sub.get('ip','')}   {' + '.join(flags)}".rstrip()))

    attachments = [("vzAny (vrf-01)", "C", c) for c in vz]
    aps_by_vrf: dict[str, list[AP]] = defaultdict(list)
    epg_colors = [RED, L3, BD_BLUE, ESG_GREEN]
    for ap in tn.get("application_profiles", []):
        epgs = []
        for i, epg in enumerate(ap.get("endpoint_groups") or []):
            epgs.append((epg["name"].replace("_", "/"), epg_colors[i % len(epg_colors)]))
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
                sels.append(f"EPG selector  {sel.get('application_profile')} / {sel.get('endpoint_group')}")
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
        aps_by_vrf[vrf or "vrf-01"].append(AP(ap["name"], esgs, epgs))

    aps_v2, center, right = layout_aps(aps_by_vrf)

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
        "fvEPgSelector,fvRsMatchEPg,l3extRsEctx,fvRsScope"
    )
    return subtree


def parse_apic(subtree: dict, tenant: str, apic_host: str) -> Model:
    by = defaultdict(list)
    for item in subtree.get("imdata", []):
        cls = next(iter(item))
        by[cls].append(item[cls]["attributes"])

    tenant = infer_tenant_from_json(subtree, tenant)
    contracts_meta = {a["name"]: a.get("scope", "") for a in by.get("vzBrCP", [])}

    l3_alias = {}
    for o in by.get("l3extOut", []):
        l3_alias[o["name"]] = o.get("nameAlias") or o["name"]
    l3_vrf = {}
    for r in by.get("l3extRsEctx", []):
        out = r["dn"].split("/out-")[1].split("/")[0]
        l3_vrf[out] = r.get("tnFvCtxName")
    l3_01 = [f"{l3_alias.get(n, n)}    {n}" for n, v in l3_vrf.items() if v == "vrf-01"]
    l3_02 = [f"{l3_alias.get(n, n)}    {n}" for n, v in l3_vrf.items() if v == "vrf-02"]
    if not l3_01:
        l3_01 = [f"{l3_alias.get(n, n)}    {n}" for n in l3_alias if "vrf-01" in n]
    if not l3_02:
        l3_02 = [f"{l3_alias.get(n, n)}    {n}" for n in l3_alias if "vrf-02" in n]

    vz = []
    for r in by.get("vzRsAnyToCons", []):
        if "/ctx-vrf-01/" in r["dn"]:
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

    attachments = [("vzAny (vrf-01)", "C", c) for c in vz]
    ap_esgs: dict[str, list[ESG]] = defaultdict(list)
    ap_vrf: dict[str, str] = {}
    for e in by.get("fvESg", []):
        ap = e["dn"].split("/ap-")[1].split("/")[0]
        name = e["name"]
        esg = ESG(name, selectors.get(name, []), esg_cons.get(name, []), esg_provs.get(name, []))
        ap_esgs[ap].append(esg)
        ap_vrf[ap] = esg_vrf.get(name) or ("vrf-02" if "external-subnets" in ap else "vrf-01")
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
        vrf = ap_vrf.get(name, "vrf-02" if "external-subnets" in name else "vrf-01")
        aps_by_vrf[vrf].append(AP(name, ap_esgs.get(name, []), ap_epgs.get(name, [])))
    aps_v2, center, right = layout_aps(aps_by_vrf)

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
        notes="Read-only query of the running tenant. Service-graph / PBR objects exist on the fabric but are omitted from this ESG view.",
        l3outs_vrf01=l3_01,
        l3outs_vrf02=l3_02,
    )


def fingerprint(model: Model) -> set[tuple]:
    items = set()
    for ap in model.aps_vrf02 + model.aps_vrf01_center + model.aps_vrf01_right:
        for e in ap.esgs:
            items.add((ap.name, e.name, tuple(sorted(e.consumers)), tuple(sorted(e.providers)), tuple(sorted(e.selectors))))
    items.add(("vzAny", tuple(sorted(model.vz_consumers))))
    return items


def _l3_labels(model: Model, which: str) -> list[str]:
    extras = model.l3outs_vrf01 if which == "01" else model.l3outs_vrf02
    fallback = model.l3_vrf01 if which == "01" else model.l3_vrf02
    if extras:
        return extras
    if fallback and fallback.strip():
        return [fallback]
    return []


def _draw_contract_table(d, model: Model, top: int, canvas_h: int) -> None:
    d.rounded_rectangle((32, top, W - 32, canvas_h - 52), radius=6, outline=TENANT_GREEN, width=2)
    d.text((48, top + 12), "Contract relationships", font=F(17, bold=True), fill=NAVY)
    d.text((300, top + 18), "Consumer  →  contract  →  Provider", font=F(13), fill=GRAY)
    cols = [("Contract", 48, 640), ("Scope", 700, 110), ("Consumers", 830, 1280), ("Providers", 2130, 1180)]
    hy = top + 50
    d.rectangle((40, hy, W - 40, hy + 26), fill=(236, 245, 228))
    for title, x, _w in cols:
        d.text((x, hy + 5), title, font=F(13, bold=True), fill=TENANT_GREEN)
    ry = hy + 30
    for i, (contract, scope, cons, prov) in enumerate(model.table_rows):
        if i % 2 == 0:
            d.rectangle((40, ry - 1, W - 40, ry + 27), fill=(250, 250, 250))
        d.text((48, ry + 5), contract, font=F(13, bold=True), fill=NAVY)
        if scope:
            chip(d, 700, ry + 4, scope, (236, 245, 228), TENANT_GREEN, TENANT_GREEN)
        d.text((830, ry + 5), cons, font=F(12), fill=NAVY)
        muted = prov.startswith("no provider") or prov == "not attached"
        d.text((2130, ry + 5), prov, font=F(12), fill=MUTED if muted else NAVY)
        ry += 28
    d.text((48, ry + 8), model.notes, font=F(12), fill=MUTED)


def _center_ap_height(ap: AP) -> int:
    if ap.name == "network-segments-esgs" and len(ap.esgs) == 2:
        return 32 + max(esg_height(ap.esgs[0]), esg_height(ap.esgs[1])) + 16
    return ap_height(ap)


def _vzany_height(consumers: list[str]) -> int:
    return 36 + 17 * max(len(consumers), 1) + 28


def measure_topo_bottom(model: Model, dual: bool) -> int:
    """Lowest Y of VRF content so the contract table stays underneath."""
    if dual:
        left = 128
        for _ in _l3_labels(model, "02"):
            left += 34 + 10
        left += 4
        for ap in model.aps_vrf02:
            left += ap_height(ap) + 12

        center = 328
        for ap in model.aps_vrf01_center:
            if ap.name == "network-segments":
                center = 328 + ap_height(ap) + 12
            else:
                center += _center_ap_height(ap) + 12

        right = 268
        for ap in model.aps_vrf01_right:
            right += ap_height(ap) + 10

        header = 86 + max(156 if "k8s" in (model.l3_vrf01 or "").lower() else 0, _vzany_height(model.vz_consumers))
        bds = 268 + 46
        return max(left, center, right, header, bds) + 24

    y = 128
    for _ in _l3_labels(model, "01"):
        y += 34 + 10
    by = y + 8
    if model.bds:
        by += 56 * ((len(model.bds) - 1) // 5)
    col_y = [by + 64] * 3
    for ap in model.aps_vrf01_center + model.aps_vrf01_right:
        i = col_y.index(min(col_y))
        col_y[i] += ap_height(ap) + 12
    header = 86 + _vzany_height(model.vz_consumers)
    return max(col_y + [header, by + 46]) + 24


def render(model: Model, outfile: Path):
    dual = bool(model.aps_vrf02) or bool(_l3_labels(model, "02"))
    table_h = 80 + 28 * max(len(model.table_rows), 1) + 40
    topo_bottom = measure_topo_bottom(model, dual)
    canvas_h = max(H, topo_bottom + 20 + table_h + 44)

    img = Image.new("RGB", (W, canvas_h), (255, 255, 255))
    d = ImageDraw.Draw(img)

    cloud(d, 22, 8)
    d.text((138, 20), model.title, font=F(22, bold=True), fill=NAVY)
    d.text((268, 26), model.subtitle, font=F(14), fill=GRAY)

    kx = 1180
    for label, col in (("tenant", TENANT_GREEN), ("VRF", VRF_ORANGE), ("AP", AP_RED), ("ESG", ESG_GREEN), ("BD", BD_BLUE), ("EPG", EPG_DARK)):
        d.rectangle((kx, 28, kx + 14, 40), fill=col)
        d.text((kx + 18, 26), label, font=F(12), fill=GRAY)
        kx += 78
    for kind, col, label in (("C", CONS, "consumer"), ("P", PROV, "provider")):
        rr(d, (kx, 26, kx + 16, 42), r=2, fill=col, outline=col)
        d.text((kx + 3, 27), kind, font=F(10, bold=True), fill=(255, 255, 255))
        d.text((kx + 20, 26), label, font=F(12), fill=GRAY)
        kx += 88
    d.text((kx + 4, 26), "CCI consumed-IF   I intra", font=F(12), fill=GRAY)

    d.rounded_rectangle((16, 58, W - 16, canvas_h - 44), radius=8, outline=TENANT_GREEN, width=3)

    if dual:
        left = (32, 74, 900, topo_bottom)
        right = (920, 74, W - 32, topo_bottom)
        d.rounded_rectangle(left, radius=6, outline=VRF_ORANGE, width=2)
        d.rounded_rectangle(right, radius=6, outline=VRF_ORANGE, width=2)

        router(d, 52, 90)
        d.text((98, 92), "vrf-02  (outside)", font=F(17, bold=True), fill=NAVY)
        y = 128
        for label in _l3_labels(model, "02"):
            y += l3out_box(d, 52, y, 828, label) + 10
        y += 4
        for ap in model.aps_vrf02:
            y += draw_ap(d, 52, y, 828, ap) + 12

        router(d, 940, 90)
        d.text((986, 92), "vrf-01  (inside)", font=F(17, bold=True), fill=NAVY)
        l3out_box(d, 940, 128, 620, model.l3_vrf01 or (_l3_labels(model, "01") or [""])[0])
        show_k8s = "k8s" in (model.l3_vrf01 or "").lower()
        if show_k8s:
            d.line((1568, 145, 1624, 145), fill=L3, width=3)
            k8s_stack(d, 1630, 86, 500)
            vzany_box(d, 2380, 86, 964, model.vz_consumers)
        else:
            vzany_box(d, 2380, 86, 964, model.vz_consumers)

        bx = 940
        for bd in model.bds:
            bd_box(d, bx, 268, 360, bd)
            bx += 380

        cy = 328
        for ap in model.aps_vrf01_center:
            if ap.name == "network-segments":
                h = draw_ap(d, 940, cy, 760, ap)
                cy = 328 + h + 12
            elif ap.name == "network-segments-esgs" and len(ap.esgs) == 2:
                h = 32 + max(esg_height(ap.esgs[0]), esg_height(ap.esgs[1])) + 16
                rr(d, (940, cy, 940 + 1420, cy + h), r=5, fill=BOX, outline=AP_RED, width=2)
                d.rectangle((941, cy + 1, 940 + 1419, cy + 7), fill=AP_RED)
                d.text((950, cy + 10), f"AP  {ap.name}", font=F(13, bold=True), fill=NAVY)
                draw_esg(d, 950, cy + 32, 690, ap.esgs[0])
                draw_esg(d, 1660, cy + 32, 680, ap.esgs[1])
                cy += h + 12
            else:
                cy += draw_ap(d, 940, cy, 1420, ap) + 12

        col, cw = 2380, 964
        yy = 268
        for ap in model.aps_vrf01_right:
            yy += draw_ap(d, col, yy, cw, ap) + 10
    else:
        d.rounded_rectangle((32, 74, W - 32, topo_bottom), radius=6, outline=VRF_ORANGE, width=2)
        router(d, 52, 90)
        d.text((98, 92), "vrf-01", font=F(17, bold=True), fill=NAVY)
        y = 128
        for label in _l3_labels(model, "01"):
            y += l3out_box(d, 52, y, 1600, label) + 10
        vzany_box(d, 2380, 86, 964, model.vz_consumers)
        bx, by = 52, y + 8
        for i, bd in enumerate(model.bds):
            if i and i % 5 == 0:
                bx = 52
                by += 56
            bd_box(d, bx, by, 360, bd)
            bx += 380
        aps = model.aps_vrf01_center + model.aps_vrf01_right
        n_cols = 3
        col_w = 1080
        col_gap = 16
        col_y = [by + 64] * n_cols
        for ap in aps:
            i = col_y.index(min(col_y))
            x = 52 + i * (col_w + col_gap)
            col_y[i] += draw_ap(d, x, col_y[i], col_w, ap) + 12

    _draw_contract_table(d, model, topo_bottom + 20, canvas_h)
    d.text((24, canvas_h - 34), "© 2026 Cisco and/or its affiliates. All rights reserved.", font=F(12), fill=FOOTER)
    d.text((W - 110, canvas_h - 36), "cisco", font=F(18, bold=True), fill=NAVY)

    outfile.parent.mkdir(parents=True, exist_ok=True)
    img.save(outfile, "PNG", optimize=True)
    print(f"wrote {outfile}  {img.size}")


def load_tenant_model(data: dict, tenant: str, source: str) -> Model:
    """Accept raw APIC subtree JSON (imdata) or a sanitized snapshot."""
    tenant = infer_tenant_from_json(data, tenant)
    if "imdata" in data:
        model = parse_apic(data, tenant, source)
        if source and "://" not in source:
            model.subtitle = f"ACTUAL   ·   {source}   ·   uni/tn-{tenant}"
            model.notes = "Rendered from a saved APIC tenant.json (no credentials stored)."
        return model
    return parse_snapshot_data(data, tenant)


def parse_snapshot(path: Path) -> Model:
    return load_tenant_model(json.loads(path.read_text()), DEFAULT_TENANT, path.name)


def parse_snapshot_data(snap: dict, fallback_tenant: str) -> Model:
    contracts_meta = snap.get("contracts", {})
    attachments = [("vzAny (vrf-01)", "C", c) for c in snap.get("vz_consumers_vrf01", [])]
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
            (e["name"].replace("_", "/"), (196, 30, 58) if "96" in e["name"] else (0, 112, 186))
            for e in snap.get("epgs", [])
        ],
    )
    aps_v2 = [aps[n] for n in aps if n == "external-subnets-esgs"]
    center = [epg_ap]
    for n in ("network-segments-esgs", "node-subnets-esgs"):
        if n in aps:
            center.append(aps[n])
    right = [aps[n] for n in aps if n not in ("external-subnets-esgs", "network-segments-esgs", "node-subnets-esgs")]
    bds = []
    for b in snap.get("bds", []):
        flags = " + ".join(x for x in ("public", "shared") if x in b.get("scope", ""))
        bds.append(BD(b["name"].replace("_", "/"), f"GW  {b.get('ip','')}   {flags}".rstrip()))
    l3 = snap.get("l3outs", {})
    tenant = snap.get("tenant", fallback_tenant)
    o01 = next((n for n, v in l3.items() if n.endswith("vrf-01") or v.get("vrf") == "vrf-01"), f"{tenant}.vrf-01")
    o02 = next((n for n, v in l3.items() if n.endswith("vrf-02") or v.get("vrf") == "vrf-02"), f"{tenant}.vrf-02")
    return Model(
        title=tenant,
        subtitle=f"ACTUAL   ·   APIC {snap.get('host','')}   ·   uni/tn-{tenant}   ·   {snap.get('source','')}",
        l3_vrf02=f"{l3.get(o02, {}).get('alias', o02)}    {o02}",
        l3_vrf01=f"{l3.get(o01, {}).get('alias', o01)}    {o01}",
        vz_consumers=list(snap.get("vz_consumers_vrf01", [])),
        aps_vrf02=aps_v2,
        aps_vrf01_center=center,
        aps_vrf01_right=right,
        bds=bds,
        table_rows=table_from_attachments(contracts_meta, attachments),
        notes="Rendered from a sanitized read-only snapshot of the running tenant (no credentials stored).",
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


def prompt_cli(job: Job) -> Job:
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
    nac = resolve_path(nac_in) if nac_in else None
    if nac and not nac.is_file():
        raise SystemExit(f"NAC file not found: {nac}")
    if json_path and not json_path.is_file():
        raise SystemExit(f"tenant.json not found: {json_path}")
    if not nac and not json_path and not from_apic:
        raise SystemExit("Provide a NAC file, a tenant.json file, or retrieve from APIC.")
    return Job(tenant, nac, json_path, from_apic, host, user, password)


def prompt_job(job: Job) -> Job:
    """Dialog: optional NAC, plus tenant.json from file or APIC login.

    Password is read into memory only and is never written to disk.
    """
    os.environ.setdefault("TK_SILENCE_DEPRECATION", "1")
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox
    except Exception:
        return prompt_cli(job)

    result: dict = {"ok": False}
    root = tk.Tk()
    root.title("ACI Tenant Diagram")
    root.resizable(False, False)
    pad = {"padx": 12, "pady": 4}

    tk.Label(root, text="Render tenant / VRF / ESG diagrams", font=("Arial", 13, "bold")).grid(
        row=0, column=0, columnspan=3, sticky="w", **pad
    )
    tk.Label(
        root,
        text="Use NAC, tenant.json, or both. Password is not saved. Lab APIC uses a self-signed certificate.",
        fg="#555555",
        wraplength=560,
        justify="left",
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
    tk.Radiobutton(modes, text="Log on to APIC and retrieve tenant.json", variable=json_mode, value="apic").pack(anchor="w")

    tk.Label(root, text="tenant.json").grid(row=5, column=0, sticky="e", **pad)
    json_var = tk.StringVar(value=str(suggested_json(job.tenant)))
    json_entry = tk.Entry(root, textvariable=json_var, width=52)
    json_entry.grid(row=5, column=1, sticky="we", **pad)

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

    tk.Label(root, text="APIC host").grid(row=6, column=0, sticky="e", **pad)
    host_var = tk.StringVar(value=job.apic_host)
    tk.Entry(root, textvariable=host_var, width=52).grid(row=6, column=1, columnspan=2, sticky="we", **pad)
    tk.Label(root, text="APIC user").grid(row=7, column=0, sticky="e", **pad)
    user_var = tk.StringVar(value=job.apic_user)
    tk.Entry(root, textvariable=user_var, width=52).grid(row=7, column=1, columnspan=2, sticky="we", **pad)
    tk.Label(root, text="APIC password").grid(row=8, column=0, sticky="e", **pad)
    pass_var = tk.StringVar()
    tk.Entry(root, textvariable=pass_var, width=52, show="*").grid(row=8, column=1, columnspan=2, sticky="we", **pad)
    tk.Label(
        root,
        text="Leave password blank to use the APIC_PASS environment variable. It is never written to disk.",
        fg="#555555",
        wraplength=560,
        justify="left",
    ).grid(row=9, column=1, columnspan=2, sticky="w", **pad)

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
            messagebox.showerror("Required", "Supply a NAC file, a tenant.json file, or retrieve from APIC.")
            return
        password = pass_var.get() or os.environ.get("APIC_PASS") or None
        host = host_var.get().strip() or DEFAULT_APIC_HOST
        user = user_var.get().strip() or DEFAULT_APIC_USER
        if from_apic and not host:
            messagebox.showerror("Required", "Enter the APIC host or set APIC_HOST in diagrams/.env")
            return
        if from_apic and not user:
            messagebox.showerror("Required", "Enter the APIC user or set APIC_USER in diagrams/.env")
            return
        if from_apic and not password:
            messagebox.showerror("Required", "Enter the APIC password or set APIC_PASS.")
            return
        result["ok"] = True
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
    btns.grid(row=10, column=0, columnspan=3, sticky="e", padx=12, pady=10)
    tk.Button(btns, text="Cancel", command=cancel, width=10).pack(side="right", padx=4)
    tk.Button(btns, text="Render", command=submit, width=10, default="active").pack(side="right")
    root.bind("<Return>", lambda _e: submit())
    tenant_entry.focus_set()
    tenant_entry.selection_range(0, "end")
    root.mainloop()
    if not result.get("ok"):
        raise SystemExit("cancelled")
    return result["job"]


def annotate_diff(intent: Model, actual: Model) -> None:
    same = fingerprint(intent) == fingerprint(actual)
    if same:
        actual.notes = (
            "Live fabric matches NAC intent for AP / ESG membership, selectors, and C/P attachments.  "
            + actual.notes
        )
        return
    missing = fingerprint(intent) - fingerprint(actual)
    extra = fingerprint(actual) - fingerprint(intent)
    actual.notes = f"DIFF vs intent — missing {len(missing)}  extra {len(extra)}.  " + actual.notes
    print("missing", missing)
    print("extra", extra)


def run_job(job: Job) -> None:
    if not job.nac and not job.tenant_json and not job.from_apic:
        raise SystemExit("Provide a NAC file, a tenant.json file, or retrieve from APIC.")

    data = None
    if job.from_apic:
        if not job.apic_host:
            raise SystemExit("APIC host is not set. Copy diagrams/.env.example to diagrams/.env or pass --apic-host.")
        if not job.apic_user:
            raise SystemExit("APIC user is not set. Set APIC_USER in diagrams/.env or pass --apic-user.")
        password = job.apic_pass or os.environ.get("APIC_PASS")
        if not password:
            password = getpass.getpass(f"Password for {job.apic_user}@{job.apic_host}: ")
        data = fetch_apic(job.tenant, job.apic_host, job.apic_user, password)
        job.tenant = infer_tenant_from_json(data, job.tenant)
    elif job.tenant_json:
        data = json.loads(job.tenant_json.read_text())
        job.tenant = infer_tenant_from_json(data, job.tenant)

    outdir = tenant_dir(job.tenant)
    outdir.mkdir(parents=True, exist_ok=True)

    if job.from_apic and data is not None:
        saved = outdir / "tenant.json"
        saved.write_text(json.dumps(data, indent=2) + "\n")
        print(f"wrote {saved}")

    intent = None
    if job.nac:
        if not job.nac.is_file():
            raise SystemExit(f"NAC file not found: {job.nac}")
        intent = parse_yaml(job.nac, job.tenant)
        render(intent, outdir / f"tn-{job.tenant}-intent.png")

    actual = None
    if data is not None:
        source = job.apic_host if job.from_apic else str(job.tenant_json)
        actual = load_tenant_model(data, job.tenant, source)
        if intent is not None:
            annotate_diff(intent, actual)
        render(actual, outdir / f"tn-{job.tenant}-actual-apic.png")


def main():
    parser = argparse.ArgumentParser(
        description="Render ACI tenant diagrams from optional NAC YAML and/or tenant JSON."
    )
    parser.add_argument("--tenant", default=DEFAULT_TENANT, help="Tenant name")
    parser.add_argument("--nac", help="Path to the NAC YAML file (optional)")
    parser.add_argument("--tenant-json", help="Path to tenant.json or a sanitized APIC snapshot")
    parser.add_argument("--from-apic", action="store_true", help="Log on to APIC and retrieve tenant.json")
    parser.add_argument("--apic-host", default=os.environ.get("APIC_HOST", DEFAULT_APIC_HOST))
    parser.add_argument("--apic-user", default=os.environ.get("APIC_USER", DEFAULT_APIC_USER))
    parser.add_argument("--no-prompt", action="store_true", help="Use flags only; do not open the dialog")
    args = parser.parse_args()

    job = Job(
        tenant=args.tenant.strip(),
        nac=resolve_path(args.nac) if args.nac else None,
        tenant_json=resolve_path(args.tenant_json) if args.tenant_json else None,
        from_apic=args.from_apic,
        apic_host=args.apic_host,
        apic_user=args.apic_user,
        apic_pass=os.environ.get("APIC_PASS"),
    )
    if args.no_prompt or args.nac or args.tenant_json or args.from_apic:
        run_job(job)
        return
    run_job(prompt_job(job))


if __name__ == "__main__":
    main()
