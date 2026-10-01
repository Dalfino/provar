# Roadmap

## v0.1 — Foundation (shipped)

- [x] Black-box target client (OpenAI-compatible) with rate-limit-aware backoff
- [x] Suite/corpus loader with strict validation + content hashing
- [x] `hospital-qa-v1` corpus: 35 probes / 55 transcripts across 4 families
- [x] 7 deterministic judges (refusal, citation contract, canary, safety-guard, PHI, consistency)
- [x] Async runner with per-probe isolation, retries, error taxonomy
- [x] Verdict engine: severity weights, A–F grades, floor/ceiling governance gates
- [x] Postmortem engine: clusters, trigger signatures, root-cause hypotheses, remediation, regression sets
- [x] Evidence pack `provar.evidence/0.1`: SHA-256 chain + `provar verify`
- [x] Report cards (MD + standalone HTML)
- [x] Demo: `target_hospital_qa` service + live Evidence Pack 001
- [x] 25-test suite, fully offline

## v0.2 — Trust & breadth (next)

- [ ] Detached signatures over `chain_root` (PGP or JWS) + key publication
- [ ] `--baseline` mode: diff a run against a prior pack, emit delta verdict (regression gate)
- [ ] CI mode: exit non-zero on verdict worse than policy threshold (`--max-verdict CONDITIONAL_PASS`)
- [ ] LLM-judge as opt-in, clearly-labeled annex (never in the sealed verdict)
- [ ] Multi-turn probes (conversation-level traps, drift across turns)
- [ ] Second suite: `triage-chat-v1` (symptom-collection bots)
- [ ] Target kinds: `openai_compat_vision`, `agent_loop` (tool-calling systems)

## v0.3 — Operations

- [ ] GitHub Action / container for scheduled assurance runs
- [ ] `provar serve`: local dashboard of pack history and dimension trends
- [ ] SARIF export for security dashboards
- [ ] Enterprise pack format: industry-specific corpora (imaging, pathology, documentation)

## v1.0 — The assurance layer

- [ ] Signed pack registry (append-only, organization-scoped)
- [ ] Procurement mode: vendor-submitted packs + buyer-side re-verification
- [ ] Continuous assurance: scheduled probes on production traffic patterns (synthetic always)
- [ ] Verdict API for release pipelines (deploy gate as code)

## Non-goals

- Clinical validation of medical devices (that is MDR/FDA territory, not ours)
- Training-data or weight inspection (ADR-0001: black-box only)
- Real patient data anywhere in the pipeline — synthetic corpora forever
