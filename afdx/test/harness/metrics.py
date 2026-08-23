"""
The parameter set. THIS IS THE FILE YOU EDIT BY HAND.

Every parameter the harness tests is one line below. That line carries everything
about it: the name, the unit, what it measures in one sentence, and how much it is
allowed to move before the test fails.

To change a tolerance, edit the number on the line. To stop testing a parameter,
delete the line. To add one, add a line here, then add the matching method to
extractor.py and implement it in afdx.py.

Run `python3 -m harness list` to print this set as a table.
"""

from dataclasses import dataclass

# Smallest difference we ever call a difference. Without it a parameter whose
# baseline is 0 could never pass, because "1% of 0" is 0.
ABSOLUTE_SLACK = 1e-12


@dataclass(frozen=True)
class Metric:
    """One tested parameter.

    `frozen=True` makes instances read-only, so nothing can quietly change a
    tolerance at runtime -- the only way to change one is to edit this file.
    """

    name: str
    unit: str
    meaning: str
    tolerance: float = 0.0  # relative; 0.0 means "must match exactly"

    def accepts(self, baseline: float, actual: float) -> bool:
        """True if `actual` is close enough to `baseline` for this parameter."""
        allowed = ABSOLUTE_SLACK + self.tolerance * abs(baseline)
        return abs(actual - baseline) <= allowed

    @property
    def label(self) -> str:
        """The name with its unit, e.g. `latency_max (us)`."""
        return f"{self.name} ({self.unit})" if self.unit else self.name


# --------------------------------------------------------------------------- #
# Run -- one value each, for the whole simulation.
# --------------------------------------------------------------------------- #

RUN_METRICS = [
    Metric("sim_duration", "s",
           "how much simulated time the run covered"),
    Metric("vl_count", "",
           "how many virtual links the run produced output for"),
    Metric("switch_count", "",
           "how many switches the run produced output for"),
    Metric("end_system_count", "",
           "how many end systems the run produced output for"),
    Metric("frames_sent", "",
           "frames produced by all sources, added up"),
    Metric("frames_delivered", "",
           "deliveries at all sinks; a multicast frame counts once per receiver"),
    Metric("frames_lost", "",
           "expected deliveries minus actual deliveries, added up over all VLs"),
    Metric("config_fingerprint", "",
           "hash of every resolved config value; changes when an .ini is edited"),
]


# --------------------------------------------------------------------------- #
# Per virtual link. A virtual link (VL) is one logical AFDX flow: a fixed route
# from one sender to one or more receivers, with a guaranteed bandwidth.
# --------------------------------------------------------------------------- #

VL_METRICS = [
    Metric("frames_sent", "",
           "frames the source produced for this VL"),
    Metric("receiver_count", "",
           "how many end systems receive this VL; more than 1 means multicast"),
    Metric("frames_delivered", "",
           "deliveries at sinks for this VL"),
    Metric("frames_lost", "",
           "frames_sent x receiver_count, minus frames_delivered"),
    Metric("dropped_in_queue", "",
           "frames thrown away because a switch queue was full"),
    Metric("dropped_by_policer", "",
           "frames rejected by the rate limiter for exceeding their budget"),
    Metric("latency_max", "us",
           "worst end-to-end delay, from source to sink", tolerance=0.05),
    Metric("latency_mean", "us",
           "average end-to-end delay, from source to sink", tolerance=0.01),
    Metric("jitter", "us",
           "spread of end-to-end delay: the worst minus the best", tolerance=0.10),
    Metric("bag_wait_max", "us",
           "worst wait for this VL's BAG slot. BAG is the minimum gap the end "
           "system must keep between two frames of the same VL",
           tolerance=0.05),
    Metric("credit_min", "bits",
           "lowest token-bucket credit reached. The token bucket is the rate "
           "limiter's budget; a negative value means it rejected a frame",
           tolerance=0.05),
]


# --------------------------------------------------------------------------- #
# Per switch.
# --------------------------------------------------------------------------- #

SWITCH_METRICS = [
    Metric("queue_len_max", "bits",
           "largest backlog that built up inside this switch", tolerance=0.05),
    Metric("queueing_time_max", "us",
           "worst time a frame spent waiting in this switch", tolerance=0.05),
    Metric("queueing_time_mean", "us",
           "average time a frame spent waiting in this switch", tolerance=0.01),
]


# Used by measure.py and report.py to walk all three groups the same way.
# Each entry is (group name in the baseline file, the metric list).
GROUPS = [
    ("run", RUN_METRICS),
    ("switches", SWITCH_METRICS),
    ("vls", VL_METRICS),
]
