# AFDX regression tests

Runs the three test networks, measures a fixed set of parameters from each run, and
fails if any of them moved more than allowed.

This checks that the model is **unchanged**, not that it is **correct**. That is what
you want while refactoring: it tells you when a change you believed was harmless was
not.

`afdx/simulations/AutoNetwork.ini` is not involved and is never touched.

## Quick start

```sh
# once, and again after any C++ change (both projects must use the same MODE)
(cd ../../queueinglib && make MODE=release -j8)
(cd ..               && make makefiles && make MODE=release -j8)

# then, from this directory
source /path/to/omnetpp/setenv     # puts opp_run and opp_scavetool on PATH
./run_tests.sh
```

| Command | Meaning |
|---|---|
| `./run_tests.sh` | run all three networks and compare against their baselines |
| `./run_tests.sh --network SimpleNetwork` | just one (the folder name works too) |
| `./run_tests.sh --record` | save this run as the new baseline |
| `./run_tests.sh --list` | print every parameter and what it measures |

Exit status is 0 only if every network passed.

## Reading the result

A green run says how many parameters were checked:

```
      SimpleNetwork  144 parameters, all ok
```

A red run names each one that failed and why:

```
      SimpleNetwork  144 parameters, 142 ok, 2 FAILED

        FAIL  VL 1 latency_max (us)   baseline 497.27   actual 646.451   +149.181 (+30.0%), allowed 5%
        FAIL  VL 5 frames_delivered   baseline 1000   actual 998   -2, must match exactly
```

Every parameter either passes or fails. There is nothing in between, and nothing that
reports a difference but passes anyway.

Two failures are worth recognising on sight:

- `NOT MEASURED in this run` — the baseline has a number, this run does not. Something
  stopped recording.
- `NEW -- not in the baseline` / `GONE -- not in this run` — a whole VL or switch
  appeared or disappeared. The message names which one.

Both are what you should see if you deliberately change what the model records. Check
that the change is the one you meant, then `./run_tests.sh --record`.

## The parameters

`./run_tests.sh --list` prints the live set, straight out of `harness/metrics.py`, so it
can never fall out of date. There are three groups.

**Run** — one value each, for the whole simulation:

| Parameter | Meaning | Tolerance |
|---|---|---|
| `sim_duration` (s) | how much simulated time the run covered | exact |
| `vl_count` | how many virtual links produced output | exact |
| `switch_count` | how many switches produced output | exact |
| `end_system_count` | how many end systems produced output | exact |
| `frames_sent` | frames produced by all sources | exact |
| `frames_delivered` | deliveries at all sinks | exact |
| `frames_lost` | expected deliveries minus actual | exact |
| `config_fingerprint` | hash of every resolved config value | exact |

**Per virtual link** — a VL is one logical AFDX flow: a fixed route from one sender to
one or more receivers, with a guaranteed share of the bandwidth.

| Parameter | Meaning | Tolerance |
|---|---|---|
| `frames_sent` | frames the source produced for this VL | exact |
| `receiver_count` | how many end systems receive it; >1 means multicast | exact |
| `frames_delivered` | deliveries at sinks | exact |
| `frames_lost` | `frames_sent × receiver_count − frames_delivered` | exact |
| `dropped_in_queue` | frames thrown away because a switch queue was full | exact |
| `dropped_by_policer` | frames rejected by the rate limiter | exact |
| `latency_max` (µs) | worst delay from source to sink | 5% |
| `latency_mean` (µs) | average delay from source to sink | 1% |
| `jitter` (µs) | worst delay minus best | 10% |
| `bag_wait_max` (µs) | worst wait for the VL's BAG slot | 5% |
| `credit_min` (bits) | lowest token-bucket credit; negative means a rejection | 5% |

**Per switch:**

| Parameter | Meaning | Tolerance |
|---|---|---|
| `queue_len_max` (bits) | largest backlog inside the switch | 5% |
| `queueing_time_max` (µs) | worst wait inside the switch | 5% |
| `queueing_time_mean` (µs) | average wait inside the switch | 1% |

Counts are exact because a changed frame count is behaviour, not rounding. Averages get
1% because they are taken over hundreds of frames and barely move. Maxima get 5% because
a single unlucky frame shifts them, and jitter gets 10% because it is the difference of
two extremes and so inherits the wobble of both.

Three terms in the table:

- **BAG** — Bandwidth Allocation Gap: the minimum time an end system must leave between
  two frames of the same VL. `bag_wait_max` is how long a frame waited for its turn.
- **Token bucket** — the rate limiter's budget, measured in bits. Every frame spends
  some; the budget refills over time. `credit_min` going negative means a frame was
  rejected, so it and `dropped_by_policer` check each other.
- **Policer** — the part of a switch that enforces that budget.

## Baselines

One JSON file per network, at `networks/<name>/baseline.json`:

```json
{
  "run":      { "vl_count": 11, "frames_sent": 7750 },
  "switches": { "0": { "queue_len_max": 12032.0 } },
  "vls":      { "1": { "frames_sent": 1000, "latency_max": 497.27 } }
}
```

Committed, and small enough to read in a review: 19 parameters for
`basicTwoEndSystem`, 144 for `simpleNetwork`, 353 for `realisticNetwork`.

VL ids are hex, exactly as they appear in the raw `.vec` file, so you can grep a
baseline entry straight back to the simulation output.

## The code

Six small files in `harness/`.

| File | Job |
|---|---|
| `metrics.py` | **the parameter set — this is the file you edit by hand** |
| `extractor.py` | the API a model must implement, one empty method per parameter |
| `afdx.py` | that API, implemented for this model |
| `measure.py` | runs the spec against an extractor; saves and loads baselines |
| `report.py` | compares two sets of measurements and prints the result |
| `__main__.py` | the command line |

