import time
from referee.game import PlayerColor, Action, EatAction, CascadeAction, MoveAction
from .state import DIR_DELTA, GameState, get_legal_moves, DIRECTIONS, _ADJ


# ---------------------------------------------------------------------------
# Heuristic
# ---------------------------------------------------------------------------

_CENTRE_DIST = [
    abs(r - 3.5) + abs(c - 3.5)
    for r in range(8)
    for c in range(8)
]

WIN_SCORE = 100_000
LOSS_SCORE = -100_000


def heuristic(state: GameState, my_color: PlayerColor, is_placement: bool = False) -> float:
    opponent = PlayerColor.BLUE if my_color == PlayerColor.RED else PlayerColor.RED

    my_tokens = state.red_tokens if my_color == PlayerColor.RED else state.blue_tokens
    opp_tokens = state.blue_tokens if my_color == PlayerColor.RED else state.red_tokens

    if not is_placement:
        if opp_tokens == 0:
            return WIN_SCORE
        if my_tokens == 0:
            return LOSS_SCORE

    # Material is most important because Cascade is won by eliminating tokens.
    token_diff = (my_tokens - opp_tokens) * 150

    total_score = 0
    centre_weight = 18 if is_placement else 1.5

    for r in range(8):
        for c in range(8):
            cell = state.get(r, c)
            if not cell:
                continue

            color, height = cell
            dist = _CENTRE_DIST[r * 8 + c]
            edge_dist = min(r, 7 - r, c, 7 - c)

            # Edge danger: cells near edge are easier to push off.
            edge_penalty = max(0, 2 - edge_dist) * height * 8

            # Height is useful, but not too much. Over-rewarding height caused bad play.
            height_score = (height ** 1.3) * 8

            if color == my_color:
                total_score += height_score
                total_score -= dist * centre_weight
                total_score -= edge_penalty

                for d in DIRECTIONS:
                    dest = _ADJ[r][c][d]
                    if dest is None:
                        continue

                    nr, nc = dest
                    adj_cell = state.get(nr, nc)

                    # Reward immediate EAT opportunity.
                    if adj_cell and adj_cell[0] == opponent and height >= adj_cell[1]:
                        total_score += 60 + adj_cell[1] * 20

                    # Penalise if opponent can eat us next turn.
                    if adj_cell and adj_cell[0] == opponent and adj_cell[1] >= height:
                        total_score -= 80 + height * 20

                    # Mobility / flexibility.
                    if adj_cell is None or adj_cell[0] == my_color:
                        total_score += 2

                # Reward cascade threats only when they actually line up with enemies.
                if height >= 2:
                    for d in DIRECTIONS:
                        dr, dc = DIR_DELTA[d]
                        for step in range(1, height + 1):
                            nr = r + dr * step
                            nc = c + dc * step

                            if not (0 <= nr <= 7 and 0 <= nc <= 7):
                                break

                            target = state.get(nr, nc)

                            if target and target[0] == opponent:
                                target_edge_dist = min(nr, 7 - nr, nc, 7 - nc)

                                # Higher reward if cascade can affect a big/enemy edge stack.
                                total_score += 50 + target[1] * 25

                                if target_edge_dist <= 1:
                                    total_score += 40 + target[1] * 15

                                break

            else:
                # Penalise opponent material/height.
                total_score -= (height ** 1.3) * 8

                # Opponent near edge is good for us because we may push them off.
                total_score += edge_penalty * 0.8

                for d in DIRECTIONS:
                    dest = _ADJ[r][c][d]
                    if dest is None:
                        continue

                    nr, nc = dest
                    adj_cell = state.get(nr, nc)

                    # Penalise opponent EAT opportunities.
                    if adj_cell and adj_cell[0] == my_color and height >= adj_cell[1]:
                        total_score -= 70 + adj_cell[1] * 20

    # Avoid repeated board states because repetition leads to draws.
    current_hash = state.board_hash()
    repetitions = state.position_history.get(current_hash, 0)
    repetition_penalty = repetitions * 800

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
                        return -200 - target[1] * 20
                return -100

            case CascadeAction(coord, direction):
                cell = state.get(coord.r, coord.c)
                if not cell:
                    return 10

                height = cell[1]
                dr, dc = DIR_DELTA[direction]

                score = 0

                for step in range(1, height + 1):
                    nr = coord.r + dr * step
                    nc = coord.c + dc * step

                    if not (0 <= nr <= 7 and 0 <= nc <= 7):
                        break

                    target = state.get(nr, nc)

                    if target and target[0] == opponent:
                        score -= 80 + target[1] * 20
                        break

                return score

            case MoveAction():
                return 5

            case _:
                return 20

    return sorted(moves, key=move_priority)


