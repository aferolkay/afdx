"""
The developer API: how a simulation's raw output becomes the parameters in
metrics.py.

There is one method here for every Metric in metrics.py, and the method name is
the metric name with its group as a prefix:

    run_<name>(self)              for every metric in RUN_METRICS
    switch_<name>(self, switch)   for every metric in SWITCH_METRICS
    vl_<name>(self, vl)           for every metric in VL_METRICS

To test a different model, subclass Extractor and fill in every method. Python
will refuse to create an instance of a subclass that forgot one, so the list
below is a contract, not a suggestion.

See afdx.py for a complete implementation.

Return None from any method when the value cannot be measured in this run. The
report then says "not measured", which is a failure -- if a parameter used to be
measurable and no longer is, that is something you want to know about.
"""

from abc import ABC, abstractmethod


class Extractor(ABC):
    """Reads one simulation run and answers one question per method.

    ABC means "abstract base class": a class that exists to be inherited from,
    not used directly. Every @abstractmethod below must be filled in by whoever
    inherits it.
    """

    # ----------------------------------------------------------------- #
    # What is in this run. Everything else is asked once per item in
    # these two lists.
    # ----------------------------------------------------------------- #

    @abstractmethod
    def virtual_links(self) -> list[str]:
        """Ids of every virtual link in this run, as strings.

        The string is used as-is in the baseline file, so pick something a
        person can look up -- the AFDX model uses the VL id in hex, exactly as
        it appears in the raw .vec file.
        """

    @abstractmethod
    def switches(self) -> list[str]:
        """Ids of every switch in this run, as strings."""

    # ----------------------------------------------------------------- #
    # Run: one value each for the whole simulation.
    # ----------------------------------------------------------------- #

    @abstractmethod
    def run_sim_duration(self) -> float | None:
        """Simulated seconds the run covered."""

    @abstractmethod
    def run_vl_count(self) -> int | None:
        """How many virtual links produced output."""

    @abstractmethod
    def run_switch_count(self) -> int | None:
        """How many switches produced output."""

    @abstractmethod
    def run_end_system_count(self) -> int | None:
        """How many end systems produced output."""

    @abstractmethod
    def run_frames_sent(self) -> int | None:
        """Frames produced by every source, added up."""

    @abstractmethod
    def run_frames_delivered(self) -> int | None:
        """Deliveries at every sink, added up."""

    @abstractmethod
    def run_frames_lost(self) -> int | None:
        """Expected deliveries minus actual, added up over every VL."""

    @abstractmethod
    def run_config_fingerprint(self) -> str | None:
        """A hash of every resolved configuration value.

        Its job is to fail the moment somebody edits an .ini, before any
        measured number has had a chance to move.
        """

    # ----------------------------------------------------------------- #
    # Per virtual link. `vl` is one of the ids from virtual_links().
    # ----------------------------------------------------------------- #

    @abstractmethod
    def vl_frames_sent(self, vl: str) -> int | None:
        """Frames the source produced for this VL."""

    @abstractmethod
    def vl_receiver_count(self, vl: str) -> int | None:
        """How many end systems receive this VL. More than 1 means multicast."""

    @abstractmethod
    def vl_frames_delivered(self, vl: str) -> int | None:
        """Deliveries at sinks for this VL.

        A multicast frame is delivered once per receiver, so this counts up to
        frames_sent x receiver_count.
        """

    @abstractmethod
    def vl_frames_lost(self, vl: str) -> int | None:
        """Expected deliveries minus actual deliveries for this VL."""

    @abstractmethod
    def vl_dropped_in_queue(self, vl: str) -> int | None:
        """Frames of this VL thrown away because a switch queue was full."""

    @abstractmethod
    def vl_dropped_by_policer(self, vl: str) -> int | None:
        """Frames of this VL rejected by the rate limiter."""

    @abstractmethod
    def vl_latency_max(self, vl: str) -> float | None:
        """Worst end-to-end delay for this VL, in microseconds."""

    @abstractmethod
    def vl_latency_mean(self, vl: str) -> float | None:
        """Average end-to-end delay for this VL, in microseconds."""

    @abstractmethod
    def vl_jitter(self, vl: str) -> float | None:
        """Worst end-to-end delay minus best, in microseconds."""

    @abstractmethod
    def vl_bag_wait_max(self, vl: str) -> float | None:
        """Worst wait for this VL's BAG slot, in microseconds."""

    @abstractmethod
    def vl_credit_min(self, vl: str) -> float | None:
        """Lowest token-bucket credit this VL reached, in bits.

        Negative means the rate limiter rejected a frame, so this and
        vl_dropped_by_policer check each other.
        """

    # ----------------------------------------------------------------- #
    # Per switch. `switch` is one of the ids from switches().
    # ----------------------------------------------------------------- #

    @abstractmethod
    def switch_queue_len_max(self, switch: str) -> float | None:
        """Largest backlog inside this switch, in bits."""

    @abstractmethod
    def switch_queueing_time_max(self, switch: str) -> float | None:
        """Worst time a frame waited in this switch, in microseconds."""

    @abstractmethod
    def switch_queueing_time_mean(self, switch: str) -> float | None:
        """Average time a frame waited in this switch, in microseconds."""
