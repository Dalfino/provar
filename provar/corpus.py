"""Probe corpus loading and validation (see docs/CORPUS_SPEC.md)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .judges import JUDGES

SEVERITIES = {"critical", "major", "minor"}
FAMILIES = {"refusal_traps", "robustness", "fairness_consistency", "privacy"}


@dataclass
class Probe:
    id: str
    family: str
    category: str
    severity: str
    judge: str
    params: dict
    expect: str
    notes: str
    prompt: str | None = None
    variants: list | None = None
    system_preset: str = "base_clinical"

    def transcripts(self) -> list:
        if self.variants:
            return list(self.variants)
        return [self.prompt]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "family": self.family,
            "category": self.category,
            "severity": self.severity,
            "judge": self.judge,
            "params": self.params,
            "expect": self.expect,
            "notes": self.notes,
        }


@dataclass
class Suite:
    id: str
    version: str
    description: str
    system_presets: dict
    probes: list
    content_hash: str = ""

    def transcript_count(self) -> int:
        return sum(len(p.transcripts()) for p in self.probes)


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def load_suite(path: str | Path) -> Suite:
    raw = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError(f"Suite file {path} is not a YAML mapping")

    suite_id = data.get("suite")
    version = str(data.get("version", "0.0.0"))
    if not suite_id:
        raise ValueError("Suite file missing top-level 'suite' id")

    presets = data.get("system_presets") or {}
    if "base_clinical" not in presets:
        raise ValueError("Suite must define a 'base_clinical' system preset")

    probes_raw = data.get("probes") or []
    if not probes_raw:
        raise ValueError("Suite contains no probes")

    probes, seen = [], set()
    for i, p in enumerate(probes_raw):
        where = f"probes[{i}]"
        pid = p.get("id")
        if not pid:
            raise ValueError(f"{where}: missing id")
        if pid in seen:
            raise ValueError(f"{where}: duplicate probe id {pid}")
        seen.add(pid)

        family = p.get("family")
        if family not in FAMILIES:
            raise ValueError(f"{where} ({pid}): unknown family '{family}'")
        severity = p.get("severity")
        if severity not in SEVERITIES:
            raise ValueError(f"{where} ({pid}): severity must be one of {sorted(SEVERITIES)}")
        judge = p.get("judge")
        if not isinstance(judge, dict) or judge.get("name") not in JUDGES:
            raise ValueError(f"{where} ({pid}): judge.name must be one of {sorted(JUDGES)}")
        prompt, variants = p.get("prompt"), p.get("variants")
        if bool(prompt) == bool(variants):
            raise ValueError(f"{where} ({pid}): exactly one of 'prompt' or 'variants' is required")
        if variants and (not isinstance(variants, list) or len(variants) < 2):
            raise ValueError(f"{where} ({pid}): 'variants' must be a list of >= 2 prompts")

        probes.append(
            Probe(
                id=pid,
                family=family,
                category=p.get("category", "uncategorized"),
                severity=severity,
                judge=judge["name"],
                params=judge.get("params") or {},
                expect=p.get("expect", ""),
                notes=p.get("notes", ""),
                prompt=prompt,
                variants=variants,
                system_preset=p.get("system_preset", "base_clinical"),
            )
        )

    for p in probes:
        if p.system_preset not in presets:
            raise ValueError(f"probe {p.id}: unknown system_preset '{p.system_preset}'")

    content_hash = "sha256:" + hashlib.sha256(_canonical(data).encode("utf-8")).hexdigest()

    return Suite(
        id=suite_id,
        version=version,
        description=data.get("description", ""),
        system_presets=presets,
        probes=probes,
        content_hash=content_hash,
    )
