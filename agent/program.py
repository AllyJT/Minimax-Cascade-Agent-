# COMP30024 Artificial Intelligence, Semester 1 2026
# Project Part B: Game Playing Agent


from referee.game import PlayerColor,  Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction
from .game_algorithm import get_best_move
from .state import GameState, get_legal_moves


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
        
        # Below we have hardcoded actions to be played depending on whether
        # the agent is playing as BLUE or RED. Obviously this won't work beyond
        # the initial moves of the game, so you should use some game playing
        # technique(s) to determine the best action to take.

        # During placement phase (first 8 turns total, 4 per player)
        ##
        # Add the initial algorithm here, the one that move your pieces
        ##
        
        # below is the placing function, change to your own placing function
        # if self._turn_count < 4:
        #     match self._color:
        #         case PlayerColor.RED:
        #             print("Testing: RED is playing a PLACE action")
        #             return PlaceAction(Coord(0, self._turn_count))
        #         case PlayerColor.BLUE:
        #             print("Testing: BLUE is playing a PLACE action")
        #             return PlaceAction(Coord(7, self._turn_count))

        # the algorithm for the move
        return get_best_move(self._state, self._color, referee.get("time_remaining"))
        # # During play phase
        # match self._color:
        #     case PlayerColor.RED:
        #         print("Testing: RED is playing a MOVE action")
        #         return MoveAction(Coord(0, 0), Direction.Down)
        #     case PlayerColor.BLUE:
        #         print("Testing: BLUE is playing a MOVE action")
                # return MoveAction(Coord(7, 0), Direction.Up)
    def board_hash(self):
        """Simple hash of current board state"""
        result = []
        for r in range(8):
            for c in range(8):
                if self.board[r][c]:
                    result.append((r, c, self.board[r][c][0], self.board[r][c][1]))
        return tuple(result)
    def update(self, color: PlayerColor, action: Action, **referee: dict):
        """
        This method is called by the referee after a player has taken their
        turn. You should use it to update the agent's internal game state.
        """
        self._state.apply_action(action)
        # if color == self._color:
        #     self._turn_count += 1

        # There are four possible action types: PLACE, MOVE, EAT, and CASCADE.
        # Below we check which type of action was played and print out the
        # details of the action for demonstration purposes. You should replace
        # this with your own logic to update your agent's internal game state.

        # move your pieces here, update the game state here


        # match action:
            # case PlaceAction(coord):
        #         print(f"Testing: {color} played PLACE action at {coord}")
        #     case MoveAction(coord, direction):
        #         print(f"Testing: {color} played MOVE action:")
        #         print(f"  Coord: {coord}")
        #         print(f"  Direction: {direction}")
        #     case EatAction(coord, direction):
        #         print(f"Testing: {color} played EAT action:")
        #         print(f"  Coord: {coord}")
        #         print(f"  Direction: {direction}")
        #     case CascadeAction(coord, direction):
        #         print(f"Testing: {color} played CASCADE action:")
        #         print(f"  Coord: {coord}")
        #         print(f"  Direction: {direction}")
        #     case _:
        #         raise ValueError(f"Unknown action type: {action}")
