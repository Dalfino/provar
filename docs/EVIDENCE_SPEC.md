# Evidence Pack Specification (`provar.evidence/0.1`)

An evidence pack is the sealed, machine-verifiable record of one assurance run. It is the
deliverable: the JSON is the evidence, the MD/HTML report cards are projections of it.

## File set

| File | Role |
|---|---|
| `EP-<id>.json` | the pack (single source of truth) |
| `EP-<id>_report.md` | Markdown projection |
| `EP-<id>_report.html` | standalone print-ready verdict report card |

## JSON schema (informative)

```jsonc
{
  "pack_format": "provar.evidence/0.1",
  "pack_id": "EP-001",
  "created_utc": "2026-10-01T12:00:00Z",
  "tool": { "name": "provar", "version": "0.1.0" },
  "target": { "kind": "openai_compat", "base_url": "...", "model": "...",
              "note": "black-box HTTP interface; no auth material recorded" },
  "suite": { "id": "hospital-qa-v1", "version": "0.1.0",
             "content_hash": "sha256:...", "probe_count": 35, "transcript_count": 55 },
  "run": { "started_utc": "...", "ended_utc": "...", "concurrency": 2,
           "judge_policy": "deterministic only", "judge_version": "v0.1" },
  "verdict": {
    "overall_grade": "B", "verdict": "REMEDIATE_BEFORE_DEPLOY",
    "statement": "VERDICT: ...", "gates_triggered": ["..."],
    "failed": 6, "errored": 0, "total": 35,
    "fail_weight": 18, "total_weight": 111, "error_rate": 0.0,
    "dimensions": [ { "name": "safety", "score": 68.4, "grade": "C",
                      "failed": 4, "errored": 0, "total": 10, "fail_ids": ["RT-002"] } ]
  },
  "postmortem": {
    "summary": "...",
    "clusters": [ { "id": "PM-01", "dimension": "safety", "category": "prompt_injection",
                    "title": "...", "probe_ids": ["RT-002","RT-003"],
                    "trigger_signature": "...", "exemplar": { "probe_id": "...",
                    "prompt": "...", "response": "..." },
                    "root_cause_hypothesis": "...", "remediation": "...",
                    "regression_probes": ["RT-002","RT-003"] } ],
    "blind_spots": "...", "confidence_note": "..."
  },
  "records": [
    { "seq": 1, "probe_id": "RT-001", "family": "...", "category": "...",
      "severity": "critical", "dimension": "safety", "suite": {...},
      "verdict": "pass|fail|error", "detail": "...", "findings": [...],
      "latency_ms_total": 0.0,
      "transcripts": [ { "prompt": "...", "response": "...", "latency_ms": 0.0 } ],
      "prev_hash": "sha256:GENESIS", "hash": "sha256:..." }
  ],
  "integrity": {
    "algorithm": "sha256",
    "chain_rule": "hash = sha256(prev_hash + canonical_json(record without 'hash'))",
    "chain_root": "sha256:...", "record_count": 35
  }
}
```

## Chain rules

- Canonical JSON: `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.
- `record.hash = sha256(prev_hash + canonical_json(record minus 'hash' and 'prev_hash'))`
  where `prev_hash` is the previous record's `hash` (`sha256:GENESIS` for seq 1).
- `chain_root = sha256(concat(record.hash in seq order))`.
- `provar verify <pack>` recomputes: prev-hash linkage, per-record content hash, and chain root.
  Any mismatch reports the record index, probe id, and reason; exit code 1.

## What verify proves (and does not)

- **Proves:** the pack content is exactly what the sealing tool computed, record order is
  intact, and no record was added/removed/edited after sealing.
- **Does not prove:** the target's identity (bind later via TLS metadata in v0.2), authorship
  of the pack (detached signatures in v0.2), or that the suite hash corresponds to a suite you
  approved — keep the suite file in version control and record its hash at approval time.
