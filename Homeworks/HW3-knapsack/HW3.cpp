#include <iostream>
#include <vector>
#include <random>
#include <chrono>
#include <algorithm>
#include <numeric>
#include <cstdlib>
#include <cstring>

using namespace std;

static mt19937_64 rng((unsigned)chrono::high_resolution_clock::now().time_since_epoch().count());

// how many chromosomes in the population
const int POPULATION_SIZE = 200;
// chance each bit to flip during mutation
const double MUTATION_RATE = 0.02;
// number of top chromosomes to keep for the next generation
const int ELITE_COUNT = 4;
const double MAX_TIME = 1.5;
// number of results to print
const int RESULTS_NEEDED = 10;

// Whole flow
// 1. Initialize → random population of POPULATION_SIZE (200) chromosomes each with N genes, evaluate and repair each
// 2. Sort by value, save best chromosome value into array
// 3. Build next generation:
//    - Elites: top ELITE_COUNT (4) chromosomes from current gen are copied unchanged to the new generation and they for sure will be in the final new generation
//    - Rest (POPULATION_SIZE - ELITE_COUNT): repeat (196) times with the rest of the population + the top chromosomes as well, because they are still in the population → tournament-pick 2 random parents → crossover → mutate → evaluate → repair → add child
// 4. Replace old population with new one
// 5. Repeat 2–4 until time runs out
// 6. Pick 10 evenly-spaced values from the saved array, print them + final

struct Item {
    // each item has a weight and value
    long long w;
    long long v;
};


struct Chromosome {
    vector<uint8_t> genes;
    long long chrom_weight = 0;
    long long chrom_value = 0;
};


int N;
long long M;
vector<Item> items;


// a func which calculates the weight and value of a chromosome
void evaluate(Chromosome& chrom) {
    long long w = 0;
    long long v = 0;
    for (int i = 0; i < N; i++) {
        if (chrom.genes[i]) {
            w += items[i].w;
            v += items[i].v;
        }
    }
    chrom.chrom_weight = w;
    chrom.chrom_value = v;
}


// a func which removes bad items from a chromosome until it reaches a weight <= M
void repair(Chromosome& chrom) {
    if (chrom.chrom_weight <= M) return;

    // we sort item indices by value/weight worst first
    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        return (double)items[a].v / items[a].w < (double)items[b].v / items[b].w;
    });
    // remove worst ones until the weight is <= M
    for (int i : order) {
        if (chrom.genes[i] == 1) {
            chrom.genes[i] = 0;
            chrom.chrom_weight -= items[i].w;
            chrom.chrom_value -= items[i].v;
            if (chrom.chrom_weight <= M) break;
        }
    }
}


// we initialize the population where for every chromosome, for every gene in it we randomly pick 0 or 1 and then we evaluate (calculate its weight and value)
// and repair (remove items until weight <= M)
vector<Chromosome> initialize() {
    vector<Chromosome> population(POPULATION_SIZE);
    for (int i = 0; i < POPULATION_SIZE; i++) {
        population[i].genes.resize(N);
        for (int j = 0; j < N; j++) {
            population[i].genes[j] = rng() % 2;
        }
        evaluate(population[i]);
        repair(population[i]);
    }
    return population;
}


// pick 2 random chromosomes, return the one with higher value
const Chromosome& tournament_selection(const vector<Chromosome>& population) {
    int a = rng() % POPULATION_SIZE;
    int b = rng() % POPULATION_SIZE;
    if (population[a].chrom_value > population[b].chrom_value) return population[a];
    return population[b];
}


// we make a one-point crossover: first half from parent1, second half from parent2
Chromosome crossover(const Chromosome& parent1, const Chromosome& parent2) {
    Chromosome child;
    child.genes.resize(N);
    int cut = rng() % N;
    for (int i = 0; i < N; i++) {
        child.genes[i] = (i < cut) ? parent1.genes[i] : parent2.genes[i];
    }
    return child;
}


// flip each bit with MUTATION_RATE probability
void mutate(Chromosome& chrom) {
    uniform_real_distribution<double> dist(0.0, 1.0);
    for (int i = 0; i < N; i++) {
        if (dist(rng) < MUTATION_RATE) {
            chrom.genes[i] = 1 - chrom.genes[i];
        }
    }
}


// main GA algorithm - evolves population until time runs out, returns best value per generation
vector<long long> run_ga() {
    vector<Chromosome> population = initialize();
    vector<long long> best_per_gen;
    auto t_start = chrono::high_resolution_clock::now();

    while (true) {
        auto now = chrono::high_resolution_clock::now();
        if (chrono::duration<double>(now - t_start).count() > MAX_TIME) break;

        // sort population by value
        sort(population.begin(), population.end(), [](const Chromosome& a, const Chromosome& b) {
            return a.chrom_value > b.chrom_value;
        });
        // record the best value of the chromosome in the current generation
        best_per_gen.push_back(population[0].chrom_value);

        // build next generation
        vector<Chromosome> new_population;
        new_population.reserve(POPULATION_SIZE);

        // elitism: copy top ELITE_COUNT chromosomes so that they are used another time in the next gen
        for (int i = 0; i < ELITE_COUNT; i++) {
            new_population.push_back(population[i]);
        }

        // Create children until we have a full new population
        while ((int)new_population.size() < POPULATION_SIZE) {
            const Chromosome& parent1 = tournament_selection(population);
            const Chromosome& parent2 = tournament_selection(population);
            Chromosome child = crossover(parent1, parent2);
            mutate(child);
            evaluate(child);
            repair(child);
            new_population.push_back(std::move(child));
        }

        population = std::move(new_population);
    }

    return best_per_gen;
}


// pick RESULTS_NEEDED evenly spaced values from list to print
vector<long long> sample_results(const vector<long long>& best_per_gen) {
    int size = (int)best_per_gen.size();
    vector<long long> result;
    if (size >= RESULTS_NEEDED) {
        for (int i = 0; i < RESULTS_NEEDED; i++) {
            int idx = (int)round((double)i * (size - 1) / (RESULTS_NEEDED - 1));
            result.push_back(best_per_gen[idx]);
        }
        return result;
    }
    // if not enough generations, pad with the last value
    result = best_per_gen;
    while ((int)result.size() < RESULTS_NEEDED) {
        result.push_back(best_per_gen.back());
    }
    return result;
}


void read_input() {
    cin >> M >> N;
    items.resize(N);
    for (int i = 0; i < N; i++) {
        cin >> items[i].w >> items[i].v;
    }
}


int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    auto t_start = chrono::high_resolution_clock::now();
    read_input();

    const char* env = getenv("FMI_TIME_ONLY");
    bool time_only = (env && strcmp(env, "1") == 0);

    vector<long long> best_per_gen = run_ga();
    vector<long long> final_results = sample_results(best_per_gen);

    auto t_end = chrono::high_resolution_clock::now();
    double elapsed_ms = chrono::duration<double, milli>(t_end - t_start).count();

    cout.setf(std::ios::fixed);
    cout.precision(2);
    cout << "# TIMES_MS: alg=" << elapsed_ms << "\n";

    if (!time_only) {
        for (long long v : final_results) {
            cout << v << "\n";
        }
        cout << "\n" << final_results.back() << "\n";
    }

    return 0;
}
