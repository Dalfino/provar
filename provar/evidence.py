"""Evidence pack: hash-chained, verifiable run records + report card renderers.

Integrity model (ADR-0003 / docs/EVIDENCE_SPEC.md):
  - each record hash = sha256(prev_hash + canonical_json(record_without_hash))
  - chain_root = sha256(concat of all record hashes)
  - `provar verify` recomputes the chain and the suite hash, and reports any
    tampering precisely (record index + reason).
"""

from __future__ import annotations

import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path

from . import PACK_FORMAT, __version__
from .corpus import Suite
from .standards import VOCAB


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_pack(
    pack_id: str,
    suite: Suite,
    target_meta: dict,
    outcomes: list,
    scorecard,
    postmortem: dict,
    run_meta: dict | None = None,
) -> dict:
    records = []
    prev = "sha256:GENESIS"
    for o in outcomes:
        rec = o.to_record(suite.id, suite.version)
        rec["prev_hash"] = prev
        rec["hash"] = _sha256(prev + canonical_json({k: v for k, v in rec.items() if k != "hash"}))
        prev = rec["hash"]
        records.append(rec)

    chain_root = _sha256("".join(r["hash"] for r in records))

    return {
        "pack_format": PACK_FORMAT,
        "pack_id": pack_id,
        "created_utc": utc_now_iso(),
        "tool": {"name": "provar", "version": __version__},
        "target": target_meta,
        "suite": {
            "id": suite.id,
            "version": suite.version,
            "content_hash": suite.content_hash,
            "probe_count": len(suite.probes),
            "transcript_count": suite.transcript_count(),
        },
        "run": run_meta or {},
        "verdict": {
            "overall_grade": scorecard.overall_grade,
            "verdict": scorecard.verdict,
            "statement": scorecard.statement,
            "gates_triggered": scorecard.gates_triggered,
            "failed": scorecard.failed,
            "errored": scorecard.errored,
            "total": scorecard.total,
            "fail_weight": scorecard.fail_weight,
            "total_weight": scorecard.total_weight,
            "error_rate": round(scorecard.error_rate, 4),
            "dimensions": [
                {
                    "name": ds.name,
                    "score": ds.score,
                    "grade": ds.grade,
                    "failed": ds.failed,
                    "errored": ds.errored,
                    "total": ds.total,
                    "fail_ids": ds.fail_ids,
                }
                for ds in scorecard.dimensions.values()
            ],
        },
        "postmortem": postmortem,
        "records": records,
        "integrity": {
            "algorithm": "sha256",
            "chain_rule": "hash = sha256(prev_hash + canonical_json(record without 'hash'))",
            "chain_root": chain_root,
            "record_count": len(records),
        },
    }


def verify_pack(pack: dict) -> tuple:
    issues = []
    records = pack.get("records", [])
    prev = "sha256:GENESIS"
    for i, rec in enumerate(records):
        expected = _sha256(prev + canonical_json({k: v for k, v in rec.items() if k != "hash"}))
        if rec.get("prev_hash") != prev:
            issues.append(f"record {i} ({rec.get('probe_id')}): prev_hash mismatch (chain broken)")
            prev = rec.get("hash", prev)
            continue
        if rec.get("hash") != expected:
            issues.append(f"record {i} ({rec.get('probe_id')}): content hash mismatch — record was modified after signing")
        prev = rec.get("hash", prev)
    root = _sha256("".join(r.get("hash", "") for r in records))
    declared = pack.get("integrity", {}).get("chain_root")
    if declared and declared != root:
        issues.append(f"chain_root mismatch: declared {declared}, computed {root}")
    return (len(issues) == 0, issues)


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------


def _standards_rows(pack: dict) -> list:
    """Aggregated, de-duplicated standards mapping across all probe records."""
    seen = set()
    for r in pack.get("records", []):
        for tag in r.get("standards", []):
            seen.add(tag)
    return sorted(seen)


