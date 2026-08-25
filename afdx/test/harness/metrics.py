"""The small, fixed set of values compared by the regression harness."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Metric:
    """One observable simulation result."""

    name: str
    unit: str
    meaning: str

    @property
    def label(self) -> str:
        return f"{self.name} ({self.unit})" if self.unit else self.name


# The simulation uses a fixed seed, so results are deterministic and are compared
# exactly. A tolerance would allow a small functional change to pass unnoticed.
RUN_METRICS = [
    Metric("sim_duration", "s", "simulated time covered by the run"),
]

VL_METRICS = [
    Metric("frames_sent", "", "frames produced by the source"),
    Metric("frames_delivered", "", "deliveries observed at all receivers"),
    Metric("dropped_in_queue", "", "frames discarded by full switch queues"),
    Metric("dropped_by_policer", "", "frames rejected by traffic policing"),
    Metric("latency_max", "us", "worst end-to-end latency"),
    Metric("latency_mean", "us", "mean end-to-end latency"),
]

SWITCH_METRICS = [
    Metric("queueing_time_max", "us", "worst queueing delay in the switch"),
]
