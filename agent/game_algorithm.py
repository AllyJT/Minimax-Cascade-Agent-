import time
from referee.game import PlayerColor, Action, Coord, EatAction, CascadeAction, MoveAction, PlaceAction
from .state import GameState, get_legal_moves, DIRECTIONS, _ADJ


# ---------------------------------------------------------------------------
# Heuristic
# ---------------------------------------------------------------------------

# Pre-compute Manhattan distance from centre (3.5, 3.5) for each cell
_CENTRE_DIST = [
    abs(r - 3.5) + abs(c - 3.5)
    for r in range(8)
    for c in range(8)
]


def heuristic(state: GameState, my_color: PlayerColor, is_placement: bool = False) -> float:
    opponent = PlayerColor.BLUE if my_color == PlayerColor.RED else PlayerColor.RED

    # Use incremental token counts — no board scan needed
    my_tokens  = state.red_tokens  if my_color == PlayerColor.RED  else state.blue_tokens
    opp_tokens = state.blue_tokens if my_color == PlayerColor.RED  else state.red_tokens

    if not is_placement:
        if opp_tokens == 0: return float('inf')
        if my_tokens == 0: return float('-inf')
    
    # Strategy 1 Token different, with the strongest weight
    token_diff = (my_tokens - opp_tokens) * 100

    centre_weight = 25 if is_placement else 1
    total_score = 0

    for r in range(8):
        for c in range(8):
            cell = state.get(r, c)
            if not cell:
                continue

            dist = _CENTRE_DIST[r * 8 + c]
            color, height = cell
            edge_danger = (dist ** 2) # the edge is dangerous, penalise

            # Strategy 2: favour height of stack
            reserve_height = (height ** 1.5) * 15

            
            if color == my_color:
                total_score += reserve_height
                total_score -= dist * edge_danger* centre_weight

                for d in DIRECTIONS:
                    dest = _ADJ[r][c][d]
                    if dest is None:
                        continue
                    nr, nc = dest
                    adj_cell = state.get(nr, nc)

                    # EAT opportunity
                    if adj_cell and adj_cell[0] == opponent and height >= adj_cell[1]:
                        total_score += 20 + adj_cell[1] * 5  # reward eating taller stacks more

                    # Mobility: count moves available
                    if adj_cell is None or adj_cell[0] == my_color:
                        total_score += 1

                # CASCADE threat: tall stacks near enemies are dangerous for opponent
                if height >= 3:
                    for d in DIRECTIONS:
                        dr, dc = DIRECTIONS[0].value if hasattr(DIRECTIONS[0], 'value') else (0, 0)
                        # scan cascade path for enemy tokens
                        from .state import DIR_DELTA
                        ddr, ddc = DIR_DELTA[d]
                        for step in range(1, height + 1):
                            nr2 = r + ddr * step
                            nc2 = c + ddc * step
                            if not (0 <= nr2 <= 7 and 0 <= nc2 <= 7):
                                break
                            target = state.get(nr2, nc2)
                            if target and target[0] == opponent:
                                total_score += 15
                                break
            # reward us to have tall opponent stack near edge
            else:
                total_score -= reserve_height
                total_score += dist * height * centre_weight


    current_hash       = state.board_hash()
    repetitions        = state.position_history.get(current_hash, 0)
    repetition_penalty = repetitions * 500

    return token_diff + total_score - repetition_penalty


# ---------------------------------------------------------------------------
# Move ordering
# ---------------------------------------------------------------------------

def order_moves(moves, state: GameState, my_color: PlayerColor):
    opponent = PlayerColor.BLUE if my_color == PlayerColor.RED else PlayerColor.RED

    def move_priority(move):
        match move:
            case EatAction(coord, direction):
                dest = _ADJ[coord.r][coord.c][direction]
                if dest:
                    target = state.get(dest[0], dest[1])
                    if target:
                        return -target[1] - 100   # eat is best; bigger targets first
                return -1
            case CascadeAction(coord, direction):
                # Prefer cascades that threaten enemies
                from .state import DIR_DELTA
                cell = state.get(coord.r, coord.c)
                if not cell:
                    return 5
                height = cell[1]
                dr, dc = DIR_DELTA[direction]
                for step in range(1, height + 1):
                    nr = coord.r + dr * step
                    nc = coord.c + dc * step
                    if not (0 <= nr <= 7 and 0 <= nc <= 7):
                        break
                    target = state.get(nr, nc)
                    if target and target[0] == opponent:
                        return -50   # threatening cascade
                return 0
            case MoveAction():
                return 1
            case _:
                return 2

    return sorted(moves, key=move_priority)


