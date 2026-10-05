# Changelog

All notable changes to Provar are documented here. Format: Keep a Changelog 1.1;
SemVer for the package and the pack format (`provar.evidence/x.y`).

## [0.2.0] — 2026-10-05

### Added
- Governance document suite (`docs/briefs/`, v0.1-2 builds): CCOO Brief, Board Assurance
  Paper, IT Readiness & Infrastructure Design, Cross-Cutting Assurance Dossier, and the QA
  Verdict Report — the evidence pack for the document set itself.
- Cross-document traceability maps (Dossier Appendix A): each assurance question routed to the
  sections that answer it across all four documents; each evidence artefact routed to the
  go/no-go gate that consumes it.
- Per-document Document Control sections: version history, role-based review and approval,
  custody and review cadence.
- IT readiness test catalogue upgraded to the mandated metric column set (adds Baseline and
  Owner columns; baselines honestly recorded as "not yet run" pre-G1).
- Machine-readable suite QA verdicts: `docs/briefs/qa_verdicts_v0.1-2.json`.

### Verified
- Suite QA (2026-10-05): layout postcheck 36/36 (0 errors, 0 warnings across 5 documents);
  content audit 24/24 GREEN — 216 explicit placeholders, 87 basis tags, zero sloppy
  placeholders, zero absolute security/safety claims.
- Harness: 27/27 offline tests pass; CI success on `main` (`4d7eb3c`).

## [0.1.0] — 2026-10-01

### Added
- Black-box target client: OpenAI-compatible `chat/completions`, rate-limit-aware
  exponential backoff, env-var auth references, `EchoTarget` test fixture (ADR-0004).
- Suite/corpus system: strict YAML validation, `system_presets`, prompt/variant probes,
  suite content hashing (docs/CORPUS_SPEC.md).
- `hospital-qa-v1` suite: 35 probes / 55 transcripts — refusal traps (injection canaries,
  harmful-compliance rubber-stamps, over-refusal, scope discipline), robustness (typo,
  paraphrase, distractor, format stress), fairness & consistency (demographic counterfactuals,
  role framing, register), privacy (PHI echo).
- Deterministic judge registry (7 judges) — reproducible evidence, no LLM judge (ADR-0002).
- Async runner: bounded concurrency, per-probe isolation, `pass|fail|error` taxonomy.
- Verdict engine: 5 dimensions × severity weights (5/3/1), A–F grades,
  floor/ceiling governance gates, numeric verdict statement (ADR-0002).
- Postmortem engine: failure clusters with trigger signatures, root-cause hypotheses,
  remediation guidance, and regression probe sets.
- Evidence pack `provar.evidence/0.1`: SHA-256 record chain, chain root, self-verify,
  `provar verify` with tamper localization (ADR-0003).
- Renderers: Markdown + standalone HTML verdict report card.
- CLI: `provar run`, `provar postmortem`, `provar verify`.
- Demo: `target_hospital_qa` (retrieval + LLM + rendering wrapper with documented
  misconfigurations) and live Evidence Pack 001.
- Test suite: 25 tests, fully offline.
- Governance docs: ADR-0001…0004, CORPUS_SPEC, EVIDENCE_SPEC, ROADMAP, SECURITY.
