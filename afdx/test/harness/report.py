"""
Compare a run against a baseline, and print the result.

Every parameter either passes or fails. There are no in-between categories: if a
value moved further than metrics.py allows, that is a failure, and if a parameter
that used to be measurable no longer is, that is also a failure.
"""

from dataclasses import dataclass
from typing import Any

from .measure import Measurements
from .metrics import RUN_METRICS, SWITCH_METRICS, VL_METRICS, Metric


class _Missing:
    """Marks a parameter that is not in one side at all.

    A dedicated object rather than None, because None is a real value here: it
    means "the run did not measure this".
    """

    def __repr__(self):
        return "<missing>"


MISSING = _Missing()


@dataclass
class Check:
    """The verdict on one parameter."""

    where: str        # "run", "switch 3", "VL 1f"
    metric: Metric
    baseline: Any
    actual: Any

    @property
    def ok(self) -> bool:
        """@property lets this be read as `check.ok`, with no parentheses."""
        if self.baseline is MISSING or self.actual is MISSING:
            return False
        if self.baseline is None or self.actual is None:
            # Both unmeasured is fine; one of the two changing is not.
            return self.baseline is None and self.actual is None
        if isinstance(self.baseline, str) or isinstance(self.actual, str):
            return self.baseline == self.actual
        return self.metric.accepts(self.baseline, self.actual)

    @property
    def note(self) -> str:
        """A short explanation, for the cases a number cannot express."""
        if self.baseline is MISSING:
            return "NEW -- not in the baseline"
        if self.actual is MISSING:
            return "GONE -- not in this run"
        if self.baseline is None and self.actual is not None:
            return "newly measurable (baseline had no value)"
        if self.actual is None and self.baseline is not None:
            return "NOT MEASURED in this run"
        return ""

    def describe(self) -> str:
        """One line explaining the verdict."""
        if self.note:
            return self.note
        if isinstance(self.baseline, str):
            return f"baseline {self.baseline[:16]}...  actual {self.actual[:16]}..."

        delta = self.actual - self.baseline
        line = (f"baseline {_number(self.baseline)}   "
                f"actual {_number(self.actual)}   {_number(delta, sign=True)}")
        if self.baseline:
            line += f" ({delta / self.baseline:+.1%})"
        if self.metric.tolerance:
            line += f", allowed {self.metric.tolerance:.0%}"
        else:
            line += ", must match exactly"
        return line


def compare(baseline: Measurements, current: Measurements) -> list[Check]:
    """Check every parameter in the spec, on both sides."""
    checks = []

    for metric in RUN_METRICS:
        checks.append(Check("run", metric,
                            baseline.run.get(metric.name, MISSING),
                            current.run.get(metric.name, MISSING)))

    checks += _compare_group("switch", SWITCH_METRICS,
                             baseline.switches, current.switches)
    checks += _compare_group("VL", VL_METRICS, baseline.vls, current.vls)
    return checks


def _compare_group(label, metrics, baseline_items, current_items):
    """Compare one group -- every switch, or every VL -- on both sides."""
    checks = []
    for item in _sorted_ids(set(baseline_items) | set(current_items)):
        # An item present on only one side gets MISSING for every one of its
        # parameters, so the report says which switch or VL appeared or vanished
        # rather than just that a count changed.
        old = baseline_items.get(item, {})
        new = current_items.get(item, {})
        for metric in metrics:
            checks.append(Check(f"{label} {item}", metric,
                                old.get(metric.name, MISSING),
                                new.get(metric.name, MISSING)))
    return checks


def print_report(checks: list[Check], label: str = "", indent: str = "") -> bool:
    """Print failures and a summary line. Returns True if everything passed."""
    failed = [c for c in checks if not c.ok]
    name = f"{label}  " if label else ""

    if not failed:
        print(f"{indent}{name}{len(checks)} parameters, all ok")
        return True

    print(f"{indent}{name}{len(checks)} parameters, "
          f"{len(checks) - len(failed)} ok, {len(failed)} FAILED")
    print()
    width = max(len(f"{c.where} {c.metric.label}") for c in failed)
    for check in failed:
        position = f"{check.where} {check.metric.label}"
        print(f"{indent}  FAIL  {position:<{width}}   {check.describe()}")
    print()
    return False


def _number(value, sign=False):
    """Compact number formatting: 497.27, 1000, +2, -0.0031."""
    if isinstance(value, int):
        return f"{value:+d}" if sign else str(value)
    return f"{value:+.6g}" if sign else f"{value:.6g}"


def _sorted_ids(ids):
    """Shortest first, then alphabetical -- so hex ids read in numeric order."""
    return sorted(ids, key=lambda i: (len(i), i))
