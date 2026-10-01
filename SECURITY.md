# Security Policy

## Reporting

Report vulnerabilities to the maintainers via GitHub Security Advisories
("Report a vulnerability" on the repository). Do not open public issues for
exploitable behavior. Expect acknowledgment within 72 hours; fixes or
mitigations within 30 days for high-severity findings.

## Scope

In scope: the `provar` package (parsing, judging, evidence sealing, CLI), the
evidence pack format and its verification, and the demo target.

Out of scope: the systems you point Provar at. Auditing targets you do not own
or lack authorization to test is unlawful in most jurisdictions. Provar is a
tool for authorized assurance — keep target configs inside your authorization
boundary.

## Data-handling principles (enforced by design)

1. **No PHI, ever.** Corpora are synthetic. Evidence packs store full
   transcripts by design — if you probe a system with real identifiers, they
   will be recorded. That is a deployment-policy failure, not a Provar one.
2. **No secrets in artifacts.** Target auth is referenced by environment
   variable name (`api_key_env`) and resolved at runtime; tokens are never
   written to configs, packs, logs, or stack traces.
3. **Tamper-evidence.** Records are hash-chained; `provar verify` detects any
   post-seal modification and localizes it to a record index.
4. **Fail-safe scoring.** Transport errors and judge exceptions become
   `error` outcomes — they never crash a run and never count as product
   failures; degraded runs cannot produce `CERTIFIED_PASS`.

## Hardening guidance for deployments

- Run probes from a dedicated audit network segment; treat probe traffic as
  legitimate load (the demo target enforces 8 s spacing + serialization for
  rate-limited upstreams).
- Restrict who can write suites: probes are executable expectations — a
  malicious suite can exfiltrate whatever the target echoes into a pack.
  Review suite diffs like code.
- Keep evidence packs access-controlled: they contain the full transcript of
  your system's worst behavior, which is exactly what an attacker wants.
