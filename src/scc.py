"""STEP 2 — SCC 분석: Kosaraju + Tarjan + 브릿지 노드"""
import networkx as nx
from collections import defaultdict
import pandas as pd


# ── Kosaraju ─────────────────────────────────────────────────────
def kosaraju(G: nx.DiGraph) -> list[frozenset]:
    nodes = list(G.nodes())
    visited = set()
    finish_order = []

    def dfs1(u):
        stack = [(u, iter(G.successors(u)))]
        visited.add(u)
        while stack:
            node, children = stack[-1]
            try:
                v = next(children)
                if v not in visited:
                    visited.add(v)
                    stack.append((v, iter(G.successors(v))))
            except StopIteration:
                finish_order.append(node)
                stack.pop()

    for n in nodes:
        if n not in visited:
            dfs1(n)

    Gr = G.reverse()
    visited2 = set()
    sccs = []

    def dfs2(u):
        comp = []
        stack = [u]
        visited2.add(u)
        while stack:
            node = stack.pop()
            comp.append(node)
            for v in Gr.successors(node):
                if v not in visited2:
                    visited2.add(v)
                    stack.append(v)
        return comp

    for n in reversed(finish_order):
        if n not in visited2:
            sccs.append(frozenset(dfs2(n)))

    return sccs


# ── Tarjan ────────────────────────────────────────────────────────
def tarjan(G: nx.DiGraph) -> list[frozenset]:
    index_counter = [0]
    stack = []
    lowlink = {}
    index = {}
    on_stack = {}
    sccs = []

    def strongconnect(v):
        index[v] = lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack[v] = True

        dfs_stack = [(v, iter(G.successors(v)))]
        while dfs_stack:
            node, children = dfs_stack[-1]
            try:
                w = next(children)
                if w not in index:
                    dfs_stack.append((w, iter(G.successors(w))))
                    index[w] = lowlink[w] = index_counter[0]
                    index_counter[0] += 1
                    stack.append(w)
                    on_stack[w] = True
                elif on_stack.get(w):
                    lowlink[node] = min(lowlink[node], index[w])
            except StopIteration:
                dfs_stack.pop()
                if dfs_stack:
                    parent = dfs_stack[-1][0]
                    lowlink[parent] = min(lowlink[parent], lowlink[node])
                if lowlink[node] == index[node]:
                    comp = []
                    while True:
                        w = stack.pop()
                        on_stack[w] = False
                        comp.append(w)
                        if w == node:
                            break
                    sccs.append(frozenset(comp))

    for v in G.nodes():
        if v not in index:
            strongconnect(v)

    return sccs


# ── 브릿지 노드 (SCC condensation 기반) ──────────────────────────
def bridge_nodes(G: nx.DiGraph, sccs: list[frozenset]) -> pd.DataFrame:
    node_to_scc = {}
    for i, scc in enumerate(sccs):
        for n in scc:
            node_to_scc[n] = i

    cond = nx.condensation(G)
    scc_connections = defaultdict(set)

    for u, v in cond.edges():
        scc_connections[u].add(v)
        scc_connections[v].add(u)

    # Nodes that belong to SCCs with external edges
    records = []
    for scc_id, scc in enumerate(sccs):
        n_connected = len(scc_connections[scc_id])
        if n_connected > 0:
            for node in scc:
                out_cross = sum(1 for _, tgt in G.out_edges(node) if node_to_scc[tgt] != scc_id)
                in_cross  = sum(1 for src, _ in G.in_edges(node)  if node_to_scc[src] != scc_id)
                cross = out_cross + in_cross
                if cross > 0:
                    records.append({"species": node, "scc_id": scc_id,
                                    "cross_edges": cross, "scc_connections": n_connected})

    df = pd.DataFrame(records).sort_values("cross_edges", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1
    return df


def run_scc_analysis(G: nx.DiGraph):
    k_sccs = kosaraju(G)
    t_sccs = tarjan(G)

    k_set = set(k_sccs)
    t_set = set(t_sccs)
    match = k_set == t_set
    print(f"Kosaraju SCCs : {len(k_sccs)}")
    print(f"Tarjan SCCs   : {len(t_sccs)}")
    print(f"Results match : {match}")
    if not match:
        print("  MISMATCH!")

    bridges = bridge_nodes(G, k_sccs)
    print(f"\nBridge nodes (top 10):")
    print(bridges.head(10).to_string(index=False))

    return k_sccs, t_sccs, bridges


if __name__ == "__main__":
    import sys; sys.path.insert(0, ".")
    from src.graph import build_graph
    G = build_graph("data/parana_edgelist.csv")
    run_scc_analysis(G)
