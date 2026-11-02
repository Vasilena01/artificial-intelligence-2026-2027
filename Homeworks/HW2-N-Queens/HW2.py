import sys
import os
import time
import random

BIG_N = 1000             # max value of N for checking all rows
INIT_SAMPLES = 50        # rows sampled per column for large N
MOVE_SAMPLES = 50        # rows sampled per move for large N
STEPS_PER_QUEEN = 8      # step budget = STEPS_PER_QUEEN * N
MAX_RANDOM_PROBES = 100  # tries to find conflicted queen via random sampling
MAX_RESTARTS = 20        # restart with fresh init if stuck in local min

class Board:
    def __init__(self, n):
        self.n = n
        self.queens = [0] * n              # queens[col] = row
        self.row_count = [0] * n           # queens per row
        self.diag1 = [0] * (2 * n - 1)     # '/' diagonals: index = row + col
        self.diag2 = [0] * (2 * n - 1)     # '\' diagonals: index = row - col + n - 1

    def place(self, r, c):
        self.queens[c] = r
        self.row_count[r] += 1
        self.diag1[r + c] += 1
        self.diag2[r - c + self.n - 1] += 1

    def remove(self, r, c):
        self.row_count[r] -= 1
        self.diag1[r + c] -= 1
        self.diag2[r - c + self.n - 1] -= 1

    def conflicts_at(self, r, c):
        return self.row_count[r] + self.diag1[r + c] + self.diag2[r - c + self.n - 1]

    def conflicts_of_queen(self, c):
        r = self.queens[c]
        return self.conflicts_at(r, c) - 3

    def move_queen(self, c, new_r):
        old_r = self.queens[c]
        if old_r == new_r:
            return
        self.remove(old_r, c)
        self.place(new_r, c)

def print_board(queens, n):
    for r in range(n):
        row = []
        for c in range(n):
            row.append('*' if queens[c] == r else '_')
        print(' '.join(row))

def greedy_init(board):
    # place queens column by column, each placed in the row with the fewest conflicts
    n = board.n

    # randomized column order
    cols = list(range(n))
    random.shuffle(cols)

    for c in cols:
        best_row = 0
        best_conflicts = n + 1

        if n <= BIG_N:
            # here we check every row
            for r in range(n):
                conflicts = board.conflicts_at(r, c)
                if conflicts < best_conflicts:
                    best_conflicts = conflicts
                    best_row = r
                elif conflicts == best_conflicts and random.random() < 0.5:
                    best_row = r
        else:
            # here we sample random rows + diagonal fallback
            candidates = [random.randrange(n) for _ in range(INIT_SAMPLES)]
            candidates.append(c % n)  # deterministic seed row
            for r in candidates:
                conflicts = board.conflicts_at(r, c)
                if conflicts < best_conflicts:
                    best_conflicts = conflicts
                    best_row = r
                elif conflicts == best_conflicts and random.random() < 0.5:
                    best_row = r

        board.place(best_row, c)


def find_conflicted_queen(board):
    # picks a rndm col, checks if it is conflicted and repeats up to max_random_probes
    n = board.n
    row_count = board.row_count
    diag1 = board.diag1
    diag2 = board.diag2
    queens = board.queens
    nm1 = n - 1
    randrange = random.randrange

    for _ in range(MAX_RANDOM_PROBES):
        c = randrange(n)
        r = queens[c]
        if row_count[r] + diag1[r + c] + diag2[r - c + nm1] - 3 > 0:
            return c
    for c in range(n):
        r = queens[c]
        if row_count[r] + diag1[r + c] + diag2[r - c + nm1] - 3 > 0:
            return c
    return -1


def find_best_row(board, c):
    # return the row with the fewest conflicts for queen in column c
    n = board.n
    row_count = board.row_count
    diag1 = board.diag1
    diag2 = board.diag2
    current_row = board.queens[c]
    nm1 = n - 1

    best_row = current_row
    best_conflicts = n + 1

    if n <= BIG_N:
        for r in range(n):
            conflicts = row_count[r] + diag1[r + c] + diag2[r - c + nm1]
            if r == current_row:
                conflicts -= 3
            if conflicts < best_conflicts:
                best_conflicts = conflicts
                best_row = r
            elif conflicts == best_conflicts and random.random() < 0.5:
                best_row = r
    else:
        # eval current row first
        r = current_row
        conflicts = row_count[r] + diag1[r + c] + diag2[r - c + nm1] - 3
        best_conflicts = conflicts
        best_row = r
        # sample random rows
        randrange = random.randrange
        for _ in range(MOVE_SAMPLES):
            r = randrange(n)
            conflicts = row_count[r] + diag1[r + c] + diag2[r - c + nm1]
            if r == current_row:
                conflicts -= 3
            if conflicts < best_conflicts:
                best_conflicts = conflicts
                best_row = r
            elif conflicts == best_conflicts and random.random() < 0.5:
                best_row = r

    return best_row

def try_solve_board(board, max_steps):
    for _ in range(max_steps):
        c = find_conflicted_queen(board)
        if c == -1:
            return True
        new_row = find_best_row(board, c)
        board.move_queen(c, new_row)
    return find_conflicted_queen(board) == -1

def solve(n):
    # we make a loop with max_restarts to generate a new greedy init until we find a solution or exceed the max restarts
    max_steps = STEPS_PER_QUEEN * n
    for _ in range(MAX_RESTARTS):
        board = Board(n)
        greedy_init(board)
        if try_solve_board(board, max_steps):
            return board.queens[:]
    return None


def main():
    data = sys.stdin.read().strip()
    n = int(data)

    show_board = '--print-board' in sys.argv

    time_only = os.environ.get('FMI_TIME_ONLY') == '1'

    # edge cases
    if n == 1:
        t0 = time.perf_counter()
        solution = [0]
        elapsed_ms = (time.perf_counter() - t0) * 1000
        if time_only:
            print(f"# TIMES_MS: alg={elapsed_ms:.3f}")
            return
        print(f"# TIMES_MS: alg={elapsed_ms:.3f}")
        print(solution)
        if show_board:
            print_board(solution, n)
        return

    if n == 2 or n == 3:
        if time_only:
            print("# TIMES_MS: alg=0")
            return
        print(-1)
        return

    # n >= 4: solve
    t0 = time.perf_counter()
    solution = solve(n)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    if time_only:
        print(f"# TIMES_MS: alg={elapsed_ms:.3f}")
        return

    print(f"# TIMES_MS: alg={elapsed_ms:.3f}")
    if solution is None:
        print(-1)
        return

    print(solution)
    if show_board:
        print_board(solution, n)


if __name__ == '__main__':
    main()
