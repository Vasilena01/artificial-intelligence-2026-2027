#!/usr/bin/env python3
import os
import sys
import random
import time

# how many chromosomes in the population
POPULATION_SIZE = 200
# chance each bit to flip during mutation
MUTATION_RATE = 0.02
# number of top chromosomes to keep for the next generation
ELITE_COUNT = 4
MAX_TIME = 1.5
# number of results to print
RESULTS_NEEDED = 10

# Whole flow
# 1. Initialize → random population of POPULATION_SIZE (200) chromosomes each with N genes, evaluate and repair each
# 2. Sort by value, save best chromosome value into array
# 3. Build next generation:
#    - Elites: top ELITE_COUNT (4) chromosomes from current gen are copied unchanged to the new generation and they for sure will be in the final new generation
#    - Rest (POPULATION_SIZE - ELITE_COUNT): repeat (196) times with the rest of the population + the top chromosomes as well, because they are still in the population → tournament-pick 2 random parents → crossover → mutate → evaluate → repair → add child
# 4. Replace old population with new one
# 5. Repeat 2–4 until time runs out
# 6. Pick 10 evenly-spaced values from the saved array, print them + final

class Item:
    def __init__(self, w, v):
        # each item has a weight and value
        self.w = w
        self.v = v


class Chromosome:
    def __init__(self, genes):
        self.genes = genes
        self.chrom_weight = 0
        self.chrom_value = 0


# a func which calculates the weight and value of a chromosome
def evaluate(chrom, items):
    w = 0
    v = 0
    for i, bit in enumerate(chrom.genes):
        if bit:
            w += items[i].w
            v += items[i].v
    chrom.chrom_weight = w
    chrom.chrom_value = v


# a func which removes bad items from a chromosome until it reaches a weight <= M
def repair(chrom, items, M):
    if chrom.chrom_weight <= M:
        return
    
    # we sort item indices by value/weight worst first
    order = sorted(range(len(items)), key=lambda i: items[i].v / items[i].w)
    # remove worst ones until the weight is <= M
    for i in order:
        if chrom.genes[i] == 1:
            chrom.genes[i] = 0
            chrom.chrom_weight -= items[i].w
            chrom.chrom_value -= items[i].v
            if chrom.chrom_weight <= M:
                break


# we initialize the population where for every chromosome, for every gene in it we randomly pick 0 or 1 and then we eveluate (calculate its weight and value) 
# and repair (remove items until weight <= M)
def initialize(N, items, M):
    population = []
    for _ in range(POPULATION_SIZE):
        genes = [random.randint(0, 1) for _ in range(N)]
        chrom = Chromosome(genes)
        evaluate(chrom, items)
        repair(chrom, items, M)
        population.append(chrom)
    return population


# pick 2 random chromosomes, return the one with higher value
def tournament_selection(population):
    a = random.randrange(POPULATION_SIZE)
    b = random.randrange(POPULATION_SIZE)
    if population[a].chrom_value > population[b].chrom_value:
        return population[a]
    return population[b]


# we make a one-point crossover: first half from parent1, second half from parent2
def crossover(parent1, parent2, N):
    cut = random.randrange(N)
    child_genes = parent1.genes[:cut] + parent2.genes[cut:]
    return Chromosome(child_genes)


# flip each bit with MUTATION_RATE probability
def mutate(chrom):
    for i in range(len(chrom.genes)):
        if random.random() < MUTATION_RATE:
            chrom.genes[i] = 1 - chrom.genes[i]


# main GA algorithm - evolves population until time runs out, returns best value per generation
def run_ga(N, items, M):
    population = initialize(N, items, M)
    best_per_gen = []
    t_start = time.perf_counter()

    while True:
        if time.perf_counter() - t_start > MAX_TIME:
            break

        # sort population by value
        population.sort(key=lambda c: c.chrom_value, reverse=True)
        # record the best value of the chromosome in the current generation
        best_per_gen.append(population[0].chrom_value)

        # build next generation
        new_population = []

        # elitism: copy top ELITE_COUNT chromosomes so that they are used another time in the next gen
        for i in range(ELITE_COUNT):
            new_population.append(population[i])

        # Create children until we have a full new population
        while len(new_population) < POPULATION_SIZE:
            parent1 = tournament_selection(population)
            parent2 = tournament_selection(population)
            child = crossover(parent1, parent2, N)
            mutate(child)
            evaluate(child, items)
            repair(child, items, M)
            new_population.append(child)

        population = new_population

    return best_per_gen


# pick RESULTS_NEEDED evenly spaced values from list to print
def sample_results(best_per_gen):
    size = len(best_per_gen)
    if size >= RESULTS_NEEDED:
        sampled = []
        for i in range(RESULTS_NEEDED):
            idx = round(i * (size - 1) / (RESULTS_NEEDED - 1))
            sampled.append(best_per_gen[idx])
        return sampled
    # if not enough generations, pad with the last value
    result = list(best_per_gen)
    while len(result) < RESULTS_NEEDED:
        result.append(best_per_gen[-1])
    return result


def read_input():
    tokens = iter(sys.stdin.read().split())
    M = int(next(tokens))
    N = int(next(tokens))
    items = []
    for _ in range(N):
        w = int(next(tokens))
        v = int(next(tokens))
        items.append(Item(w, v))
    return M, N, items


if __name__ == "__main__":
    t_start = time.perf_counter()
    M, N, items = read_input()

    time_only = os.environ.get("FMI_TIME_ONLY") == "1"

    best_per_gen = run_ga(N, items, M)
    final_results = sample_results(best_per_gen)

    elapsed_ms = (time.perf_counter() - t_start) * 1000
    print(f"# TIMES_MS: alg={elapsed_ms:.2f}")

    if not time_only:
        for v in final_results:
            print(v)
        print()
        print(final_results[-1])
