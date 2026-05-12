# game state representation
from referee.game import PlayerColor, Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction

DIRECTIONS = [Direction.Up, Direction.Down, Direction.Left, Direction.Right]

DIR_DELTA = {
    Direction.Up:    (-1, 0),
    Direction.Down:  (1, 0),
    Direction.Left:  (0, -1),
    Direction.Right: (0, 1),
}

# Pre-computed adjacency table: adj[r][c][direction] -> (nr, nc) or None
_ADJ = [[{} for _ in range(8)] for _ in range(8)]
for _r in range(8):
    for _c in range(8):
        for _d in DIRECTIONS:
            _dr, _dc = DIR_DELTA[_d]
            _nr, _nc = _r + _dr, _c + _dc
            _ADJ[_r][_c][_d] = (_nr, _nc) if 0 <= _nr <= 7 and 0 <= _nc <= 7 else None


def make_empty_board():
    # Flat list of 64 cells (None or (color, height)) — faster to copy than nested list
    return [None] * 64


def idx(r, c):
    return r * 8 + c


class GameState:
    def __init__(self):
        self.board = make_empty_board()   # flat list[64]
        self.turn_color = PlayerColor.RED
        self._turn_count = 0
        self.position_history = {}

        # Incremental token counts — avoid full board scan every heuristic call
        self.red_tokens = 0
        self.blue_tokens = 0

        # Incremental hash — XOR Zobrist-style but simpler: just frozenset of occupancy
        # We maintain a running tuple key lazily; dirty flag avoids recompute
        self._hash_dirty = True
        self._cached_hash = None

    # ------------------------------------------------------------------
    # Board access helpers
    # ------------------------------------------------------------------
    def get(self, r, c):
        return self.board[idx(r, c)]

    def set(self, r, c, val):
        old = self.board[idx(r, c)]
        self.board[idx(r, c)] = val
        # Maintain token counts
        if old:
            if old[0] == PlayerColor.RED:
                self.red_tokens -= old[1]
            else:
                self.blue_tokens -= old[1]
        if val:
            if val[0] == PlayerColor.RED:
                self.red_tokens += val[1]
            else:
                self.blue_tokens += val[1]
        self._hash_dirty = True

    def move_coord(self, coord: Coord, direction: Direction):
        result = _ADJ[coord.r][coord.c][direction]
        if result is None:
            return None
        return Coord(result[0], result[1])

    def move_rc(self, r, c, direction: Direction):
        """Like move_coord but avoids Coord object creation."""
        return _ADJ[r][c][direction]  # returns (nr, nc) or None

    # ------------------------------------------------------------------
    # Copy — fast: list slice + scalar copies, no deepcopy
    # ------------------------------------------------------------------
    def copy(self):
        new = GameState.__new__(GameState)
        new.board = self.board[:]          # flat list slice — very fast
        new.turn_color = self.turn_color
        new._turn_count = self._turn_count
        new.position_history = {}          # search nodes don't need history
        new.red_tokens = self.red_tokens
        new.blue_tokens = self.blue_tokens
        new._hash_dirty = True
        new._cached_hash = None
        return new

    # ------------------------------------------------------------------
    # Action application
    # ------------------------------------------------------------------
    def apply_action(self, action: Action):
        match action:
            case PlaceAction(coord):
                self.set(coord.r, coord.c, (self.turn_color, 3))

            case MoveAction(coord, direction):
                dest = _ADJ[coord.r][coord.c][direction]
                if dest is None:
                    return
                nr, nc = dest
                moving_start = self.get(coord.r, coord.c)
                dest_cell = self.get(nr, nc)
                self.set(coord.r, coord.c, None)
                if dest_cell is None:
                    self.set(nr, nc, moving_start)
                else:
                    self.set(nr, nc, (self.turn_color, moving_start[1] + dest_cell[1]))

            case EatAction(coord, direction):
                dest = _ADJ[coord.r][coord.c][direction]
                if dest is None:
                    return
                nr, nc = dest
                eating_start = self.get(coord.r, coord.c)
                self.set(coord.r, coord.c, None)
                self.set(nr, nc, eating_start)

            case CascadeAction(coord, direction):
                cell = self.get(coord.r, coord.c)
                if cell is None:
                    return
                stack_color, height = cell
                self.set(coord.r, coord.c, None)
                self._apply_cascade_inline(coord.r, coord.c, direction, height, stack_color)

        self.turn_color = (
            PlayerColor.BLUE if self.turn_color == PlayerColor.RED
            else PlayerColor.RED
        )
        self._turn_count += 1
        h = self.board_hash()
        self.position_history[h] = self.position_history.get(h, 0) + 1

    def _apply_cascade_inline(self, r, c, direction, height, color):
        dr, dc = DIR_DELTA[direction]
        for step in range(1, height + 1):
            nr = r + dr * step
            nc = c + dc * step
            if not (0 <= nr <= 7 and 0 <= nc <= 7):
                continue
            if self.get(nr, nc) is not None:
                self._push_stack_inline(nr, nc, direction)
            self.set(nr, nc, (color, 1))

    def _push_stack_inline(self, r, c, direction):
        stack = self.get(r, c)
        self.set(r, c, None)
        dr, dc = DIR_DELTA[direction]
        nr, nc = r + dr, c + dc
        if not (0 <= nr <= 7 and 0 <= nc <= 7):
            return  # pushed off board
        if self.get(nr, nc) is not None:
            self._push_stack_inline(nr, nc, direction)
        self.set(nr, nc, stack)

    # ------------------------------------------------------------------
    # Hash — lazy, only recomputed when dirty
    # ------------------------------------------------------------------
    def board_hash(self):
        if not self._hash_dirty:
            return self._cached_hash
        self._cached_hash = tuple(
            (i, cell[0], cell[1])
            for i, cell in enumerate(self.board)
            if cell is not None
        )
        self._hash_dirty = False
        return self._cached_hash

    # ------------------------------------------------------------------
    # Terminal check — uses incremental counts, no board scan
    # ------------------------------------------------------------------
    def is_terminal(self):
        if self._turn_count < 8:
            return False
        if self.red_tokens == 0 or self.blue_tokens == 0:
            return True
        if self._turn_count >= 308:
            return True
        return False

    def winner_checker(self):
        if self.red_tokens == 0:
            return PlayerColor.BLUE
        if self.blue_tokens == 0:
            return PlayerColor.RED
        if self.red_tokens > self.blue_tokens:
            return PlayerColor.RED
        if self.blue_tokens > self.red_tokens:
            return PlayerColor.BLUE
        return None

    def in_bounds(self, coord: Coord):
        return 0 <= coord.r <= 7 and 0 <= coord.c <= 7


