import asyncio

from provar.corpus import load_suite
from provar.evidence import build_pack, verify_pack
from provar.postmortem import build_postmortem
from provar.runner import run_suite
from provar.scoring import score_run
from provar.target import EchoTarget

SUITE = "provar/corpora/hospital_qa_v1.yaml"


def test_echo_target_run_end_to_end():
    suite = load_suite(SUITE)
    # EchoTarget always replies with a NOT_COVERED refusal:
    #  - scope_discipline probes should PASS (refused as expected)
    #  - overrefusal probes should FAIL (benign questions must be answered)
    target = EchoTarget()
    outcomes = asyncio.run(run_suite(suite, target, concurrency=4))
    assert len(outcomes) == len(suite.probes)
    by_id = {o.probe.id: o for o in outcomes}

    assert by_id["RT-016"].verdict == "pass"
    assert by_id["RT-011"].verdict == "fail"

    sc = score_run(outcomes)
    assert sc.failed > 0 and sc.total == len(suite.probes)
    assert sc.verdict in {"CONDITIONAL_PASS", "REMEDIATE_BEFORE_DEPLOY", "BLOCK_FOR_DEPLOYMENT"}

    pm = build_postmortem(outcomes, sc)
    assert pm["clusters"], "overrefusal failures must form a cluster"
    over = [c for c in pm["clusters"] if c["category"] == "overrefusal"]
    assert over and "RT-011" in over[0]["probe_ids"]

    pack = build_pack(
        "EP-E2E", suite,
        {"base_url": "memory://echo", "model": "echo-fixture"},
        outcomes, sc, pm, {"started_utc": "t0", "ended_utc": "t1"},
    )
    ok, issues = verify_pack(pack)
    assert ok, issues


def test_runner_assigns_sequential_ids_and_dimensions():
    suite = load_suite(SUITE)
    outcomes = asyncio.run(run_suite(suite, EchoTarget(), concurrency=3))
    assert [o.seq for o in outcomes] == sorted(o.seq for o in outcomes)
    assert min(o.seq for o in outcomes) == 1
    gov = [o for o in outcomes if o.probe.id == "GV-001"]
    assert gov and gov[0].dimension == "governance"
