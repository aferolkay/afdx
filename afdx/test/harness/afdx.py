"""
The Extractor for this AFDX model.

Everything the model records is a raw cOutVector created by NetworkStatistics,
named after the thing it measures -- `E2ELatency_VL1f`, `SWQueueingTime_SW3`. So
each method below is mostly "find the right vector, take its max / mean / length".

Nothing was added to the model to make this work. The harness reads what the
simulation already writes.

Where each vector comes from in the model:

    TrafficSource_VL<hex>            AFDXMarshall.cc:75    one entry per frame created
    E2ELatency_VL<hex>               Sink_ext.cc:27        one entry per delivery
    LatencyAt#ES<n>_VL<hex>          Sink_ext.cc:28        same, split per receiver
    ESBagLatency_VL<hex>             RedundancyController.cc:29
    DroppedFrameQueue_VL<hex>        PassiveQueue.cc:78    one entry per full-queue drop
    DroppedFrameTraffPol_VL<hex>     TrafficPolicy.cc:88   one entry per rejection
    TokenBucketCredit#SW<n>_VL<hex>  TrafficPolicy.cc:49-79
    SWQueueLength_SW<n>              PassiveQueue.cc:104-195
    SWQueueingTime_SW<n>             PassiveQueue.cc:128-183
"""

import csv
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .extractor import Extractor

# Vector names, as built by NetworkStatistics::createRecorder. VL ids are hex, and
# are kept exactly as written so a baseline entry greps straight back to the .vec.
PER_VL = re.compile(r"^(?P<family>[A-Za-z]+)_VL(?P<vl>[0-9a-fA-F]+)$")
LATENCY_AT = re.compile(r"^LatencyAt#ES(?P<es>\d+)_VL(?P<vl>[0-9a-fA-F]+)$")
CREDIT = re.compile(r"^TokenBucketCredit#SW(?P<sw>\d+)_VL(?P<vl>[0-9a-fA-F]+)$")
SWITCH_VECTOR = re.compile(r"^SWQueue(?:Length|ingTime)_SW(?P<sw>\d+)$")

MODULE_ES = re.compile(r"\bES\[(\d+)\]")

# Cmdenv prints e.g. "<!> Simulation time limit reached -- at t=1s, event #789198"
TIME_LIMIT_LINE = re.compile(r"at t=(?P<t>[0-9.eE+-]+)s")

# Vector families that mean "this VL exists", even if nothing else was recorded.
VL_FAMILIES = frozenset({
    "TrafficSource", "E2ELatency", "ESBagLatency", "ESSchedulingLatency",
    "ESTotalLatency", "DroppedFrameQueue", "DroppedFrameTraffPol",
})

# Config entries that record WHERE output went, not what the model does. Hashing
# them would make the fingerprint change whenever you use a different output dir.
IGNORED_CONFIG = frozenset({"result-dir", "output-scalar-file", "output-vector-file"})

SECONDS_TO_US = 1e6


def _to_us(seconds):
    """Seconds to microseconds, rounded to picoseconds so the JSON stays readable."""
    return None if seconds is None else round(seconds * SECONDS_TO_US, 6)