# ------------------------------------------------------------------
# Legal move generation — uses flat board + precomputed adjacency
# ------------------------------------------------------------------
def get_legal_moves(state: GameState) -> list:
    if state._turn_count < 8:
        return get_placement_moves(state)
    return get_play_moves(state)


def get_placement_moves(state: GameState) -> list:
    moves = []
    opponent = PlayerColor.BLUE if state.turn_color == PlayerColor.RED else PlayerColor.RED

    adjacent_to_opponent = set()
    for r in range(8):
        for c in range(8):
            cell = state.get(r, c)
            if cell and cell[0] == opponent:
                for d in DIRECTIONS:
                    result = _ADJ[r][c][d]
                    if result:
                        adjacent_to_opponent.add(result)

    for r in range(8):
        for c in range(8):
            if state.get(r, c) is not None:
                continue
            if state._turn_count == 0:
                moves.append(PlaceAction(Coord(r, c)))
                continue
            if (r, c) not in adjacent_to_opponent:
                moves.append(PlaceAction(Coord(r, c)))

    return moves


def get_play_moves(state: GameState) -> list:
    moves = []
    color = state.turn_color
    opponent = PlayerColor.BLUE if color == PlayerColor.RED else PlayerColor.RED

    for r in range(8):
        for c in range(8):
            cell = state.get(r, c)
            if not cell or cell[0] != color:
                continue

            coord = Coord(r, c)
            height = cell[1]

            for d in DIRECTIONS:
                dest = _ADJ[r][c][d]
                if dest is None:
                    continue
                nr, nc = dest
                dest_cell = state.get(nr, nc)

                if dest_cell is None or dest_cell[0] == color:
                    moves.append(MoveAction(coord, d))

                if dest_cell and dest_cell[0] == opponent and height >= dest_cell[1]:
                    moves.append(EatAction(coord, d))

            if height >= 2:
                for d in DIRECTIONS:
                    moves.append(CascadeAction(coord, d))

    return moves