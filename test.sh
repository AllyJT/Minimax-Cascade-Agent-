#!/bin/bash
GAMES=10

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------
# vs random (RED)
AVR_W=0; AVR_L=0; AVR_D=0
# vs random (BLUE)
AVB_W=0; AVB_L=0; AVB_D=0
# vs greedy (RED)
AGR_W=0; AGR_L=0; AGR_D=0
# vs greedy (BLUE)
AGB_W=0; AGB_L=0; AGB_D=0
# vs minimax (RED)
AMR_W=0; AMR_L=0; AMR_D=0
# vs minimax (BLUE)
AMB_W=0; AMB_L=0; AMB_D=0

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
run_game() {
    local red=$1
    local blue=$2
    python -m referee "$red" "$blue" 2>&1
}

record() {
    local result=$1
    local win_color=$2   # the color our agent is playing
    local w_var=$3
    local l_var=$4
    local d_var=$5

    if echo "$result" | grep -q "winner is $win_color"; then
        eval "$w_var=\$((\$$w_var + 1))"
    elif echo "$result" | grep -qE "winner is (RED|BLUE)"; then
        eval "$l_var=\$((\$$l_var + 1))"
    else
        eval "$d_var=\$((\$$d_var + 1))"
    fi
}

# ---------------------------------------------------------------------------
echo "========================================"
echo "TEST 1: agent (RED) vs random_agent (BLUE)"
echo "========================================"
for i in $(seq 1 $GAMES); do
    echo -n "  Game $i ... "
    result=$(run_game agent random_agent)
    record "$result" RED AVR_W AVR_L AVR_D
    echo "$result" | grep -oE "winner is (RED|BLUE)|draw" | tail -1
done
echo "  W $AVR_W / L $AVR_L / D $AVR_D"

# ---------------------------------------------------------------------------
echo ""
echo "========================================"
echo "TEST 2: random_agent (RED) vs agent (BLUE)"
echo "========================================"
for i in $(seq 1 $GAMES); do
    echo -n "  Game $i ... "
    result=$(run_game random_agent agent)
    record "$result" BLUE AVB_W AVB_L AVB_D
    echo "$result" | grep -oE "winner is (RED|BLUE)|draw" | tail -1
done
echo "  W $AVB_W / L $AVB_L / D $AVB_D"

# ---------------------------------------------------------------------------
echo ""
echo "========================================"
echo "TEST 3: agent (RED) vs greedy_agent (BLUE)"
echo "========================================"
for i in $(seq 1 $GAMES); do
    echo -n "  Game $i ... "
    result=$(run_game agent greedy_agent)
    record "$result" RED AGR_W AGR_L AGR_D
    echo "$result" | grep -oE "winner is (RED|BLUE)|draw" | tail -1
done
echo "  W $AGR_W / L $AGR_L / D $AGR_D"

# ---------------------------------------------------------------------------
echo ""
echo "========================================"
echo "TEST 4: greedy_agent (RED) vs agent (BLUE)"
echo "========================================"
for i in $(seq 1 $GAMES); do
    echo -n "  Game $i ... "
    result=$(run_game greedy_agent agent)
    record "$result" BLUE AGB_W AGB_L AGB_D
    echo "$result" | grep -oE "winner is (RED|BLUE)|draw" | tail -1
done
echo "  W $AGB_W / L $AGB_L / D $AGB_D"

# ---------------------------------------------------------------------------
echo ""
echo "========================================"
echo "TEST 5: agent (RED) vs minimax_agent (BLUE)"
echo "========================================"
for i in $(seq 1 $GAMES); do
    echo -n "  Game $i ... "
    result=$(run_game agent minimax_agent)
    record "$result" RED AMR_W AMR_L AMR_D
    echo "$result" | grep -oE "winner is (RED|BLUE)|draw" | tail -1
done
echo "  W $AMR_W / L $AMR_L / D $AMR_D"

# ---------------------------------------------------------------------------
echo ""
echo "========================================"
echo "TEST 6: minimax_agent (RED) vs agent (BLUE)"
echo "========================================"
for i in $(seq 1 $GAMES); do
    echo -n "  Game $i ... "
    result=$(run_game minimax_agent agent)
    record "$result" BLUE AMB_W AMB_L AMB_D
    echo "$result" | grep -oE "winner is (RED|BLUE)|draw" | tail -1
done
echo "  W $AMB_W / L $AMB_L / D $AMB_D"

# ---------------------------------------------------------------------------
# Totals
# ---------------------------------------------------------------------------
RANDOM_W=$((AVR_W + AVB_W))
RANDOM_L=$((AVR_L + AVB_L))
RANDOM_D=$((AVR_D + AVB_D))

GREEDY_W=$((AGR_W + AGB_W))
GREEDY_L=$((AGR_L + AGB_L))
GREEDY_D=$((AGR_D + AGB_D))

MINI_W=$((AMR_W + AMB_W))
MINI_L=$((AMR_L + AMB_L))
MINI_D=$((AMR_D + AMB_D))

TOTAL_W=$((RANDOM_W + GREEDY_W + MINI_W))
TOTAL_G=$((GAMES * 6))

echo ""
echo "========================================"
echo "FINAL SUMMARY  (W / L / D  out of $((GAMES * 2)) games each)"
echo "========================================"
echo "vs random_agent:  $RANDOM_W W / $RANDOM_L L / $RANDOM_D D"
echo "vs greedy_agent:  $GREEDY_W W / $GREEDY_L L / $GREEDY_D D"
echo "vs minimax_agent: $MINI_W W / $MINI_L L / $MINI_D D"
echo "----------------------------------------"
echo "total agent wins: $TOTAL_W / $TOTAL_G"