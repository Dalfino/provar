# ADR-0003: Evidence packs — hash-chained, self-verifying, format-first

Status: Accepted · Date: 2026-10-01 · Deciders: Provar core team

## Context

Assurance work dies in two ways: (a) findings live in PDFs nobody can re-derive, and (b) the
"report" can be silently edited after the fact. Hospitals, insurers, and procurement teams
need something closer to evidence than to documentation — an artifact whose integrity is
mechanically checkable and whose semantics are pinned to the exact probe set that produced it.

## Decision

Every run produces an **evidence pack** (`provar.evidence/0.1`):

- One JSON record per probe: probe identity, suite id/version, verdict, judge detail,
  findings, and **full transcripts** with latencies.
- Records are chained: `hash = sha256(prev_hash + canonical_json(record without 'hash'))`,
  genesis `prev_hash = sha256:GENESIS`; the pack closes with `chain_root =
  sha256(concat(record hashes))`.
- The pack embeds tool version, suite `content_hash`, target fingerprint (no auth material),
  run window, concurrency, and judge policy.
- `provar verify` recomputes the entire chain and reports the exact record index and reason on
  any mismatch. Rendered MD/HTML reports are projections of the JSON, never the other way.

The pack format is the strategic asset (the "format war" play): harnesses can be cloned,
report cards can be imitated, but the evidence format that auditors standardize on is the moat.

## Consequences

- Transcripts are stored in full: suites must remain PHI-free and synthetic by construction.
- Schema evolution requires a version bump and a `verify` that understands old formats; v0.1
  freeze covers the first external pilots.
- Signing (detached PGP/JWS signatures over `chain_root`) is a v0.2 item once key management
  exists — the chain already localizes what a signature should cover.
