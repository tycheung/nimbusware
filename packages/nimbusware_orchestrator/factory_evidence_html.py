from __future__ import annotations

import html
from typing import Any

from agent_core.mapping import mapping_or_empty


def render_factory_evidence_html(bundle: dict[str, Any]) -> str:
    run_id = html.escape(str(bundle.get("run_id") or "—"))
    rows = bundle.get("scorecard_rows") or []
    fs = mapping_or_empty(bundle.get("factory_status"))
    put = mapping_or_empty(bundle.get("put_e2e"))
    row_html = "".join(
        f"<tr><th scope=\"row\">{html.escape(str(r.get('dimension') or ''))}</th>"
        f"<td>{html.escape(str(r.get('value') or '—'))}</td></tr>"
        for r in rows
        if isinstance(r, dict)
    )
    stages = bundle.get("factory_stages") or []
    stage_items = "".join(
        f"<li>{html.escape(str(s.get('stage_name') or 'stage'))}</li>"
        for s in stages
        if isinstance(s, dict)
    )
    flow = html.escape(str(put.get("flow_id") or "—"))
    verdict = html.escape(str(put.get("verdict") or "—"))
    complete = "yes" if bundle.get("factory_complete") else "no"
    tier = html.escape(str(fs.get("tier") or "—"))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Factory evidence — {run_id}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #111; }}
    table {{ border-collapse: collapse; width: min(40rem, 100%); }}
    th, td {{ border: 1px solid #ccc; padding: 0.5rem 0.75rem; text-align: left; }}
    th {{ background: #f4f4f4; width: 40%; }}
    h1 {{ font-size: 1.25rem; }}
    .muted {{ color: #555; }}
  </style>
</head>
<body>
  <h1>Factory evidence scorecard</h1>
  <p class="muted">Run <code>{run_id}</code> · tier {tier} · factory complete: {complete}</p>
  <table aria-label="Factory scorecard">
    <tbody>{row_html}</tbody>
  </table>
  <h2>PUT E2E</h2>
  <p>Flow <strong>{flow}</strong> — verdict <strong>{verdict}</strong></p>
  {"<h2>Factory stages</h2><ul>" + stage_items + "</ul>" if stage_items else ""}
</body>
</html>
"""
