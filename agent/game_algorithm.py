# agent/game_algorithm.py
import os
import time
import numpy as np
from referee.game import PlayerColor, Action, Coord, EatAction, CascadeAction, MoveAction, PlaceAction
from .state import GameState, get_legal_moves, DIRECTIONS
from .features import extract_features


# load learned weights once at import time
_WEIGHTS_FILE = os.path.join(os.path.dirname(__file__), "weights.npy")

if os.path.exists(_WEIGHTS_FILE):
    _data   = np.load(_WEIGHTS_FILE)
    _W      = _data[0]
    _X_mean = _data[1]
    _X_std  = _data[2]
    _USE_ML = True
    print("Loaded learned heuristic weights.")
else:
    _USE_ML = False
    print("weights.npy not found — using hand-tuned heuristic.")


def heuristic(state: GameState, my_color, is_placement=False) -> float:
    opponent      = PlayerColor.BLUE if my_color == PlayerColor.RED else PlayerColor.RED
    token_diff    = (my_tokens - opp_tokens) * 50
    centre_weight = 25 if is_placement else 1
    centre_score  = 0
    eat_score     = 0

    for r in range(8):
        for c in range(8):
            cell = state.board[r][c]
            if not cell:
                continue
            dist = abs(r - 3.5) + abs(c - 3.5)
            if cell[0] == my_color:
                centre_score -= dist * cell[1] * centre_weight
                for d in DIRECTIONS:
                    adj = state.move_coord(Coord(r, c), d)
                    if adj is None:
                        continue
                    adj_cell = state.board[adj.r][adj.c]
                    if adj_cell and adj_cell[0] == opponent and cell[1] >= adj_cell[1]:
                        eat_score += 20
            else:
                centre_score += dist * cell[1] * centre_weight

    current_hash       = state.board_hash()
    repetitions        = state.position_history.get(current_hash, 0)
    repetition_penalty = repetitions * 500

    return token_diff + centre_score + eat_score - repetition_penalty


def order_moves(moves, state, my_color):
    def move_priority(move):
        match move:
            case EatAction(coord, direction):
                dest = state.move_coord(coord, direction)
                if dest and state.board[dest.r][dest.c]:
                    return -state.board[dest.r][dest.c][1]
                return -1
            case CascadeAction():
                return 0
            case MoveAction():
                return 1
            case _:
                return 2
    return sorted(moves, key=move_priority)


def minimax(state, depth, alpha, beta, maximising, my_color):
    if depth == 0 or state.is_terminal():
        return heuristic(state, my_color, state._turn_count < 8)

    if maximising:
        best = float('-inf')
        for move in order_moves(get_legal_moves(state), state, my_color):
            new_state = state.copy()
            new_state.apply_action(move)
            score = minimax(new_state, depth - 1, alpha, beta, False, my_color)
            best  = max(best, score)
            alpha = max(alpha, best)
            if beta <= alpha:
                break
        return best
    else:
        best = float('inf')
        for move in order_moves(get_legal_moves(state), state, my_color):
            new_state = state.copy()
            new_state.apply_action(move)
            score = minimax(new_state, depth - 1, alpha, beta, True, my_color)
            best  = min(best, score)
            beta  = min(beta, best)
            if beta <= alpha:
                break
        return best


def get_best_move(state: GameState, my_color, time_remaining=None) -> Action:
    moves = get_legal_moves(state)
    if not moves:
        return None

    best_move = moves[0]
    best_score = float('-inf')

    # placement has 60+ moves — depth 3 takes 90+ seconds, must use depth 1
    depth = 2 if state._turn_count < 8 else 3

    for move in order_moves(moves, state, my_color):
        new_state = state.copy()
        new_state.position_history = state.position_history.copy()
        new_state.apply_action(move)
        score = minimax(new_state, depth=depth, alpha=float('-inf'),
                        beta=float('inf'), maximising=False, my_color=my_color)
        if score > best_score:
            best_score = score
            best_move = move

    return best_move