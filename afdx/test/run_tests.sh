#!/usr/bin/env bash
#
# AFDX regression tests.
#
# For each network: run the simulation, check it behaved sanely, then measure the
# parameter set in harness/metrics.py and compare it against the saved baseline.
#
#   ./run_tests.sh                          all networks
#   ./run_tests.sh --network SimpleNetwork  just one (folder name also works)
#   ./run_tests.sh --record                 save this run as the new baseline
#   ./run_tests.sh --list                   print every parameter and what it measures
#
# Exit status is 0 only if every network passed.
#
set -uo pipefail

cd "$(dirname "$0")" || exit 1
TEST_DIR=$PWD
SIM=$TEST_DIR/../src/afdx
QUEUEINGLIB=$TEST_DIR/../../queueinglib

# Folder and config names differ in the networks as authored, so the mapping is
# written out rather than derived. "folder:config"
NETWORKS=(
    "basicTwoEndSystem:BasicTwoEndSystems"
    "simpleNetwork:SimpleNetwork"
    "realisticNetwork:realisticNetwork"
)

ONLY=""
RECORD=0

while [ $# -gt 0 ]; do
    case "$1" in
        --network)
            [ $# -ge 2 ] || { echo "--network requires a name" >&2; exit 2; }
            ONLY=$2
            shift 2
            ;;
        --record)   RECORD=1; shift ;;
        --list)     python3 -m harness list; exit 0 ;;
        -h|--help)  sed -n '2,14p' "$0"; exit 0 ;;
        *)          echo "unknown option: $1" >&2; exit 2 ;;
    esac
done

if [ -n "$ONLY" ]; then
    found=0
    for entry in "${NETWORKS[@]}"; do
        folder=${entry%%:*}
        config=${entry##*:}
        if [ "$ONLY" = "$folder" ] || [ "$ONLY" = "$config" ]; then
            found=1
            break
        fi
    done
    if [ $found -eq 0 ]; then
        echo "unknown network: $ONLY" >&2
        exit 2
    fi
fi

# ---------------------------------------------------------------------------
# environment
# ---------------------------------------------------------------------------
# Work out where OMNeT++ is from what is on PATH, rather than hardcoding a path.
if ! command -v opp_run >/dev/null 2>&1; then
    echo "error: opp_run not on PATH -- source the OMNeT++ setenv script first" >&2
    exit 2
fi
OMNETPP_BIN=$(dirname "$(command -v opp_run)")
OMNETPP_ROOT=$(dirname "$OMNETPP_BIN")

# opp_scavetool links against liboppscave_dbg.so; without lib/ on the loader path
# it dies with "cannot open shared object file". queueinglib is needed by the model.
export LD_LIBRARY_PATH="$OMNETPP_ROOT/lib:$QUEUEINGLIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PATH="$OMNETPP_BIN:$PATH"

if [ ! -x "$SIM" ]; then
    echo "error: $SIM not built. Build both projects in the same MODE:" >&2
    echo "         (cd ../../queueinglib && make MODE=release -j8)" >&2
    echo "         (cd .. && make makefiles && make MODE=release -j8)" >&2
    exit 2
fi

# Things the model prints when one of its own invariants breaks. Any of these
# means the run is not worth measuring, even if it exited 0.
BAD_PATTERNS='VL Table Not Found|Invalid VL Table|Key Not Found in VL Table|Max limit for VLID queue|was not correctly reserved|This should not happen|Not found - 3\.|NetworkStatistics::.*default|<!> Error|Fatal|terminate called'

FAILED=()
PASSED=()

for entry in "${NETWORKS[@]}"; do
    folder=${entry%%:*}
    config=${entry##*:}
    [ -n "$ONLY" ] && [ "$ONLY" != "$config" ] && [ "$ONLY" != "$folder" ] && continue

    net_dir=$TEST_DIR/networks/$folder
    results=$net_dir/results
    baseline=$net_dir/baseline.json
    log=$results/run.log

    echo "==================================================================="
    echo "$config  ($folder)"
    echo "==================================================================="

    rm -rf "$results"
    mkdir -p "$results"

    # --- run ----------------------------------------------------------------
    # The working directory must stay TEST_DIR: the route-table paths inside the
    # network .ini files are relative to it (VLRouter opens them with a plain
    # ifstream).
    "$SIM" -u Cmdenv -c "$config" -n .:../src:../../queueinglib \
           --result-dir="networks/$folder/results" regression.ini >"$log" 2>&1
    rc=$?

    ok=1
    if [ $rc -ne 0 ]; then
        echo "      FAIL: simulation exited $rc (see $log)"
        tail -15 "$log" | sed 's/^/        /'
        ok=0
    fi

    if grep -qE "$BAD_PATTERNS" "$log"; then
        echo "      FAIL: the model reported an internal problem:"
        grep -oE "$BAD_PATTERNS" "$log" | sort | uniq -c | sed 's/^/        /'
        ok=0
    fi

    if ! grep -q "Simulation time limit reached" "$log"; then
        echo "      FAIL: the run did not reach the time limit (ended early?)"
        ok=0
    fi

    for ext in sca vec; do
        if ! ls "$results"/*."$ext" >/dev/null 2>&1 || \
           [ ! -s "$(ls "$results"/*."$ext" 2>/dev/null | head -1)" ]; then
            echo "      FAIL: no non-empty .$ext file was produced"
            ok=0
        fi
    done

    if [ $ok -eq 0 ]; then
        FAILED+=("$config")
        continue
    fi
    echo "      ran to t=1s, exit 0, results written"

    # --- measure, then record or compare -------------------------------------
    if [ $RECORD -eq 1 ]; then
        if python3 -m harness record "$results" "$baseline" \
                --label "$config" --indent "      "; then
            PASSED+=("$config")
        else
            FAILED+=("$config")
        fi
        continue
    fi

    if [ ! -f "$baseline" ]; then
        echo "      FAIL: no baseline at $baseline (use --record deliberately)"
        FAILED+=("$config")
        continue
    fi

    if python3 -m harness check "$results" "$baseline" \
            --label "$config" --indent "      "; then
        PASSED+=("$config")
    else
        FAILED+=("$config")
    fi
done

echo
echo "==================================================================="
echo "passed: ${#PASSED[@]}  ${PASSED[*]}"
if [ ${#FAILED[@]} -gt 0 ]; then
    echo "FAILED: ${#FAILED[@]}  ${FAILED[*]}"
    exit 1
fi
echo "all good"