class AfdxExtractor(Extractor):
    """Reads one AFDX run's .sca and .vec files."""

    def __init__(self, results_dir):
        self.results_dir = Path(results_dir)

        # name -> tuple of recorded values. Raw cOutVectors have globally unique
        # names, so the module they were created in does not matter here.
        self._vectors: dict[str, tuple[float, ...]] = {}
        # Every module that appears anywhere in the results, for the census.
        self._modules: set[str] = set()
        # "kind|module|name|value" for every config and parameter row.
        self._config_rows: list[str] = []

        self._load()

        # Worked out once in _load(), because several methods need them.
        self._vl_ids: list[str] = []
        self._switch_ids: list[str] = []
        self._receivers: dict[str, set[int]] = {}
        self._credit_vectors: dict[str, list[str]] = {}
        self._discover()

    # ------------------------------------------------------------------ #
    # loading
    # ------------------------------------------------------------------ #

    def _load(self):
        """Export the raw results to CSV with opp_scavetool, then read them."""
        if shutil.which("opp_scavetool") is None:
            sys.exit("error: opp_scavetool not on PATH -- source the OMNeT++ "
                     "setenv script first")

        sca = sorted(self.results_dir.glob("*.sca"))
        vec = sorted(self.results_dir.glob("*.vec"))
        if not sca or not vec:
            sys.exit(f"error: no .sca/.vec files in {self.results_dir}")

        # tempfile.TemporaryDirectory cleans itself up when the `with` block ends,
        # even if something raises inside it.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            # -T picks which record types to export: s=scalars, p=parameters,
            # h=histograms, t=statistics, v=vectors. --precision is pinned so
            # float formatting can never cause a difference by itself.
            self._export(sca, tmp / "scalars.csv", types="sthp", flatten=True)
            self._export(vec, tmp / "vectors.csv", types="v", flatten=False)
            self._read_scalars(tmp / "scalars.csv")
            self._read_vectors(tmp / "vectors.csv")

    def _export(self, inputs, out_path, types, flatten):
        command = ["opp_scavetool", "export", "-T", types, "-F", "CSV-R",
                   "--precision=12", "-o", str(out_path)]
        if flatten:
            # Turn each statistic's fields (count, mean, min, max, ...) into
            # ordinary scalar rows, so everything reads the same way.
            command.append("-w")
        command += [str(p) for p in inputs]

        done = subprocess.run(command, capture_output=True, text=True)
        if done.returncode != 0:
            sys.exit(f"error: opp_scavetool failed\n{done.stderr}")

    def _read_scalars(self, path):
        for row in _rows(path):
            if row["module"]:
                self._modules.add(row["module"])
            if row["type"] in ("param", "config", "itervar"):
                # config rows carry their name in attrname, params in name.
                name = row["name"] or row["attrname"]
                if name in IGNORED_CONFIG:
                    continue
                value = row.get("attrvalue") or row.get("value") or ""
                self._config_rows.append(
                    f"{row['type']}|{row['module']}|{name}|{value}")

    def _read_vectors(self, path):
        for row in _rows(path):
            if row["type"] != "vector":
                continue
            if row["module"]:
                self._modules.add(row["module"])
            name = row["name"]
            # A ':' in the name means it came from a @statistic declaration
            # (`queueLength:vector`), not from NetworkStatistics. Those are the
            # ones PassiveQueue.h's AFDX_PQ compiles out, so they are all empty.
            if ":" in name:
                continue
            self._vectors[name] = _floats(row["vecvalue"])

    def _discover(self):
        """Work out which VLs, switches and receivers this run contains."""
        vls, switches = set(), set()

        for name in self._vectors:
            match = PER_VL.match(name)
            if match and match.group("family") in VL_FAMILIES:
                vls.add(match.group("vl"))

            match = LATENCY_AT.match(name)
            if match:
                vl = match.group("vl")
                vls.add(vl)
                self._receivers.setdefault(vl, set()).add(int(match.group("es")))

            match = CREDIT.match(name)
            if match:
                vl = match.group("vl")
                vls.add(vl)
                self._credit_vectors.setdefault(vl, []).append(name)

            match = SWITCH_VECTOR.match(name)
            if match:
                switches.add(int(match.group("sw")))

        # Sorted by length first, so 'ff' comes before '100' -- hex ids read in
        # numeric order rather than alphabetical.
        self._vl_ids = sorted(vls, key=lambda v: (len(v), v))
        self._switch_ids = [str(s) for s in sorted(switches)]

    # ------------------------------------------------------------------ #
    # small helpers
    # ------------------------------------------------------------------ #

    def _values(self, name):
        """Recorded values of one vector; an empty tuple if it does not exist."""
        return self._vectors.get(name, ())

    def _count(self, name):
        """How many values a vector recorded, or None if it does not exist.

        None (rather than 0) matters: a vector that was never created means the
        model stopped measuring something, which the report flags. Compare with
        the drop counters below, which do default to 0.
        """
        return len(self._vectors[name]) if name in self._vectors else None

    # ------------------------------------------------------------------ #
    # what is in this run
    # ------------------------------------------------------------------ #

    def virtual_links(self):
        return self._vl_ids

    def switches(self):
        return self._switch_ids

    # ------------------------------------------------------------------ #
    # run
    # ------------------------------------------------------------------ #

    def run_sim_duration(self):
        log = self.results_dir / "run.log"
        if not log.exists():
            return None
        # The last match wins: the time-limit line is printed near the end.
        found = None
        for line in log.read_text(errors="replace").splitlines():
            match = TIME_LIMIT_LINE.search(line)
            if match:
                found = match
        return float(found.group("t")) if found else None

    def run_vl_count(self):
        return len(self._vl_ids)

    def run_switch_count(self):
        return len(self._switch_ids)

    def run_end_system_count(self):
        return len({int(i) for m in self._modules for i in MODULE_ES.findall(m)})

    def run_frames_sent(self):
        return _total(self.vl_frames_sent(vl) for vl in self._vl_ids)

    def run_frames_delivered(self):
        return _total(self.vl_frames_delivered(vl) for vl in self._vl_ids)

    def run_frames_lost(self):
        return _total(self.vl_frames_lost(vl) for vl in self._vl_ids)

    def run_config_fingerprint(self):
        digest = hashlib.sha256()
        for row in sorted(self._config_rows):
            digest.update(row.encode())
            digest.update(b"\0")
        return digest.hexdigest()

    # ------------------------------------------------------------------ #
    # per virtual link
    # ------------------------------------------------------------------ #

    def vl_frames_sent(self, vl):
        return self._count(f"TrafficSource_VL{vl}")

    def vl_receiver_count(self, vl):
        return len(self._receivers.get(vl, ())) or None

    def vl_frames_delivered(self, vl):
        return self._count(f"E2ELatency_VL{vl}")

    def vl_frames_lost(self, vl):
        sent = self.vl_frames_sent(vl)
        delivered = self.vl_frames_delivered(vl)
        if sent is None or delivered is None:
            return None
        # A multicast VL is delivered once per receiver, so the number of
        # deliveries to expect is sent x receivers, not sent. realisticNetwork
        # has 30 VLs but 54 receivers; without the factor this would read as
        # roughly -5700 lost frames.
        receivers = self.vl_receiver_count(vl) or 1
        return sent * receivers - delivered

    def vl_dropped_in_queue(self, vl):
        # 0, not None, when the vector is missing: a drop vector is only written
        # once a drop actually happens, so its absence really does mean zero.
        # Recording 0 makes a drop appearing later a changed value, and so a
        # failure, rather than a quietly new parameter.
        return len(self._values(f"DroppedFrameQueue_VL{vl}"))

    def vl_dropped_by_policer(self, vl):
        return len(self._values(f"DroppedFrameTraffPol_VL{vl}"))

    def vl_latency_max(self, vl):
        return _to_us(_max(self._values(f"E2ELatency_VL{vl}")))

    def vl_latency_mean(self, vl):
        return _to_us(_mean(self._values(f"E2ELatency_VL{vl}")))

    def vl_jitter(self, vl):
        values = self._values(f"E2ELatency_VL{vl}")
        return _to_us(max(values) - min(values)) if values else None

    def vl_bag_wait_max(self, vl):
        return _to_us(_max(self._values(f"ESBagLatency_VL{vl}")))

    def vl_credit_min(self, vl):
        # One token bucket per switch on the route, so take the worst of them.
        credits = [value
                   for name in self._credit_vectors.get(vl, [])
                   for value in self._values(name)]
        return min(credits) if credits else None

    # ------------------------------------------------------------------ #
    # per switch
    # ------------------------------------------------------------------ #

    def switch_queue_len_max(self, switch):
        return _max(self._values(f"SWQueueLength_SW{switch}"))

    def switch_queueing_time_max(self, switch):
        return _to_us(_max(self._values(f"SWQueueingTime_SW{switch}")))

    def switch_queueing_time_mean(self, switch):
        return _to_us(_mean(self._values(f"SWQueueingTime_SW{switch}")))


# --------------------------------------------------------------------------- #
# module-level helpers: they need no state, so they are plain functions
# --------------------------------------------------------------------------- #

def _rows(path):
    """Yield each row of a scavetool CSV export as a dict.

    `yield` makes this a generator: rows come out one at a time instead of the
    whole file being held in memory at once.
    """
    # A vector's samples arrive as one enormous quoted field; the csv module's
    # default limit is 128 KiB, which they exceed.
    csv.field_size_limit(sys.maxsize)
    with open(path, newline="") as handle:
        yield from csv.DictReader(handle)


def _floats(field):
    return tuple(float(x) for x in field.split()) if field and field.strip() else ()


def _max(values):
    return max(values) if values else None


def _mean(values):
    return sum(values) / len(values) if values else None


def _total(values):
    """Add up values, ignoring any that could not be measured."""
    known = [v for v in values if v is not None]
    return sum(known) if known else None
