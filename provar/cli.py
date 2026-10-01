"""Provar CLI.

  provar run         execute a suite against a target, emit an evidence pack
  provar postmortem  re-render postmortem/report artifacts from a pack
  provar verify      verify the hash chain of an evidence pack
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
from .evidence import build_pack, utc_now_iso, verify_pack, write_pack_outputs
from .postmortem import build_postmortem
from .runner import run_suite
from .scoring import score_run
from .target import target_from_config


def _load_targets(path: str) -> dict:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return data.get("targets") or {}


def cmd_run(args) -> int:
    suite = load_suite(args.suite)
    targets = _load_targets(args.target_config)
    if args.target not in targets:
        print(f"error: target '{args.target}' not in {args.target_config}", file=sys.stderr)
        return 2
    cfg = targets[args.target]
    cfg.setdefault("base_url", "")
    target = target_from_config(cfg)

    target_meta = {
        "kind": "openai_compat",
        "base_url": cfg.get("base_url"),
        "model": cfg.get("model"),
        "note": "black-box HTTP interface; no auth material recorded",
    }

    state = {"started": utc_now_iso()}

    def progress(done, total, outcome):
        mark = {"pass": ".", "fail": "F", "error": "E"}[outcome.verdict]
        print(mark, end="", flush=True)
        if done % 60 == 0 or done == total:
            print(f"  [{done}/{total}]", flush=True)

    outcomes = asyncio.run(
        run_suite(suite, target, concurrency=args.concurrency, progress_cb=progress)
    )
    ended = utc_now_iso()

    scorecard = score_run(outcomes)
    postmortem = build_postmortem(outcomes, scorecard)
    run_meta = {
        "started_utc": state["started"],
        "ended_utc": ended,
        "concurrency": args.concurrency,
        "judge_policy": "deterministic only",
        "judge_version": "v0.1.1",
    }
    pack = build_pack(args.pack_id, suite, target_meta, outcomes, scorecard, postmortem, run_meta)
    paths = write_pack_outputs(pack, args.out)

    print()
    print(scorecard.statement)
    if scorecard.gates_triggered:
        pass
    print()
    print("Postmortem clusters:", len(postmortem["clusters"]))
    print("Artifacts:")
    for k, v in paths.items():
        print(f"  {k}: {v}")
    ok, issues = verify_pack(pack)
    print(f"Chain self-verify: {'OK' if ok else 'FAILED'}")
    for i in issues:
        print("  -", i)
    return 0


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
    ap = argparse.ArgumentParser(prog="provar", description="Provar — assurance layer for hospital AI")
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
