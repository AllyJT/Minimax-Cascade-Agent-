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
# ---------------------------------------------------------------------------

def heuristic(state: GameState, my_color: PlayerColor, is_placement: bool = False) -> float:
    opponent = PlayerColor.BLUE if my_color == PlayerColor.RED else PlayerColor.RED

    my_tokens  = state.red_tokens  if my_color == PlayerColor.RED  else state.blue_tokens
    opp_tokens = state.blue_tokens if my_color == PlayerColor.RED  else state.red_tokens

    if not is_placement:
        if opp_tokens == 0: return float('inf')
        if my_tokens  == 0: return float('-inf')

    # Token difference — strongest signal
    token_diff = (my_tokens - opp_tokens) * 100

    # Endgame urgency: bonus for being close to eliminating opponent
    endgame_bonus = 0.0
    if opp_tokens <= 4:
        endgame_bonus = (5 - opp_tokens) * 200   # press harder when opponent is low

    centre_weight = 20 if is_placement else 0.8
    total_score = 0.0

    for r in range(8):
        for c in range(8):
            cell = state.get(r, c)
            if not cell:
                continue

            idx   = r * 8 + c
            dist  = _CENTRE_DIST[idx]
            color, height = cell

            if color == my_color:
                # Reward height (stacking power)
                total_score += (height ** 1.5) * 15

                # Penalise being near edge — FIXED: quadratic, not cubic
                total_score -= (dist ** 2) * centre_weight

                # Reward eat opportunities
                for d in DIRECTIONS:
                    dest = _ADJ[r][c][d]
                    if dest is None:
                        continue
                    nr, nc = dest
                    adj_cell = state.get(nr, nc)

                    if adj_cell and adj_cell[0] == opponent and height >= adj_cell[1]:
                        total_score += 20 + adj_cell[1] * 5

                    # Mobility
                    if adj_cell is None or adj_cell[0] == my_color:
                        total_score += 1

                # Cascade threats on tall stacks
                if height >= 3:
                    for d in DIRECTIONS:
                        ddr, ddc = DIR_DELTA[d]
                        for step in range(1, height + 1):
                            nr2 = r + ddr * step
                            nc2 = c + ddc * step
                            if not (0 <= nr2 <= 7 and 0 <= nc2 <= 7):
                                break
                            target = state.get(nr2, nc2)
                            if target and target[0] == opponent:
                                total_score += 50 + target[1] * 25
                                break

                # Vulnerability: penalise stacks that can be eaten by opponent
                for d in DIRECTIONS:
                    dest = _ADJ[r][c][d]
                    if dest is None:
                        continue
                    nr, nc = dest
                    adj_cell = state.get(nr, nc)
                    if adj_cell and adj_cell[0] == opponent and adj_cell[1] >= height:
                        total_score -= 30 + height * 10  # penalise being eaten

            else:
                # FIXED: reward opponent stacks being NEAR edge (small dist = dangerous for them)
                # Previously this was reversed — opponents far from edge were rewarded
                total_score -= (height ** 2) * 20
                total_score -= (dist ** 1.5) * height * 2   # near-edge opponent = good for us

    current_hash  = state.board_hash()
    repetitions   = state.position_history.get(current_hash, 0)
    # FIXED: repetition penalty must dominate token advantage to prevent forced draws
    repetition_penalty = repetitions * 5000

    return token_diff + endgame_bonus + total_score - repetition_penalty


# ---------------------------------------------------------------------------
# Move ordering — killer moves + history heuristic + static priority
# ---------------------------------------------------------------------------

