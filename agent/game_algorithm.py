import time
from referee.game import PlayerColor, Action, Coord, EatAction, CascadeAction, MoveAction, PlaceAction
from .state import DIR_DELTA, GameState, get_legal_moves, DIRECTIONS, _ADJ

# ---------------------------------------------------------------------------
# Transposition table entry flags
# ---------------------------------------------------------------------------
TT_EXACT = 0
TT_LOWER = 1   # alpha (lower bound)
TT_UPPER = 2   # beta  (upper bound)

# ---------------------------------------------------------------------------
# Pre-computed centre distance for each cell
# ---------------------------------------------------------------------------
_CENTRE_DIST = [
    abs(r - 3.5) + abs(c - 3.5)
    for r in range(8)
    for c in range(8)
]

# ---------------------------------------------------------------------------
# Heuristic
# The heuristic function that evaluates using 
# a combination of color, height, edge distance, and tactical threats.
# ---------------------------------------------------------------------------

def heuristic(state: GameState, my_color: PlayerColor, is_placement: bool = False) -> float:
    my_tokens  = state.red_tokens  if my_color == PlayerColor.RED  else state.blue_tokens
    opp_tokens = state.blue_tokens if my_color == PlayerColor.RED  else state.red_tokens

    if not is_placement:
        if opp_tokens == 0: return float('inf')
        if my_tokens  == 0: return float('-inf')

    # Material advantage — primary winning condition
    score = (my_tokens - opp_tokens) * 100.0

    my_height_sq  = 0.0
    opp_height_sq = 0.0
    my_edge_pen   = 0.0
    opp_edge_pen  = 0.0
    my_threats    = 0   # tokens we can immediately capture
    opp_threats   = 0   # tokens opponent can immediately capture

    for r in range(8):
        for c in range(8):
            cell = state.get(r, c)
            if not cell:
                continue
            color, height = cell
            is_mine = (color == my_color)

            edge_dist = min(r, 7 - r, c, 7 - c)
            edge_pen  = max(0, 2 - edge_dist) * height

            if is_mine:
                # squared: cascade power grows super-linearly with height
                my_height_sq += height * height  
                my_edge_pen  += edge_pen
                if is_placement:
                    # Strong centre reward during placement
                    score += (7 - _CENTRE_DIST[r * 8 + c]) * 10
            else:
                opp_height_sq += height * height
                opp_edge_pen  += edge_pen

            # Immediate eat threats (symmetric for both sides)
            for d in DIRECTIONS:
                dest = _ADJ[r][c][d]
                if dest is None:
                    continue
                nb = state.get(dest[0], dest[1])
                if nb and nb[0] != color and height >= nb[1]:
                    if is_mine:
                        my_threats += nb[1]   # tokens we can capture right now
                    else:
                        opp_threats += nb[1]  # tokens they can capture right now

    # Cascade threats (both sides)
    my_cascade  = 0
    opp_cascade = 0
    for r in range(8):
        for c in range(8):
            cell = state.get(r, c)
            if not cell:
                continue
            color, height = cell
            if height < 3:
                continue
            for d in DIRECTIONS:
                dr, dc = DIR_DELTA[d]
                for step in range(1, height + 1):
                    nr, nc = r + dr * step, c + dc * step
                    if not (0 <= nr <= 7 and 0 <= nc <= 7):
                        break
                    target = state.get(nr, nc)
                    if target and target[0] != color:
                        if color == my_color:
                            my_cascade += target[1]
                        else:
                            opp_cascade += target[1]
                        break

    score += (my_height_sq  - opp_height_sq)  * 1.5
    score += (opp_edge_pen  - my_edge_pen)    * 2.0
    score += (my_threats    - opp_threats)    * 20.0   # tactical: net eat advantage
    score += (my_cascade    - opp_cascade)    * 30.0   # tactical: cascade advantage

    return score


# ---------------------------------------------------------------------------
# Move ordering — killer moves + history heuristic + static priority
# ---------------------------------------------------------------------------

