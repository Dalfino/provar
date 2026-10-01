# ADR-0001: Black-box probing only — no source, no weights, no PHI

Status: Accepted · Date: 2026-10-01 · Deciders: Provar core team

## Context

Hospital AI assurance efforts split into three camps: benchmark leaderboards (measure base
models in labs), open-model evals (require weights), and white-box audits (require source and
infrastructure access). None of them measure the composed deployment a hospital actually
operates. Meanwhile hospitals cannot share source code, weights, or patient data with
third-party auditors, and AI vendors resist giving auditors anything internal.

## Decision

Provar audits **deployed systems through their public serving interface only**: an
OpenAI-compatible chat completions endpoint. Probes are synthetic text. No model weights, no
training data, no source code, no PHI are required — or accepted — anywhere in the pipeline.

## Consequences

- Any vendor system can be audited by pointing Provar at an endpoint + auth token. This makes
  procurement-time assurance possible ("prove it before we buy it").
- Findings are behavioral, not mechanistic: we can *prove* a failure occurred and precisely
  characterize its trigger, but not its internal cause. The postmortem engine therefore emits
  root-cause **hypotheses** with remediation, not claims about internals.
- Repeatability across deployments of the same model is meaningful: score deltas localize
  failures to the wrapper layer (retrieval, prompts, rendering) rather than the model.
- White-box evidence (weights, config) can complement packs later as an opt-in annex; it is
  never a requirement for a verdict.
