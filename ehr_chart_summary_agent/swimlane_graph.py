"""
Interactive Multi-Track Clinical Swimlane Graph Generator (Backed by HL7 FHIR R4).

Synchronizes four parallel temporal clinical tracks along a shared horizontal timeline:
  - Track 1: Encounters, Admissions & Specialist Consults (FHIR Encounter + DocumentReference)
  - Track 2: Medication Changes, Held Drugs & Real-World Adherence (FHIR MedicationRequest)
  - Track 3: Longitudinal Lab Trajectories, Vitals & Diagnostic Imaging (FHIR Observation + DiagnosticReport)
  - Track 4: Open Clinical Loops, Care Gaps & Safety Alerts (FHIR Flag)

Produces:
1. Synchronized 4-track structured timeline data + cross-track causal links parsed from FHIR
2. Mermaid `gantt` 4-track temporal swimlane diagram + Markdown horizontal swimlane matrix
3. Self-contained interactive HTML/SVG Multi-Track Clinical Swimlane application (XSS-hardened)
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

SWIMLANE_TRACKS: list[dict[str, Any]] = [
    {
        "track_id": "track_1_encounters",
        "track_number": 1,
        "label": "Track 1 · Encounters & Notes",
        "subtitle": "Admissions, ED Visits, Consults & Triage",
        "color": "#3b82f6",
    },
    {
        "track_id": "track_2_medications",
        "track_number": 2,
        "label": "Track 2 · Medications & Adherence",
        "subtitle": "Starts, Dose Changes, Held Drugs & Barriers",
        "color": "#8b5cf6",
    },
    {
        "track_id": "track_3_diagnostics",
        "track_number": 3,
        "label": "Track 3 · Labs, Vitals & Imaging",
        "subtitle": "Biomarker Trajectories, CT & Echocardiography",
        "color": "#06b6d4",
    },
    {
        "track_id": "track_4_open_loops",
        "track_number": 4,
        "label": "Track 4 · Open Loops & Safety Alerts",
        "subtitle": "Dropped Follow-Ups, Toxicity & Action Triggers",
        "color": "#f43f5e",
    },
]

_SAFE_FILENAME_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")


def _compute_age_sex(birth_date: str, gender: str) -> str:
    sex_label = (gender or "Unknown").capitalize()
    try:
        dob = datetime.strptime(birth_date[:10], "%Y-%m-%d")
        age = max(0, 2026 - dob.year - ((11, 13) < (dob.month, dob.day)))
        return f"{age}yo {sex_label}"
    except Exception:
        return sex_label


def extract_swimlane_from_fhir_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    """
    Extracts or dynamically synthesizes the 4-track temporal swimlane structure
    directly from a FHIR R4 `Patient/$everything` Bundle.
    """
    entries = bundle.get("entry", [])
    patient_res: dict[str, Any] = {}
    encounters: list[dict[str, Any]] = []
    medications: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    imaging: list[dict[str, Any]] = []
    flags: list[dict[str, Any]] = []

    for item in entries:
        res = item.get("resource", {})
        rtype = res.get("resourceType")
        if rtype == "Patient":
            patient_res = res
        elif rtype == "Encounter":
            encounters.append(res)
        elif rtype == "MedicationRequest":
            medications.append(res)
        elif rtype == "Observation":
            observations.append(res)
        elif rtype == "DiagnosticReport":
            imaging.append(res)
        elif rtype == "Flag":
            flags.append(res)

    pid = patient_res.get("id", "unknown")
    names = patient_res.get("name", [])
    full_name = "Unknown Patient"
    if names:
        given = " ".join(names[0].get("given", []))
        family = names[0].get("family", "")
        full_name = f"{given} {family}".strip() or names[0].get("text", "Unknown Patient")

    age_sex = _compute_age_sex(patient_res.get("birthDate", ""), patient_res.get("gender", ""))
    headline = f"Longitudinal FHIR Clinical Timeline — {full_name}"
    embedded_swimlane: dict[str, Any] | None = None

    for ext in patient_res.get("extension", []):
        url = ext.get("url", "")
        if url.endswith("/swimlane-headline") and ext.get("valueString"):
            headline = ext["valueString"]
        elif url.endswith("/swimlane-json") and ext.get("valueString"):
            try:
                embedded_swimlane = json.loads(ext["valueString"])
            except json.JSONDecodeError:
                embedded_swimlane = None

    if embedded_swimlane and embedded_swimlane.get("timepoints"):
        return {
            "patient_id": pid,
            "patient_name": full_name,
            "age_sex": embedded_swimlane.get("age_sex", age_sex),
            "headline": headline,
            "timepoints": embedded_swimlane["timepoints"],
            "causal_links": embedded_swimlane.get("causal_links", []),
        }

    # Dynamic synthesis fallback for any arbitrary FHIR Patient/$everything bundle without extensions
    sorted_encs = sorted(encounters, key=lambda e: (e.get("period", {}).get("start") or ""))
    timepoints: list[dict[str, Any]] = []
    for idx, enc in enumerate(sorted_encs[-4:] or [{"period": {"start": "2026-11-12"}, "type": [{"text": "Clinical Review"}]}], start=1):
        dt = (enc.get("period", {}).get("start") or "2026-11-12")[:10]
        enc_title = (enc.get("type") or [{}])[0].get("text", "Clinical Encounter")
        reason = (enc.get("reasonCode") or [{}])[0].get("text", "Clinical evaluation")
        is_active = enc.get("status") == "in-progress"

        med_summary = ", ".join(
            (m.get("medicationCodeableConcept", {}).get("text") or "Medication")
            for m in medications[:3]
        ) or "No medications recorded"

        obs_summary = "; ".join(
            f"{o.get('code', {}).get('text', 'Lab')}: "
            f"{o.get('valueQuantity', {}).get('value', o.get('valueString', ''))}"
            for o in observations[:3]
        ) or "Routine diagnostics"

        flag_summary = "; ".join(
            f.get("code", {}).get("text", "Clinical follow-up")[:90] for f in flags[:2]
        ) or "Routine care monitoring"

        timepoints.append(
            {
                "time_id": f"T{idx}",
                "date": dt,
                "display_date": dt,
                "phase": "Active Triage" if is_active else f"Encounter {idx}",
                "tracks": {
                    "track_1_encounters": {
                        "node_id": f"G{idx}_1",
                        "title": enc_title[:45],
                        "badge": "TODAY" if is_active else "FHIR ENC",
                        "severity": "critical" if is_active else "info",
                        "summary": reason[:110],
                        "details": f"FHIR Encounter/{enc.get('id', 'enc')}",
                    },
                    "track_2_medications": {
                        "node_id": f"G{idx}_2",
                        "title": "FHIR Medication Regimen",
                        "badge": "MEDS",
                        "severity": "warning" if any(m.get("status") == "on-hold" for m in medications) else "normal",
                        "summary": med_summary[:110],
                        "details": f"{len(medications)} MedicationRequest resource(s) in FHIR.",
                    },
                    "track_3_diagnostics": {
                        "node_id": f"G{idx}_3",
                        "title": "FHIR Labs & Imaging",
                        "badge": "DIAGNOSTICS",
                        "severity": "info",
                        "summary": obs_summary[:110],
                        "details": f"{len(observations)} Observation(s), {len(imaging)} DiagnosticReport(s).",
                    },
                    "track_4_open_loops": {
                        "node_id": f"G{idx}_4",
                        "title": "Open Loops & Alerts",
                        "badge": "ALERTS" if flags else "OK",
                        "severity": "critical" if flags else "normal",
                        "summary": flag_summary[:110],
                        "details": f"{len(flags)} active FHIR Flag resource(s).",
                    },
                },
            }
        )

    return {
        "patient_id": pid,
        "patient_name": full_name,
        "age_sex": age_sex,
        "headline": headline,
        "timepoints": timepoints,
        "causal_links": [],
    }


def build_mermaid_swimlane(pdata: dict[str, Any]) -> str:
    """Builds a synchronized 4-track Mermaid gantt swimlane diagram from FHIR swimlane data."""
    pid = pdata["patient_id"]
    lines = [
        "```mermaid",
        "gantt",
        f'    title 4-Track Clinical Swimlane Timeline — {pdata["patient_name"]} ({pid})',
        "    dateFormat  YYYY-MM-DD",
        "    axisFormat  %b %d, %Y",
    ]

    for track in SWIMLANE_TRACKS:
        tid = track["track_id"]
        lines.append(f'    section {track["label"]}')
        for idx, tp in enumerate(pdata["timepoints"], start=1):
            node = tp["tracks"][tid]
            sev = node["severity"]
            if sev == "critical":
                tag = "crit, "
            elif sev == "warning":
                tag = "active, "
            elif sev == "normal":
                tag = "done, "
            else:
                tag = ""
            clean_title = (
                node["title"]
                .replace(":", " -")
                .replace(";", ",")
                .replace("#", "")
            )
            lines.append(
                f'    [{tp["display_date"]}] {clean_title} :{tag}t{track["track_number"]}_{idx}, {tp["date"]}, 3d'
            )

    lines.append("```")
    return "\n".join(lines)


def build_markdown_swimlane_matrix(pdata: dict[str, Any]) -> str:
    """Builds a synchronized 4-track horizontal timeline Markdown table."""
    tps = pdata["timepoints"]
    headers = ["Parallel Clinical Track"] + [
        f"**{tp['display_date']}**<br>*{tp['phase']}*" for tp in tps
    ]
    sep = [":---"] + [":---" for _ in tps]

    rows = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(sep) + " |",
    ]

    severity_icon = {
        "critical": "🔴",
        "warning": "🟠",
        "info": "🔵",
        "normal": "🟢",
    }

    for track in SWIMLANE_TRACKS:
        tid = track["track_id"]
        cells = [f"**{track['label']}**<br>_{track['subtitle']}_"]
        for tp in tps:
            node = tp["tracks"][tid]
            icon = severity_icon.get(node["severity"], "⚪")
            cell = (
                f"{icon} **`[{node['badge']}]` {node['title']}**<br>"
                f"{node['summary']}"
            )
            cells.append(cell)
        rows.append("| " + " | ".join(cells) + " |")

    if pdata.get("causal_links"):
        rows.append("\n### Cross-Track Temporal Causal Links")
        for link in pdata["causal_links"]:
            rows.append(f"- **[{link['from']} → {link['to']}]**: {link['label']}")

    return "\n".join(rows)


def generate_interactive_swimlane_html(
    selected_patient_id: str,
    patients_swimlane_map: dict[str, dict[str, Any]],
) -> str:
    """
    Generates a self-contained, XSS-hardened interactive HTML/SVG 4-Track Clinical Swimlane
    viewer inside `<workspace>/outputs/clinical_swimlane_<patient_id>.html`.
    """
    clean_pid = selected_patient_id.strip().lower()
    if not _SAFE_FILENAME_RE.match(clean_pid):
        raise ValueError("Invalid patient_id for swimlane output filename.")

    pkg_dir = Path(__file__).resolve().parent
    base_dir = pkg_dir.parent if pkg_dir.name == "ehr_chart_summary_agent" else pkg_dir
    outputs_root = (base_dir / "outputs").resolve()
    outputs_root.mkdir(parents=True, exist_ok=True)
    target_path = (outputs_root / f"clinical_swimlane_{clean_pid}.html").resolve()
    if outputs_root not in target_path.parents:
        raise ValueError("Output path traversal blocked.")

    # Escape closing script sequences (`</`) to prevent script-context breakout (CWE-79)
    safe_payload_json = json.dumps(
        {
            "selected_patient_id": selected_patient_id,
            "tracks": SWIMLANE_TRACKS,
            "patients": patients_swimlane_map,
        },
        indent=2,
    ).replace("</", "<\\/")

    safe_title_id = re.sub(r"[^A-Za-z0-9_\-]", "", selected_patient_id)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>FHIR Multi-Track Clinical Swimlane Graph — {safe_title_id}</title>
  <style>
    :root {{
      --bg: #0b1120;
      --panel: #111827;
      --panel-alt: #1e293b;
      --border: #334155;
      --text: #f8fafc;
      --muted: #94a3b8;
      --crit-bg: rgba(244, 63, 94, 0.16);
      --crit-border: #f43f5e;
      --warn-bg: rgba(245, 158, 11, 0.16);
      --warn-border: #f59e0b;
      --info-bg: rgba(56, 189, 248, 0.15);
      --info-border: #38bdf8;
      --norm-bg: rgba(16, 185, 129, 0.14);
      --norm-border: #10b981;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif;
      background: var(--bg);
      color: var(--text);
      padding: 20px 24px 40px;
      line-height: 1.45;
    }}
    .topbar {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      padding: 16px 20px;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      margin-bottom: 16px;
    }}
    .title-block h1 {{ font-size: 1.22rem; font-weight: 700; }}
    .title-block p {{ color: var(--muted); font-size: 0.85rem; margin-top: 3px; }}
    .controls {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }}
    .patient-tabs {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      background: #0f172a;
      padding: 4px;
      border-radius: 8px;
      border: 1px solid var(--border);
    }}
    .tab-btn {{
      background: transparent;
      color: var(--muted);
      border: none;
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 0.78rem;
      font-weight: 600;
      cursor: pointer;
    }}
    .tab-btn.active {{ background: #2563eb; color: #fff; }}
    .filter-btn {{
      background: var(--panel-alt);
      color: var(--text);
      border: 1px solid var(--border);
      padding: 7px 12px;
      border-radius: 8px;
      font-size: 0.8rem;
      cursor: pointer;
    }}
    .filter-btn.active {{ border-color: #38bdf8; background: rgba(56, 189, 248, 0.18); }}
    .headline-banner {{
      padding: 12px 18px;
      background: linear-gradient(90deg, rgba(37,99,235,0.18), rgba(244,63,94,0.14));
      border: 1px solid var(--border);
      border-radius: 10px;
      margin-bottom: 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }}
    .patient-chip {{ font-weight: 700; font-size: 0.95rem; color: #93c5fd; }}
    .legend {{ display: flex; gap: 14px; font-size: 0.78rem; color: var(--muted); align-items: center; }}
    .legend span {{ display: inline-flex; align-items: center; gap: 5px; }}
    .dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}
    .swimlane-viewport {{
      position: relative;
      overflow-x: auto;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
    }}
    .swimlane-grid {{ position: relative; display: grid; min-width: 1120px; }}
    .svg-overlay {{
      position: absolute;
      top: 0; left: 0;
      width: 100%; height: 100%;
      pointer-events: none;
      z-index: 5;
    }}
    .time-header-row, .track-row {{ display: grid; border-bottom: 1px solid var(--border); }}
    .track-row:last-child {{ border-bottom: none; }}
    .track-label-cell {{
      position: sticky; left: 0; z-index: 10;
      background: #0f172a;
      border-right: 2px solid var(--border);
      padding: 16px 14px;
      display: flex; flex-direction: column; justify-content: center;
    }}
    .track-title {{ font-weight: 700; font-size: 0.85rem; display: flex; align-items: center; gap: 8px; }}
    .track-sub {{ font-size: 0.74rem; color: var(--muted); margin-top: 4px; }}
    .time-col-header {{
      padding: 14px 12px;
      background: #0f172a;
      border-right: 1px dashed var(--border);
      text-align: center;
    }}
    .date-str {{ font-weight: 700; font-size: 0.84rem; color: #e2e8f0; }}
    .phase-str {{ font-size: 0.73rem; color: #38bdf8; margin-top: 2px; text-transform: uppercase; }}
    .node-cell {{
      padding: 14px 10px;
      border-right: 1px dashed rgba(51, 65, 85, 0.65);
      display: flex; align-items: stretch; position: relative;
    }}
    .event-card {{
      width: 100%;
      border-radius: 10px;
      padding: 10px 12px;
      border: 1.5px solid var(--border);
      background: var(--panel-alt);
      cursor: pointer;
      transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;
      position: relative; z-index: 6;
    }}
    .event-card:hover, .event-card.highlighted {{ transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,0,0,0.45); }}
    .event-card.dimmed {{ opacity: 0.28; }}
    .event-card.sev-critical {{ background: var(--crit-bg); border-color: var(--crit-border); }}
    .event-card.sev-warning {{ background: var(--warn-bg); border-color: var(--warn-border); }}
    .event-card.sev-info {{ background: var(--info-bg); border-color: var(--info-border); }}
    .event-card.sev-normal {{ background: var(--norm-bg); border-color: var(--norm-border); }}
    .card-top {{ display: flex; justify-content: space-between; align-items: center; gap: 6px; margin-bottom: 6px; }}
    .badge {{
      font-size: 0.65rem; font-weight: 700; padding: 2px 6px; border-radius: 4px;
      text-transform: uppercase; background: rgba(15, 23, 42, 0.65); color: #f8fafc;
    }}
    .node-id-tag {{ font-size: 0.65rem; color: var(--muted); font-family: monospace; }}
    .card-title {{ font-weight: 700; font-size: 0.82rem; margin-bottom: 5px; color: #ffffff; }}
    .card-summary {{ font-size: 0.75rem; color: #cbd5e1; }}
    .bottom-grid {{ display: grid; grid-template-columns: 1.2fr 1fr; gap: 16px; margin-top: 16px; }}
    @media (max-width: 960px) {{ .bottom-grid {{ grid-template-columns: 1fr; }} }}
    .info-panel {{ background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 16px 20px; }}
    .info-panel h3 {{ font-size: 0.95rem; margin-bottom: 10px; color: #93c5fd; }}
    .causal-list {{ list-style: none; display: flex; flex-direction: column; gap: 8px; }}
    .causal-item {{
      padding: 9px 12px; border-radius: 8px; background: var(--panel-alt);
      border-left: 3px solid #38bdf8; font-size: 0.8rem; cursor: pointer;
    }}
    .causal-item:hover {{ background: rgba(56, 189, 248, 0.16); }}
  </style>
</head>
<body>
  <div class="topbar">
    <div class="title-block">
      <h1>FHIR Multi-Track Clinical Swimlane Graph</h1>
      <p>Synchronizing 4 parallel HL7 FHIR R4 temporal tracks along a shared horizontal timeline</p>
    </div>
    <div class="controls">
      <div class="patient-tabs" id="patientTabs"></div>
      <button class="filter-btn active" id="toggleLinksBtn">Causal Connectors: ON</button>
      <button class="filter-btn" id="filterCritBtn">Highlight Critical / Warning Only</button>
    </div>
  </div>

  <div class="headline-banner">
    <div>
      <span class="patient-chip" id="patientBannerName"></span>
      <span id="patientBannerHeadline" style="margin-left:10px; font-size:0.88rem; color:#e2e8f0;"></span>
    </div>
    <div class="legend">
      <span><i class="dot" style="background:#f43f5e"></i> Critical / Alert</span>
      <span><i class="dot" style="background:#f59e0b"></i> Dose Change / Held / Gap</span>
      <span><i class="dot" style="background:#38bdf8"></i> Consult / Diagnostic</span>
      <span><i class="dot" style="background:#10b981"></i> Baseline / Stable</span>
    </div>
  </div>

  <div class="swimlane-viewport">
    <div class="swimlane-grid" id="swimlaneGrid">
      <svg class="svg-overlay" id="svgOverlay"></svg>
      <div id="gridContent"></div>
    </div>
  </div>

  <div class="bottom-grid">
    <div class="info-panel">
      <h3>Cross-Track Causal &amp; Temporal Correlations</h3>
      <ul class="causal-list" id="causalList"></ul>
    </div>
    <div class="info-panel">
      <h3>Clinical Event Inspector</h3>
      <div style="color:var(--muted); font-size:0.84rem;" id="inspectorBody">
        Click or hover over any node across the 4 parallel FHIR tracks to inspect clinical details.
      </div>
    </div>
  </div>

  <script>
    const DATA = {safe_payload_json};
    let currentPatientId = DATA.selected_patient_id;
    let showLinks = true;
    let criticalOnly = false;

    function esc(val) {{
      const s = String(val ?? "");
      return s
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }}

    function renderPatientTabs() {{
      const container = document.getElementById("patientTabs");
      container.innerHTML = "";
      Object.values(DATA.patients).forEach(p => {{
        const btn = document.createElement("button");
        btn.className = "tab-btn" + (p.patient_id === currentPatientId ? " active" : "");
        btn.textContent = p.patient_id + " · " + p.patient_name;
        btn.onclick = () => {{ currentPatientId = p.patient_id; renderAll(); }};
        container.appendChild(btn);
      }});
    }}

    function renderGrid() {{
      const pdata = DATA.patients[currentPatientId];
      document.getElementById("patientBannerName").textContent =
        pdata.patient_name + " (" + pdata.patient_id + ", " + pdata.age_sex + ")";
      document.getElementById("patientBannerHeadline").textContent = pdata.headline;

      const tps = pdata.timepoints;
      const colTemplate = "230px repeat(" + tps.length + ", minmax(195px, 1fr))";
      const content = document.getElementById("gridContent");
      content.innerHTML = "";

      const headerRow = document.createElement("div");
      headerRow.className = "time-header-row";
      headerRow.style.gridTemplateColumns = colTemplate;

      const corner = document.createElement("div");
      corner.className = "track-label-cell";
      corner.innerHTML = '<div class="track-title">Shared Timeline →</div><div class="track-sub">4 FHIR Tracks</div>';
      headerRow.appendChild(corner);

      tps.forEach(tp => {{
        const th = document.createElement("div");
        th.className = "time-col-header";
        th.innerHTML = '<div class="date-str">' + esc(tp.display_date) + '</div><div class="phase-str">' + esc(tp.phase) + '</div>';
        headerRow.appendChild(th);
      }});
      content.appendChild(headerRow);

      DATA.tracks.forEach(track => {{
        const row = document.createElement("div");
        row.className = "track-row";
        row.style.gridTemplateColumns = colTemplate;

        const labelCell = document.createElement("div");
        labelCell.className = "track-label-cell";
        labelCell.innerHTML =
          '<div class="track-title"><span class="dot" style="background:' + esc(track.color) + '"></span>' +
          esc(track.label) + '</div><div class="track-sub">' + esc(track.subtitle) + '</div>';
        row.appendChild(labelCell);

        tps.forEach(tp => {{
          const node = tp.tracks[track.track_id];
          const cell = document.createElement("div");
          cell.className = "node-cell";

          const sevClass = ["critical", "warning", "info", "normal"].includes(node.severity) ? node.severity : "info";
          const card = document.createElement("div");
          card.className = "event-card sev-" + sevClass;
          card.id = "node-" + esc(node.node_id);
          if (criticalOnly && sevClass !== "critical" && sevClass !== "warning") {{
            card.classList.add("dimmed");
          }}

          card.innerHTML =
            '<div class="card-top"><span class="badge">' + esc(node.badge) + '</span>' +
            '<span class="node-id-tag">' + esc(node.node_id) + '</span></div>' +
            '<div class="card-title">' + esc(node.title) + '</div>' +
            '<div class="card-summary">' + esc(node.summary) + '</div>';

          card.onmouseenter = () => inspectNode(tp, track, node);
          card.onclick = () => inspectNode(tp, track, node);
          cell.appendChild(card);
          row.appendChild(cell);
        }});
        content.appendChild(row);
      }});

      const causalList = document.getElementById("causalList");
      causalList.innerHTML = "";
      (pdata.causal_links || []).forEach(link => {{
        const li = document.createElement("li");
        li.className = "causal-item";
        li.innerHTML = "<strong>[" + esc(link.from) + " → " + esc(link.to) + "]</strong> " + esc(link.label);
        li.onmouseenter = () => highlightPair(link.from, link.to);
        li.onmouseleave = () => clearHighlights();
        causalList.appendChild(li);
      }});

      requestAnimationFrame(drawCausalConnectors);
    }}

    function inspectNode(tp, track, node) {{
      const pdata = DATA.patients[currentPatientId];
      const related = (pdata.causal_links || []).filter(l => l.from === node.node_id || l.to === node.node_id);
      const relHtml = related.length
        ? '<div style="margin-top:10px; padding-top:8px; border-top:1px solid #334155;">' +
          '<strong style="font-size:0.78rem; color:#38bdf8;">Linked Cross-Track Events:</strong>' +
          '<ul style="margin-top:4px; padding-left:16px; font-size:0.78rem; color:#cbd5e1;">' +
          related.map(r => "<li>[" + esc(r.from) + " → " + esc(r.to) + "] " + esc(r.label) + "</li>").join("") +
          "</ul></div>"
        : "";

      document.getElementById("inspectorBody").innerHTML =
        '<div style="font-size:0.78rem; color:#38bdf8; font-weight:700;">' + esc(tp.display_date) + " · " + esc(track.label) + "</div>" +
        '<div style="font-size:1rem; font-weight:700; color:#fff; margin:4px 0;">' + esc(node.title) + ' <span class="badge">' + esc(node.badge) + "</span></div>" +
        '<div style="font-size:0.84rem; color:#e2e8f0; margin-bottom:6px;">' + esc(node.summary) + "</div>" +
        '<div style="font-size:0.8rem; color:#94a3b8;">' + esc(node.details) + "</div>" +
        relHtml;
    }}

    function highlightPair(fromId, toId) {{
      document.querySelectorAll(".event-card").forEach(el => el.classList.add("dimmed"));
      const a = document.getElementById("node-" + fromId);
      const b = document.getElementById("node-" + toId);
      if (a) {{ a.classList.remove("dimmed"); a.classList.add("highlighted"); }}
      if (b) {{ b.classList.remove("dimmed"); b.classList.add("highlighted"); }}
    }}

    function clearHighlights() {{
      document.querySelectorAll(".event-card").forEach(el => {{
        el.classList.remove("highlighted");
        if (!criticalOnly) el.classList.remove("dimmed");
      }});
    }}

    function drawCausalConnectors() {{
      const svg = document.getElementById("svgOverlay");
      svg.innerHTML = "";
      if (!showLinks) return;

      const grid = document.getElementById("swimlaneGrid");
      const gridRect = grid.getBoundingClientRect();
      svg.setAttribute("width", grid.scrollWidth);
      svg.setAttribute("height", grid.scrollHeight);

      const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
      defs.innerHTML =
        '<marker id="arrow" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">' +
        '<path d="M 0 1 L 10 5 L 0 9 z" fill="rgba(56, 189, 248, 0.75)" /></marker>';
      svg.appendChild(defs);

      const pdata = DATA.patients[currentPatientId];
      (pdata.causal_links || []).forEach(link => {{
        const fromEl = document.getElementById("node-" + link.from);
        const toEl = document.getElementById("node-" + link.to);
        if (!fromEl || !toEl) return;
        const r1 = fromEl.getBoundingClientRect();
        const r2 = toEl.getBoundingClientRect();
        const x1 = r1.left - gridRect.left + r1.width / 2;
        const y1 = r1.top - gridRect.top + r1.height / 2;
        const x2 = r2.left - gridRect.left + r2.width / 2;
        const y2 = r2.top - gridRect.top + r2.height / 2;
        const dx = Math.abs(x2 - x1) * 0.45 + 25;
        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute("d", "M " + x1 + " " + y1 + " C " + (x1 + dx) + " " + y1 + ", " + (x2 - dx) + " " + y2 + ", " + x2 + " " + y2);
        path.setAttribute("fill", "none");
        path.setAttribute("stroke", "rgba(56, 189, 248, 0.55)");
        path.setAttribute("stroke-width", "2.2");
        path.setAttribute("stroke-dasharray", "5,4");
        path.setAttribute("marker-end", "url(#arrow)");
        svg.appendChild(path);
      }});
    }}

    document.getElementById("toggleLinksBtn").onclick = function() {{
      showLinks = !showLinks;
      this.textContent = "Causal Connectors: " + (showLinks ? "ON" : "OFF");
      this.classList.toggle("active", showLinks);
      drawCausalConnectors();
    }};

    document.getElementById("filterCritBtn").onclick = function() {{
      criticalOnly = !criticalOnly;
      this.classList.toggle("active", criticalOnly);
      renderGrid();
    }};

    window.addEventListener("resize", () => requestAnimationFrame(drawCausalConnectors));
    function renderAll() {{ renderPatientTabs(); renderGrid(); }}
    renderAll();
  </script>
</body>
</html>
"""
    target_path.write_text(html, encoding="utf-8")
    return str(target_path)
