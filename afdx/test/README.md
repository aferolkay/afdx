# AFDX regression harness

This harness answers one question: did a code change alter the observable behavior
of any of the three supplied AFDX simulations?

It runs each network with a fixed seed, extracts a deliberately small set of results,
and compares them exactly with a committed JSON baseline. It is a characterization
test: matching the baseline means "unchanged", not necessarily "correct".

`afdx/simulations/AutoNetwork.ini` is not used or modified.

## Run it

Build the simulation and `queueinglib` in the same mode, then source the OMNeT++
environment so `opp_run` and `opp_scavetool` are on `PATH`.

From `afdx/test`:

```sh
./run_tests.sh
./run_tests.sh --network SimpleNetwork
./run_tests.sh --list
```

Use `./run_tests.sh --record` only after reviewing and accepting an intentional
behavior change. It replaces all three baselines with the current results. A missing
baseline is an error and is never created implicitly.

The command exits with status 0 only when every selected network matches. A failure
identifies the virtual link or switch and shows the old and new values:

```text
SimpleNetwork  72 parameters, 71 ok, 1 FAILED

  FAIL  VL 1 latency_max (us)  baseline 497.27  actual 498.27  +1 (+0.2%), must match exactly
```

## What is compared

The fixed seed makes these runs deterministic, so every value must match exactly.
Allowing percentage drift would let a real behavior change pass unnoticed.

| Scope | Parameter | Why it matters |
|---|---|---|
| run | `sim_duration` | proves the complete scenario ran |
| each VL | `frames_sent` | traffic produced |
| each VL | `frames_delivered` | traffic received, including multicast deliveries |
| each VL | `dropped_in_queue` | congestion loss |
| each VL | `dropped_by_policer` | traffic-policy rejection |
| each VL | `latency_mean` | typical end-to-end timing |
| each VL | `latency_max` | worst end-to-end timing |
| each switch | `queueing_time_max` | worst internal congestion delay |

The VL and switch id sets are compared too. Adding or removing one therefore fails
without needing separate count parameters.

This set intentionally excludes:

- run-wide totals that duplicate the per-VL counts;
- values derived from other metrics, such as `sent - delivered`;
- configuration hashes, which describe inputs rather than behavior;
- internal algorithm state such as token-bucket credit;
- redundant queue length, jitter, and average switch delay measurements.

Keeping the primitive observations per VL avoids a different kind of blind spot:
network-wide averages can stay unchanged when one flow improves and another degrades.

## Developer API

[`harness/extractor.py`](harness/extractor.py) is the interface a simulator adapter
implements. It contains one abstract method per primitive result, plus methods that
enumerate VL and switch ids. Python will not instantiate an incomplete adapter.

The supplied [`harness/afdx.py`](harness/afdx.py) implementation reads this model's
existing OMNeT++ vectors with `opp_scavetool`; the model itself is not instrumented or
changed by the harness.

The Python comparison logic can be checked without OMNeT++:

```sh
python3 -m unittest discover -s . -p 'test_*.py'
```

The remaining files have narrow roles:

| File | Responsibility |
|---|---|
| `metrics.py` | fixed metric names, units, and meanings |
| `measure.py` | call the extractor and load/save JSON |
| `report.py` | exact comparison and readable failures |
| `__main__.py` | command-line interface |
| `run_tests.sh` | run the three simulations and invoke the Python harness |

An extractor method may return `None` when raw output is missing. Missing data is
always a failure, including when both the old and new value are missing, and the
`record` command refuses to create an incomplete baseline.

## Baselines

Each network owns one readable file:

```text
networks/basicTwoEndSystem/baseline.json
networks/simpleNetwork/baseline.json
networks/realisticNetwork/baseline.json
```

The structure mirrors the scopes above:

```json
{
  "run": {"sim_duration": 1.0},
  "switches": {"0": {"queueing_time_max": 60.27}},
  "vls": {
    "1": {
      "dropped_by_policer": 0,
      "dropped_in_queue": 0,
      "frames_delivered": 1000,
      "frames_sent": 1000,
      "latency_max": 497.27,
      "latency_mean": 497.27
    }
  }
}
```

VL ids remain in the hexadecimal form used by the raw vector names, making a failed
entry easy to locate in the simulation output.

## Scope and limitation

The three networks cover end-system delivery, multicast, routing through multiple
switches, and queueing. `basicTwoEndSystem` currently emits no switch vectors because
its `Switch[0]` naming does not satisfy the model's switch-plane detector; switch
coverage comes from the other two networks.

All three current baselines contain zero queue and policer drops. They will catch a
change that introduces a drop, but they do not exercise the code path that handles an
intentional drop. A separate overloaded scenario would be needed for that coverage.

Like any summary-based regression test, this cannot prove two complete event traces
are identical. It is designed to give a small, explainable signal for the most useful
observable AFDX outcomes.