class MoveOrderer:
    def __init__(self):
        # killer_moves[depth] = list of up to 2 moves that caused cutoffs
        self.killer_moves: dict[int, list] = {}
        # history[move_key] = count of cutoffs this move caused
        self.history: dict = {}
    
    # Get killer moves for this depth, or empty list if none recorded
    def get_killers(self, depth: int):
        return self.killer_moves.get(depth, [])
    
    # Record a killer move that caused a cutoff at this depth
    def record_killer(self, depth: int, move):
        killers = self.killer_moves.setdefault(depth, [])
        if move not in killers:
            killers.insert(0, move)
            if len(killers) > 2:
                killers.pop()

    # Record a killer move for the history heuristic
    # the score grows exponentially with depth to prioritise cutoffs caused deeper in the tree
    def record_history(self, move, depth: int):
        key = self._move_key(move)
        self.history[key] = self.history.get(key, 0) + (2 ** depth)

    # Convert a move to a hashable key for heuristic scoring
    def _move_key(self, move):
        return str(move)

    # Order the move based on the killer moves, history heuristic, and static priority
    def order_moves(self, moves, state: GameState, my_color: PlayerColor, depth: int):
        opponent = PlayerColor.BLUE if my_color == PlayerColor.RED else PlayerColor.RED
        killers  = self.get_killers(depth)

        # Prioritise moves with the order of 
        # 1. Winning move (captures last token)
        # 2. Killer moves from this depth
        # 3. History heuristic score
        # 4. Static: eat > cascade > move
        def priority(move):

            if move in killers:
                return -9000 + killers.index(move)

            hist = self.history.get(self._move_key(move), 0)

            match move:
                case EatAction(coord, direction):
                    dest = _ADJ[coord.r][coord.c][direction]
                    if dest:
                        target = state.get(dest[0], dest[1])
                        if target:
                            captured = target[1]
                            # Check if this is a killing move
                            opp_total = state.blue_tokens if my_color == PlayerColor.RED else state.red_tokens
                            if captured >= opp_total:
                                return -100000
                            return -1000 - captured * 10 - hist
                    return -500 - hist

                case CascadeAction(coord, direction):
                    cell = state.get(coord.r, coord.c)
                    if not cell:
                        return -hist
                    height = cell[1]
                    dr, dc = DIR_DELTA[direction]
                    for step in range(1, height + 1):
                        nr = coord.r + dr * step
                        nc = coord.c + dc * step
                        if not (0 <= nr <= 7 and 0 <= nc <= 7):
                            break
                        target = state.get(nr, nc)
                        if target and target[0] == opponent:
                            return -200 - target[1] * 10 - hist
                    return 0 - hist

                case MoveAction():
                    return 100 - hist

                case PlaceAction(coord):
                    dist = abs(coord.r - 3.5) + abs(coord.c - 3.5)
                    return int(150 + dist) - hist  # centre placements first

                case _:
                    return 300

        return sorted(moves, key=priority)


# ---------------------------------------------------------------------------
# Alpha-beta minimax with transposition table
# The alpha-beta search is implemented with a time guard that raises 
# TimeoutError when the deadline is exceeded.
# ---------------------------------------------------------------------------

def minimax(
    state: GameState,
    depth: int,
    alpha: float,
    beta: float,
    maximising: bool,
    my_color: PlayerColor,
    deadline: float,
    tt: dict,
    orderer: MoveOrderer,
    path_set: set = None,
    game_history: dict = None,
    tt_depth_offset: int = 0,
) -> float:
    if time.time() > deadline:
        raise TimeoutError()

    opponent = PlayerColor.BLUE if my_color == PlayerColor.RED else PlayerColor.RED

    h = state.board_hash()

    # Cycle detection: if this position appears on the current search path,
    # the line leads to a draw by repetition — score it neutrally
    if path_set is not None and h in path_set:
        return 0

    # --- Terminal / leaf ---
    if state.is_terminal():
        winner = state.winner_checker()
        if winner == my_color:  return  1_000_000 + depth
        if winner is None:      return  0
        return                         -1_000_000 - depth

    if depth == 0:
        leaf_score = heuristic(state, my_color, state._turn_count < 8)
        if game_history:
            reps = game_history.get(h, 0)
            leaf_score -= reps * 150   # penalise positions already seen in the actual game
        return leaf_score

    # --- Transposition table lookup ---
    board_key = (h, depth, maximising)
    if board_key in tt:
        tt_score, tt_flag, tt_depth = tt[board_key]
        if tt_depth >= depth:
            if tt_flag == TT_EXACT:
                return tt_score
            elif tt_flag == TT_LOWER:
                alpha = max(alpha, tt_score)
            elif tt_flag == TT_UPPER:
                beta  = min(beta, tt_score)
            if alpha >= beta:
                return tt_score

    orig_alpha = alpha
    current_color = my_color if maximising else opponent
    moves = orderer.order_moves(get_legal_moves(state), state, current_color, depth)

    if not moves:
        return heuristic(state, my_color, state._turn_count < 8)

    best = float('-inf') if maximising else float('inf')
    best_move = None

    if path_set is not None:
        path_set.add(h)

    #  --- Explore moves in order using minimax and alpha-beta pruning ---
    for move in moves:
        new_state = state.copy()
        new_state.apply_action(move)

        score = minimax(
            new_state, depth - 1, alpha, beta,
            not maximising, my_color, deadline, tt, orderer, path_set, game_history
        )

        if maximising:
            if score > best:
                best = score
                best_move = move
            alpha = max(alpha, best)
        else:
            if score < best:
                best = score
                best_move = move
            beta = min(beta, best)

        if alpha >= beta:
            # Record killer and history for move ordering
            if best_move:
                orderer.record_killer(depth, best_move)
                orderer.record_history(best_move, depth)
            break

    if path_set is not None:
        path_set.discard(h)

    # --- Store in transposition table ---
    if best == float('-inf') or best == float('inf'):
        tt_flag = TT_EXACT
    elif best <= orig_alpha:
        tt_flag = TT_UPPER
    elif best >= beta:
        tt_flag = TT_LOWER
    else:
        tt_flag = TT_EXACT

    # Limit TT size to avoid memory issues
    if len(tt) < 500_000:
        tt[board_key] = (best, tt_flag, depth)

    return best