# ---------------------------------------------------------------------------
# Alpha-beta minimax
# ---------------------------------------------------------------------------

def minimax(
    state: GameState,
    depth: int,
    alpha: float,
    beta: float,
    maximising: bool,
    my_color: PlayerColor,
    deadline: float,
) -> float:

    if time.time() > deadline:
        raise TimeoutError()

    if state.is_terminal():
        winner = state.winner_checker()
        if winner == my_color:
            return WIN_SCORE + depth
        if winner is None:
            return 0
        return LOSS_SCORE - depth

    if depth == 0:
        return heuristic(state, my_color, state._turn_count < 8)

    moves = get_legal_moves(state)

    if not moves:
        return 0

    current_color = my_color if maximising else (
        PlayerColor.BLUE if my_color == PlayerColor.RED else PlayerColor.RED
    )

    moves = order_moves(moves, state, current_color)

    if maximising:
        best = float("-inf")

        for move in moves:
            new_state = state.copy()
            new_state.apply_action(move)

            score = minimax(
                new_state,
                depth - 1,
                alpha,
                beta,
                False,
                my_color,
                deadline,
            )

            best = max(best, score)
            alpha = max(alpha, best)

            if beta <= alpha:
                break

        return best

    else:
        best = float("inf")

        for move in moves:
            new_state = state.copy()
            new_state.apply_action(move)

            score = minimax(
                new_state,
                depth - 1,
                alpha,
                beta,
                True,
                my_color,
                deadline,
            )

            best = min(best, score)
            beta = min(beta, best)

            if beta <= alpha:
                break

        return best


# ---------------------------------------------------------------------------
# Iterative deepening with time guard
# ---------------------------------------------------------------------------

_TIME_SAFETY_MARGIN = 0.05
_MAX_TIME_PER_MOVE = 1.0


def get_best_move(
    state: GameState,
    my_color: PlayerColor,
    time_remaining=None,
) -> Action:

    moves = get_legal_moves(state)

    if not moves:
        return None

    if len(moves) == 1:
        return moves[0]

    if time_remaining is not None:
        budget = min(time_remaining / 100, _MAX_TIME_PER_MOVE)
        budget = max(budget - _TIME_SAFETY_MARGIN, 0.05)
    else:
        budget = _MAX_TIME_PER_MOVE

    deadline = time.time() + budget

    ordered = order_moves(moves, state, my_color)

    # Immediate winning move check.
    for move in ordered:
        new_state = state.copy()
        new_state.apply_action(move)

        if new_state.is_terminal() and new_state.winner_checker() == my_color:
            return move

    # Placement phase: keep it simpler and faster.
    if state._turn_count < 8:
        best_move = ordered[0]
        best_score = float("-inf")

        for move in ordered:
            new_state = state.copy()
            new_state.apply_action(move)

            try:
                score = minimax(
                    new_state,
                    depth=2,
                    alpha=float("-inf"),
                    beta=float("inf"),
                    maximising=False,
                    my_color=my_color,
                    deadline=deadline,
                )
            except TimeoutError:
                score = heuristic(new_state, my_color, True)

            if score > best_score:
                best_score = score
                best_move = move

        return best_move

    # Depth-0 fallback.
    best_move = ordered[0]
    best_score = float("-inf")

    for move in ordered:
        new_state = state.copy()
        new_state.apply_action(move)
        score = heuristic(new_state, my_color, False)

        if score > best_score:
            best_score = score
            best_move = move

    # Iterative deepening.
    for depth in range(1, 5):
        candidate_move = best_move
        candidate_score = float("-inf")

        try:
            for move in ordered:
                new_state = state.copy()
                new_state.position_history = state.position_history.copy()
                new_state.apply_action(move)

                score = minimax(
                    new_state,
                    depth=depth,
                    alpha=float("-inf"),
                    beta=float("inf"),
                    maximising=False,
                    my_color=my_color,
                    deadline=deadline,
                )

                if score > candidate_score:
                    candidate_score = score
                    candidate_move = move

            best_move = candidate_move
            best_score = candidate_score

            # Put best move first next round to improve alpha-beta pruning.
            ordered = [best_move] + [m for m in ordered if m != best_move]

        except TimeoutError:
            break

    return best_move