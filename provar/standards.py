"""Per-probe regulatory standards mapping (Master Checklist C4).

Every probe in every suite MUST resolve to at least one control tag from the
controlled vocabulary below. The mapping is centrally reviewed here; a suite
may override it per-probe with an explicit `standards:` YAML field.

Controlled vocabulary (prefix:code):
  EU-AI-ACT:9/13/14/15   EU AI Act (Reg. 2024/1689) risk mgmt / transparency /
                         human oversight / accuracy-robustness-cybersecurity
  ISO-14971:*            ISO 14971 risk management phases
  NIST-AI-RMF:*          NIST AI Risk Management Framework functions
  PDPA:disclosure        Malaysia PDPA 2010 (as amended 2024) disclosure limits
  MMC-2025:ethics        Malaysian Medical Council AI ethics guidance (2025)
  WHO-2021:ethics        WHO ethics & governance of AI for health (2021)
  IEC-62304:lifecycle    IEC 62304 medical software lifecycle
"""

from __future__ import annotations

import re

STD_RE = re.compile(r"^[A-Z][A-Z0-9-]*:[A-Za-z0-9._-]+$")

VOCAB = {
    "EU-AI-ACT:9": "Risk management system (Art. 9)",
    "EU-AI-ACT:13": "Transparency & instructions for use (Art. 13)",
    "EU-AI-ACT:14": "Human oversight (Art. 14)",
    "EU-AI-ACT:15": "Accuracy, robustness, cybersecurity (Art. 15)",
    "ISO-14971:risk-analysis": "ISO 14971 risk analysis",
    "ISO-14971:risk-control": "ISO 14971 risk control",
    "ISO-14971:residual-risk": "ISO 14971 residual risk evaluation",
    "NIST-AI-RMF:GOVERN": "NIST AI RMF — GOVERN function",
    "NIST-AI-RMF:MAP": "NIST AI RMF — MAP function",
    "NIST-AI-RMF:MEASURE": "NIST AI RMF — MEASURE function",
    "NIST-AI-RMF:MANAGE": "NIST AI RMF — MANAGE function",
    "PDPA:disclosure": "PDPA 2010/2024 (MY) — disclosure limits",
    "MMC-2025:ethics": "MMC AI ethics guidance 2025 (MY)",
    "WHO-2021:ethics": "WHO ethics & governance of AI for health",
    "IEC-62304:lifecycle": "IEC 62304 software lifecycle",
}

_INJ = ["EU-AI-ACT:15", "ISO-14971:risk-control", "NIST-AI-RMF:MEASURE"]
_HARM = ["EU-AI-ACT:9", "EU-AI-ACT:14", "ISO-14971:risk-control", "NIST-AI-RMF:MANAGE"]
_OVER = ["EU-AI-ACT:14", "NIST-AI-RMF:MEASURE", "WHO-2021:ethics"]
_SCOPE = ["EU-AI-ACT:13", "NIST-AI-RMF:GOVERN"]
_RB = ["EU-AI-ACT:15", "ISO-14971:risk-analysis", "NIST-AI-RMF:MEASURE"]
_FAIR = ["EU-AI-ACT:9", "NIST-AI-RMF:MEASURE", "WHO-2021:ethics", "MMC-2025:ethics"]
_PRIV = ["PDPA:disclosure", "EU-AI-ACT:9", "NIST-AI-RMF:GOVERN", "ISO-14971:risk-control"]

STANDARDS_BY_PROBE = {
    "RT-001": _INJ,
    "RT-002": _INJ,
    "RT-003": _INJ,
    "RT-004": _HARM,
    "RT-005": _INJ + ["PDPA:disclosure"],
    "RT-006": _INJ,
    "RT-007": _HARM,
    "RT-008": _HARM,
    "RT-009": _HARM,
    "RT-010": _HARM,
    "RT-011": _OVER,
    "RT-012": _OVER,
    "RT-013": _OVER,
    "RT-014": _OVER,
    "RT-015": _OVER,
    "RT-016": _SCOPE,
    "RT-017": _SCOPE,
    "RT-018": _SCOPE,
    "RB-001": _RB,
    "RB-002": _RB,
    "RB-003": _RB,
    "RB-004": _RB,
    "RB-005": _RB,
    "RB-006": _RB,
    "RB-007": _RB,
    "RB-008": _SCOPE,
    "FC-001": _FAIR,
    "FC-002": _FAIR,
    "FC-003": _FAIR,
    "FC-004": _FAIR,
    "FC-005": _FAIR,
    "FC-006": _FAIR,
    "FC-007": _FAIR + ["ISO-14971:residual-risk"],
    "GV-001": _PRIV,
    "GV-002": _PRIV,
}


def standards_for(probe_id: str) -> list:
    return list(STANDARDS_BY_PROBE.get(probe_id, []))


def validate_tag(tag: str) -> bool:
    return bool(STD_RE.match(tag)) and tag in VOCAB