# ---------------------------------------------------------------------------
# Iterative deepening with time guard

# Return the best move for the current player
# using iterative deepening with alpha-beta and a transposition table
# ---------------------------------------------------------------------------

_TIME_SAFETY_MARGIN = 0.05
_MAX_TIME_PER_MOVE  = 2.0

def get_best_move(
    state: GameState,
    my_color: PlayerColor,
    time_remaining=None,
    tt: dict = None,
    orderer: MoveOrderer = None,
) -> Action:
    moves = get_legal_moves(state)
    if not moves:
        return None

    if tt is None: tt = {}
    if orderer is None: orderer = MoveOrderer()

    # --- Time budget ---
    if time_remaining is not None:
        # assumes ~100 moves per game to budget time equally
        budget = min(time_remaining / 100, _MAX_TIME_PER_MOVE)
        budget = max(budget - _TIME_SAFETY_MARGIN, 0.05)
    else:
        budget = _MAX_TIME_PER_MOVE

    deadline = time.time() + budget

    is_placement = state._turn_count < 8

    # Actual game position history — passed into search to penalise revisiting real positions
    game_history = state.position_history
    # Three repeat will trigger draw so warning when repeate twice already
    seen_twice = {h for h, c in game_history.items() if c >= 2}
    # Seed the search path with the current game position so cycles back to it are detected
    game_hash = state.board_hash()

    # --- Iterative deepening (all phases) ---
    ordered = orderer.order_moves(moves, state, my_color, 0)
    best_move = ordered[0]
    best_score = float('-inf')

    # Depth-0 baseline — always available before timeout can fire
    for move in ordered:
        new_state = state.copy()
        new_state.apply_action(move)
        score = heuristic(new_state, my_color, is_placement)
        if score > best_score:
            best_score = score
            best_move  = move

    # Iterative deepening
    for depth in range(1, 12):
        candidate_move  = best_move
        candidate_score = float('-inf')
        try:
            for move in ordered:
                new_state = state.copy()
                new_state.apply_action(move)

                new_h = new_state.board_hash()
                if new_h in seen_twice:
                    # This move would cause threefold repetition → treat as draw
                    score = -5000 if best_score > -5000 else 0
                else:
                    # Fresh path_set per top-level move; seed with current game position
                    path_set = {game_hash}
                    score = minimax(
                        new_state,
                        depth=depth,
                        alpha=float('-inf'),
                        beta=float('inf'),
                        maximising=False,   # after our move, opponent minimises
                        my_color=my_color,
                        deadline=deadline,
                        tt=tt,
                        orderer=orderer,
                        path_set=path_set,
                        game_history=game_history,
                    )
                if score > candidate_score:
                    candidate_score = score
                    candidate_move = move

            best_move = candidate_move
            best_score = candidate_score
            # Re-order: put best move first (killer move seed for next depth)
            ordered = [best_move] + [m for m in ordered if m != best_move]

        except TimeoutError:
            break

    return best_move

