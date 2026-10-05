"""Async probe runner: expands suites into transcripts, calls the target,
applies deterministic judges, and records tamper-evident outcomes."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from .corpus import Probe, Suite
from .judges import JUDGES
from .target import OpenAICompatTarget

DIMENSION_BY_CATEGORY = {
    "prompt_injection": "safety",
    "harmful_compliance": "safety",
    "overrefusal": "refusal_calibration",
    "scope_discipline": "refusal_calibration",
    "typo": "robustness",
    "paraphrase": "robustness",
    "distractor": "robustness",
    "format_stress": "robustness",
    "demographic_swap": "fairness",
    "role_framing": "fairness",
    "register": "fairness",
    "phi_handling": "governance",
}


def dimension_for(probe: Probe) -> str:
    return DIMENSION_BY_CATEGORY.get(probe.category, "safety")


@dataclass
class Transcript:
    prompt: str
    response: str
    latency_ms: float = 0.0
    error: str | None = None


@dataclass
class ProbeOutcome:
    seq: int
    probe: Probe
    dimension: str
    verdict: str  # pass | fail | error
    detail: str
    findings: list = field(default_factory=list)
    transcripts: list = field(default_factory=list)
    latency_ms_total: float = 0.0

    def to_record(self, suite_id: str, suite_version: str) -> dict:
        return {
            "seq": self.seq,
            "probe_id": self.probe.id,
            "family": self.probe.family,
            "category": self.probe.category,
            "severity": self.probe.severity,
            "dimension": self.dimension,
            "suite": {"id": suite_id, "version": suite_version},
            "verdict": self.verdict,
            "detail": self.detail,
            "findings": self.findings,
            "standards": list(self.probe.standards),
            "latency_ms_total": round(self.latency_ms_total, 1),
            "transcripts": [
                {
                    "prompt": t.prompt,
                    "response": t.response,
                    "latency_ms": round(t.latency_ms, 1),
                    **({"error": t.error} if t.error else {}),
                }
                for t in self.transcripts
            ],
        }


async def _run_probe(probe: Probe, system: str, target, sem: asyncio.Semaphore) -> ProbeOutcome:
    async with sem:
        transcripts: list = []
        for user_prompt in probe.transcripts():
            result = await target.complete(system, user_prompt, probe_id=probe.id)
            transcripts.append(
                Transcript(
                    prompt=user_prompt,
                    response=result.text,
                    latency_ms=result.latency_ms,
                    error=result.error,
                )
            )
        latency_total = sum(t.latency_ms for t in transcripts)
        errors = [t.error for t in transcripts if t.error]
        if errors and all(errors):
            return ProbeOutcome(
                seq=0,
                probe=probe,
                dimension=dimension_for(probe),
                verdict="error",
                detail=f"target unreachable after retries: {errors[0]}",
                transcripts=transcripts,
                latency_ms_total=latency_total,
            )
        texts = [t.response for t in transcripts]
        judge_fn = JUDGES[probe.judge]
        try:
            res = judge_fn(texts, probe.params)
        except Exception as exc:  # judge bug must never crash the run
            return ProbeOutcome(
                seq=0,
                probe=probe,
                dimension=dimension_for(probe),
                verdict="error",
                detail=f"judge raised: {type(exc).__name__}: {exc}",
                transcripts=transcripts,
                latency_ms_total=latency_total,
            )
        return ProbeOutcome(
            seq=0,
            probe=probe,
            dimension=dimension_for(probe),
            verdict="pass" if res.passed else "fail",
            detail=res.detail,
            findings=res.findings,
            transcripts=transcripts,
            latency_ms_total=latency_total,
        )


async def run_suite(
    suite: Suite,
    target,
    concurrency: int = 3,
    progress_cb=None,
) -> list:
    sem = asyncio.Semaphore(max(1, concurrency))
    tasks = [
        asyncio.create_task(_run_probe(p, suite.system_presets[p.system_preset], target, sem))
        for p in suite.probes
    ]
    outcomes = []
    done_count = 0
    for coro in asyncio.as_completed(tasks):
        outcome = await coro
        outcomes.append(outcome)
        done_count += 1
        if progress_cb:
            progress_cb(done_count, len(tasks), outcome)
    outcomes.sort(key=lambda o: o.probe.id)
    for i, o in enumerate(outcomes, start=1):
        o.seq = i
    return outcomes
