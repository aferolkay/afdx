"""Interface between simulation output and the regression parameters.

Implement this class for another simulator. Each method converts raw output into
one stable, observable value; the harness handles storage and comparison.
"""

from abc import ABC, abstractmethod


class Extractor(ABC):
    """Extract the fundamental results of one AFDX simulation run."""

    @abstractmethod
    def virtual_links(self) -> list[str]:
        """Stable ids of all virtual links present in the output."""

    @abstractmethod
    def switches(self) -> list[str]:
        """Stable ids of all switches present in the output."""

    @abstractmethod
    def run_sim_duration(self) -> float | None:
        """Simulated seconds covered by the run."""

    @abstractmethod
    def vl_frames_sent(self, vl: str) -> int | None:
        """Frames produced for a virtual link."""

    @abstractmethod
    def vl_frames_delivered(self, vl: str) -> int | None:
        """Deliveries at all receivers of a virtual link."""

    @abstractmethod
    def vl_dropped_in_queue(self, vl: str) -> int | None:
        """Frames discarded by full switch queues."""

    @abstractmethod
    def vl_dropped_by_policer(self, vl: str) -> int | None:
        """Frames rejected by traffic policing."""

    @abstractmethod
    def vl_latency_max(self, vl: str) -> float | None:
        """Worst end-to-end latency in microseconds."""

    @abstractmethod
    def vl_latency_mean(self, vl: str) -> float | None:
        """Mean end-to-end latency in microseconds."""

    @abstractmethod
    def switch_queueing_time_max(self, switch: str) -> float | None:
        """Worst queueing delay in a switch, in microseconds."""
