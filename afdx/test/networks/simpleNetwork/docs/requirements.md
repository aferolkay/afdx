# simpleNetwork — Requirements

Derived from `topology.png` (Figure 6.1: Example Network Configuration With Virtual Links) and
`virtual-link-description.png` (Table 6.1: Message Set and End-to-End Delays), cross-checked against the
`afdx` OMNeT++ component library this project depends on (`AFDX-master/afdx`, referenced by this project's
`.project` and used by `simulations/networks/basicTwoEndSystem`).

**Note on the folder name:** the docs originally lived in `simulations/networks/simple-network/`. OMNeT++'s
NED loader requires every folder segment of a NED source path to be a valid NED identifier once any `.ned`
file lives there (letters/digits/underscore only) — verified directly with `opp_nedtool`/`opp_run`, which
both hard-error (`Declared package '...' does not match...` / syntax error) on a hyphen. The folder was
renamed to `simulations/networks/simpleNetwork/` (matching the existing `basicTwoEndSystem` naming
convention) so the network's `.ned`/`.ini` files could live alongside these docs.

## 1. Topology

7 end systems (E0–E6), 5 switches (S1–S5). Node degree and per-link VL sets were cross-validated against
Table 6.1's source/destination columns (every VL's path was checked to start at its `Ea` end system and
terminate at its `Eb` end system through a consistent set of switch hops) — all 11 VLs check out with no
contradictions, so the topology below should be an exact reconstruction of the figure, not a guess.

```
E0 ─────┐                                   ┌───── E3
        │                                   │
E1 ──── S1 ──────── S2 ──────── S4 ──────── E2
                     │           │
                    S3          S5
                   /   \         │
                 E5     E4      E6
```

(S3 hangs off S1, not S2 — see edge list below for exact attachment.)

### Edge list (port ↔ port), with per-direction VL sets

| Link | Direction | VLs carried |
|---|---|---|
| E0 – S1 | E0 → S1 | V1, V2, V12 |
| E0 – S1 | S1 → E0 | V5 |
| E1 – S1 | E1 → S1 | V5 |
| E1 – S1 | S1 → E1 | V14 |
| E4 – S3 | E4 → S3 | V8, V9, V13 |
| E5 – S3 | E5 → S3 | V6, V7 |
| S3 – S1 | S3 → S1 | V6, V7, V8, V9, V13 |
| S1 – S2 | S1 → S2 | V1, V2, V6, V7, V8, V9, V12, V13 |
| S1 – S2 | S2 → S1 | V14 |
| S2 – E3 | S2 → E3 | V1, V6, V11 |
| S2 – S4 | S2 → S4 | V2, V7, V8, V9, V12, V13 |
| S2 – S4 | S4 → S2 | V11, V14 |
| S4 – E2 | S4 → E2 | V2, V7, V8, V9, V12, V13 |
| S4 – E2 | E2 → S4 | V11 |
| S4 – S5 | S5 → S4 | V14 |
| S5 – E6 | E6 → S5 | V14 |

No link carries traffic in both directions except E0–S1 and E1–S1 (both local to S1) and S1–S2 / S2–S4
(trunk links, asymmetric traffic in each direction).

### Port count per switch

| Switch | Ports | Attached to |
|---|---|---|
| S1 | 4 | E0, E1, S2, S3 |
| S2 | 3 | S1, S4, E3 |
| S3 | 3 | S1, E4, E5 |
| S4 | 3 | S2, S5, E2 |
| S5 | 2 | S4, E6 |

## 2. Virtual links (from Table 6.1)

| VL | Frame size `p` (bytes) | Source `Ea` | Dest `Eb` | BAG (ms) | Offset `O` (µs) | Published theoretical E2E delay `c` (µs) |
|---|---|---|---|---|---|---|
| V1 | 1183 | E0 | E3 | 1 | 0 | 482.32 |
| V2 | 572 | E0 | E2 | 2 | 1524.44 | 365.32 |
| V5 | 375 | E1 | E0 | 1 | 0 | 136.8 |
| V6 | 842 | E5 | E3 | 1 | 0 | 575.28 |
| V7 | 750 | E5 | E2 | 1 | 503.68 | 590.64 |
| V8 | 1042 | E4 | E2 | 2 | 482.84 | 691.44 |
| V9 | 618 | E4 | E2 | 1 | 0 | 521.84 |
| V11 | 240 | E2 | E3 | 4 | 0 | 267.28 |
| V12 | 600 | E0 | E2 | 2 | 523.32 | 374.28 |
| V13 | 618 | E4 | E2 | 2 | 1500 | 521.84 |
| V14 | 240 | E6 | E1 | 2 | 0 | 222.52 |

