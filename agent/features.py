# agent/features.py
import numpy as np
from referee.game import PlayerColor, Coord
from .state import GameState, get_legal_moves, DIRECTIONS


def extract_features(state: GameState, my_color: PlayerColor) -> np.ndarray:
    opponent = PlayerColor.BLUE if my_color == PlayerColor.RED else PlayerColor.RED

    my_tokens = 0
    opp_tokens = 0
    centre_score = 0.0
    eat_opportunities = 0
    my_cascade = 0
    opp_cascade = 0

    for r in range(8):
        for c in range(8):
            cell = state.board[r][c]
            if not cell:
                continue
            color, height = cell
            dist = abs(r - 3.5) + abs(c - 3.5)

            if color == my_color:
                my_tokens += height
                centre_score -= dist * height
                if height >= 2:
                    my_cascade += height
                for d in DIRECTIONS:
                    adj = state.move_coord(Coord(r, c), d)
                    if adj is None:
                        continue
                    adj_cell = state.board[adj.r][adj.c]
                    if adj_cell and adj_cell[0] == opponent and height >= adj_cell[1]:
                        eat_opportunities += 1
            else:
                opp_tokens += height
                centre_score += dist * height
                if height >= 2:
                    opp_cascade += height

    my_mobility = 0
    opp_mobility = 0
    if state.turn_color == my_color:
        my_mobility = len(get_legal_moves(state))
        flipped = state.copy()
        flipped.turn_color = opponent
        opp_mobility = len(get_legal_moves(flipped))
    else:
        opp_mobility = len(get_legal_moves(state))
        flipped = state.copy()
        flipped.turn_color = my_color
        my_mobility = len(get_legal_moves(flipped))

    return np.array([
        my_tokens - opp_tokens,
        centre_score,
        eat_opportunities,
        my_cascade,
        opp_cascade,
        my_mobility - opp_mobility,
    ], dtype=np.float32)