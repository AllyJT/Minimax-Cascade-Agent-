from referee.game import PlayerColor, Action
from agent.state import GameState, get_legal_moves
import random

class Agent:
    def __init__(self, color: PlayerColor, **referee: dict):
        self._color = color
        self._state = GameState()
        print(f"Simple Minimax Agent playing as {color}")

    def action(self, **referee: dict) -> Action:
        moves = get_legal_moves(self._state)
        best_move = moves[0]
        best_score = float('-inf')

        for move in moves:
            new_state = self._state.copy()
            new_state.apply_action(move)
            score = self.minimax(new_state, depth=2, maximising=False)
            if score > best_score:
                best_score = score
                best_move = move

        return best_move

    def minimax(self, state, depth, maximising):
        if depth == 0 or state.is_terminal():
            return self.heuristic(state)

        moves = get_legal_moves(state)
        if not moves:
            return self.heuristic(state)

        if maximising:
            best = float('-inf')
            for move in moves:
                new_state = state.copy()
                new_state.apply_action(move)
                best = max(best, self.minimax(new_state, depth - 1, False))
            return best
        else:
            best = float('inf')
            for move in moves:
                new_state = state.copy()
                new_state.apply_action(move)
                best = min(best, self.minimax(new_state, depth - 1, True))
            return best

    def heuristic(self, state):
        opponent = PlayerColor.BLUE if self._color == PlayerColor.RED else PlayerColor.RED
        my_tokens = sum(cell[1] for row in state.board for cell in row if cell and cell[0] == self._color)
        opp_tokens = sum(cell[1] for row in state.board for cell in row if cell and cell[0] == opponent)
        return my_tokens - opp_tokens

    def update(self, color: PlayerColor, action: Action, **referee: dict):
        self._state.apply_action(action)