"""STEP 4 — Collective Influence (Morone & Makse 2015)"""
import networkx as nx
import pandas as pd
from collections import deque


def ball(G: nx.DiGraph, node: str, l: int) -> set:
    """Nodes at exactly l hops from node (undirected BFS)."""
    G_undir = G.to_undirected()
    visited = {node: 0}
    queue = deque([node])
    while queue:
        cur = queue.popleft()
        if visited[cur] < l:
            for nb in G_undir.neighbors(cur):
                if nb not in visited:
                    visited[nb] = visited[cur] + 1
                    queue.append(nb)
    return {n for n, d in visited.items() if d == l}


def compute_ci(G: nx.DiGraph, l: int = 2) -> pd.DataFrame:
    G_undir = G.to_undirected()
    degree = dict(G_undir.degree())
    records = []
    for node in G.nodes():
        ki = degree[node]
        ball_l = ball(G, node, l)
        ci = (ki - 1) * sum(degree[j] - 1 for j in ball_l)
        records.append({
            "species": node,
            "ci_score": ci,
            "_node_id": G.nodes[node].get("node_id", node),
        })
    df = (pd.DataFrame(records)
          .sort_values(["ci_score", "_node_id", "species"], ascending=[False, True, True])
          .reset_index(drop=True))
    df["rank"] = df.index + 1
    df = df.drop(columns=["_node_id"])
    return df


def top_ci(G: nx.DiGraph, k: int = 10, l: int = 2) -> pd.DataFrame:
    df = compute_ci(G, l=l)
    print(f"Collective Influence (l={l}) — Top 10:")
    print(df.head(k).to_string(index=False))
    return df


if __name__ == "__main__":
    import sys; sys.path.insert(0, ".")
    from src.graph import build_graph
    G = build_graph("data/parana_edgelist.csv")
    top_ci(G)
