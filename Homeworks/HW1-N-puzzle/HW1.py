import math
import os
import time


def is_solvable(board_state, size):
    arr = [x for x in board_state if x != 0]
    inversions = 0
    for a in range(len(arr)):
        for b in range(a + 1, len(arr)):
            if arr[a] > arr[b]:
                inversions += 1

    #  Odd board: inversions must be even
    if size % 2 == 1:
        return inversions % 2 == 0

    # Even board: inversions + blank row must be odd
    empty_row = board_state.index(0) // size
    return (inversions + empty_row) % 2 == 1


def manhattan_distance(board_state, target_positions, size):
    total = 0
    for pos, val in enumerate(board_state):
        if val == 0:
            continue
        row, col = pos // size, pos % size
        target_row, target_col = target_positions[val]
        total += abs(row - target_row) + abs(col - target_col)
    return total


def possible_moves(empty_pos, size):
    options = []
    row, col = empty_pos // size, empty_pos % size
    if row < size - 1:
        options.append(('up', empty_pos + size))
    if row > 0:
        options.append(('down', empty_pos - size))
    if col < size - 1:
        options.append(('left', empty_pos + 1))
    if col > 0:
        options.append(('right', empty_pos - 1))
    return options


def swap(board_state, pos_a, pos_b):
    arr = list(board_state)
    arr[pos_a], arr[pos_b] = arr[pos_b], arr[pos_a]
    return tuple(arr)


REVERSE = {'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left'}


def ida_star(start_state, target_state, size, target_positions):
    moves_taken = []

    def search(board_state, cost_so_far, last_move, threshold, empty_pos, seen):
        estimate = cost_so_far + manhattan_distance(board_state, target_positions, size)
        if estimate > threshold:
            return estimate
        if board_state == target_state:
            return True

        next_threshold = math.inf
        seen.add(board_state)

        for direction, next_empty in possible_moves(empty_pos, size):
            if last_move is not None and direction == REVERSE[last_move]:
                continue

            next_state = swap(board_state, empty_pos, next_empty)
            if next_state in seen:
                continue

            moves_taken.append(direction)
            outcome = search(next_state, cost_so_far + 1, direction, threshold, next_empty, seen)
            if outcome is True:
                return True
            if outcome < next_threshold:
                next_threshold = outcome
            moves_taken.pop()
            seen.discard(next_state)

        return next_threshold

    threshold = manhattan_distance(start_state, target_positions, size)
    while True:
        seen = set()
        outcome = search(start_state, 0, None, threshold, start_state.index(0), seen)
        if outcome is True:
            return moves_taken
        if outcome == math.inf:
            return None
        threshold = outcome


def run():
    n = int(input())
    i = int(input())
    size = int(math.sqrt(n + 1))

    # We construct the board
    board_state = []
    for _ in range(size):
        board_state.extend(map(int, input().split()))
    board_state = tuple(board_state)

    # If the input board is not solvable, we print -1 and return
    if not is_solvable(board_state, size):
        print(-1)
        return

    # We construct the goal board: we place the tiles 1..n in order and we insert the blank at index i
    target_state = list(range(1, n + 1))
    if i == -1:
        i = n
    target_state.insert(i, 0)
    target_state = tuple(target_state)

    target_positions = {val: (idx // size, idx % size) for idx, val in enumerate(target_state)}

    time_only = os.environ.get('FMI_TIME_ONLY', '0') == '1'
    if time_only:
        start_time = time.perf_counter()

    moves_taken = ida_star(board_state, target_state, size, target_positions)

    if time_only:
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        print(f"# TIMES_MS: alg={elapsed_ms}")
        return

    if moves_taken is None:
        print(-1)
    else:
        print(len(moves_taken))
        for direction in moves_taken:
            print(direction)


if __name__ == "__main__":
    run()
