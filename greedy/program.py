# greedy_agent/program.py
"""
Greedy agent: evaluates all legal moves one ply deep and picks the best
immediately, with no lookahead into the opponent's response.

Greedy heuristic (from the acting player's perspective):
  1. Token count difference          (primary objective)
  2. Stack height advantage          (tall stacks = future power)
  3. Immediate threats               (pieces adjacent to capturable enemies)
  4. Edge safety                     (penalise own pieces near edges)
  5. Cascade path value              (how many enemy tokens a cascade hits)
"""

from referee.game import PlayerColor, Action, PlaceAction, EatAction, CascadeAction, MoveAction
from agent.state import GameState, get_legal_moves, DIRECTIONS, _ADJ


INF = float("inf")


# ---------------------------------------------------------------------------
# Greedy evaluation (single-ply, no recursion)
# ---------------------------------------------------------------------------
def _greedy_eval(state: GameState, color: PlayerColor) -> float:
    opponent = PlayerColor.BLUE if color == PlayerColor.RED else PlayerColor.RED

    my_tok  = state.red_tokens  if color == PlayerColor.RED  else state.blue_tokens
    opp_tok = state.blue_tokens if color == PlayerColor.RED  else state.red_tokens

    if opp_tok == 0:
        return INF
    if my_tok == 0:
        return -INF

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


class Agent:
    def __init__(self, color: PlayerColor, **referee: dict):
        self._color = color
        self._state = GameState()

    def action(self, **referee: dict) -> Action:
        moves = get_legal_moves(self._state)
        if not moves:
            raise RuntimeError("No legal moves")

        best_move  = moves[0]
        best_score = -INF

        for move in moves:
            child = self._state.copy()
            child.apply_action(move)
            score = _greedy_eval(child, self._color)
            if score > best_score:
                best_score = score
                best_move  = move

        return best_move

    def update(self, color: PlayerColor, action: Action, **referee: dict):
        self._state.apply_action(action)