from referee.game import PlayerColor, Action
from agent.state import GameState, get_legal_moves
import random

class Agent:
    def __init__(self, color: PlayerColor, **referee: dict):
        self._color = color
        self._state = GameState()
        print(f"Random Agent playing as {color}")

    def action(self, **referee: dict) -> Action:
        moves = get_legal_moves(self._state)
        return random.choice(moves)

    def update(self, color: PlayerColor, action: Action, **referee: dict):
        self._state.apply_action(action)