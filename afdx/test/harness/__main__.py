"""
Command line entry point. Run it as a module, from the test/ directory:

    python3 -m harness list
    python3 -m harness record networks/simpleNetwork/results networks/simpleNetwork/baseline.json
    python3 -m harness check  networks/simpleNetwork/results networks/simpleNetwork/baseline.json

`python3 -m harness` runs this file because of its name: __main__.py is what
Python looks for when you run a package directly.

Normally you would use ./run_tests.sh instead, which builds the paths for you.
"""

import argparse
import sys
from pathlib import Path

from .afdx import AfdxExtractor
from .measure import Measurements, measure
from .metrics import RUN_METRICS, SWITCH_METRICS, VL_METRICS
from .report import compare, print_report


def command_list(args):
    """Print the parameter set, so the spec documents itself."""
    groups = [("RUN -- one value each, for the whole simulation", "", RUN_METRICS),
              ("PER VIRTUAL LINK -- repeated for every VL", "vl.<id>.", VL_METRICS),
              ("PER SWITCH -- repeated for every switch", "switch.<id>.", SWITCH_METRICS)]

    for title, prefix, metrics in groups:
        print(f"\n{title}\n{'-' * len(title)}")
        width = max(len(m.label) for m in metrics)
        for metric in metrics:
            allowed = "exact" if not metric.tolerance else f"{metric.tolerance:.0%}"
            print(f"  {prefix}{metric.label:<{width}}  [{allowed:>5}]  {metric.meaning}")

    total = len(RUN_METRICS) + len(VL_METRICS) + len(SWITCH_METRICS)
    print(f"\n{total} parameters defined, in test/harness/metrics.py")
    print("[exact] means the value may not move at all.\n")
    return 0


def command_record(args):
    """Measure a run and save it as the baseline to compare future runs against."""
    result = measure(AfdxExtractor(args.results))
    result.save(args.baseline)
    print(f"{_prefix(args)}recorded {result.count} parameters -> {args.baseline}")
    return 0


def command_check(args):
    """Measure a run and compare it against the baseline."""
    if not Path(args.baseline).exists():
        print(f"{_prefix(args)}no baseline at {args.baseline} -- run `record` first")
        return 1

    checks = compare(Measurements.load(args.baseline),
                     measure(AfdxExtractor(args.results)))
    return 0 if print_report(checks, args.label, args.indent) else 1


def _prefix(args):
    return f"{args.indent}{args.label}  " if args.label else args.indent


def main(argv=None):
    parser = argparse.ArgumentParser(prog="harness", description=__doc__)
    # Subcommands: `harness record ...` and `harness check ...` each get their
    # own arguments, and `dest="command"` records which one was used.
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("list", help="print every parameter and what it measures")

    for name, help_text in [("record", "save this run as the new baseline"),
                            ("check", "compare this run against the baseline")]:
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument("results", type=Path, help="a network's results directory")
        sub.add_argument("baseline", type=Path, help="the baseline .json file")
        sub.add_argument("--label", default="", help="name to print in the report")
        sub.add_argument("--indent", default="", help="indent for the report")

    args = parser.parse_args(argv)
    return {"list": command_list,
            "record": command_record,
            "check": command_check}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
