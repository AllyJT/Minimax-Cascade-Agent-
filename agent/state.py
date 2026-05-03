# game state representation
import copy

from referee.game import PlayerColor,  Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction


def make_empty_board():
    return [[None] * 8 for _ in range(8)]

class GameState:
    def __init__(self):
        self.board = make_empty_board()
        self.turn_color = PlayerColor.RED
        self._turn_count = 0
        self.position_history = {}

    
    # apply the action to the game state
    # update turn color, turn count
    def apply_action(self, action: Action):
        match action:
            case PlaceAction(coord):
                self.board[coord.r][coord.c] = (self.turn_color, 3)
            
            # when you move pices, update the board
            case MoveAction(coord, direction):
                moving_dest = self._step(coord, direction)
                moving_start = self.board[coord.r][coord.c]
                self.board[coord.r][coord.c] = None

                # update the stack start to our new position (destination)
                if self.board[moving_dest.r][moving_dest.c] is None:
                    # record the move to the board history
                    self.board[moving_dest.r][moving_dest.c] = moving_start
                else: 
                    # if there is a stack, combine their heights
                    _, moving_dest_height = self.board[moving_dest.r][moving_dest.c]
                    self.board[moving_dest.r][moving_dest.c] = (self.turn_color, moving_start[1] + moving_dest_height)
            
            case EatAction(coord, direction):
                eating_dest = self._step(coord, direction)
                eating_start = self.board[coord.r][coord.c]
                self.board[coord.r][coord.c] = None
                self.board[eating_dest.r][eating_dest.c] = eating_start

            case CascadeAction(coord, direction):
                stack_color, moving_dest_height = self.board[coord.r][coord.c]
                self.board[coord.r][coord.c] = None
                self._apply_cascade(coord, direction, moving_dest_height, stack_color)

        self.turn_color = (
            PlayerColor.BLUE if self.turn_color == PlayerColor.RED
            else PlayerColor.RED
        )
        self._turn_count += 1
    
    def _step(self, coord: Coord, direction: Direction):
        """ Get the direction coord """
        dr, dc = {
            Direction.Up: (-1, 0),
            Direction.Down: (1, 0),
            Direction.Left: (0, -1),
            Direction.Right: (0, 1)
        }[direction]
        return Coord(coord.r + dr, coord.c + dc)
    
    def _apply_cascade(self, coord: Coord, direction: Direction, height: int, color: PlayerColor):
        """Spread cascade"""

        # apply caseacade 
        cells = []
        current = coord

        for _ in range(height):
            current = self._step(current, direction)
            cells.append(current)
        
        for i in reversed(range(len(cells))):
            cell = cells[i]

            if self.board[cell.r][cell.c] is not None: 
                pushed_dest = self._step(cell, direction)
                if self._in_bounds(pushed_dest):
                    self.board[pushed_dest.r][pushed_dest.c] = self.board[cell.r][cell.c]

                # else pushed off board, eliminated
                self.board[cell.r][cell.c] = None
        # Place one token per cell in path
        for cell in cells:
            if self._in_bounds(cell):
                self.board[cell.r][cell.c] = (color, 
                    (self.board[cell.r][cell.c][1] + 1) 
                    if self.board[cell.r][cell.c] else 1)
    
    def _in_bounds(self, coord: Coord):
        return 0 <= coord.r <= 7 and 0 <= coord.c <= 7
    def copy(self):
        new = GameState()
        new.board = copy.deepcopy(self.board)
        new.turn_color = self.turn_color
        new._turn_count = self._turn_count
        new.position_history = self.position_history.copy()
        return new

    def is_terminal(self):
        red_tokens = sum(
            h for row in self.board for cell in row 
            if cell and (color := cell[0]) == PlayerColor.RED
            for _, h in [cell]
        )
        blue_tokens = sum(
            h for row in self.board for cell in row
            if cell and cell[0] == PlayerColor.BLUE
            for _, h in [cell]
        )
        if red_tokens == 0 or blue_tokens == 0:
            return True
        if self._turn_count >= 300:
            return True
        return False

    def winner(self):
        red_tokens = sum(cell[1] for row in self.board for cell in row if cell and cell[0] == PlayerColor.RED)
        blue_tokens = sum(cell[1] for row in self.board for cell in row if cell and cell[0] == PlayerColor.BLUE)
        if red_tokens == 0:
            return PlayerColor.BLUE
        if blue_tokens == 0:
            return PlayerColor.RED
        if red_tokens > blue_tokens:
            return PlayerColor.RED
        if blue_tokens > red_tokens:
            return PlayerColor.BLUE
        return None
                

    pass