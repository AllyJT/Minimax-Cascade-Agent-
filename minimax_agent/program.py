# minimax_agent/program.py
"""
Minimax agent: plain alpha-beta search to a fixed depth of 3,
with the same evaluation function used in greedy_agent but now
considering the opponent's best responses.

This represents the 'adversarial search' benchmark tier.
Intentionally kept simple (no TT, no iterative deepening) so it
stays clearly weaker than the main agent while still looking ahead.
"""

import time
from referee.game import PlayerColor, Action, PlaceAction
from agent.state import GameState, get_legal_moves, DIRECTIONS, _ADJ

INF   = float("inf")
WIN   =  100_000
LOSS  = -100_000
DEPTH =  3   # fixed lookahead — strong enough to be a real test


# ---------------------------------------------------------------------------
# Evaluation (same as greedy, symmetric)
# ---------------------------------------------------------------------------
def _eval(state: GameState, color: PlayerColor) -> float:
    my_tok  = state.red_tokens  if color == PlayerColor.RED  else state.blue_tokens
    opp_tok = state.blue_tokens if color == PlayerColor.RED  else state.red_tokens

    if opp_tok == 0:
        return WIN
    if my_tok == 0:
        return LOSS

    token_score      = (my_tok - opp_tok) * 10.0
    my_height        = 0.0
    opp_height       = 0.0
    my_edge_penalty  = 0.0
    opp_edge_penalty = 0.0
    my_threats       = 0
    opp_threats      = 0

    for r in range(8):
        for c in range(8):
            cell = state.board[r * 8 + c]
            if cell is None:
                continue
            cell_color, height = cell
            is_mine = (cell_color == color)

            edge_dist = min(r, 7 - r, c, 7 - c)
            edge_pen  = max(0, 2 - edge_dist) * height
            h_score   = height * height * 0.5

            threats = 0
            for d in DIRECTIONS:
                nb = _ADJ[r][c][d]
                if nb is None:
                    continue
                nb_cell = state.board[nb[0] * 8 + nb[1]]
                if nb_cell and nb_cell[0] != cell_color and height >= nb_cell[1]:
                    threats += 1

            if is_mine:
                my_height       += h_score
                my_edge_penalty += edge_pen
                my_threats      += threats
            else:
                opp_height       += h_score
                opp_edge_penalty += edge_pen
                opp_threats      += threats

    return (
        token_score
        + (my_height - opp_height) * 1.0
        + (opp_edge_penalty - my_edge_penalty) * 0.5
        + (my_threats - opp_threats) * 2.0
    )


# ---------------------------------------------------------------------------
# Move ordering — cheap heuristic to improve cutoffs
# ---------------------------------------------------------------------------
def _priority(move: Action) -> int:
    from referee.game import EatAction, CascadeAction, MoveAction
    if isinstance(move, EatAction):     return 3
    if isinstance(move, CascadeAction): return 2
    if isinstance(move, MoveAction):    return 1
    return 0


# ---------------------------------------------------------------------------
# Alpha-beta
# ---------------------------------------------------------------------------
def _alphabeta(
    state: GameState,
    depth: int,
    alpha: float,
    beta: float,
    maximising: bool,
    root_color: PlayerColor,
) -> float:
    if state.is_terminal():
        winner = state.winner_checker()
        if winner == root_color: return WIN + depth
        if winner is None:       return 0
        return LOSS - depth

    if depth == 0:
        return _eval(state, root_color)

    moves = get_legal_moves(state)
    if not moves:
        return 0  # stalemate

    moves = sorted(moves, key=_priority, reverse=True)

    if maximising:
        best = -INF
        for move in moves:
            child = state.copy()
            child.apply_action(move)
            best = max(best, _alphabeta(child, depth - 1, alpha, beta, False, root_color))
            alpha = max(alpha, best)
            if alpha >= beta:
                break
        return best
    else:
        best = INF
        for move in moves:
            child = state.copy()
            child.apply_action(move)
            best = min(best, _alphabeta(child, depth - 1, alpha, beta, True, root_color))
            beta = min(beta, best)
            if alpha >= beta:
                break
        return best


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class Agent:
    def __init__(self, color: PlayerColor, **referee: dict):
        self._color = color
        self._state = GameState()

    def action(self, **referee: dict) -> Action:
        moves = get_legal_moves(self._state)
        if not moves:
            raise RuntimeError("No legal moves")
        if len(moves) == 1:
            return moves[0]

        moves = sorted(moves, key=_priority, reverse=True)

        best_move  = moves[0]
        best_score = -INF
        alpha, beta = -INF, INF

        for move in moves:
            child = self._state.copy()
            child.apply_action(move)
            score = _alphabeta(child, DEPTH - 1, alpha, beta, False, self._color)
            if score > best_score:
                best_score = score
                best_move  = move
            alpha = max(alpha, score)

        return best_move

    def update(self, color: PlayerColor, action: Action, **referee: dict):
        self._state.apply_action(action)