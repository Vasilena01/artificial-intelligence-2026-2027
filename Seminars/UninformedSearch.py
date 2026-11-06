# Notes
# UCS - unified cost search - its idea is to start from the root node and find the cheapest path to
# one of its destination nodes (G1, G2...)
# We save nodes in a PQ, ordered by their path cost, so each time we pop from the PQ the cheapest node
# and we push its children to the PQ, untill we reach a node at the top which is a destination node. Then this node is the
# cheapest path to a destination node.

# DLS - depth-limited search - its idea is to search the deepest node in a branch
# until a certain depth is reached. If the goal is not found, the search backtracks
# and continues with the next branch. DLS is useful for searching deep trees
# where the solution is known to be at a certain depth.

# IDS - iterative deepening search - its idea is to combine the benefits of
# depth-first search and breadth-first search.

# 

# Tasks
print("hello world")