def render_markdown(pack: dict) -> str:
    v = pack["verdict"]
    lines = [
        f"# Provar Evidence Pack {pack['pack_id']}",
        "",
        f"- **Target:** `{pack['target'].get('base_url')}` (model `{pack['target'].get('model')}`)",
        f"- **Suite:** {pack['suite']['id']} v{pack['suite']['version']} (`{pack['suite']['content_hash'][:19]}…`)",
        f"- **Run:** {pack['run'].get('started_utc')} → {pack['run'].get('ended_utc')} | concurrency {pack['run'].get('concurrency')}",
        f"- **Tool:** provar {pack['tool']['version']}",
        "",
        "## Verdict",
        "",
        "```",
        v["statement"],
        "```",
        "",
        "## Postmortem",
        "",
        pack["postmortem"]["summary"],
        "",
    ]
    for c in pack["postmortem"]["clusters"]:
        lines += [
            f"### {c['id']} — {c['title']}",
            "",
            f"- **Dimension:** {c['dimension']} | **Category:** {c['category']} | **Penalty:** {c['weighted_penalty']}",
            f"- **Failed probes:** {', '.join(c['probe_ids'])}",
            f"- **Trigger signature:** {c['trigger_signature']}",
            f"- **Root-cause hypothesis:** {c['root_cause_hypothesis']}",
            f"- **Remediation:** {c['remediation']}",
            f"- **Regression set:** re-run {', '.join(c['regression_probes'])} after the fix",
            "",
        ]
        if c.get("exemplar"):
            ex = c["exemplar"]
            lines += [
                f"**Exemplar ({ex['probe_id']})**",
                "",
                "> **Prompt:** " + ex["prompt"].replace("\n", " ")[:300],
                ">",
                "> **Response:** " + ex["response"].replace("\n", " ")[:300],
                "",
            ]
    lines += [
        "## Standards coverage",
        "",
        "Every probe carries at least one control tag; aggregated mapping for this run:",
        "",
    ]
    for tag in _standards_rows(pack):
        lines.append(f"- `{tag}` — {VOCAB.get(tag, 'control tag')}")
    lines += [
        "",
        "## Integrity",
        "",
        f"- chain: `{pack['integrity']['chain_rule']}`",
        f"- chain_root: `{pack['integrity']['chain_root']}`",
        f"- records: {pack['integrity']['record_count']}",
        "",
        "_Behavioral assurance snapshot generated by Provar. Not a regulatory certification._",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML report card (standalone, print-ready)
# ---------------------------------------------------------------------------

_CSS = """
:root{--ink:#0f172a;--muted:#64748b;--line:#e2e8f0;--bg:#f8fafc;--card:#ffffff;
--green:#15803d;--amber:#b45309;--red:#b91c1c;--blue:#1d4ed8}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',system-ui,-apple-system,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--ink);line-height:1.55}
.wrap{max-width:960px;margin:0 auto;padding:32px 20px}
header.hero{background:#0b1220;color:#f1f5f9;border-radius:14px;padding:28px 32px;margin-bottom:24px}
header.hero .brand{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:#94a3b8}
header.hero h1{font-size:30px;margin:6px 0 2px}
header.hero .sub{color:#cbd5e1;font-size:14px}
.verdict-band{display:flex;gap:24px;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:22px 28px;margin-bottom:20px;flex-wrap:wrap}
.grade-letter{font-size:64px;font-weight:800;line-height:1}
.grade-A,.grade-B{color:var(--green)} .grade-C,.grade-D{color:var(--amber)} .grade-F{color:var(--red)}
.chip{display:inline-block;padding:6px 14px;border-radius:999px;font-weight:700;font-size:13px;letter-spacing:.06em}
.chip-CERTIFIED_PASS{background:#dcfce7;color:var(--green)}
.chip-CONDITIONAL_PASS{background:#fef3c7;color:var(--amber)}
.chip-REMEDIATE_BEFORE_DEPLOY{background:#ffedd5;color:var(--amber)}
.chip-BLOCK_FOR_DEPLOYMENT{background:#fee2e2;color:var(--red)}
.statement{background:#0b1220;color:#e2e8f0;border-radius:12px;padding:16px 20px;font-family:Consolas,Menlo,monospace;font-size:12.5px;white-space:pre-wrap;margin:14px 0 20px}
section{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:22px 26px;margin-bottom:20px}
h2{font-size:18px;margin-bottom:14px}
h3{font-size:15px;margin:16px 0 8px}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th{text-align:left;color:var(--muted);font-weight:600;border-bottom:2px solid var(--line);padding:8px 10px}
td{border-bottom:1px solid var(--line);padding:9px 10px;vertical-align:top}
.bar{height:10px;border-radius:6px;background:#e2e8f0;overflow:hidden;min-width:120px}
.bar>span{display:block;height:100%;border-radius:6px}
.sA{background:#16a34a}.sB{background:#65a30d}.sC{background:#d97706}.sD{background:#ea580c}.sF{background:#dc2626}
.muted{color:var(--muted);font-size:12.5px}
.pill{font-size:11.5px;padding:2px 9px;border-radius:999px;background:#f1f5f9;border:1px solid var(--line)}
.quote{background:#f8fafc;border-left:3px solid #cbd5e1;padding:8px 12px;margin:8px 0;border-radius:0 8px 8px 0;font-size:12.5px}
footer{color:var(--muted);font-size:12px;margin-top:8px;text-align:center}
code{background:#f1f5f9;border-radius:4px;padding:1px 5px;font-size:.92em}
@media print{body{background:#fff}.wrap{padding:0}}
"""


def _bar(score: float, grade: str) -> str:
    return f'<div class="bar"><span class="s{grade}" style="width:{max(2, min(100, score))}%"></span></div>'


def render_html(pack: dict) -> str:
    v = pack["verdict"]
    e = html.escape
    dims = sorted(v["dimensions"], key=lambda d: -d["total"])
    dim_rows = "".join(
        f"<tr><td><b>{e(d['name'])}</b></td>"
        f"<td>{d['score']:.0f}/100 <b class='grade-{d['grade']}'>{d['grade']}</b></td>"
        f"<td>{_bar(d['score'], d['grade'])}</td>"
        f"<td>{d['failed']}/{d['total']} failed"
        + (f" <span class='pill'>{e(', '.join(d['fail_ids'][:5]))}</span>" if d["fail_ids"] else "")
        + (f"<br><span class='muted'>{d['errored']} errored</span>" if d.get("errored") else "")
        + "</td></tr>"
        for d in dims
    )
    clusters = ""
    for c in pack["postmortem"]["clusters"]:
        ex = c.get("exemplar") or {}
        clusters += (
            f"<section><h3>{e(c['id'])} — {e(c['title'])}</h3>"
            f"<p class='muted'>dimension <b>{e(c['dimension'])}</b> · category <b>{e(c['category'])}</b> · "
            f"penalty {c['weighted_penalty']} · probes {e(', '.join(c['probe_ids']))}</p>"
            f"<p><b>Trigger signature:</b> {e(c['trigger_signature'])}</p>"
            f"<p><b>Root-cause hypothesis:</b> {e(c['root_cause_hypothesis'])}</p>"
            f"<p><b>Remediation:</b> {e(c['remediation'])}</p>"
            f"<p class='muted'>Regression set: re-run {e(', '.join(c['regression_probes']))} after the fix.</p>"
            + (
                f"<div class='quote'><b>Exemplar ({e(ex.get('probe_id',''))})</b><br>"
                f"<b>Prompt:</b> {e(ex.get('prompt','')[:280])}<br>"
                f"<b>Response:</b> {e(ex.get('response','')[:280])}</div>"
                if ex
                else ""
            )
            + "</section>"
        )
    clean = "".join(
        f"<tr><td><code>{e(r['probe_id'])}</code></td><td>{e(r['category'])}</td>"
        f"<td>{e(r['severity'])}</td><td><b>{e(r['verdict'])}</b></td><td>{e(r['detail'][:180])}</td></tr>"
        for r in pack["records"] if r["verdict"] == "fail"
    ) or "<tr><td colspan='5' class='muted'>No failed probes.</td></tr>"

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Provar Evidence Pack {e(pack['pack_id'])}</title><style>{_CSS}</style></head>
<body><div class="wrap">
<header class="hero">
  <div class="brand">PROVAR · EVIDENCE PACK {e(pack['pack_id'])}</div>
  <h1>Postmortem &amp; Verdict Report</h1>
  <div class="sub">target <code>{e(str(pack['target'].get('base_url')))}</code> · model <code>{e(str(pack['target'].get('model')))}</code> ·
  suite {e(pack['suite']['id'])} v{e(pack['suite']['version'])} · {e(pack['created_utc'])}</div>
</header>
<div class="verdict-band">
  <div class="grade-letter grade-{v['overall_grade']}">{v['overall_grade']}</div>
  <div>
    <span class="chip chip-{e(v['verdict'])}">{e(v['verdict'].replace('_', ' '))}</span>
    <div style="margin-top:8px" class="muted">{v['failed']} failed · {v['errored']} errored · {v['total']} probes ·
    severity-weighted {v['fail_weight']:.0f}/{v['total_weight']:.0f}</div>
  </div>
</div>
<div class="statement">{e(v['statement'])}</div>
<section><h2>Dimension scores</h2><table>
<tr><th>Dimension</th><th>Score</th><th></th><th>Failures</th></tr>{dim_rows}</table></section>
<h2 style="margin:18px 4px">Postmortem</h2>
<p style="margin:0 4px 14px">{e(pack['postmortem']['summary'])}</p>
{clusters}
<section><h2>Failed probes (verbatim register)</h2><table>
<tr><th>Probe</th><th>Category</th><th>Severity</th><th>Verdict</th><th>Detail</th></tr>{clean}</table></section>
<section><h2>Integrity</h2>
<table><tr><th>Field</th><th>Value</th></tr>
<tr><td>Chain rule</td><td><code>{e(pack['integrity']['chain_rule'])}</code></td></tr>
<tr><td>Chain root</td><td><code>{e(pack['integrity']['chain_root'])}</code></td></tr>
<tr><td>Suite hash</td><td><code>{e(pack['suite']['content_hash'])}</code></td></tr>
<tr><td>Records</td><td>{pack['integrity']['record_count']}</td></tr>
<tr><td>Judges</td><td>Deterministic only (no LLM judge) — transcripts are ground truth</td></tr>
<tr><td>Standards mapped</td><td>{e(' · '.join(_standards_rows(pack))) or '—'}</td></tr>
</table></section>
<footer>Generated by Provar {e(pack['tool']['version'])} · Behavioral assurance snapshot — not a regulatory certification ·
Verify with <code>provar verify</code></footer>
</div></body></html>"""


def write_pack_outputs(pack: dict, out_dir: str | Path) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pid = pack["pack_id"]
    paths = {
        "json": out / f"{pid}.json",
        "md": out / f"{pid}_report.md",
        "html": out / f"{pid}_report.html",
    }
    paths["json"].write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf-8")
    paths["md"].write_text(render_markdown(pack), encoding="utf-8")
    paths["html"].write_text(render_html(pack), encoding="utf-8")
    return paths
