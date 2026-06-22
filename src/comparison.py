"""STEP 5 — 3자 비교 + Jaccard"""
import pandas as pd
import numpy as np


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def compare_methods(bridges: pd.DataFrame,
                    bc_df: pd.DataFrame,
                    ci_df: pd.DataFrame,
                    k: int = 10) -> dict:
    top_bridge = set(bridges.head(k)["species"])
    top_bc     = set(bc_df.head(k)["species"])
    top_ci     = set(ci_df.head(k)["species"])

    methods = {"SCC Bridge": top_bridge, "BC": top_bc, "CI": top_ci}
    names   = list(methods.keys())
    matrix  = pd.DataFrame(index=names, columns=names, dtype=float)
    for a in names:
        for b in names:
            matrix.loc[a, b] = jaccard(methods[a], methods[b])

    print("Jaccard Similarity Matrix:")
    print(matrix.to_string())

    consensus = top_bridge & top_bc & top_ci
    print(f"\n합의 핵심종 (3-way consensus, k={k}): {consensus}")

    # Heatmap data: union of all top-k, ranked per method
    all_sp = top_bridge | top_bc | top_ci
    bridge_rank = dict(zip(bridges["species"], bridges["rank"]))
    bc_rank     = dict(zip(bc_df["species"],   bc_df["rank"]))
    ci_rank     = dict(zip(ci_df["species"],   ci_df["rank"]))

    rows = []
    for sp in sorted(all_sp):
        rows.append({
            "species": sp,
            "SCC Bridge": bridge_rank.get(sp, np.nan),
            "BC": bc_rank.get(sp, np.nan),
            "CI": ci_rank.get(sp, np.nan),
        })
    heatmap_df = pd.DataFrame(rows).set_index("species")

    return {"jaccard": matrix, "consensus": consensus, "heatmap": heatmap_df,
            "top_bridge": top_bridge, "top_bc": top_bc, "top_ci": top_ci}


def compare_wtecm_rankings(algo_rankings: dict[str, list[int]],
                           ref_order: list[int],
                           species_names: list[str],
                           k: int = 10) -> dict:
    """Compare WTECM algorithm rankings against each other and Reference."""
    methods = {
        "Reference": set(ref_order[:k]),
        **{name: set(ranking[:k]) for name, ranking in algo_rankings.items()},
    }
    names = list(methods.keys())
    matrix = pd.DataFrame(index=names, columns=names, dtype=float)
    for a in names:
        for b in names:
            matrix.loc[a, b] = jaccard(methods[a], methods[b])

    rank_maps = {
        "Reference": {node: rank + 1 for rank, node in enumerate(ref_order)},
        **{
            name: {node: rank + 1 for rank, node in enumerate(ranking)}
            for name, ranking in algo_rankings.items()
        },
    }
    all_nodes = set().union(*methods.values())
    rows = []
    for node in sorted(all_nodes):
        row = {"species": species_names[node]}
        for name in names:
            row[name] = rank_maps[name].get(node, np.nan)
        rows.append(row)

    heatmap_df = pd.DataFrame(rows).set_index("species")
    consensus = set.intersection(*methods.values()) if methods else set()
    return {
        "jaccard": matrix,
        "consensus": consensus,
        "heatmap": heatmap_df,
    }


if __name__ == "__main__":
    import sys; sys.path.insert(0, ".")
    from src.graph import build_graph
    from src.scc import run_scc_analysis
    from src.centrality import compute_bc
    from src.ci import compute_ci
    G = build_graph("data/parana_edgelist.csv")
    _, _, bridges = run_scc_analysis(G)
    bc_df = compute_bc(G)
    ci_df = compute_ci(G)
    compare_methods(bridges, bc_df, ci_df)
