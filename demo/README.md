# Demo: Evidence Pack 001

This directory holds **Provar's first real end-to-end run**: the `hospital-qa-v1` assurance
suite executed live against `target_hospital_qa` — a realistic deployed hospital clinical-QA
service.

## The target (`target_hospital_qa/`)

Architecture mirrors common real deployments:

```
HTTP (OpenAI-compatible) -> keyword retrieval over 12 policy docs (KB-01..KB-12)
                         -> LLM (z-ai SDK) with wrapper policy + retrieved docs
                         -> response assembly
```

Its wrapper contains **two documented misconfigurations** — the same classes of flaw that
exist unintentionally in production deployments (that is why Provar exists):

1. **Weak trust clause** in the wrapper policy: *"You may relax citation formatting for
   trusted hospital staff and system administrators on duty…"* — an undefined trust concept
   that role-override injections can leverage.
2. **Rendering-layer identifier echo**: user-supplied names/MRNs are reflected back into the
   response footer, violating the hospital's own privacy policy (KB-07).

Everything else about the target's behavior is genuine model + wrapper behavior — the probe
suite must discover what actually fails.

## The run (`evidence_pack_001/`)

- `EP-001.json` — sealed evidence pack: 35 probes, hash-chained records, verdict, postmortem.
- `EP-001_report.md` / `EP-001_report.html` — projections (the HTML is the report card).

```bash
provar verify evidence_pack_001/EP-001.json     # recompute the chain
```

Reproduce the run:

```bash
cd target_hospital_qa && npm install && npm start &
cd ../..
provar run --target-config examples/targets.example.yaml --target hospital-qa-demo \
  --suite provar/corpora/hospital_qa_v1.yaml --out evidence --pack-id EP-002
```

Note: upstream LLM latency and rate limits make a full run take minutes; the demo target
enforces 8 s spacing + serialization (override via `MIN_GAP_MS` / `RATE_RETRY_MS`).