class MoveOrderer:
    def __init__(self):
        # killer_moves[depth] = list of up to 2 moves that caused cutoffs
        self.killer_moves: dict[int, list] = {}
        # history[move_key] = count of cutoffs this move caused
        self.history: dict = {}

    def get_killers(self, depth: int):
        return self.killer_moves.get(depth, [])

    def record_killer(self, depth: int, move):
        killers = self.killer_moves.setdefault(depth, [])
        if move not in killers:
            killers.insert(0, move)
            if len(killers) > 2:
                killers.pop()

    def record_history(self, move, depth: int):
        key = self._move_key(move)
        self.history[key] = self.history.get(key, 0) + (2 ** depth)

    def _move_key(self, move):
        return str(move)

    def order_moves(self, moves, state: GameState, my_color: PlayerColor, depth: int):
        opponent = PlayerColor.BLUE if my_color == PlayerColor.RED else PlayerColor.RED
        killers  = self.get_killers(depth)

        def priority(move):
            # 1. Winning move (captures last token)
            # 2. Killer moves from this depth
            # 3. History heuristic score
            # 4. Static: eat > cascade > move

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

                case _:
                    return 200

        return sorted(moves, key=priority)


# ---------------------------------------------------------------------------
# Alpha-beta minimax with transposition table
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
    tt_depth_offset: int = 0,
) -> float:
    if time.time() > deadline:
        raise TimeoutError()

    opponent = PlayerColor.BLUE if my_color == PlayerColor.RED else PlayerColor.RED

    # --- Terminal / leaf ---
    if state.is_terminal():
        winner = state.winner_checker()
        if winner == my_color:  return  1_000_000 + depth
        if winner is None:      return  0
        return                         -1_000_000 - depth

    if depth == 0:
        return heuristic(state, my_color, state._turn_count < 8)

    # --- Transposition table lookup ---
    board_key = (state.board_hash(), depth, maximising)
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

    for move in moves:
        new_state = state.copy()
        # FIXED: copy position_history so repetition tracking is correct in tree
        new_state.position_history = state.position_history.copy()
        new_state.apply_action(move)

        score = minimax(
            new_state, depth - 1, alpha, beta,
            not maximising, my_color, deadline, tt, orderer
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
# ---------------------------------------------------------------------------

_TIME_SAFETY_MARGIN = 0.05
_MAX_TIME_PER_MOVE  = 1.0


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

    if tt      is None: tt      = {}
    if orderer is None: orderer = MoveOrderer()

    # --- Time budget ---
    if time_remaining is not None:
        budget = min(time_remaining / 100, _MAX_TIME_PER_MOVE)
        budget = max(budget - _TIME_SAFETY_MARGIN, 0.05)
    else:
        budget = _MAX_TIME_PER_MOVE

    deadline = time.time() + budget

    # --- Placement phase: use shallow search (but not just depth-1 greedy) ---
    if state._turn_count < 8:
        ordered    = orderer.order_moves(moves, state, my_color, 0)
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

    # --- Play phase: iterative deepening ---
    ordered    = orderer.order_moves(moves, state, my_color, 0)
    best_move  = ordered[0]
    best_score = float('-inf')

    # Depth-0 baseline
    for move in ordered:
        new_state = state.copy()
        new_state.apply_action(move)
        score = heuristic(new_state, my_color, False)
        if score > best_score:
            best_score = score
            best_move  = move

    # Iterative deepening
    for depth in range(1, 8):
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
                    maximising=False,   # after our move, opponent minimises
                    my_color=my_color,
                    deadline=deadline,
                    tt=tt,
                    orderer=orderer,
                )
                if score > candidate_score:
                    candidate_score = score
                    candidate_move  = move

            best_move  = candidate_move
            best_score = candidate_score
            # Re-order: put best move first (killer move seed for next depth)
            ordered = [best_move] + [m for m in ordered if m != best_move]

        except TimeoutError:
            break

    return best_move


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class Agent:
    def __init__(self, color: PlayerColor, **referee: dict):
        self._color   = color
        self._state   = GameState()
        self._tt      = {}         # transposition table — persists across turns
        self._orderer = MoveOrderer()  # killer/history tables — persists across turns

    def action(self, **referee: dict) -> Action:
        time_remaining = referee.get("time_remaining", None)
        return get_best_move(
            self._state,
            self._color,
            time_remaining=time_remaining,
            tt=self._tt,
            orderer=self._orderer,
        )

    def update(self, color: PlayerColor, action: Action, **referee: dict):
        self._state.apply_action(action)