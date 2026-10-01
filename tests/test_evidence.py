import json

from provar.corpus import Probe
from provar.evidence import build_pack, canonical_json, verify_pack
from provar.runner import ProbeOutcome
from provar.scoring import score_run


def mk_outcome(seq, pid, verdict="pass", severity="major", category="paraphrase", detail=""):
    p = Probe(id=pid, family="robustness", category=category, severity=severity,
              judge="variants_consistent", params={}, expect="", notes="", prompt="p")
    o = ProbeOutcome(seq=seq, probe=p, dimension="robustness", verdict=verdict,
                     detail=detail, transcripts=[])
    return o


def make_pack(tmp_path):
    outcomes = [mk_outcome(1, "RB-001", "pass"),
                mk_outcome(2, "RB-002", "fail", detail="expected class CITED; got REFUSED")]
    suite_stub = type("S", (), {})()
    suite_stub.id = "hospital-qa-v1"
    suite_stub.version = "0.1.0"
    suite_stub.content_hash = "sha256:test"
    suite_stub.probes = [o.probe for o in outcomes]

    def transcript_count():
        return 2
    suite_stub.transcript_count = transcript_count

    sc = score_run(outcomes)
    pm = {"summary": "s", "clusters": [], "blind_spots": "b", "confidence_note": "c"}
    pack = build_pack("EP-TEST", suite_stub, {"base_url": "http://x", "model": "m"},
                      outcomes, sc, pm, {"started_utc": "t0", "ended_utc": "t1"})
    return pack, outcomes, sc


def test_pack_chain_verifies(tmp_path):
    pack, _, _ = make_pack(tmp_path)
    ok, issues = verify_pack(pack)
    assert ok, issues
    assert pack["integrity"]["record_count"] == 2
    assert pack["integrity"]["chain_root"].startswith("sha256:")


def test_tamper_detection_record_content(tmp_path):
    pack, _, _ = make_pack(tmp_path)
    pack["records"][1]["detail"] = "totally different story"
    ok, issues = verify_pack(pack)
    assert not ok
    assert any("RB-002" in i and "modified" in i for i in issues)


def test_tamper_detection_chain_root(tmp_path):
    pack, _, _ = make_pack(tmp_path)
    pack["integrity"]["chain_root"] = "sha256:fake"
    ok, issues = verify_pack(pack)
    assert not ok
    assert any("chain_root mismatch" in i for i in issues)


def test_tamper_detection_prev_hash_break(tmp_path):
    pack, _, _ = make_pack(tmp_path)
    pack["records"][0]["hash"] = "sha256:broken"
    ok, issues = verify_pack(pack)
    assert not ok
    assert any("chain broken" in i or "mismatch" in i for i in issues)


def test_canonical_json_deterministic():
    a = canonical_json({"b": 1, "a": [1, 2]})
    b = canonical_json({"a": [1, 2], "b": 1})
    assert a == b and json.loads(a) == {"a": [1, 2], "b": 1}
