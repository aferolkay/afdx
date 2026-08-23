"""
Run the parameter set in metrics.py against an Extractor, and store the answer.

The result is a Measurements object, which saves and loads itself as JSON. That
JSON file is what gets committed as a baseline.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .extractor import Extractor
from .metrics import RUN_METRICS, SWITCH_METRICS, VL_METRICS

# A value that could not be measured. Stored as JSON null.
NOT_MEASURED = None


@dataclass
class Measurements:
    """Every parameter of one run, grouped the way metrics.py groups them.

    `field(default_factory=dict)` gives each new instance its own empty dict.
    A plain `= {}` default would share one dict between every instance, which is
    a classic Python trap -- dataclasses refuse to let you write it.
    """

    run: dict[str, Any] = field(default_factory=dict)
    switches: dict[str, dict[str, Any]] = field(default_factory=dict)
    vls: dict[str, dict[str, Any]] = field(default_factory=dict)

    def save(self, path: Path) -> None:
        """Write as pretty-printed JSON, so a diff is readable in review."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(
            {"run": self.run, "switches": self.switches, "vls": self.vls},
            indent=2,
            sort_keys=True,
        )
        path.write_text(text + "\n")

    @classmethod
    def load(cls, path: Path) -> "Measurements":
        """Read a saved file back.

        @classmethod means this is called on the class, not on an instance:
        `Measurements.load(path)`. It is the usual way to write an alternative
        constructor in Python.
        """
        data = json.loads(Path(path).read_text())
        return cls(run=data["run"], switches=data["switches"], vls=data["vls"])

    @property
    def count(self) -> int:
        """How many individual parameters this holds."""
        return (len(self.run)
                + sum(len(v) for v in self.switches.values())
                + sum(len(v) for v in self.vls.values()))


def _call(extractor: Extractor, method_name: str, *args) -> Any:
    """Call one extractor method by its name.

    `getattr(obj, "vl_jitter")` fetches the method whose name is that string,
    which is what lets metrics.py stay the single source of truth: the metric's
    name IS the method's name, so adding a metric needs no changes here.
    """
    method = getattr(extractor, method_name, None)
    if method is None:
        raise AttributeError(
            f"{type(extractor).__name__} has no method {method_name}(). "
            f"metrics.py lists this parameter, so the extractor must provide it."
        )
    return method(*args)


def measure(extractor: Extractor) -> Measurements:
    """Ask the extractor for every parameter in the spec."""
    result = Measurements()

    for metric in RUN_METRICS:
        result.run[metric.name] = _call(extractor, f"run_{metric.name}")

    for switch in extractor.switches():
        result.switches[switch] = {
            metric.name: _call(extractor, f"switch_{metric.name}", switch)
            for metric in SWITCH_METRICS
        }

    for vl in extractor.virtual_links():
        result.vls[vl] = {
            metric.name: _call(extractor, f"vl_{metric.name}", vl)
            for metric in VL_METRICS
        }

    return result
