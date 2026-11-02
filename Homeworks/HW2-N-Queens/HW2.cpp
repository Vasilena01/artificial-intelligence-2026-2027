#include <iostream>
#include <vector>
#include <random>
#include <chrono>
#include <cstdlib>
#include <string>
using namespace std;

static mt19937_64 rng((unsigned long long)chrono::high_resolution_clock::now().time_since_epoch().count());

const int BIG_N = 1000;             // max value of N for checking all rows
const int INIT_SAMPLES = 50;        // rows sampled per column for large N
const int MOVE_SAMPLES = 50;        // rows sampled per move for large N
const int STEPS_PER_QUEEN = 8;      // step budget = STEPS_PER_QUEEN * N
const int MAX_RANDOM_PROBES = 100;  // tries to find conflicted queen via random sampling
const int MAX_RESTARTS = 20;        // restart with fresh init if stuck in local min

struct Board {
    int n;
    vector<int> queens;      // queens[col] = row
    vector<int> row_count;   // queens per row
    vector<int> diag1;       // '/' diagonals: index = row + col
    vector<int> diag2;       // '\' diagonals: index = row - col + n - 1

    void init(int n_) {
        n = n_;
        queens.assign(n, 0);
        row_count.assign(n, 0);
        diag1.assign(2 * n - 1, 0);
        diag2.assign(2 * n - 1, 0);
    }

    inline void place(int r, int c) {
        queens[c] = r;
        row_count[r]++;
        diag1[r + c]++;
        diag2[r - c + n - 1]++;
    }

    inline void remove(int r, int c) {
        row_count[r]--;
        diag1[r + c]--;
        diag2[r - c + n - 1]--;
    }

    inline int conflicts_at(int r, int c) {
        return row_count[r] + diag1[r + c] + diag2[r - c + n - 1];
    }

    inline int conflicts_of_queen(int c) {
        int r = queens[c];
        return conflicts_at(r, c) - 3;
    }

    inline void move_queen(int c, int new_r) {
        int old_r = queens[c];
        if (old_r == new_r) return;
        remove(old_r, c);
        place(new_r, c);
    }
};

void print_board(const vector<int>& queens, int n) {
    for (int r = 0; r < n; r++) {
        for (int c = 0; c < n; c++) {
            cout << (queens[c] == r ? '*' : '_');
            if (c + 1 < n) cout << ' ';
        }
        cout << '\n';
    }
}

void greedy_init(Board& board) {
    // place queens column by column, each placed in the row with the fewest conflicts
    int n = board.n;

    // randomized column order
    vector<int> cols(n);
    for (int i = 0; i < n; i++) cols[i] = i;
    for (int i = n - 1; i > 0; i--) {
        int j = (int)(rng() % (i + 1));
        swap(cols[i], cols[j]);
    }

    for (int c : cols) {
        int best_row = 0;
        int best_conflicts = n + 1;

        if (n <= BIG_N) {
            // here we check every row
            for (int r = 0; r < n; r++) {
                int conflicts = board.conflicts_at(r, c);
                if (conflicts < best_conflicts) {
                    best_conflicts = conflicts;
                    best_row = r;
                } else if (conflicts == best_conflicts && (rng() & 1)) {
                    best_row = r;
                }
            }
        } else {
            // here we sample random rows + diagonal fallback
            vector<int> candidates;
            candidates.reserve(INIT_SAMPLES + 1);
            for (int i = 0; i < INIT_SAMPLES; i++) candidates.push_back((int)(rng() % n));
            candidates.push_back(c % n);  // deterministic seed row
            for (int r : candidates) {
                int conflicts = board.conflicts_at(r, c);
                if (conflicts < best_conflicts) {
                    best_conflicts = conflicts;
                    best_row = r;
                } else if (conflicts == best_conflicts && (rng() & 1)) {
                    best_row = r;
                }
            }
        }

        board.place(best_row, c);
    }
}

int find_conflicted_queen(Board& board) {
    // picks a rndm col, checks if it is conflicted and repeats up to max_random_probes
    int n = board.n;
    int nm1 = n - 1;

    for (int i = 0; i < MAX_RANDOM_PROBES; i++) {
        int c = (int)(rng() % n);
        int r = board.queens[c];
        if (board.row_count[r] + board.diag1[r + c] + board.diag2[r - c + nm1] - 3 > 0) {
            return c;
        }
    }
    for (int c = 0; c < n; c++) {
        int r = board.queens[c];
        if (board.row_count[r] + board.diag1[r + c] + board.diag2[r - c + nm1] - 3 > 0) {
            return c;
        }
    }
    return -1;
}

