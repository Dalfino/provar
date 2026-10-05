# Provar Master Checklist — Deployable, Commercial-Grade, Rare, All-Green

> The single source of truth for "is this thing ready?" Every item is machine-verified by
> [`qa/scorecard.py`](../qa/scorecard.py) (run `python qa/scorecard.py`). A release is only
> allowed when all 36 items report **GREEN**. The scorecard is the instrument; this document
> is the contract. Items are re-checked on every commit in CI.

**Legend:** instrument = how the verdict is produced, not by opinion. GREEN / AMBER / RED follow
the same discipline as our evidence packs: a claim without a verifier is not green, it is noise.

---

## Pillar A — Deployability (9 items)

| ID | Target | Verification instrument |
|----|--------|-------------------------|
| A1 | Clean install: `pip install -e ".[dev]"` exits 0, `provar --version` works | scorecard exec + exit code |
| A2 | One-command **offline** demo: `provar demo` → evidence pack, `CERTIFIED_PASS`, no network, no Node | scorecard exec + pack inspection |
| A3 | CLI surface complete: `run`, `demo`, `verify`, `postmortem`, `--version`, useful `--help` | scorecard exec of each command |
| A4 | CI matrix on Python 3.10 / 3.11 / 3.12 | CI workflow parse + remote run |
| A5 | Runtime dependencies ≤ 3, floor-pinned (aiohttp, PyYAML) | pyproject parse |
| A6 | Docker: `Dockerfile` present, `provar demo` as default entrypoint | file check + docker ignore hygiene |
| A7 | Exit-code contract: `0` = green/conditional, `1` = remediate, `3` = block, `2` = config error — documented in README & `--help` | scorecard exec of scripted run |
| A8 | Targets configured via YAML; auth only via environment variable name (`api_key_env`), never literals | config parse + secret scan |
| A9 | CI YAML is valid (parses, triggers on `main` + PRs) | YAML parse of workflow |

## Pillar B — Commercial-standard quality (11 items)

| ID | Target | Verification instrument |
|----|--------|-------------------------|
| B1 | README: positioning, honest limitations, quickstart incl. offline path, exit-code table | content check |
| B2 | LICENSE present (MIT) | file check |
| B3 | Version single-source discipline: `pyproject.toml` == `provar/__init__.py` == CHANGELOG head | parse + compare |
| B4 | ARCHITECTURE.md + ≥ 4 ADRs | file checks |
| B5 | Specs: CORPUS_SPEC + EVIDENCE_SPEC + verdict model documented (ADR-0002) | file checks |
| B6 | SECURITY.md with disclosure policy + no-PHI design note | file check |
| B7 | Test suite ≥ 40 tests, 100% pass, fully offline | `pytest -q` exec |
| B8 | `py.typed` shipped; public API annotated | file check |
| B9 | Secret scan clean: no `github_pat_`, `ghp_`, `sk-`, `AKIA` patterns in tracked files | regex walk |
| B10 | No real PHI anywhere: corpus is synthetic (spec + corpus header assert it) | corpus load + spec check |
| B11 | ROADMAP.md with honest status markers (shipped / in-progress / future) | file check |

## Pillar C — Competitive rarity (8 items)

What makes Provar rare is not any single feature — it is that all eight hold **simultaneously,
in one open-core harness**. Generic red-team scanners have (1)–(2) at best; LLM-eval platforms
lose (1) and (3); MLOps monitors have none of (4)–(7).

| ID | Target | Verification instrument |
|----|--------|-------------------------|
| C1 | **Deterministic judges only** — no LLM-as-judge anywhere in the verdict path; every finding reproducible from recorded transcripts | judges module audit + ADR-0002 |
| C2 | **Hash-chained evidence**: `hash = sha256(prev_hash + canonical_json(record))`, chain root, `provar verify` pinpoints tampering (index + reason) | verify on pristine + tampered pack (tests) |
| C3 | **Verdict reproducibility**: identical transcripts → identical chain_root | two-run test on deterministic target |
| C4 | **Per-probe standards mapping**: 100% of probes carry ≥ 1 control tag (EU AI Act, ISO 14971, NIST AI RMF, PDPA, MMC, WHO) | corpus validation |
| C5 | **Refusal-balance coverage**: both under-refusal (safety traps) and over-refusal (benign-but-must-answer) families | corpus family check |
| C6 | **Demographic counterfactual fairness** with deterministic parity judging | corpus + judge check |
| C7 | **Postmortem engine**: failure clustering with root-cause hypothesis, remediation, and regression set per cluster | postmortem output check |
| C8 | **Severity-weighted gates with floors/ceilings**: ≥2 critical safety fails → BLOCK floor regardless of score; usability-only failures → CONDITIONAL ceiling | scoring unit tests |

## Pillar D — Green verdicts in all aspects (8 items)

| ID | Target | Verification instrument |
|----|--------|-------------------------|
| D1 | pytest: all tests pass | `pytest -q` |
| D2 | Offline demo pack: `CERTIFIED_PASS`, 0 failed, chain self-verify OK | `provar demo` exec + pack |
| D3 | **Negative demo**: planted failures are detected — verdict degrades to REMEDIATE/BLOCK (proves no rubber-stamping) | `provar demo --negative` exec |
| D4 | EP-001 (live hospital-qa run): chain verifies; `REMEDIATE_BEFORE_DEPLOY` verdict stands as detection evidence | `provar verify` on committed pack |
| D5 | Corpus validates: ≥ 35 probes / ≥ 55 transcripts, unique ids, schema-clean, all standards-tagged | `load_suite` validation |
| D6 | Scorecard itself: **36/36 GREEN**, exit 0 | `python qa/scorecard.py` |
| D7 | Remote CI green on `main` after push | GitHub Actions status |
| D8 | Governance document suite: 36/36 layout postchecks + 24/24 content-audit checks stay green | `docs/briefs/qa_verdicts_v0.1-2.json` |

---

## What GREEN does *not* mean (honesty clause)

- D2/D6 certify **the harness and this repository**, not any real hospital AI system.
- A real deployment's verdict comes from `provar run` against *that* system — that is the product.
- EP-001's `REMEDIATE_BEFORE_DEPLOY` is intentionally green-as-evidence: the engine detects
  real misconfigurations instead of flattering the demo target.
- Behavioral snapshot ≠ regulatory certification. See README "Honest limitations".

## Change discipline

- Any new feature must add or update a checklist row + scorecard check in the same PR.
- Scorecard exit code gates releases; a red item blocks the tag.
- Checklist edits require a CHANGELOG entry under the release that ships them.
