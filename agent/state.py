# game state representation
import copy

from referee.game import PlayerColor,  Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction

DIRECTIONS = [Direction.Up, Direction.Down, Direction.Left, Direction.Right]

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
                moving_dest = self.move_coord(coord, direction)
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
                eating_dest = self.move_coord(coord, direction)
                eating_start = self.board[coord.r][coord.c]
                self.board[coord.r][coord.c] = None
                self.board[eating_dest.r][eating_dest.c] = eating_start

            case CascadeAction(coord, direction):
                stack_color, moving_dest_height = self.board[coord.r][coord.c]
                self.board[coord.r][coord.c] = None
                self.apply_cascade(coord, direction, moving_dest_height, stack_color)

        self.turn_color = (
            PlayerColor.BLUE if self.turn_color == PlayerColor.RED
            else PlayerColor.RED
        )
        self._turn_count += 1
    
    def move_coord(self, coord: Coord, direction: Direction):
        """ Get the direction coord """
        dr, dc = {
            Direction.Up: (-1, 0),
            Direction.Down: (1, 0),
            Direction.Left: (0, -1),
            Direction.Right: (0, 1)
        }[direction]
        new_dr, new_dc = coord.r + dr, coord.c + dc
        if 0 <= new_dr <= 7 and 0 <= new_dc <= 7:
            return Coord(new_dr, new_dc)
        return None
    
    def apply_cascade(self, coord: Coord, direction: Direction, height: int, color: PlayerColor):
        """Spread cascade"""

        # apply caseacade 
        cells = []
        current = coord

        for _ in range(height):
            current = self.move_coord(current, direction)
            if current is None:
                break
            cells.append(current)
        
        for i in reversed(range(len(cells))):
            cell = cells[i]

            if self.board[cell.r][cell.c] is not None: 
                pushed_dest = self.move_coord(cell, direction)
                if pushed_dest is not None:
                    self.board[pushed_dest.r][pushed_dest.c] = self.board[cell.r][cell.c]

                # else pushed off board, eliminated
                self.board[cell.r][cell.c] = None
        # Place one token per cell in path
        for cell in cells:
            if self.in_bounds(cell):
                self.board[cell.r][cell.c] = (color, 
                    (self.board[cell.r][cell.c][1] + 1) 
                    if self.board[cell.r][cell.c] else 1)
    
    def in_bounds(self, coord: Coord):
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

    def winner_checker(self):
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
                
def get_legal_moves(state: GameState) -> list:
    # placement phase — first 8 turns total (4 per player)
    if state._turn_count < 8:
        return get_placement_moves(state)
    return get_play_moves(state)


def get_placement_moves(state: GameState) -> list:
    moves = []
    opponent = PlayerColor.BLUE if state.turn_color == PlayerColor.RED else PlayerColor.RED

    # find all cells adjacent to opponent stacks
    adjacent_to_opponent = set()
    for r in range(8):
        for c in range(8):
            if state.board[r][c] and state.board[r][c][0] == opponent:
                for d in DIRECTIONS:
                    adj = state.move_coord(Coord(r, c), d)
                    if adj is None:
                        continue
                    if state.in_bounds(adj):
                        adjacent_to_opponent.add((adj.r, adj.c))

    for r in range(8):
        for c in range(8):
            # must be empty
            if state.board[r][c] is not None:
                continue
            # first move of the game has no restriction
            if state._turn_count == 0:
                moves.append(PlaceAction(Coord(r, c)))
                continue
            # cannot place adjacent to opponent
            if (r, c) not in adjacent_to_opponent:
                moves.append(PlaceAction(Coord(r, c)))

    return moves


def get_play_moves(state: GameState) -> list:
    moves = []
    opponent = PlayerColor.BLUE if state.turn_color == PlayerColor.RED else PlayerColor.RED

    for r in range(8):
        for c in range(8):
            cell = state.board[r][c]
            if not cell or cell[0] != state.turn_color:
                continue

            coord = Coord(r, c)
            height = cell[1]

            for d in DIRECTIONS:
                dest = state.move_coord(coord, d)
                if dest is None:
                    continue
                if not state.in_bounds(dest):
                    continue
                dest_cell = state.board[dest.r][dest.c]

                # MOVE: empty or friendly
                if dest_cell is None or dest_cell[0] == state.turn_color:
                    moves.append(MoveAction(coord, d))

                # EAT: enemy and tall enough
                if dest_cell and dest_cell[0] == opponent and height >= dest_cell[1]:
                    moves.append(EatAction(coord, d))

                # CASCADE: height >= 2
                if height >= 2:
                    moves.append(CascadeAction(coord, d))

    return moves