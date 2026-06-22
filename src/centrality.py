"""STEP 3 — Betweenness Centrality"""
import networkx as nx
import pandas as pd


def compute_bc(G: nx.DiGraph) -> pd.DataFrame:
    bc = nx.betweenness_centrality(G, normalized=True, weight=None)
    records = [
        {
            "species": species,
            "bc_score": score,
            "_node_id": G.nodes[species].get("node_id", species),
        }
        for species, score in bc.items()
    ]
    df = (pd.DataFrame(records)
          .sort_values(["bc_score", "_node_id", "species"], ascending=[False, True, True])
          .reset_index(drop=True))
    df["rank"] = df.index + 1
    df = df.drop(columns=["_node_id"])
    return df


def top_bc(G: nx.DiGraph, k: int = 10) -> pd.DataFrame:
    df = compute_bc(G)
    print("Betweenness Centrality — Top 10:")
    print(df.head(k).to_string(index=False))
    return df


if __name__ == "__main__":
    import sys; sys.path.insert(0, ".")
    from src.graph import build_graph
    G = build_graph("data/parana_edgelist.csv")
    top_bc(G)