The last column (`c_actual` / `c_Vi`, identical in the table) is the paper's own worst-case end-to-end delay
bound for each VL — not a simulation input. It's kept here as a validation target: once the model runs, the
simulated max per-VL latency should sit at or below these numbers.

### Per-end-system source VL sets (drives `messageCount` and per-index VL assignment)

| End system | VLs sourced (→ `messageSource[]`/`afdxMarshall[]` index) |
|---|---|
| E0 | V1(0), V2(1), V12(2) |
| E1 | V5(0) |
| E2 | V11(0) |
| E3 | — (sink only, `messageCount=0`) |
| E4 | V8(0), V9(1), V13(2) |
| E5 | V6(0), V7(1) |
| E6 | V14(0) |

## 3. Per-switch VL routing tables (derived from §1, format matches `switchRouteTable.txt`)

`S1.txt` (ports: 0=E0, 1=E1, 2=S2, 3=S3)
```
0x1 : {2}      // V1  -> S2
0x2 : {2}      // V2  -> S2
0x5 : {0}      // V5  -> E0
0x6 : {2}      // V6  -> S2 (relayed from S3)
0x7 : {2}      // V7  -> S2
0x8 : {2}      // V8  -> S2
0x9 : {2}      // V9  -> S2
0xD : {2}      // V13 -> S2
0xC : {2}      // V12 -> S2
0xE : {1}      // V14 -> E1
```

`S2.txt` (ports: 0=S1, 1=S4, 2=E3)
```
0x1 : {2}      // V1  -> E3
0x6 : {2}      // V6  -> E3
0xB : {2}      // V11 -> E3
0x2 : {1}      // V2  -> S4
0x7 : {1}      // V7  -> S4
0x8 : {1}      // V8  -> S4
0x9 : {1}      // V9  -> S4
0xC : {1}      // V12 -> S4
0xD : {1}      // V13 -> S4
0xE : {0}      // V14 -> S1
```

`S3.txt` (ports: 0=S1, 1=E4, 2=E5)
```
0x6 : {0}      // V6  -> S1
0x7 : {0}      // V7  -> S1
0x8 : {0}      // V8  -> S1
0x9 : {0}      // V9  -> S1
0xD : {0}      // V13 -> S1
```

`S4.txt` (ports: 0=S2, 1=S5, 2=E2)
```
0x2 : {2}      // V2  -> E2
0x7 : {2}      // V7  -> E2
0x8 : {2}      // V8  -> E2
0x9 : {2}      // V9  -> E2
0xC : {2}      // V12 -> E2
0xD : {2}      // V13 -> E2
0xB : {0}      // V11 -> S2
0xE : {0}      // V14 -> S2
```

`S5.txt` (ports: 0=S4, 1=E6)
```
0xE : {0}      // V14 -> S4
```

Note: `VLRouter` (the component behind each switch's routing) throws a runtime error for any VL ID that
arrives without a table entry — every VL that can ever reach a given switch must be listed, including
pure pass-through VLs. The tables above were built to cover exactly that for all 5 switches.

## 4. Decisions taken (confirmed with the user before implementing)

1. **Redundancy: dual A/B network.** Built as a genuine dual-redundant AFDX network, matching the `afdx`
   library's `EndSystem`/`RedundancyController`/`RedundancyChecker` design (and `basicTwoEndSystem`'s
   convention) — `SwitchA[5]`/`SwitchB[5]` are two mirrored planes with identical topology/routing, and
   every end system's `ethPortA`/`ethPortB` connect one to each plane. This goes beyond what `topology.png`
   draws (a single plane) but matches how this component library is meant to be used.