# ---------------------------------------------------------------------------
# Alpha-beta minimax
# ---------------------------------------------------------------------------

def minimax(state: GameState, depth: int, alpha: float, beta: float,
            maximising: bool, my_color: PlayerColor,
            deadline: float) -> float:
    # Time check — bail early if we're over budget
    if time.time() > deadline:
        raise TimeoutError()

    if depth == 0 or state.is_terminal():
        return heuristic(state, my_color, state._turn_count < 8)

    moves = order_moves(get_legal_moves(state), state, my_color)
    if not moves:
        return heuristic(state, my_color, state._turn_count < 8)

    if maximising:
        best = float('-inf')
        for move in moves:
            new_state = state.copy()
            new_state.apply_action(move)
            score = minimax(new_state, depth - 1, alpha, beta, False, my_color, deadline)
            if score > best:
                best = score
            if best > alpha:
                alpha = best
            if beta <= alpha:
                break
        return best
    else:
        best = float('inf')
        for move in moves:
            new_state = state.copy()
            new_state.apply_action(move)
            score = minimax(new_state, depth - 1, alpha, beta, True, my_color, deadline)
            if score < best:
                best = score
            if best < beta:
                beta = best
            if beta <= alpha:
                break
        return best


# ---------------------------------------------------------------------------
# Iterative deepening with time guard
# ---------------------------------------------------------------------------

# Safety margin: stop searching with this many seconds left so we don't TLE
_TIME_SAFETY_MARGIN = 0.05   # 50 ms buffer per move

# Hard cap on time per move (seconds). 180s / ~150 expected moves ≈ 1.2s each,
# but we keep a generous cap so early game doesn't blow the budget.
_MAX_TIME_PER_MOVE = 1.0


def get_best_move(state: GameState, my_color: PlayerColor,
                  time_remaining=None) -> Action:
    moves = get_legal_moves(state)
    if not moves:
        return None

    # ---- Time budget -------------------------------------------------------
    if time_remaining is not None:
        # Scale time per move based on how much we have left
        # Assume ~100 remaining play moves on average
        budget = min(time_remaining / 100, _MAX_TIME_PER_MOVE)
        budget = max(budget - _TIME_SAFETY_MARGIN, 0.05)  # at least 50ms
    else:
        budget = _MAX_TIME_PER_MOVE

    deadline = time.time() + budget

    # ---- Placement phase: depth 1 (huge branching factor ~50+ moves) -------
    if state._turn_count < 8:
        ordered = order_moves(moves, state, my_color)
        best_move  = ordered[0]
        best_score = float('-inf')
        for move in ordered:
            new_state = state.copy()
            new_state.apply_action(move)
            score = heuristic(new_state, my_color, True)
            if score > best_score:
                best_score = score
                best_move  = move
        return best_move

    # ---- Play phase: iterative deepening -----------------------------------
    ordered      = order_moves(moves, state, my_color)
    best_move    = ordered[0]   # fallback: best-ordered move at depth 0
    best_score   = float('-inf')

    # Evaluate depth-0 scores so we always have something to return
    for move in ordered:
        new_state = state.copy()
        new_state.apply_action(move)
        score = heuristic(new_state, my_color, False)
        if score > best_score:
            best_score = score
            best_move  = move

    # Iterative deepening: depth 1, 2, 3, ...
    for depth in range(1, 5):   # cap at depth 4; time guard will cut earlier
        candidate_move  = best_move
        candidate_score = float('-inf')
        try:
            for move in ordered:
                new_state = state.copy()
                new_state.position_history = state.position_history.copy()
                new_state.apply_action(move)
                score = minimax(
                    new_state,
                    depth=depth,
                    alpha=float('-inf'),
                    beta=float('inf'),
                    maximising=False,
                    my_color=my_color,
                    deadline=deadline,
                )
                if score > candidate_score:
                    candidate_score = score
                    candidate_move  = move

            # Full depth completed — commit result
            best_move  = candidate_move
            best_score = candidate_score

            # Re-order for next iteration: put best move first (cheap killer move)
            ordered = [best_move] + [m for m in ordered if m != best_move]

        except TimeoutError:
            # Incomplete depth — discard partial results, keep last complete depth
            break

    return best_move