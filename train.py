# train.py
# Run this ONCE offline to produce agent/weights.npy
# Usage: python train.py
#
# Plays self-play games at shallow depth for speed,
# collects (features, outcome) pairs, fits linear regression,
# saves weights to agent/weights.npy

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

from referee.game import PlayerColor
from agent.state import GameState, get_legal_moves
from agent.features import extract_features
from agent.game_algorithm import get_best_move
from agent.game_algorithm import minimax, order_moves


# ── config ────────────────────────────────────────────────────────────────────
NUM_GAMES      = 50    # number of self-play games
SAMPLE_EVERY   = 3      # record state every N turns
MAX_TURNS      = 80    # cap per game to keep things moving
TIME_PER_MOVE  = 0.3   # seconds per move during self-play (keeps it fast)
OUTPUT_FILE    = os.path.join("agent", "weights.npy")
# ─────────────────────────────────────────────────────────────────────────────


from agent.game_algorithm import minimax, order_moves

def play_game():
    state = GameState()
    records = []

    for turn in range(MAX_TURNS):
        if state.is_terminal():
            break

        if turn % SAMPLE_EVERY == 0:
            red_features  = extract_features(state, PlayerColor.RED)
            blue_features = extract_features(state, PlayerColor.BLUE)
            records.append((red_features, blue_features))

        # depth 1 only — fast
        moves = get_legal_moves(state)
        if not moves:
            break

        best_move  = moves[0]
        best_score = float('-inf')
        for move in order_moves(moves, state, state.turn_color):
            new_state = state.copy()
            new_state.apply_action(move)
            score = minimax(new_state, depth=1, alpha=float('-inf'),
                            beta=float('inf'), maximising=False,
                            my_color=state.turn_color)
            if score > best_score:
                best_score = score
                best_move  = move

        state.apply_action(best_move)

    winner = state.winner_checker()
    outcome = 1.0 if winner == PlayerColor.RED else (-1.0 if winner == PlayerColor.BLUE else 0.0)

    labeled = []
    for red_features, blue_features in records:
        labeled.append((red_features,  outcome))
        labeled.append((blue_features, -outcome))

    return labeled


def train():
    print(f"Running {NUM_GAMES} self-play games (time limit: {TIME_PER_MOVE}s/move)...")
    all_features = []
    all_labels   = []

    for i in range(NUM_GAMES):
        if (i + 1) % 20 == 0:
            print(f"  game {i + 1}/{NUM_GAMES}")
        try:
            for features, label in play_game():
                all_features.append(features)
                all_labels.append(label)
        except Exception as e:
            print(f"  game {i+1} failed: {e}")
            continue

    X = np.array(all_features, dtype=np.float32)
    y = np.array(all_labels,   dtype=np.float32)

    print(f"\nCollected {len(y)} samples.")
    print(f"Outcomes — RED wins: {int(np.sum(y==1))}, "
          f"BLUE wins: {int(np.sum(y==-1))}, "
          f"draws: {int(np.sum(y==0))}")

    # normalise
    X_mean = X.mean(axis=0)
    X_std  = X.std(axis=0) + 1e-8
    X_norm = (X - X_mean) / X_std

    # fit
    weights, _, _, _ = np.linalg.lstsq(X_norm, y, rcond=None)

    feature_names = [
        "token_diff", "centre_score", "eat_opportunities",
        "my_cascade", "opp_cascade", "mobility_diff"
    ]
    print("\nLearned weights:")
    for name, w in zip(feature_names, weights):
        print(f"  {name:25s}: {w:+.4f}")

    os.makedirs("agent", exist_ok=True)
    np.save(OUTPUT_FILE, np.stack([weights, X_mean, X_std]))
    print(f"\nSaved to {OUTPUT_FILE}")


if __name__ == "__main__":
    train()