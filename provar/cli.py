"""Provar CLI.

  provar run         execute a suite against a target, emit an evidence pack
  provar demo        offline one-command demo against a packaged reference target
  provar postmortem  re-render postmortem/report artifacts from a pack
  provar verify      verify the hash chain of an evidence pack

Exit codes (docs/MASTER_CHECKLIST.md A7):
  0  green — CERTIFIED_PASS or CONDITIONAL_PASS (demo: expected verdict matched)
  1  remediate — REMEDIATE_BEFORE_DEPLOY (demo: detection assertion failed)
  2  config / runtime error
  3  block — BLOCK_FOR_DEPLOYMENT
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import yaml

from . import __version__
from .corpus import load_suite
from .demo import DEMO_DIR, reference_broken, reference_safe
from .evidence import build_pack, utc_now_iso, verify_pack, write_pack_outputs
from .postmortem import build_postmortem
from .runner import run_suite
from .scoring import (
    VERDICT_BLOCK,
    VERDICT_CERTIFIED,
    VERDICT_CONDITIONAL,
    VERDICT_REMEDIATE,
    score_run,
)
from .target import target_from_config

_EXIT_FOR_VERDICT = {
    VERDICT_CERTIFIED: 0,
    VERDICT_CONDITIONAL: 0,
    VERDICT_REMEDIATE: 1,
    VERDICT_BLOCK: 3,
}


def _load_targets(path: str) -> dict:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return data.get("targets") or {}


def _execute(suite, target, target_meta: dict, pack_id: str, out: str, concurrency: int):
    """Shared run pipeline: probe -> score -> postmortem -> pack -> artifacts."""

    def progress(done, total, outcome):
        mark = {"pass": ".", "fail": "F", "error": "E"}[outcome.verdict]
        print(mark, end="", flush=True)
        if done % 60 == 0 or done == total:
            print(f"  [{done}/{total}]", flush=True)

    started = utc_now_iso()
    outcomes = asyncio.run(
        run_suite(suite, target, concurrency=concurrency, progress_cb=progress)
    )
    ended = utc_now_iso()

    scorecard = score_run(outcomes)
    postmortem = build_postmortem(outcomes, scorecard)
    run_meta = {
        "started_utc": started,
        "ended_utc": ended,
        "concurrency": concurrency,
        "judge_policy": "deterministic only",
        "judge_version": "v0.1.1",
    }
    pack = build_pack(pack_id, suite, target_meta, outcomes, scorecard, postmortem, run_meta)
    paths = write_pack_outputs(pack, out)

    print()
    print(scorecard.statement)
    print()
    print("Postmortem clusters:", len(postmortem["clusters"]))
    print("Artifacts:")
    for k, v in paths.items():
        print(f"  {k}: {v}")
    ok, issues = verify_pack(pack)
    print(f"Chain self-verify: {'OK' if ok else 'FAILED'}")
    for i in issues:
        print("  -", i)
    return pack, scorecard


def cmd_run(args) -> int:
    try:
        suite = load_suite(args.suite)
        targets = _load_targets(args.target_config)
    except (OSError, yaml.YAMLError, ValueError) as exc:
        print(f"error: cannot load config/suite: {exc}", file=sys.stderr)
        return 2
    if args.target not in targets:
        print(f"error: target '{args.target}' not in {args.target_config}", file=sys.stderr)
        return 2
    cfg = targets[args.target]
    cfg.setdefault("base_url", "")
    try:
        target = target_from_config(cfg)
    except (ValueError, KeyError) as exc:
        print(f"error: invalid target config: {exc}", file=sys.stderr)
        return 2

    target_meta = {
        "kind": cfg.get("kind", "openai_compat"),
        "base_url": cfg.get("base_url"),
        "model": cfg.get("model"),
        "note": "black-box interface; no auth material recorded",
    }

    pack, scorecard = _execute(
        suite, target, target_meta, args.pack_id, args.out, args.concurrency
    )
    return _EXIT_FOR_VERDICT.get(scorecard.verdict, 1)


def cmd_demo(args) -> int:
    suite = load_suite(str(DEMO_DIR / "suite.yaml"))
    if args.negative:
        target = reference_broken()
        target_meta = {
            "kind": "reference",
            "name": "reference-broken",
            "note": "deliberately misconfigured assistant; planted failures must be detected",
        }
        pack_id = args.pack_id or "EP-DEMO-NEG"
    else:
        target = reference_safe()
        target_meta = {
            "kind": "reference",
            "name": "reference-safe",
            "note": "packaged reference assistant; offline, deterministic",
        }
        pack_id = args.pack_id or "EP-DEMO"

    pack, scorecard = _execute(suite, target, target_meta, pack_id, args.out, concurrency=4)

    if args.negative:
        # Detection assertion: the planted failures must degrade the verdict to
        # BLOCK_FOR_DEPLOYMENT (2 critical safety fails fire the BLOCK floor).
        fail_ids = {r["probe_id"] for r in pack["records"] if r["verdict"] == "fail"}
        required = {"RT-001", "RT-004", "RT-011", "RT-016", "RB-002", "RB-008", "FC-001", "GV-001"}
        missing = required - fail_ids
        if scorecard.verdict == VERDICT_BLOCK and not missing:
            print(f"Negative demo: all {len(required)} planted failures detected -> "
                  f"{VERDICT_BLOCK}. Verdict engine is not a rubber stamp.")
            return 0
        print(f"Negative demo DETECTION FAILURE: verdict {scorecard.verdict}, "
              f"undetected planted failures: {sorted(missing) or 'none'}")
        return 1

    return _EXIT_FOR_VERDICT.get(scorecard.verdict, 1)


def cmd_postmortem(args) -> int:
    pack = json.loads(Path(args.pack).read_text(encoding="utf-8"))
    from .evidence import render_html, render_markdown

    if args.html:
        Path(args.html).write_text(render_html(pack), encoding="utf-8")
        print(f"html: {args.html}")
    if args.md:
        Path(args.md).write_text(render_markdown(pack), encoding="utf-8")
        print(f"md: {args.md}")
    if not args.html and not args.md:
        print(pack.get("postmortem", {}).get("summary", "no postmortem in pack"))
    return 0


def cmd_verify(args) -> int:
    pack = json.loads(Path(args.pack).read_text(encoding="utf-8"))
    ok, issues = verify_pack(pack)
    if ok:
        print(f"OK: {pack.get('integrity', {}).get('record_count', 0)} records verified; "
              f"chain_root {pack.get('integrity', {}).get('chain_root')}")
        return 0
    print("TAMPERED / INVALID:")
    for i in issues:
        print("  -", i)
    return 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="provar",
        description="Provar — assurance layer for hospital AI",
        epilog="Exit codes: 0 green/conditional · 1 remediate · 2 config error · 3 block",
    )
    ap.add_argument("--version", action="version", version=f"provar {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="run a suite against a target and emit an evidence pack")
    p_run.add_argument("--target-config", required=True, help="targets YAML")
    p_run.add_argument("--target", required=True, help="target name inside the YAML")
    p_run.add_argument("--suite", required=True, help="suite YAML path")
    p_run.add_argument("--out", default="evidence", help="output directory")
    p_run.add_argument("--pack-id", default="EP-001")
    p_run.add_argument("--concurrency", type=int, default=3)
    p_run.set_defaults(fn=cmd_run)

    p_demo = sub.add_parser(
        "demo", help="offline demo: run the packaged demo suite against a reference target"
    )
    p_demo.add_argument(
        "--negative", action="store_true",
        help="use reference-broken; asserts every planted failure is detected (BLOCK verdict)",
    )
    p_demo.add_argument("--out", default="evidence/demo", help="output directory")
    p_demo.add_argument("--pack-id", default="", help="override evidence pack id")
    p_demo.set_defaults(fn=cmd_demo)

    p_pm = sub.add_parser("postmortem", help="re-render postmortem artifacts from a pack")
    p_pm.add_argument("--pack", required=True)
    p_pm.add_argument("--html")
    p_pm.add_argument("--md")
    p_pm.set_defaults(fn=cmd_postmortem)

    p_ver = sub.add_parser("verify", help="verify a pack's hash chain")
    p_ver.add_argument("pack")
    p_ver.set_defaults(fn=cmd_verify)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
