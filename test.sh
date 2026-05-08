#!/bin/bash
NEW_WINS=0
OLD_WINS=0
OLD_DRAWS=0
GAMES=20

echo "========================================"
echo "TEST 1: agent (RED) vs old_agent (BLUE)"
echo "========================================"
for i in $(seq 1 $GAMES); do
    echo "Game $i"
    result=$(python -m referee agent old_agent 2>&1)
    echo "$result"
    
    if echo "$result" | grep -q "winner is RED"; then
        NEW_WINS=$((NEW_WINS + 1))
    elif echo "$result" | grep -q "winner is BLUE"; then
        OLD_WINS=$((OLD_WINS + 1))
    else
        OLD_DRAWS=$((OLD_DRAWS + 1))
    fi
done

echo "========================"
echo "agent wins:     $NEW_WINS/$GAMES"
echo "old_agent wins: $OLD_WINS/$GAMES"
echo "draws:          $OLD_DRAWS/$GAMES"


echo ""
echo "=========================================="
echo "TEST 2: agent (RED) vs random_agent (BLUE)"
echo "=========================================="
AGENT_VS_RANDOM=0
RANDOM_VS_AGENT=0

for i in $(seq 1 $GAMES); do
    echo "Game $i"
    result=$(python -m referee agent random_agent 2>&1)
    echo "$result"
    
    if echo "$result" | grep -q "winner is RED"; then
        AGENT_VS_RANDOM=$((AGENT_VS_RANDOM + 1))
    else
        RANDOM_VS_AGENT=$((RANDOM_VS_AGENT + 1))
    fi
done

echo "========================"
echo "agent wins:        $AGENT_VS_RANDOM/$GAMES"
echo "random_agent wins: $RANDOM_VS_AGENT/$GAMES"


echo ""
echo "============================================"
echo "TEST 3: random_agent (RED) vs agent (BLUE)"
echo "============================================"
RANDOM_RED_WINS=0
AGENT_BLUE_WINS=0

for i in $(seq 1 $GAMES); do
    echo "Game $i"
    result=$(python -m referee random_agent agent 2>&1)
    echo "$result"
    
    if echo "$result" | grep -q "winner is BLUE"; then
        AGENT_BLUE_WINS=$((AGENT_BLUE_WINS + 1))
    else
        RANDOM_RED_WINS=$((RANDOM_RED_WINS + 1))
    fi
done

echo "========================"
echo "agent wins (BLUE):        $AGENT_BLUE_WINS/$GAMES"
echo "random_agent wins (RED):  $RANDOM_RED_WINS/$GAMES"


# echo ""
# echo "========================================"
# echo "TEST 4: agent (RED) vs minimax_agent (BLUE)"
# echo "========================================"
# AGENT_VS_MINI=0
# MINI_VS_AGENT=0
# MINI_DRAWS=0

# for i in $(seq 1 $GAMES); do
#     echo "Game $i"
#     result=$(python -m referee agent minimax_agent 2>&1)
#     echo "$result"
#     if echo "$result" | grep -q "winner is RED"; then
#         AGENT_VS_MINI=$((AGENT_VS_MINI + 1))
#     elif echo "$result" | grep -q "winner is BLUE"; then
#         MINI_VS_AGENT=$((MINI_VS_AGENT + 1))
#     else
#         MINI_DRAWS=$((MINI_DRAWS + 1))
#     fi
# done

echo "========================"
echo "agent wins:         $AGENT_VS_MINI/$GAMES"
echo "minimax_agent wins: $MINI_VS_AGENT/$GAMES"
echo "draws:              $MINI_DRAWS/$GAMES"


echo ""
echo "========================================"
echo "FINAL SUMMARY"
echo "========================================"
echo "agent vs old_agent:     $NEW_WINS W / $OLD_WINS L / $OLD_DRAWS D  (out of $GAMES)"
echo "agent vs random (RED):  $AGENT_VS_RANDOM W / $RANDOM_VS_AGENT L   (out of $GAMES)"
echo "agent vs random (BLUE): $AGENT_BLUE_WINS W / $RANDOM_RED_WINS L   (out of $GAMES)"
echo "agent vs minimax:       $AGENT_VS_MINI W / $MINI_VS_AGENT L / $MINI_DRAWS D  (out of $GAMES)"
TOTAL_AGENT=$((NEW_WINS + AGENT_VS_RANDOM + AGENT_BLUE_WINS + AGENT_VS_MINI))
TOTAL_GAMES=$((GAMES * 4))
echo "------------------------"
echo "agent total: $TOTAL_AGENT/$TOTAL_GAMES"