2. **Frame size: `p_i` is payload, header adds on top.** `messageSource[i].packetLength = p_i` (the table
   value) and `frameHeaderLength = 47` (matching `basicTwoEndSystem`'s convention) — the wire frame is
   `p_i + 47` bytes, `p_i` bytes is the application payload.

3. **Switch ingress traffic policing (`rho`/`sigma`).** Started from the textbook AFDX arrival-curve
   formula, `σ = Lmax` (bits, `Lmax` = wire frame incl. the 47B header + 20B phy overhead used internally
   by `TrafficPolicy`) and `ρ = Lmax / BAG`. **This was empirically wrong** — running the model with the
   exact-equality `σ = Lmax` caused `TrafficPolicy` to drop the large majority of frames for every VL from
   the second hop onward (verified: 1598 drops in a 500ms run). Root cause: `TrafficPolicy` re-polices a VL
   at *every* switch hop, and each hop's egress port multiplexes several VLs onto one physical link —
   between hops, a VL's frames get reshaped away from perfectly-periodic spacing by that multiplexing, so
   an exactly-one-frame burst allowance has zero margin for the jitter this introduces. `basicTwoEndSystem`'s
   own rho/sigma values already carry a large margin over the textbook minimum (~3.3x on sigma) for the same
   reason, on a topology with far less multiplexing than this one.

   **Fix:** kept `ρ = Lmax / BAG` (the correct sustained rate — this shouldn't need padding), and raised
   `σ` to `4 × Lmax`. This was the smallest margin that produced **zero drops** over a 5-second run
   (390k+ frames created) across every VL and every switch hop in the topology; verified by running the
   actual compiled model (`afdxSimulations_dbg`), not just by inspecting the NED/ini. See
   `simpleNetwork.ini`'s traffic-generation section for the final per-VL numbers.

4. **Priority / traffic class.** Left at the default priority for all VLs (single queue effectively),
   since neither doc distinguishes any VL by priority.

5. **Cosmetic marshalling fields** (`networkId`, `equipmentId`, `interfaceId`, `seqNum`, UDP ports) reuse
   `basicTwoEndSystem.ini`'s defaults, with `equipmentId` set per end-system index — these don't affect
   routing or timing, only `virtualLinkId` does.

6. **VL numeric IDs.** `Vn` maps to integer `n` directly (`V14` → `virtualLinkId = 14`, route-table key
   `0xE`), rather than an unrelated scheme like `basicTwoEndSystem`'s `0x1000`/`0x2000`.

## 5. Delivered files

- `simulations/networks/simpleNetwork/simpleNetwork.ned` — the 7 ES + dual-redundant 5-switch (×2 planes)
  topology from §1.
- `simulations/networks/simpleNetwork/simpleNetwork.ini` — per-VL `BAG`, `startTime` (= offset),
  `packetLength`, `virtualLinkId`, `rho`, `sigma`, plus the shared/global settings and per-instance
  structural sizing (`noOfPorts`, `messageCount`).
- `simulations/networks/simpleNetwork/S1.txt` … `S5.txt` — the routing tables from §3 (shared by both
  redundant planes, since they're topologically identical).

Validated by actually running the compiled `afdxSimulations_dbg` binary against `simpleNetwork.ini` for a
5-second simulated run: no NED/config errors, no `VLRouter` "key not found" errors, no `TrafficPolicy`
drops, no `RegulatorLogic` queue-overflow errors.

### Running it

```sh
cd simulations
../src/afdxSimulations_dbg \
  -n .:../src:<path-to-AFDX-master>/afdx/src:<path-to-AFDX-master>/queueinglib \
  -u Cmdenv -c SimpleNetwork -r 0 --sim-time-limit=1s \
  networks/simpleNetwork/simpleNetwork.ini
```

(`basicTwoEndSystem`'s own `simulations/run` script only passes `-n .:../src`, which is missing the `afdx`/
`queueinglib` NED paths needed to resolve `afdx.EndSystem` etc. from the command line — it works from the
OMNeT++ IDE because the IDE resolves project references itself. The `-n` list above is what actually worked
in a from-scratch shell run.)
