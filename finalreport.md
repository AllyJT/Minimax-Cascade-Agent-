The University of Melbourne

COMP30024 – Artificial Intelligence

Project Part B: Game Playing Agent

**PLAYING CASCADE USING MINIMAX**

Water Bottle: Phuong Trang Tran – 1409466, Ha Linh Nguyen – 1492069

---

## Overview

This report describes the design and implementation of a game-playing agent for Cascade, a two-player adversarial board game. The agent is built on iterative deepening alpha-beta minimax with a multi-feature evaluation function, a transposition table, and dedicated mechanisms for handling draw-by-repetition. The report is structured as follows: Section 1 describes the final agent's action selection approach; Section 2 evaluates its performance; Section 3 documents failed heuristic trials that motivated the final design; Section 4 covers technical optimisations; and Section 5 describes supporting development work.

---

## 1. Approach: Action Selection

### 1.1 Overview

The agent selects actions using **iterative deepening alpha-beta minimax** as its core search strategy. On every turn, the algorithm performs successive full-depth searches from depth 1 up to a maximum of 12, subject to a per-move time budget of 2.0 seconds. The search is guided by a multi-feature evaluation function, a transposition table, and a move ordering system. Two dedicated mechanisms handle draw-by-repetition, which was identified as the dominant failure mode in earlier versions.

---

### 1.2 Search Algorithm

**Iterative Deepening.**
At each turn, the agent runs alpha-beta minimax at depth 1, then depth 2, and so on, until the time budget is exhausted. If a `TimeoutError` is raised mid-depth, the result from the last fully completed depth is committed. This ensures the agent always returns a well-reasoned move even under time pressure, while naturally using as much of the available time as possible.

**Alpha-Beta Pruning.**
Alpha-beta pruning is applied throughout the search tree. When a beta-cutoff occurs — a move is proven too good for the maximising player, so the minimising player would avoid the subtree — the remaining moves at that node are skipped. For well-ordered move lists, this reduces the effective branching factor to approximately the square root of the full tree, allowing the agent to search roughly twice as deep as plain minimax in the same time.

**Transposition Table.**
A transposition table (TT) is maintained across the entire game, not just a single turn, so search results from earlier turns can benefit later ones. Each entry stores a score, a bound type, and the depth at which it was computed:

- `TT_EXACT`: the stored score is exact — return it directly.
- `TT_LOWER` (alpha bound): use it to raise alpha.
- `TT_UPPER` (beta bound): use it to lower beta.

The table is capped at 500,000 entries to prevent unbounded memory growth.

---

### 1.3 Move Ordering

Quality move ordering is critical to alpha-beta efficiency. A `MoveOrderer` class maintains two complementary heuristics across the entire game:

**Killer Moves.**
Up to two moves per search depth that have previously caused a beta-cutoff are stored. These are tried before other moves at the same depth in subsequent iterations, as they are statistically likely to cause cutoffs again.

**History Heuristic.**
Every move that causes a cutoff increments a persistent counter weighted by `2^depth`. Moves with higher history scores are searched earlier. This rewards moves that are consistently strong across different board positions throughout the game.

**Static Priority.**
Within each node, moves are additionally ordered by static type before killer and history scores are applied:

- Winning moves (captures the opponent's last token) — searched first
- `EatAction` moves, ordered by tokens captured (larger captures first)
- `CascadeAction` moves that threaten opponent tokens
- `MoveAction` moves
- `PlaceAction` moves, ordered by proximity to the board centre

---

### 1.4 Repetition and Cycle Handling

**Path-Set Cycle Detection.**
A mutable set of board hashes (`path_set`) is threaded through every level of the minimax recursion. Before expanding a node, the algorithm checks whether the current board hash is already in the set — if so, the line leads to a draw by repetition and is scored 0. The hash is added before recursing and removed (`discard`) after, maintaining the invariant that the set contains exactly the positions on the current search path.

**Game History Penalty at Leaf Nodes.**
The actual game's `position_history` dictionary (mapping board hash to visit count) is passed into minimax as a read-only parameter. At depth-0 leaf nodes, positions that have already been visited in the real game receive a penalty of −150 per prior visit. This steers the agent away from revisiting real-game positions and converts oscillation patterns into decisive lines.

**Threefold Repetition Avoidance.**
At the root of `get_best_move`, any move whose resulting position hash already appears two or more times in `position_history` is scored as a draw (−5000 if a better alternative exists, otherwise 0), preventing an automatic loss-by-draw.

---

### 1.5 Evaluation Function

The heuristic estimates board quality from the agent's perspective using six additive terms:

$$h(s) = 100 \cdot (T_{self} - T_{opp}) + 1.5 \cdot (H^2_{self} - H^2_{opp}) + 2.0 \cdot (E_{opp} - E_{self}) + 20 \cdot (A_{self} - A_{opp}) + 30 \cdot (C_{self} - C_{opp})$$

where $T$ denotes total tokens, $H^2$ denotes sum of squared stack heights, $E$ denotes edge penalty (height-weighted proximity to board edge), $A$ denotes immediate eat-threat tokens, and $C$ denotes cascade-threat tokens.

**Material Advantage.**
The difference in total token count is given the dominant weight of 100, reflecting that token elimination is the primary winning condition of Cascade.

**Height Advantage.**
Stack heights are squared and summed for each side. The squared term rewards concentration — a single tall stack is worth more than two short ones of equivalent total height, reflecting the greater cascade potential of taller stacks.

**Edge Penalty Advantage.**
Tokens near the board edge have fewer available moves and are more vulnerable to being pushed off by cascade actions. The net edge penalty rewards the agent for keeping its own tokens central while pushing the opponent toward the edges.

**Eat Threats.**
The net number of tokens immediately capturable by each side (via `EatAction`) is weighted at 20 per token. This is a strong short-term tactical signal — being able to capture while avoiding capture is directly decisive.

**Cascade Threats.**
For each tall stack (height ≥ 3), the search checks whether a cascade in any direction would hit an opponent token. The net cascade-threat advantage is weighted at 30 per token, higher than simple eat threats, reflecting the chained destructive potential of cascade actions.

**Centre Bonus (Placement Phase Only).**
During the four-token placement phase (`_turn_count < 8`), each own token receives a bonus of `(7 − centre_dist) × 10`, rewarding central positions that maximise future reach.

---

### 1.6 Conclusion

The agent's action selection combines iterative deepening alpha-beta search with a transposition table, killer move and history heuristic ordering, path-set cycle detection, and a six-term evaluation function. Together these components address the three main challenges of Cascade: tactical capture opportunities, positional stability, and avoidance of draw-by-repetition.

---

## 2. Performance Evaluation

### 2.1 Overview

The agent's performance was evaluated through direct match-play against three reference opponents of increasing strength: a random agent, a greedy one-ply agent, and an alpha-beta minimax reference agent at fixed depth 3 with no transposition table. For each opponent, 20 games were played from both RED and BLUE starting positions, and win, draw, and loss counts were recorded.

---

### 2.2 Results

The agent consistently defeated the random and greedy agents across all tested matches, achieving the target win rate of 90%+ from both starting colours. Against the depth-3 minimax reference agent, the final version achieved a win rate of approximately 85%+ over repeated game samples, with losses being rare and draws almost entirely eliminated by the repetition-handling mechanisms.

---

### 2.3 Identified Failure Modes

**Draw-by-Repetition.**
In early versions, the agent frequently oscillated between positions, resulting in drawn games that should have been decisive wins. This was the dominant failure mode and directly motivated the path-set cycle detection and game history penalty mechanisms described in Section 1.4.

**Shallow Search Depth.**
Before the `position_history.copy()` performance fix (Section 4.2), the agent could rarely exceed depth 4 within the time budget. After the fix, it reliably reached depth 8–10+ in the mid-game, substantially improving the quality of moves in critical positions.

---

### 2.4 Conclusion

The combination of deeper search and robust repetition handling was the decisive factor in moving the agent from a draw-prone, shallow-searching player to one that wins the clear majority of games against the depth-3 minimax reference. Remaining losses are predominantly attributable to time-pressure situations in which the search terminates at a lower depth than usual.

---

## 3. Failed Trials

### 3.1 Overview

Three agent designs were trialled and discarded before arriving at the final evaluation function. Each failed to produce decisive play against minimax-based opponents, though each failure revealed a specific design principle that informed the next iteration.

---

### 3.2 Trial 1: Starting Agent — Pure Token-Difference Minimax

#### 3.2.1 Design Rationale

The first implementation was a minimal alpha-beta minimax agent built to establish a working baseline as quickly as possible. The evaluation function was a single-term token difference:

$$h(s) = T_{self} - T_{opp}$$

where $T$ denotes the total number of tokens (summed across stack heights) owned by each side. No weights, no positional terms, and no tactical features were included. The search ran at a fixed depth of 3 with no move ordering — moves were tried in whatever order the move generator returned them — and the agent used the same fixed depth for both the placement phase and the play phase.

The board state was stored as a nested 8×8 list. `state.copy()` used `copy.deepcopy`, which copies the entire 2D structure on every search node.

#### 3.2.2 Observed Behaviour

The agent produced legal, coherent play and demonstrated basic material awareness — it consistently avoided moves that caused a net token loss and captured enemy stacks when possible. Against a random opponent it won reliably. Against the greedy reference agent results were mixed, and against the depth-3 minimax reference agent the agent drew or lost frequently.

#### 3.2.3 Identified Limitations

**No positional awareness.**
The heuristic assigned equal value to a token on the edge and one in the centre. The agent regularly placed and moved stacks into corner and edge squares, where they were vulnerable to cascade push-off and had fewer available moves.

**No tactical signals.**
Immediate eat threats and cascade opportunities were not rewarded. The agent sometimes passed up a capture that was one ply away simply because the token counts did not differ at depth 0.

**No repetition penalty.**
The agent had no mechanism to discourage revisiting positions. Against stronger opponents that could force a stable oscillation, it drew games that should have been decisive wins.

**Fixed depth and no move ordering.**
At fixed depth 3 with no ordering, alpha-beta pruning was inefficient. The effective branching factor was much larger than necessary, and the agent could not adapt its search depth to the time remaining.

#### 3.2.4 Conclusion

The starting agent established that the move generator, state representation, and minimax skeleton were correct, but its evaluation function was too coarse to produce strong play. The single-term heuristic, absence of move ordering, and fixed search depth all limited performance and directly motivated the next iteration.

---

### 3.3 Trial 2: Revised Heuristic with Tactical Penalty

#### 3.3.1 Design Rationale

After testing Trial 1, the heuristic was found to overvalue tall stacks and cascade potential while underestimating immediate tactical danger. This caused the agent to choose visually strong moves that left stacks vulnerable to capture or positional loss. The heuristic was revised to include:

- stronger penalties for stacks that could be eaten on the opponent's next turn,
- a higher weighting for material advantage, and
- a reduced reward for height unless it contributed to concrete tactical opportunities.

This made the agent less aggressive but more stable against minimax-based opponents.

#### 3.3.2 Observed Behaviour

The revised agent showed improved resistance to immediate capture threats and was less prone to sacrificing material for positional gains that did not materialise. Against simple opponents, win rates improved. However, against minimax-based agents the agent continued to produce drawn games at a high rate.

#### 3.3.3 Identified Limitations

**Non-functional Repetition Penalty.**
The repetition penalty included in this heuristic was found to be structurally broken. The root cause is that `GameState.copy()` resets `position_history` to an empty dictionary (`new.position_history = {}`). This means that inside the minimax search tree, every copied state has no memory of prior positions. The repetition penalty therefore evaluates to zero at every search node, and the agent continues to choose safe, reversible moves without penalty.

**Incomplete Board Hash.**
The board hash used for repetition detection did not include the current player's turn colour. In Cascade, a repeated position is only a true repetition if the same board state occurs with the same player to move. Omitting the turn colour caused the hash to conflate positions that are strategically distinct, further undermining the reliability of any repetition-based penalty.

#### 3.3.4 Conclusion

Trial 2 correctly identified the need for repetition penalties but failed to implement them effectively due to two structural issues: the loss of position history during state copying and the incomplete board hash definition. These findings directly motivated the final design, in which repetition handling is separated from the heuristic and implemented at the search level via `path_set` cycle detection and the read-only `game_history` penalty — both of which are immune to the state-copy issue because they do not rely on copied state objects.

---

### 3.4 Trial 3: Intermediate Agent — Expanded Heuristic with Static Move Ordering

#### 3.4.1 Design Rationale

Building on the lessons of Trials 1 and 2, a substantially revised agent was implemented as a direct predecessor to the final version. The evaluation function was extended to four terms:

$$h(s) = 50 \cdot (T_{self} - T_{opp}) + w_c \cdot \sum_{own} (-dist_{centre} \cdot height) + 20 \cdot N_{eat} - 500 \cdot R$$

where $w_c = 25$ during the placement phase and $1$ otherwise, $N_{eat}$ counts own tokens adjacent to an opponent stack that can be eaten, and $R$ is the number of times the current position hash appears in `position_history`. A static move-ordering function was also introduced, sorting moves as `EatAction` > `CascadeAction` > `MoveAction` before each minimax expansion. The search depth was made phase-adaptive: depth 1 during placement (where the branching factor exceeds 60) and depth 3 during play.

#### 3.4.2 Changes Relative to Trial 1

Compared to the starting agent, this version added:

- a weighted token-difference term (×50) with terminal detection (`+∞`/`−∞` when either side has zero tokens),
- a centre-proximity reward that pushed own stacks toward the board centre and penalised opponent stacks there,
- an eat-threat bonus counting tokens immediately capturable by the agent,
- a repetition penalty scaled by visit count,
- static move ordering to improve alpha-beta efficiency, and
- phase-adaptive depth to avoid timeout during the high-branching placement phase.

#### 3.4.3 Observed Behaviour

The agent showed clear improvements in both opening play and mid-game aggression. It placed pieces centrally, prioritised eat actions, and avoided obvious tactical blunders. Against random and greedy opponents win rates were high and consistent. Against the depth-3 minimax reference agent, performance improved but drawn games remained frequent.

#### 3.4.4 Identified Limitations

**Broken repetition penalty.**
The repetition penalty was silently non-functional inside the search tree. `GameState.copy()` resets `position_history` to an empty dictionary, so every copied node has no memory of prior positions. The penalty term evaluates to zero at every search node, and draw-by-oscillation was not prevented.

**No iterative deepening or time awareness.**
The agent used fixed depths (1 or 3) with no time budget tracking. In complex positions where depth 3 took longer than expected, the agent risked timeout; in simple positions, it did not use available time to search deeper.

**No transposition table.**
Identical positions reached by different move sequences were re-evaluated from scratch. This wasted a large fraction of the search effort, particularly in the mid-game where transpositions are common.

**`deepcopy` state copy overhead.**
The board was stored as a nested 8×8 list and copied with `copy.deepcopy` on every search node. This was the dominant runtime cost and capped the practical depth reachable within the time budget.

**Simple static move ordering.**
The ordering function assigned a fixed priority by action type but did not adapt based on the current position or learn from prior cutoffs. Killer moves and the history heuristic were absent, so the ordering did not improve as the search progressed.

#### 3.4.5 Conclusion

Trial 3 was the closest predecessor to the final agent and directly motivated the key architectural changes that define it: iterative deepening with time-budget management, a transposition table persisted across turns, the `MoveOrderer` class with killer moves and history heuristic, path-set cycle detection to replace the broken in-heuristic penalty, and a flat-array board representation to make state copies fast enough to sustain deeper search.

---

## 4. Other Technical Aspects

### 4.1 Overview

Several algorithmic and data-structure optimisations were implemented to maximise the agent's search depth within the per-move time budget. These improvements operate below the level of the search algorithm and evaluation function but have a significant effect on practical performance.

---

### 4.2 State Representation

**Flat Board Array.**
`GameState` stores the board as a flat `list[64]` rather than a nested 2D array. This makes `state.copy()` a single list slice (`board[:]`) — one of the most performance-critical operations, as a copy is made for every node in the search tree.

**Incremental Token Counts.**
`red_tokens` and `blue_tokens` are updated incrementally every time a cell is written via `set()`. Terminal detection and the material advantage term in the heuristic therefore require no board scan — they execute in O(1).

**Lazy Board Hash.**
`board_hash()` uses a dirty flag (`_hash_dirty`). The hash is recomputed only when the board has changed since the last call; multiple calls on an unchanged state return the cached result. The hash is a tuple of `(cell_index, color, height)` for all occupied cells, directly usable as a dictionary key in the TT and `path_set`.

---

### 4.3 Precomputed Lookup Tables

**Adjacency Table.**
`_ADJ[r][c][direction]` is a module-level table containing the `(nr, nc)` neighbour of every cell in every direction, or `None` if out of bounds. This eliminates repeated bounds-checking arithmetic in move generation, heuristic evaluation, and move ordering — all of which iterate over neighbours in their innermost loops.

**Centre Distance Table.**
`_CENTRE_DIST[r * 8 + c]` precomputes the Manhattan distance from the board centre (3.5, 3.5) for all 64 cells. This is used in the placement heuristic and move ordering without any arithmetic at runtime.

---

### 4.4 Iterative Deepening Re-ordering

After each completed depth, the best move found is placed at the front of the move list for the next iteration. This implements a lightweight form of principal variation re-ordering without maintaining a full PV table. The best move is then tried first at the next depth, maximising its contribution to alpha-beta pruning.

---

### 4.5 Conclusion

The combination of a flat board representation, incremental token counts, a lazy hash, and precomputed adjacency and distance tables substantially reduces per-node overhead. These optimisations were the primary enabler of the deeper search depths that distinguish the final agent's performance from earlier versions.

---

## 5. Supporting Work

### 5.1 Overview

Development of the agent was supported by systematic match-play testing against agents of varying strength, and by computational complexity analysis to identify and address performance bottlenecks. Both activities provided direct evidence of failure modes and guided each iterative improvement.

---

### 5.2 Testing Methodology

The agent was tested progressively against three opponents:

- a **random agent**, to verify basic correctness of move generation and search,
- a **greedy one-ply agent**, to verify that the search was exploiting simple tactical opportunities, and
- the **minimax reference agent** at fixed depth 3, as the primary benchmark for final performance.

Match results were observed to identify specific failure modes. The two most impactful findings — draw-by-repetition dominance and the `position_history.copy()` allocation bottleneck — were discovered through this testing process and directly produced the path-set cycle detection and game history penalty mechanisms.

---

### 5.3 Complexity Analysis

Big-O analysis was used alongside testing to identify the most time-consuming operations in the search loop. This analysis pointed to per-node memory allocation (specifically `position_history.copy()`) as the dominant overhead, and informed the decision to use the read-only `game_history` parameter pattern instead. The time budget per move was calibrated based on an estimate of expected move count across a full game (approximately 150 play turns), dividing the 180-second total budget accordingly.

---

### 5.4 Iterative Comparison

Intermediate agent versions were compared by running back-to-back match series and observing win/draw/loss distributions. Individual changes — heuristic weight adjustments, transposition table integration, move ordering additions — were each evaluated in isolation before being committed to the final version, ensuring that improvements were additive and regressions were caught early.

---

### 5.5 Conclusion

Direct match-play testing against a range of opponents, combined with complexity analysis, was the primary tool for diagnosing weaknesses and validating improvements. This approach enabled targeted, evidence-driven development and was more informative than static code analysis alone, as several key failure modes only became apparent through observed game behaviour.

---

## References

[1] GeeksForGeeks. *Minimax Algorithm in Game Theory | Set 1 (Introduction)*. Available at: https://www.geeksforgeeks.org/dsa/minimax-algorithm-in-game-theory-set-1-introduction/. Consulted for background reading on minimax and alpha-beta pruning formulation.

[2] T. K. Hoin. *AI-Project-B* (GitHub repository). Available at: https://github.com/tuankhoin/AI-Project-B. Consulted as a reference example of a prior COMP30024 Part B submission for general structural inspiration.

[3] M. Farrugia. *AI-projectB* (GitHub repository). Available at: https://github.com/matomatical/AI-projectB. Consulted as a reference example of a prior COMP30024 Part B submission for general structural inspiration.

[4] Anthropic. *Claude* (Large Language Model, claude.ai). Used as an AI coding assistant during development to help debug code, discuss algorithmic design decisions, and draft portions of this report. All algorithmic ideas and strategic decisions were conceived and verified by the team.

[5] OpenAI. *ChatGPT* (Large Language Model, chat.openai.com). Used as an AI assistant to discuss and explore game-playing algorithmic concepts during the design phase.