Each parameter is one line in `metrics.py`, carrying its name, unit, meaning and
tolerance together:

```python
Metric("latency_max", "us",
       "worst end-to-end delay, from source to sink", tolerance=0.05),
```

To loosen a tolerance, change the number. To stop testing a parameter, delete the line.
There is no separate tolerance file and no pattern matching.

### Adding a parameter

1. Add one `Metric(...)` line to the right list in `metrics.py`.
2. Add the matching `@abstractmethod` to `extractor.py`.
3. Implement it in `afdx.py`.
4. `./run_tests.sh --record`, read the diff, commit.

The method name is the metric name with its group as a prefix — `latency_max` in
`VL_METRICS` is `vl_latency_max(self, vl)`. `measure.py` looks the method up by that
name, which is why nothing between the spec and the implementation needs changing.

### Testing a different model

Subclass `Extractor`, fill in every method, and pass your subclass to `measure()`.
Python refuses to create an instance of a subclass that missed one, so the list in
`extractor.py` is enforced rather than merely documented. `afdx.py` is a complete
worked example; most of its methods are one line.

Return `None` from any method whose value this run cannot supply. The report calls
that `NOT MEASURED`, which is a failure — if something used to be measurable and no
longer is, you want to hear about it.

### Where the numbers come from

The model records everything through `NetworkStatistics`, which creates a raw
`cOutVector` named after what it measures. `afdx.py` runs `opp_scavetool` to export
those to CSV, then reduces each series to a single number.

| Parameter | Vector | Written at |
|---|---|---|
| `frames_sent` | `TrafficSource_VL<hex>` | `AFDXMarshall.cc:75` |
| `frames_delivered` | `E2ELatency_VL<hex>` | `Sink_ext.cc:27` |
| `receiver_count` | `LatencyAt#ES<n>_VL<hex>` | `Sink_ext.cc:28` |
| `latency_*`, `jitter` | `E2ELatency_VL<hex>` | `Sink_ext.cc:27` |
| `bag_wait_max` | `ESBagLatency_VL<hex>` | `RedundancyController.cc:29` |
| `dropped_in_queue` | `DroppedFrameQueue_VL<hex>` | `PassiveQueue.cc:78` |
| `dropped_by_policer` | `DroppedFrameTraffPol_VL<hex>` | `TrafficPolicy.cc:88` |
| `credit_min` | `TokenBucketCredit#SW<n>_VL<hex>` | `TrafficPolicy.cc:49-79` |
| `queue_len_max` | `SWQueueLength_SW<n>` | `PassiveQueue.cc:104-195` |
| `queueing_time_*` | `SWQueueingTime_SW<n>` | `PassiveQueue.cc:128-183` |

Nothing was added to the model to support this. Instrumenting `NetworkStatistics` to
report on itself would make the thing being tested its own witness, and would need a
rebuild before you could measure anything.

## Two things to know when reading a baseline

**`frames_lost` is not the same as "dropped".** At the 1s cut-off some frames are still
in flight, so a VL can show 999 delivered against 1000 sent with no drops anywhere.
`dropped_in_queue` and `dropped_by_policer` are the real loss counters.

**Multicast is why `receiver_count` exists.** `realisticNetwork` has 30 VLs but 54
receivers, and a delivery is recorded once per receiver. Without the multiplication,
`frames_lost` would read about −5700.

## Known quirks in the model, baselined as they are

**`basicTwoEndSystem` records nothing from its switches**, so its baseline has an empty
`switches` section and `switch_count` is 0.
`NetworkStatistics::getSwitchDefinition` (`NetworkStatistics.cc:383`) reads the
character right after `"Switch"` in the module path to tell plane A from plane B. That
network names its switches `Switch[0]` and `Switch[1]`, so it reads `[`, decides "not
plane A" on both planes, and every switch metric is gated off. Switch coverage
therefore rests on `simpleNetwork` and `realisticNetwork`; `basicTwoEndSystem` is an
end-system test.

If that is ever fixed, the network's switch parameters appear and the report says
`NEW -- not in the baseline`, which is the correct signal rather than a mystery.

**`queueLength`, `dropped` and `queueingTime` are declared but never emitted.**
`afdx/src/PassiveQueue.ned:20-25` declares them, but `PassiveQueue.h:13` defines
`AFDX_PQ` unconditionally, so the branch that would emit them never compiles. They
produce 64 empty vectors per run in `simpleNetwork`. The harness ignores them.

## Deliberately not measured

- **Per-port queue length.** `SWQueueLength#Port<p>_SW<n>` looks per-port, but
  `queueCounterInBitPerSwitch` (`NetworkStatistics.h:142`) is keyed on the switch index
  alone, so every port of a switch reports the same switch-wide backlog.
- **Per-port queueing time.** Real, but it only localises a worst case the per-switch
  parameter already catches.
- **`scheduler_busy`.** 0 in all three networks, because every ini sets
  `**.scheduler.serviceTime = 0s`.
- **A hash of the raw sample series.** It would catch reorderings that a maximum and a
  mean cannot see, but it fails without being able to say why, which is not worth it.

That last one is a real limit: two frames whose latencies shift by +1µs and −1µs leave
every parameter here untouched.

## Not implemented

- **Fingerprints** (`fingerprint = ...` in the ini): one line that catches any change in
  event ordering, including the frames `IntegrityChecker.cc:70` and
  `RedundancyChecker.cc:52` delete without recording anything.
- **Invariants**: frame conservation per VL, and BAG enforcement.
  `networks/simpleNetwork/docs/requirements.md` already lists published worst-case
  per-VL latency bounds to check against.
