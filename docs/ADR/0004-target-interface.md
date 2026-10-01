# ADR-0004: Target interface — OpenAI-compatible chat completions

Status: Accepted · Date: 2026-10-01 · Deciders: Provar core team

## Context

"Postmortem on every product in the world" (the founding requirement) demands a universal
target interface. De-facto, the industry has converged: vLLM, Ollama, TGI, LiteLLM, Azure
OpenAI, AWS Bedrock adapters, and most hospital wrapper stacks either expose or can front an
OpenAI-compatible `POST /chat/completions`.

## Decision

v0.1 supports exactly one target kind: `openai_compat`. The harness sends
`{model, messages:[{role:"system"},{role:"user"}], temperature}` and reads
`choices[0].message.content`. The system message from the suite is sent verbatim; the target's
own wrapper (retrieval, guardrails, policy) composes with it — **that composition is precisely
the artifact under audit**.

Operational requirements bundled into the client:

- Retries with **rate-limit-aware exponential backoff** (429 direct or wrapped in gateway 5xx),
  jittered — hospital-adjacent upstreams throttle.
- Per-request timeout, transport errors degrade to probe-level `error` outcomes, never
  run-level crashes.
- Auth via environment variable reference (`api_key_env`) only; no secrets in configs, logs,
  or packs.

## Consequences

- Any product exposing this interface — including multi-tenant vendor APIs — is auditable
  today with zero integration work. That is the "every product" clause.
- Non-chat surfaces (embeddings, vision, agents with tools) need new kinds
  (`openai_compat_vision`, `agent_loop`) — clean future work behind the same `TargetResult`
  contract.
- Some vendors' gateways strip system messages or inject their own; Provar records the raw
  transcripts, so such wrapper behavior shows up as anomalies in the pack instead of
  silently corrupting results.
