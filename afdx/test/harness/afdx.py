"""Extractor for the cOutVectors produced by this AFDX model."""

import csv
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .extractor import Extractor


PER_VL = re.compile(r"^(?P<family>[A-Za-z0-9]+)_VL(?P<vl>[0-9a-fA-F]+)$")
SWITCH_VECTOR = re.compile(r"^SWQueueingTime_SW(?P<sw>\d+)$")
TIME_LIMIT_LINE = re.compile(r"at t=(?P<t>[0-9.eE+-]+)s")
VL_FAMILIES = frozenset({
    "TrafficSource", "E2ELatency", "DroppedFrameQueue",
    "DroppedFrameTraffPol",
})
SECONDS_TO_US = 1e6


def _to_us(seconds):
    return None if seconds is None else round(seconds * SECONDS_TO_US, 6)


class AfdxExtractor(Extractor):
    """Read one run's vector file and log."""

    def __init__(self, results_dir):
        self.results_dir = Path(results_dir)
        self._vectors: dict[str, tuple[float, ...]] = {}
        self._load_vectors()
        self._discover_ids()

    def _load_vectors(self):
        if shutil.which("opp_scavetool") is None:
            sys.exit("error: opp_scavetool not on PATH -- source the OMNeT++ "
                     "setenv script first")

        inputs = sorted(self.results_dir.glob("*.vec"))
        if not inputs:
            sys.exit(f"error: no .vec files in {self.results_dir}")

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "vectors.csv"
            command = [
                "opp_scavetool", "export", "-T", "v", "-F", "CSV-R",
                "--precision=12", "-o", str(output),
                *(str(path) for path in inputs),
            ]
            done = subprocess.run(command, capture_output=True, text=True)
            if done.returncode != 0:
                sys.exit(f"error: opp_scavetool failed\n{done.stderr}")

            for row in _rows(output):
                if row["type"] == "vector" and ":" not in row["name"]:
                    self._vectors[row["name"]] = _floats(row["vecvalue"])

    def _discover_ids(self):
        vls, switches = set(), set()
        for name in self._vectors:
            match = PER_VL.match(name)
            if match and match.group("family") in VL_FAMILIES:
                vls.add(match.group("vl"))
            match = SWITCH_VECTOR.match(name)
            if match:
                switches.add(int(match.group("sw")))

        self._vl_ids = sorted(vls, key=lambda value: (len(value), value))
        self._switch_ids = [str(value) for value in sorted(switches)]

    def _values(self, name):
        return self._vectors.get(name, ())

    def _count(self, name):
        return len(self._vectors[name]) if name in self._vectors else None

    def virtual_links(self):
        return self._vl_ids

    def switches(self):
        return self._switch_ids

    def run_sim_duration(self):
        log = self.results_dir / "run.log"
        if not log.exists():
            return None
        found = None
        for line in log.read_text(errors="replace").splitlines():
            match = TIME_LIMIT_LINE.search(line)
            if match:
                found = match
        return float(found.group("t")) if found else None

    def vl_frames_sent(self, vl):
        return self._count(f"TrafficSource_VL{vl}")

    def vl_frames_delivered(self, vl):
        return self._count(f"E2ELatency_VL{vl}")

    def vl_dropped_in_queue(self, vl):
        # OMNeT++ does not export an empty drop vector; absence means zero.
        return len(self._values(f"DroppedFrameQueue_VL{vl}"))

    def vl_dropped_by_policer(self, vl):
        return len(self._values(f"DroppedFrameTraffPol_VL{vl}"))

    def vl_latency_max(self, vl):
        return _to_us(_max(self._values(f"E2ELatency_VL{vl}")))

    def vl_latency_mean(self, vl):
        return _to_us(_mean(self._values(f"E2ELatency_VL{vl}")))

    def switch_queueing_time_max(self, switch):
        return _to_us(_max(self._values(f"SWQueueingTime_SW{switch}")))


def _rows(path):
    csv.field_size_limit(sys.maxsize)
    with open(path, newline="") as handle:
        yield from csv.DictReader(handle)


def _floats(field):
    return tuple(float(value) for value in field.split()) \
        if field and field.strip() else ()


def _max(values):
    return max(values) if values else None


def _mean(values):
    return sum(values) / len(values) if values else None