int find_best_row(Board& board, int c) {
    // return the row with the fewest conflicts for queen in column c
    int n = board.n;
    int nm1 = n - 1;
    int current_row = board.queens[c];

    int best_row = current_row;
    int best_conflicts = n + 1;

    if (n <= BIG_N) {
        for (int r = 0; r < n; r++) {
            int conflicts = board.row_count[r] + board.diag1[r + c] + board.diag2[r - c + nm1];
            if (r == current_row) conflicts -= 3;
            if (conflicts < best_conflicts) {
                best_conflicts = conflicts;
                best_row = r;
            } else if (conflicts == best_conflicts && (rng() & 1)) {
                best_row = r;
            }
        }
    } else {
        // eval current row first
        int r = current_row;
        int conflicts = board.row_count[r] + board.diag1[r + c] + board.diag2[r - c + nm1] - 3;
        best_conflicts = conflicts;
        best_row = r;
        // sample random rows
        for (int i = 0; i < MOVE_SAMPLES; i++) {
            r = (int)(rng() % n);
            conflicts = board.row_count[r] + board.diag1[r + c] + board.diag2[r - c + nm1];
            if (r == current_row) conflicts -= 3;
            if (conflicts < best_conflicts) {
                best_conflicts = conflicts;
                best_row = r;
            } else if (conflicts == best_conflicts && (rng() & 1)) {
                best_row = r;
            }
        }
    }

    return best_row;
}

bool try_solve_board(Board& board, int max_steps) {
    for (int i = 0; i < max_steps; i++) {
        int c = find_conflicted_queen(board);
        if (c == -1) return true;
        int new_row = find_best_row(board, c);
        board.move_queen(c, new_row);
    }
    return find_conflicted_queen(board) == -1;
}

bool solve(int n, vector<int>& out) {
    // we make a loop with max_restarts to generate a new greedy init until we find a solution or exceed the max restarts
    int max_steps = STEPS_PER_QUEEN * n;
    for (int i = 0; i < MAX_RESTARTS; i++) {
        Board board;
        board.init(n);
        greedy_init(board);
        if (try_solve_board(board, max_steps)) {
            out = board.queens;
            return true;
        }
    }
    return false;
}

int main(int argc, char** argv) {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    bool show_board = false;
    for (int i = 1; i < argc; i++) {
        if (string(argv[i]) == "--print-board") show_board = true;
    }

    const char* env = getenv("FMI_TIME_ONLY");
    bool time_only = env != nullptr && string(env) == "1";

    // edge cases
    if (n == 1) {
        auto t0 = chrono::high_resolution_clock::now();
        vector<int> solution = {0};
        auto t1 = chrono::high_resolution_clock::now();
        double elapsed_ms = chrono::duration<double, milli>(t1 - t0).count();
        if (time_only) {
            cout << "# TIMES_MS: alg=" << elapsed_ms << '\n';
            return 0;
        }
        cout << "# TIMES_MS: alg=" << elapsed_ms << '\n';
        cout << "[0]\n";
        if (show_board) print_board(solution, n);
        return 0;
    }

    if (n == 2 || n == 3) {
        if (time_only) {
            cout << "# TIMES_MS: alg=0\n";
            return 0;
        }
        cout << -1 << '\n';
        return 0;
    }

    // n >= 4: solve
    auto t0 = chrono::high_resolution_clock::now();
    vector<int> solution;
    bool ok = solve(n, solution);
    auto t1 = chrono::high_resolution_clock::now();
    double elapsed_ms = chrono::duration<double, milli>(t1 - t0).count();

    if (time_only) {
        cout << "# TIMES_MS: alg=" << elapsed_ms << '\n';
        return 0;
    }

    cout << "# TIMES_MS: alg=" << elapsed_ms << '\n';
    if (!ok) {
        cout << -1 << '\n';
        return 0;
    }

    cout << '[';
    for (int c = 0; c < n; c++) {
        if (c) cout << ", ";
        cout << solution[c];
    }
    cout << "]\n";

    if (show_board) print_board(solution, n);

    return 0;
}
