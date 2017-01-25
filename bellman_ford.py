from functools import partial
from timed import timed_avg

class Graph(object):
   def __init__(self):
       self.edge = {}
       self.node = {}

   def add_edge(self, u, v, weight=1):
       self.node[u]={}
       self.node[v]={}
       if u not in self.edge:
           self.edge[u] = {}
       self.edge[u][v] = { "weight": weight }

   def nodes(self):
       return list(self.node.keys())

   def edges(self, data=True):
       for u, neigh in self.edge.items():
           for v, data in neigh.items():
               yield u,v,data

   def successors(self, node):
       if node in self.edge:
           return self.edge[node]
       else:
           return {}

INF = float('Inf')

# Utility functions
def change_state(graph, node, state=''):
    graph.node[node]['state'] = state

def is_state_equal_to(graph, node, state=''):
    return graph.node[node]['state'] == state

def state_setter_tester(graph, state):
    return (
        partial(change_state, graph, state=state),
        partial(is_state_equal_to, graph, state=state)
    )

@timed_avg(100)
def bellman_ford_classic(graph, root_node):
    """
    Bellman ford shortest path algorithm, checks if the graph has negative cycles
    Classic implementation, checks every edge at each iteration
    """

    distances = {}
    paths = {}
    has_cycle = False

    # Initialize every node to infinity except the root node
    for node in graph.nodes():
        distances[node] = 0 if node == root_node else INF
        paths[node] = []

    # Repeat n-1 times
    for _ in range(1, len(graph.nodes())):
        # Iterate over every edge
        for u, v, data in graph.edges(data=True):
            # If it can be relaxed, relax it
            if distances[v] > distances[u] + data["weight"]:
                distances[v] = distances[u] + data["weight"]
                paths[v] = paths[u] + [v]

    # If a node can still be relaxed, it means that there is a negative cycle
    for u, v, data in graph.edges(data=True):
        if distances[v] > distances[u] + data["weight"]:
            has_cycle = True

    return has_cycle, distances, paths


# Main algorithm
@timed_avg(100)
def bellman_ford_alternate(graph, root_node):
    """
    Bellman ford shortest path algorithm, checks if the graph has negative cycles
    Alternate implementation, only checks successors of nodes that have been previously relaxed
    """

    distances = {}
    #paths = {}
    has_cycle = False

    # Define open close and free state setters and testers
    stg = partial(state_setter_tester, graph)
    open, is_open = stg('open')
    close, is_closed = stg('closed')

    # Put all nodes to infinity except the root_node
    for node in graph.nodes():
        #paths[node] = []
        if node != root_node:
            distances[node] = INF
            close(node)

    # Put the root node distance to 0 and open it
    # Because it's the only "relaxed node" for the first iteration
    distances[root_node] = 0
    open(root_node)

    # Main algorithm's loop
    for _ in range(len(graph.nodes())):
        # Go over the open nodes -> nodes that have been relaxed last iteration
        for node in filter(is_open, graph.nodes()):
            # For each successor of node
            for successor in graph.successors(node):
                # Relax it if it can be relaxed
                edge_weight = graph.edge[node][successor]['weight']
                if distances[successor] > distances[node] + edge_weight: # Check
                    distances[successor] = distances[node] + edge_weight # Relaxation
                    #paths[successor] = paths[node] + [successor]
                    open(successor) # It has been relaxed, open  the node so its successors can be checked

            # The node's successors have been fully inspected so we can close it
            close(node)

    # If one node is still open after n passes
    # It means that a node has been relaxed at the last iteration
    # So the length of the path associated with this node is n
    # Which is possible only if there is a negative cycle in the graph
    for node in graph.nodes():
        if is_open(node):
            has_cycle = True

    return has_cycle, distances, None#, paths
