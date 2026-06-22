"""WTECM preprocessing, graph construction, rankings, and web export data."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import networkx as nx
import numpy as np
import pandas as pd

EPS = 1e-9

PREDATOR_NAMES = [
    "Acestrorhyncus lacustris",
    "Astyanax altiparanae",
    "Auchenipterus nuchalis",
    "Benthos",
    "Brycon orbignyanus",
    "Cyphocharax modestus",
    "Hemisorubin platyrhynchos",
    "Hoplias malabaricus",
    "Hoplosternum littorale",
    "Hypophthalmus edentatus",
    "Hypostomus sp",
    "Iheringichthys labrosus",
    "Insects",
    "Leporinus friderici",
    "Leporinus obtusidens",
    "Loricariichthys platymetopon",
    "Other benthos feeders",
    "Other detritus feeders",
    "Other insectivores",
    "Other omnivores",
    "Other piscivores",
    "Parauchenipterus galeatus",
    "Pimelodus maculatus",
    "Plagioscion squamosissimus",
    "Prochilodus lineatus",
    "Pseudoplatystoma corruscans",
    "Pterodoras granulosus",
    "Rhaphiodon vulpinus",
    "Salminus brasiliensis",
    "Schizodon altoparanae",
    "Schizodon borellii",
    "Serrasalmus marginatus",
    "Serrasalmus spilopleura",
    "Steindachnerina insculpta",
    "Trachydoras paraguayensis",
    "Zooplankton",
]

PREY_NAMES = [
    "Acestrorhyncus lacustris",
    "Aquatic macrophytes",
    "Astyanax altiparanae",
    "Auchenipterus nuchalis",
    "Benthos",
    "Brycon orbignyanus",
    "Cyphocharax modestus",
    "Detritus",
    "Hemisorubin platyrhynchos",
    "Hoplias malabaricus",
    "Hoplosternum littorale",
    "Hypophthalmus edentatus",
    "Hypostomus sp",
    "Iheringichthys labrosus",
    "Insects",
    "Leporinus friderici",
    "Leporinus obtusidens",
    "Loricariichthys platymetopon",
    "Other benthos feeders",
    "Other detritus feeders",
    "Other insectivores",
    "Other omnivores",
    "Other piscivores",
    "Parauchenipterus galeatus",
    "Periphyton",
    "Phytoplankton",
    "Pimelodus maculatus",
    "Plagioscion squamosissimus",
    "Prochilodus lineatus",
    "Pseudoplatystoma corruscans",
    "Pterodoras granulosus",
    "Rhaphiodon vulpinus",
    "Salminus brasiliensis",
    "Schizodon altoparanae",
    "Schizodon borellii",
    "Serrasalmus marginatus",
    "Serrasalmus spilopleura",
    "Steindachnerina insculpta",
    "Trachydoras paraguayensis",
    "Zooplankton",
]

TROPHIC_LEVELS = {
    "Detritus": 0,
    "Phytoplankton": 0,
    "Aquatic macrophytes": 0,
    "Periphyton": 0,
    "Zooplankton": 1,
    "Insects": 1,
    "Benthos": 1,
    "Prochilodus lineatus": 1,
    "Steindachnerina insculpta": 1,
    "Cyphocharax modestus": 1,
    "Hypophthalmus edentatus": 1,
    "Hypostomus sp": 1,
    "Loricariichthys platymetopon": 1,
    "Schizodon altoparanae": 1,
    "Schizodon borellii": 1,
    "Trachydoras paraguayensis": 1,
    "Other detritus feeders": 1,
    "Astyanax altiparanae": 2,
    "Auchenipterus nuchalis": 2,
    "Brycon orbignyanus": 2,
    "Hoplosternum littorale": 2,
    "Iheringichthys labrosus": 2,
    "Leporinus friderici": 2,
    "Leporinus obtusidens": 2,
    "Other benthos feeders": 2,
    "Other insectivores": 2,
    "Other omnivores": 2,
    "Parauchenipterus galeatus": 2,
    "Pimelodus maculatus": 2,
    "Pterodoras granulosus": 2,
    "Serrasalmus marginatus": 3,
    "Serrasalmus spilopleura": 3,
    "Acestrorhyncus lacustris": 4,
    "Hemisorubin platyrhynchos": 4,
    "Hoplias malabaricus": 4,
    "Other piscivores": 4,
    "Plagioscion squamosissimus": 4,
    "Pseudoplatystoma corruscans": 4,
    "Rhaphiodon vulpinus": 4,
    "Salminus brasiliensis": 4,
}

PREY_TO_IDX = {name: idx for idx, name in enumerate(PREY_NAMES)}
PREDATOR_NODE_IDS = [PREY_TO_IDX[name] for name in PREDATOR_NAMES]
N = len(PREY_NAMES)
N_PRED = len(PREDATOR_NAMES)


def load_matrix(path: str | Path) -> np.ndarray:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append([float(x) for x in line.split(",")])

    raw = np.array(rows, dtype=float)
    expected_shape = (N, N_PRED)
    if raw.shape != expected_shape:
        raise ValueError(f"raw matrix shape {raw.shape}, expected {expected_shape}")

    matrix = raw.T
    if not np.allclose(matrix.sum(axis=1), 1.0, atol=1e-6):
        raise ValueError("predator diet rows must sum to 1.0 after transpose")
    return matrix


def build_wtecm_graph(matrix: np.ndarray, labels: str = "name") -> nx.DiGraph:
    """Build G_wtecm with self-loops preserved and prey -> predator edges."""
    if labels not in {"name", "index"}:
        raise ValueError("labels must be 'name' or 'index'")

    def label(idx: int):
        return PREY_NAMES[idx] if labels == "name" else idx

    graph = nx.DiGraph()
    for idx, name in enumerate(PREY_NAMES):
        graph.add_node(
            label(idx),
            node_id=idx,
            species_name=name,
            trophic_level=TROPHIC_LEVELS.get(name, 0),
        )

    for pred_row, pred_node in enumerate(PREDATOR_NODE_IDS):
        for prey_idx, weight in enumerate(matrix[pred_row]):
            if weight > 0:
                graph.add_edge(
                    label(prey_idx),
                    label(pred_node),
                    weight=float(weight),
                    pred_row=pred_row,
                    prey_idx=prey_idx,
                    pred_node=pred_node,
                )
    return graph


def make_algorithm_graph(graph: nx.DiGraph) -> nx.DiGraph:
    """Build G_alg by removing self-loops for structural algorithms."""
    alg = graph.copy()
    alg.remove_edges_from(nx.selfloop_edges(alg))
    return alg


def wtecm(matrix: np.ndarray, removed_set: Iterable[int], threshold: float) -> tuple[set[int], int, int]:
    """Staged WTECM cascade using node ids for the extinct set."""
    extinct = set(removed_set)
    depth = 0

    while True:
        newly_extinct = []
        for pred_row, pred_node in enumerate(PREDATOR_NODE_IDS):
            if pred_node in extinct:
                continue
            loss_ratio = sum(
                matrix[pred_row, prey_idx]
                for prey_idx in range(N)
                if prey_idx in extinct and matrix[pred_row, prey_idx] > 0
            )
            if loss_ratio >= threshold - EPS:
                newly_extinct.append(pred_node)

        if not newly_extinct:
            break
        extinct.update(newly_extinct)
        depth += 1

    secondary = len(extinct) - len(set(removed_set))
    return extinct, secondary, depth


def compute_reference_ranking(matrix: np.ndarray, threshold: float) -> pd.DataFrame:
    records = []
    for node in range(N):
        _, secondary, depth = wtecm(matrix, {node}, threshold)
        records.append(
            {
                "node": node,
                "name": PREY_NAMES[node],
                "secondary_extinction": secondary,
                "cascade_depth": depth,
            }
        )

    df = pd.DataFrame(records)
    df = df.sort_values(
        ["secondary_extinction", "cascade_depth", "node"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    df["rank_pos"] = df.index + 1
    df["ref_rank"] = df.groupby(["secondary_extinction", "cascade_depth"])[
        "rank_pos"
    ].transform("mean")
    return df


def kosaraju(graph: nx.DiGraph) -> list[list[int]]:
    visited = set()
    finish_order = []

    def dfs1(start):
        stack = [(start, iter(graph.successors(start)))]
        visited.add(start)
        while stack:
            node, children = stack[-1]
            try:
                child = next(children)
                if child not in visited:
                    visited.add(child)
                    stack.append((child, iter(graph.successors(child))))
            except StopIteration:
                finish_order.append(node)
                stack.pop()

    for node in graph.nodes():
        if node not in visited:
            dfs1(node)

    transposed = graph.reverse(copy=True)
    visited_t = set()
    components = []

    def dfs2(start):
        comp = []
        stack = [start]
        visited_t.add(start)
        while stack:
            node = stack.pop()
            comp.append(node)
            for nb in transposed.successors(node):
                if nb not in visited_t:
                    visited_t.add(nb)
                    stack.append(nb)
        return comp

    for node in reversed(finish_order):
        if node not in visited_t:
            components.append(dfs2(node))
    return components


def scc_fragmentation_scores(graph: nx.DiGraph) -> dict[int, float]:
    """Score nodes by SCC fragmentation: how much removing each node increases SCC count."""
    original_components = kosaraju(graph)
    original_scc_count = len(original_components)

    scores = {}
    for node in graph.nodes():
        # Create graph with node removed
        g_removed = graph.copy()
        g_removed.remove_node(node)

        # Count SCCs in the graph without this node
        new_components = kosaraju(g_removed)
        new_scc_count = len(new_components)

        # Fragmentation = increase in SCC count
        # Higher fragmentation = more important node
        scores[node] = float(new_scc_count - original_scc_count)

    return scores


def ci_score(graph_und: nx.Graph, node: int, l: int = 1) -> int:
    degree = graph_und.degree(node)
    if degree == 0:
        return 0

    visited = {node}
    frontier = {node}
    for _ in range(l):
        next_frontier = set()
        for current in frontier:
            for nb in graph_und.neighbors(current):
                if nb not in visited:
                    next_frontier.add(nb)
                    visited.add(nb)
        frontier = next_frontier
    return (degree - 1) * sum(graph_und.degree(nb) - 1 for nb in frontier)


def corehd_ranking(graph: nx.DiGraph) -> list[int]:
    graph_und = graph.to_undirected().copy()
    removal_order = []

    while graph_und.number_of_nodes() > 0:
        core_num = nx.core_number(graph_und)
        in_2core = [node for node, core in core_num.items() if core >= 2]

        if not in_2core:
            removal_order.extend(
                sorted(graph_und.nodes(), key=lambda node: (-graph_und.degree(node), node))
            )
            break

        core_subgraph = graph_und.subgraph(in_2core)
        victim = sorted(
            core_subgraph.nodes(), key=lambda node: (-core_subgraph.degree(node), node)
        )[0]
        removal_order.append(victim)
        graph_und.remove_node(victim)

    return removal_order


def make_algorithm_rankings(
    graph_alg: nx.DiGraph,
) -> tuple[dict[str, list[int]], dict[str, dict[int, float]]]:
    graph_und = graph_alg.to_undirected()

    scores_kos = scc_fragmentation_scores(graph_alg)
    ranking_kos = sorted(scores_kos, key=lambda node: (-scores_kos[node], node))

    scores_bc = nx.betweenness_centrality(graph_alg, normalized=True, weight=None)
    ranking_bc = sorted(scores_bc.keys(), key=lambda node: (-scores_bc[node], node))

    scores_ci1 = {node: ci_score(graph_und, node, l=1) for node in graph_und.nodes()}
    ranking_ci1 = sorted(scores_ci1.keys(), key=lambda node: (-scores_ci1[node], node))

    scores_ci2 = {node: ci_score(graph_und, node, l=2) for node in graph_und.nodes()}
    ranking_ci2 = sorted(scores_ci2.keys(), key=lambda node: (-scores_ci2[node], node))

    ranking_corehd = corehd_ranking(graph_alg)
    scores_corehd = {node: float(N - rank) for rank, node in enumerate(ranking_corehd)}

    return (
        {
            "Kosaraju": ranking_kos,
            "BC": ranking_bc,
            "CI_l1": ranking_ci1,
            "CI_l2": ranking_ci2,
            "CoreHD": ranking_corehd,
        },
        {
            "Kosaraju": scores_kos,
            "BC": scores_bc,
            "CI_l1": scores_ci1,
            "CI_l2": scores_ci2,
            "CoreHD": scores_corehd,
        },
    )


def run_wtecm_sequence(
    ranking: list[int],
    matrix: np.ndarray,
    threshold: float,
    max_seed_removals: int = 5,
) -> list[dict]:
    extinct: set[int] = set()
    waves = []
    seed_count = 0

    for seed in ranking:
        if seed in extinct:
            continue

        before = set(extinct)
        after, _, depth = wtecm(matrix, before | {seed}, threshold)
        newly = after - before
        cascade_nodes = sorted(node for node in newly if node != seed)
        extinct = after
        seed_count += 1

        waves.append(
            {
                "seed": PREY_NAMES[seed],
                "removed": [PREY_NAMES[seed]]
                + [PREY_NAMES[node] for node in cascade_nodes],
                "cascade": [PREY_NAMES[node] for node in cascade_nodes],
                "n_alive": N - len(extinct),
                "secondary_this_wave": len(cascade_nodes),
                "depth": depth,
            }
        )

        if seed_count >= max_seed_removals or len(extinct) >= N:
            break

    return waves


def trapz(y: list[float], x: list[float]) -> float:
    if hasattr(np, "trapezoid"):
        return float(np.trapezoid(y, x))
    return float(np.trapz(y, x))


def run_sequential(
    ranking: list[int],
    matrix: np.ndarray,
    threshold: float,
) -> tuple[list[float], list[float], float, float]:
    """Survival curve with cascade-extinct species skipped as primary seeds."""
    extinct: set[int] = set()
    x_ticks = [0.0]
    survival = [1.0]
    seed_count = 0

    for node in ranking:
        if node in extinct:
            continue
        new_extinct, _, _ = wtecm(matrix, extinct | {node}, threshold)
        extinct = new_extinct
        seed_count += 1
        x_ticks.append(seed_count / N)
        survival.append(max(0.0, 1.0 - len(extinct) / N))
        if len(extinct) >= N:
            break

    if x_ticks[-1] < 1.0 and survival[-1] == 0.0:
        x_ticks.append(1.0)
        survival.append(0.0)

    auc = trapz(survival, x_ticks)
    r50 = next((x for x, s in zip(x_ticks, survival) if s <= 0.5), 1.0)
    return x_ticks, survival, auc, r50


def topk_overlap(ranking: list[int], ref_order: list[int], k: int) -> int:
    return len(set(ranking[:k]) & set(ref_order[:k]))


def topk_secondary_extinction(
    ranking: list[int],
    matrix: np.ndarray,
    threshold: float,
    k: int,
) -> tuple[int, int]:
    _, secondary, depth = wtecm(matrix, set(ranking[:k]), threshold)
    return secondary, depth


def spearman_with_tie(ranking: list[int], ref_df: pd.DataFrame) -> float:
    """Spearman rho against average-tie reference ranks, without scipy."""
    ref_rank_map = dict(zip(ref_df["node"], ref_df["ref_rank"]))
    algo_rank_map = {node: rank + 1 for rank, node in enumerate(ranking)}
    algo = np.array([float(algo_rank_map[v]) for v in range(N)], dtype=float)
    ref = np.array([float(ref_rank_map[v]) for v in range(N)], dtype=float)

    algo = algo - algo.mean()
    ref = ref - ref.mean()
    denom = float(np.sqrt(np.sum(algo ** 2) * np.sum(ref ** 2)))
    if denom == 0:
        return 0.0
    return round(float(np.sum(algo * ref) / denom), 4)


def evaluate_algorithms(
    algo_rankings: dict[str, list[int]],
    ref_df: pd.DataFrame,
    ref_auc: float,
    ref_r50: float,
    matrix: np.ndarray,
    threshold: float,
) -> dict[str, dict]:
    ref_order = list(ref_df["node"])
    ref_rank_map = dict(zip(ref_df["node"], ref_df["ref_rank"]))
    results = {}

    for name, ranking in algo_rankings.items():
        top1_sec, _ = topk_secondary_extinction(ranking, matrix, threshold, 1)
        top3_sec, _ = topk_secondary_extinction(ranking, matrix, threshold, 3)
        top5_sec, _ = topk_secondary_extinction(ranking, matrix, threshold, 5)
        top10_sec, _ = topk_secondary_extinction(ranking, matrix, threshold, 10)

        xt, sc, auc, r50 = run_sequential(ranking, matrix, threshold)
        top1_node = ranking[0]
        results[name] = {
            "x": xt,
            "sc": sc,
            "auc": auc,
            "r50": r50,
            "top1_node": top1_node,
            "top1_name": PREY_NAMES[top1_node],
            "top1_ref_rank": ref_rank_map[top1_node],
            "top1_sec": top1_sec,
            "top3_sec": top3_sec,
            "top5_sec": top5_sec,
            "top10_sec": top10_sec,
            "spearman": spearman_with_tie(ranking, ref_df),
            "top3_overlap": topk_overlap(ranking, ref_order, 3),
            "top5_overlap": topk_overlap(ranking, ref_order, 5),
            "top10_overlap": topk_overlap(ranking, ref_order, 10),
            "auc_gap": round(auc - ref_auc, 4),
            "r50_gap": round(r50 - ref_r50, 4),
        }

    return results


def random_baseline(matrix: np.ndarray, threshold: float, repeats: int = 100) -> dict:
    rand_aucs, rand_r50s = [], []
    rand_sec1, rand_sec3, rand_sec5, rand_sec10 = [], [], [], []
    curve_grid = np.linspace(0.0, 1.0, N + 1)
    rand_survival_curves = []

    for seed in range(repeats):
        rng = np.random.default_rng(seed)
        rand_rank = list(rng.permutation(N))

        xt, sc, auc, r50 = run_sequential(rand_rank, matrix, threshold)
        s1, _ = topk_secondary_extinction(rand_rank, matrix, threshold, 1)
        s3, _ = topk_secondary_extinction(rand_rank, matrix, threshold, 3)
        s5, _ = topk_secondary_extinction(rand_rank, matrix, threshold, 5)
        s10, _ = topk_secondary_extinction(rand_rank, matrix, threshold, 10)

        rand_aucs.append(auc)
        rand_r50s.append(r50)
        rand_sec1.append(s1)
        rand_sec3.append(s3)
        rand_sec5.append(s5)
        rand_sec10.append(s10)
        rand_survival_curves.append(np.interp(curve_grid, xt, sc))

    return {
        "auc_mean": float(np.mean(rand_aucs)),
        "auc_std": float(np.std(rand_aucs)),
        "r50_mean": float(np.mean(rand_r50s)),
        "r50_std": float(np.std(rand_r50s)),
        "top1_sec_mean": float(np.mean(rand_sec1)),
        "top1_sec_std": float(np.std(rand_sec1)),
        "top3_sec_mean": float(np.mean(rand_sec3)),
        "top3_sec_std": float(np.std(rand_sec3)),
        "top5_sec_mean": float(np.mean(rand_sec5)),
        "top5_sec_std": float(np.std(rand_sec5)),
        "top10_sec_mean": float(np.mean(rand_sec10)),
        "top10_sec_std": float(np.std(rand_sec10)),
        "curve_x": curve_grid.tolist(),
        "survival_mean": np.mean(rand_survival_curves, axis=0).tolist(),
        "survival_std": np.std(rand_survival_curves, axis=0).tolist(),
    }


def sensitivity_analysis(
    algo_rankings: dict[str, list[int]],
    matrix: np.ndarray,
    theta_list: list[float],
) -> pd.DataFrame:
    rows = []
    for theta in theta_list:
        ref_df = compute_reference_ranking(matrix, theta)
        ref_order = list(ref_df["node"])
        _, _, ref_auc, ref_r50 = run_sequential(ref_order, matrix, theta)
        ref_rank_map = dict(zip(ref_df["node"], ref_df["ref_rank"]))

        for name, ranking in algo_rankings.items():
            _, _, auc, r50 = run_sequential(ranking, matrix, theta)
            s1, _ = topk_secondary_extinction(ranking, matrix, theta, 1)
            s3, _ = topk_secondary_extinction(ranking, matrix, theta, 3)
            s5, _ = topk_secondary_extinction(ranking, matrix, theta, 5)
            s10, _ = topk_secondary_extinction(ranking, matrix, theta, 10)
            top1 = ranking[0]

            rows.append({
                "theta": theta,
                "Algorithm": name,
                "AUC": round(auc, 4),
                "AUC_Gap": round(auc - ref_auc, 4),
                "R50": round(r50, 4),
                "R50_Gap": round(r50 - ref_r50, 4),
                "Top1_Sec": s1,
                "Top3_Sec": s3,
                "Top5_Sec": s5,
                "Top10_Sec": s10,
                "Top1_Ref_rank": round(float(ref_rank_map[top1]), 2),
            })

    return pd.DataFrame(rows)


def save_csv_outputs(
    outdir: str | Path,
    theta: float,
    ref_df: pd.DataFrame,
    ref_auc: float,
    ref_r50: float,
    algo_rankings: dict[str, list[int]],
    algo_results: dict[str, dict],
    random_result: dict,
    sensitivity_df: pd.DataFrame | None = None,
) -> None:
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    ts = str(theta).replace(".", "")

    ref_df.drop(columns=["rank_pos"]).to_csv(
        out / f"reference_ranking_t{ts}.csv",
        index=False,
        encoding="utf-8-sig",
    )

    perf_rows = []
    for name, result in algo_results.items():
        perf_rows.append({
            "Algorithm": name,
            "Top1_name": result["top1_name"],
            "Top1_Ref_rank": round(float(result["top1_ref_rank"]), 2),
            "Top1_Sec_Ext": result["top1_sec"],
            "Top3_Sec_Ext": result["top3_sec"],
            "Top5_Sec_Ext": result["top5_sec"],
            "Top10_Sec_Ext": result["top10_sec"],
            "Survival_AUC": round(result["auc"], 4),
            "AUC_Gap": result["auc_gap"],
            "Ref_AUC": round(ref_auc, 4),
            "R50": round(result["r50"], 4),
            "R50_Gap": result["r50_gap"],
            "Ref_R50": round(ref_r50, 4),
            "Spearman_rho": result["spearman"],
            "Top3_Overlap": result["top3_overlap"],
            "Top5_Overlap": result["top5_overlap"],
            "Top10_Overlap": result["top10_overlap"],
        })

    rand = random_result
    perf_rows.append({
        "Algorithm": "Random_mean_100",
        "Survival_AUC": round(rand["auc_mean"], 4),
        "AUC_std": round(rand["auc_std"], 4),
        "AUC_Gap": round(rand["auc_mean"] - ref_auc, 4),
        "Ref_AUC": round(ref_auc, 4),
        "R50": round(rand["r50_mean"], 4),
        "R50_std": round(rand["r50_std"], 4),
        "R50_Gap": round(rand["r50_mean"] - ref_r50, 4),
        "Ref_R50": round(ref_r50, 4),
        "Top1_Sec_Ext_mean": round(rand["top1_sec_mean"], 2),
        "Top1_Sec_Ext_std": round(rand["top1_sec_std"], 2),
        "Top3_Sec_Ext_mean": round(rand["top3_sec_mean"], 2),
        "Top3_Sec_Ext_std": round(rand["top3_sec_std"], 2),
        "Top5_Sec_Ext_mean": round(rand["top5_sec_mean"], 2),
        "Top5_Sec_Ext_std": round(rand["top5_sec_std"], 2),
        "Top10_Sec_Ext_mean": round(rand["top10_sec_mean"], 2),
        "Top10_Sec_Ext_std": round(rand["top10_sec_std"], 2),
    })

    pd.DataFrame(perf_rows).to_csv(
        out / f"performance_t{ts}.csv",
        index=False,
        encoding="utf-8-sig",
    )

    ref_order = list(ref_df["node"])
    rank_rows = {"Reference": [PREY_NAMES[node] for node in ref_order[:10]]}
    for name, ranking in algo_rankings.items():
        rank_rows[name] = [PREY_NAMES[node] for node in ranking[:10]]
    pd.DataFrame(rank_rows, index=[f"Rank {i+1}" for i in range(10)]).to_csv(
        out / f"ranking_top10_t{ts}.csv",
        encoding="utf-8-sig",
    )

    if sensitivity_df is not None:
        sensitivity_df.to_csv(
            out / "sensitivity_analysis.csv",
            index=False,
            encoding="utf-8-sig",
        )


def build_analysis_bundle(
    data_path: str | Path = "data/FW_001.csv",
    theta: float = 0.7,
    sensitivity_thetas: list[float] | None = None,
    random_repeats: int = 100,
) -> dict:
    matrix = load_matrix(data_path)
    graph_wtecm = build_wtecm_graph(matrix, labels="index")
    graph_alg = make_algorithm_graph(graph_wtecm)
    algo_rankings, algo_scores = make_algorithm_rankings(graph_alg)

    ref_df = compute_reference_ranking(matrix, theta)
    ref_order = list(ref_df["node"])
    ref_x, ref_s, ref_auc, ref_r50 = run_sequential(ref_order, matrix, theta)
    ref_topk_secs = {
        k: topk_secondary_extinction(ref_order, matrix, theta, k)[0]
        for k in [1, 3, 5, 10]
    }

    algo_results = evaluate_algorithms(
        algo_rankings, ref_df, ref_auc, ref_r50, matrix, theta
    )
    random_result = random_baseline(matrix, theta, repeats=random_repeats)

    if sensitivity_thetas is None:
        sensitivity_thetas = [round(t * 0.1, 1) for t in range(1, 11)]
    sensitivity_df = sensitivity_analysis(algo_rankings, matrix, sensitivity_thetas)

    return {
        "matrix": matrix,
        "graph_wtecm": graph_wtecm,
        "graph_alg": graph_alg,
        "algo_rankings": algo_rankings,
        "algo_scores": algo_scores,
        "ref_df": ref_df,
        "ref_order": ref_order,
        "ref_x": ref_x,
        "ref_s": ref_s,
        "ref_auc": ref_auc,
        "ref_r50": ref_r50,
        "ref_topk_secs": ref_topk_secs,
        "algo_results": algo_results,
        "random_result": random_result,
        "sensitivity_df": sensitivity_df,
    }
