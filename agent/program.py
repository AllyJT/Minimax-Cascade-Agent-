# COMP30024 Artificial Intelligence, Semester 1 2026
# Project Part B: Game Playing Agent


from referee.game import PlayerColor, Action
from .game_algorithm import get_best_move
from .state import GameState


class Agent:
    """
    This class is the "entry point" for your agent, providing an interface to
    respond to various Cascade game events.
    """

    def __init__(self, color: PlayerColor, **referee: dict):
        """
        This constructor method runs when the referee instantiates the agent.
        Any setup and/or precomputation should be done here.
        """
        self._color = color
        self._state = GameState()
        match color:
            case PlayerColor.RED:
                print("Testing: I am playing as RED (first player)")
            case PlayerColor.BLUE:
                print("Testing: I am playing as BLUE")

    def action(self, **referee: dict) -> Action:
        """
        This method is called by the referee each time it is the agent's turn
        to take an action. It must always return an action object.
        """
        # During placement phase (first 8 turns total, 4 per player)
        ##
        # Add the initial algorithm here, the one that move your pieces
        ##
        
        # below is the placing function, change to your own placing function

        return get_best_move(self._state, self._color, referee.get("time_remaining"))

    def update(self, color: PlayerColor, action: Action, **referee: dict):
        """
        This method is called by the referee after a player has taken their
        turn. You should use it to update the agent's internal game state.
        """
        self._state.apply_action(action)
