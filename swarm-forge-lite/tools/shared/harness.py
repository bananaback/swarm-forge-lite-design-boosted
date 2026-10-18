#!/usr/bin/env python3
"""harness -- wiring status and cleanup for the swarm-forge-lite pack.

Usage:
  harness config            print resolved wiring as JSON
  harness status            print every resolved path and the active lane
  harness clean [TARGET]    clean hot (default), state, artifacts, or all
  harness clean --drop      also remove a root that is empty after the clear
  harness lint-record       lint a subsystem's record (or an explicit --record dir)
  harness gen-doc           sync a subsystem's requirement document to its record, keyed by id
  harness check ROLE        lint the record a role wrote, and write the computed stop test
  harness guide ROLE        print the method map and the forms
  harness init-work ROLE    write a role's empty forms to a NEW subsystem's record directory
  harness decisions ROLE    print the decision ledger of a subsystem, and the open count
  harness check-envelope    lint a dispatch envelope (duplicate blocks, the cite hint)
  harness vocab-rename      bulk rename a token across files, with a verify pass
  harness envelope ROLE     print a dispatch block with every resolved path

The CLI is a thin composition root: it loads a PathSet (over wiring) and an
OsTree (over the filesystem), then dispatches to one command. Every rule about a
value lives on that value: CleanTarget owns the target table, OptionalRoot owns
absence, and the report value objects own their rendering.
"""

import argparse
import sys

from harness_cmds import (
    _pack_design,
    _project_env_lines,
    _subsystem,
    _subsystem_name,
    _work_dir_for,
    cmd_check,
    cmd_check_envelope,
    cmd_clean,
    cmd_config,
    cmd_decisions,
    cmd_envelope,
    cmd_gen_doc,
    cmd_guide,
    cmd_init_work,
    cmd_lint_record,
    cmd_status,
    cmd_vocab_rename,
    read_decision_rows,
)
from harness_values import (
    ABSENT_TEXT,
    TARGET_NAMES,
    CleanTarget,
    ClearReport,
    DisposableTree,
    HarnessError,
    OptionalRoot,
    OsTree,
    PathSet,
    PathStatus,
    PersistentRoot,
    ResolvedWiring,
    StatusReport,
    _direct_row,
    _lane_row,
    _optional_row,
    _persistent_row,
    config_document,
    load_path_set,
    status_report,
)

__all__ = [
    "ABSENT_TEXT",
    "TARGET_NAMES",
    "CleanTarget",
    "ClearReport",
    "DisposableTree",
    "HarnessError",
    "OptionalRoot",
    "OsTree",
    "PathSet",
    "PathStatus",
    "PersistentRoot",
    "ResolvedWiring",
    "StatusReport",
    "_direct_row",
    "_lane_row",
    "_optional_row",
    "_pack_design",
    "_persistent_row",
    "_project_env_lines",
    "_subsystem",
    "_subsystem_name",
    "_work_dir_for",
    "build_parser",
    "cmd_check",
    "cmd_check_envelope",
    "cmd_clean",
    "cmd_config",
    "cmd_decisions",
    "cmd_envelope",
    "cmd_gen_doc",
    "cmd_guide",
    "cmd_init_work",
    "cmd_lint_record",
    "cmd_status",
    "cmd_vocab_rename",
    "config_document",
    "load_path_set",
    "main",
    "read_decision_rows",
    "status_report",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="harness")
    parser.add_argument("--config")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("config")
    sub.add_parser("status")

    clean = sub.add_parser("clean")
    clean.add_argument("target", nargs="?", choices=TARGET_NAMES, default="hot")
    clean.add_argument(
        "--drop",
        action="store_true",
        help="remove the root itself when it is empty after the clear",
    )

    lint = sub.add_parser("lint-record", help="lint a subsystem's requirement record")
    lint.add_argument("--subsystem")
    lint.add_argument("--record")
    lint.add_argument("--specs")
    gendoc = sub.add_parser(
        "gen-doc", help="write a subsystem's requirement document from its record"
    )
    gendoc.add_argument("--subsystem")
    gendoc.add_argument("--record")
    gendoc.add_argument("--specs")
    gendoc.add_argument("--grow", action="store_true")

    chk = sub.add_parser(
        "check", help="lint the record a role wrote, and write the stop test"
    )
    chk.add_argument("role")
    chk.add_argument("--subsystem")
    chk.add_argument("--work")

    guide = sub.add_parser("guide", help="print the method map and the forms")
    guide.add_argument("role")
    guide.add_argument("--subsystem")

    init = sub.add_parser(
        "init-work", help="write a role's empty forms to a NEW subsystem"
    )
    init.add_argument("role")
    init.add_argument("--subsystem")
    init.add_argument("--work")
    init.add_argument("--module", help="module id for a flat designer record")
    init.add_argument(
        "--flat",
        action="store_true",
        help="write the lean flat record (requirements.md, architecture.md, review.md)",
    )
    init.add_argument(
        "--force",
        action="store_true",
        help="reset an existing record to empty forms (destructive)",
    )

    ren2 = sub.add_parser("vocab-rename", help="bulk rename a token across files")
    ren2.add_argument("--from", "--old", dest="old", required=True)
    ren2.add_argument("--to", "--new", dest="new", required=True)
    ren2.add_argument("--in", dest="files", nargs="+", required=True)
    ren2.add_argument("--word", action="store_true", help="whole-word match")
    ren2.add_argument("--dry-run", action="store_true")
    ren2.add_argument(
        "--verify", action="store_true", help="fail if any occurrence remains"
    )

    env = sub.add_parser("envelope", help="print a dispatch block with resolved paths")
    env.add_argument("role")
    env.add_argument("--subsystem")

    dec = sub.add_parser("decisions", help="print the decision ledger of a subsystem")
    dec.add_argument("role")
    dec.add_argument("--subsystem")
    dec.add_argument("--work")

    cenv = sub.add_parser(
        "check-envelope", help="lint a dispatch envelope (no size limit)"
    )
    cenv.add_argument("file", nargs="?", default="-")

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        paths = load_path_set(args.config)
        tree = OsTree()
        if args.command == "config":
            cmd_config(paths)
        elif args.command == "status":
            cmd_status(paths, tree)
        elif args.command == "clean":
            cmd_clean(args.target, paths, tree, drop=args.drop)
        elif args.command == "lint-record":
            cmd_lint_record(args, paths)
        elif args.command == "gen-doc":
            cmd_gen_doc(args, paths)
        elif args.command == "check":
            cmd_check(args, paths)
        elif args.command == "guide":
            cmd_guide(args, paths)
        elif args.command == "init-work":
            cmd_init_work(args, paths)
        elif args.command == "vocab-rename":
            cmd_vocab_rename(args, paths)
        elif args.command == "envelope":
            cmd_envelope(args, paths)
        elif args.command == "decisions":
            cmd_decisions(args, paths)
        elif args.command == "check-envelope":
            cmd_check_envelope(args, paths)
    except HarnessError as error:
        print(f"harness: {error}", file=sys.stderr)
        return 2
    except KeyError as error:
        print(f"harness: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
