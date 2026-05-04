## Implement the algorithm
from referee.game import PlayerColor, Action
from .state import GameState, get_legal_moves

## Heuristic trial 1 - token count difference
# def heuristic(state: GameState, my_color) -> float:
#     opponent = PlayerColor.BLUE if my_color == PlayerColor.RED else PlayerColor.RED
#     my_tokens = sum(cell[1] for row in state.board for cell in row if cell and cell[0] == my_color)
#     opponent_tokens = sum(cell[1] for row in state.board for cell in row if cell and cell[0] == opponent)
#     # if i have more tokens than opponent -> positive number, if they have more -> negative number
#     return my_tokens - opponent_tokens


def heuristic(state: GameState, my_color) -> float:
    opponent = PlayerColor.BLUE if my_color == PlayerColor.RED else PlayerColor.RED
    my_tokens = sum(cell[1] for row in state.board for cell in row if cell and cell[0] == my_color)
    opponent_tokens = sum(cell[1] for row in state.board for cell in row if cell and cell[0] == opponent)
    # if i have more tokens than opponent -> positive number, if they have more -> negative number
    centre_score = 0
    for r in range(8):
        for c in range(8):
            cell = state.board[r][c]
            if cell and cell[0] == my_color:
                # distance from centre (3.5, 3.5) — closer is better
                dist = abs(r - 3.5) + abs(c - 3.5)
                centre_score -= dist * cell[1]  # taller stacks penalised more for being far
            elif cell and cell[0] == opponent:
                dist = abs(r - 3.5) + abs(c - 3.5)
                centre_score += dist * cell[1]
    token_diff =  (my_tokens - opponent_tokens) * 10 # 10 is a abitrary weight

    return token_diff + centre_score

def minimax(state, depth, alpha, beta, maximising, my_color):
    # looked far enough ahead of game, score board and return
    if depth == 0 or state.is_terminal():
        return heuristic(state, my_color)
    
    # my turn, pick highest score 
    if maximising:
        best = float('-inf')
        # try every move, recurse, keep the best score
        for move in get_legal_moves(state):
            new_state = state.copy()
            new_state.apply_action(move)
            score = minimax(new_state, depth - 1, alpha, beta, False, my_color)
            best = max(best, score)
            # skip branches that would score less
            alpha = max(alpha, best)
            if beta <= alpha:
                break
        return best
    # opponent's turn, opponent tries to minimize our score
    else:
        best = float('inf')
        for move in get_legal_moves(state):
            new_state = state.copy()
            new_state.apply_action(move)
            score = minimax(new_state, depth - 1, alpha, beta, True, my_color)
            best = min(best, score)
            beta = min(beta, best)
            if beta <= alpha:
                break
        return best

def get_best_move(state: GameState, my_color, time_remaining=None) -> Action:
    best_score = float('-inf')
    moves = get_legal_moves(state)
    if not moves:
        return None
    best_move = moves[0]
    
    # adjust depth based on phase and time remaining
    if state._turn_count < 8:
        depth = 2  # placement phase
    else:
        depth = 4  # play phase
    
    for move in moves:
        new_state = state.copy()
        new_state.apply_action(move)
        score = minimax(new_state, depth=depth, alpha=float('-inf'), beta=float('inf'), maximising=False, my_color=my_color)
        if score > best_score:
            best_score = score
            best_move = move
    return best_move

