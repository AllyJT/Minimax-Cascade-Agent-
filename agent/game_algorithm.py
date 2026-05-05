# agent/game_algorithm.py
import time
from referee.game import PlayerColor, Action, Coord, EatAction, CascadeAction, MoveAction, PlaceAction
from .state import GameState, get_legal_moves, DIRECTIONS


def heuristic(state: GameState, my_color, is_placement=False) -> float:
    opponent = PlayerColor.BLUE if my_color == PlayerColor.RED else PlayerColor.RED

    my_tokens = sum(cell[1] for row in state.board for cell in row if cell and cell[0] == my_color)
    opp_tokens = sum(cell[1] for row in state.board for cell in row if cell and cell[0] == opponent)

    # terminal state checks (play phase only)
    if not is_placement:
        if opp_tokens == 0:
            return float('inf')
        if my_tokens == 0:
            return float('-inf')

    # token difference — heavily weighted
    token_diff = (my_tokens - opp_tokens) * 50

    # centre control
    centre_weight = 25 if is_placement else 1
    centre_score = 0
    eat_score = 0

    for r in range(8):
        for c in range(8):
            cell = state.board[r][c]
            if not cell:
                continue
            dist = abs(r - 3.5) + abs(c - 3.5)
            if cell[0] == my_color:
                centre_score -= dist * cell[1] * centre_weight
                # reward being able to eat
                for d in DIRECTIONS:
                    adj = state.move_coord(Coord(r, c), d)
                    if adj is None:
                        continue
                    adj_cell = state.board[adj.r][adj.c]
                    if adj_cell and adj_cell[0] == opponent and cell[1] >= adj_cell[1]:
                        eat_score += 20
            else:
                centre_score += dist * cell[1] * centre_weight

    # penalise repeated positions heavily
    current_hash = state.board_hash()
    repetitions = state.position_history.get(current_hash, 0)
    repetition_penalty = repetitions * 100

    return token_diff + centre_score + eat_score - repetition_penalty


def order_moves(moves, state, my_color):
    opponent = PlayerColor.BLUE if my_color == PlayerColor.RED else PlayerColor.RED

    def move_priority(move):
        match move:
            case EatAction(coord, direction):
                dest = state.move_coord(coord, direction)
                if dest and state.board[dest.r][dest.c]:
                    return -state.board[dest.r][dest.c][1]
                return -1
            case CascadeAction():
                return 0
            case MoveAction():
                return 1
            case _:
                return 2

    return sorted(moves, key=move_priority)


def minimax(state, depth, alpha, beta, maximising, my_color):
    if depth == 0 or state.is_terminal():
        is_placement = state._turn_count < 8
        return heuristic(state, my_color, is_placement)

    if maximising:
        best = float('-inf')
        for move in order_moves(get_legal_moves(state), state, my_color):
            new_state = state.copy()
            new_state.apply_action(move)
            score = minimax(new_state, depth - 1, alpha, beta, False, my_color)
            best = max(best, score)
            alpha = max(alpha, best)
            if beta <= alpha:
                break
        return best
    else:
        best = float('inf')
        for move in order_moves(get_legal_moves(state), state, my_color):
            new_state = state.copy()
            new_state.apply_action(move)
            score = minimax(new_state, depth - 1, alpha, beta, True, my_color)
            best = min(best, score)
            beta = min(beta, best)
            if beta <= alpha:
                break
        return best


def get_best_move(state: GameState, my_color, time_remaining=None) -> Action:
    moves = get_legal_moves(state)
    if not moves:
        return None

    best_move = moves[0]

    # time budget per move
    if time_remaining is None:
        time_budget = 5.0
    elif time_remaining < 10:
        time_budget = 0.5
    elif time_remaining < 30:
        time_budget = 1.0
    else:
        time_budget = 2.0


    # placement gets less time
    if state._turn_count < 8:
        time_budget = min(time_budget, 2.0)

    start_time = time.time()

    # iterative deepening
    for depth in range(1, 4):
        if time.time() - start_time > time_budget:
            break

        depth_best_move = best_move
        depth_best_score = float('-inf')
        timed_out = False

        for move in moves:
            if time.time() - start_time > time_budget:
                timed_out = True
                break

            new_state = state.copy()
            new_state.apply_action(move)
            score = minimax(new_state, depth=depth, alpha=float('-inf'),
                          beta=float('inf'), maximising=False, my_color=my_color)

            if score > depth_best_score:
                depth_best_score = score
                depth_best_move = move

        # only update if we finished the full depth
        if not timed_out:
            best_move = depth_best_move

    return best_move