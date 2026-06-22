"""STEP 6 — Co-extinction cascade simulation"""
import networkx as nx
import pandas as pd
import random
import os


def cascade(G: nx.DiGraph, removal_order: list[str],
            threshold: float = 0.7,
            max_removals: int = None) -> dict:
    """
    removal_order 순서로 종을 하나씩 제거하고 연쇄 멸종을 전파한다.

    멸종 규칙 (diet-proportion 기반):
        종 sp의 먹이 중 사라진 것들의 diet proportion 합 > threshold 이면 sp도 멸종.
        edge weight가 없으면 균등 분배(1/out_degree)로 처리.

    Parameters
    ----------
    max_removals : 최대 직접 제거 횟수. None이면 removal_order 전체 사용.
                   robustness curve용은 None, 핵심종 시나리오는 10~15.
    """
    alive = set(G.nodes())
    waves = []

    order = removal_order if max_removals is None else removal_order[:max_removals]

    for target in order:
        if target not in alive:
            continue

        wave_removed = {target}
        alive -= {target}

        changed = True
        while changed:
            changed = False
            for sp in list(alive):
                out_deg = G.out_degree(sp)
                if out_deg == 0:
                    continue

                # diet proportion: edge weight 있으면 사용, 없으면 균등
                lost_diet = 0.0
                for prey in G.successors(sp):
                    if prey not in alive:
                        w = G[sp][prey].get("weight", 1.0 / out_deg)
                        lost_diet += w

                if lost_diet > threshold:
                    alive.discard(sp)
                    wave_removed.add(sp)
                    changed = True

        waves.append({
            "removed_this_wave": sorted(wave_removed),
            "n_alive": len(alive),
            "n_edges": G.subgraph(alive).number_of_edges(),
        })

        if not alive:
            break

    return {"waves": waves, "final_alive": sorted(alive)}


def cascade_wtecm(matrix_or_path, removal_order: list,
                  threshold: float = 0.7,
                  max_removals: int = None) -> dict:
    """Run staged WTECM cascade from the raw matrix model.

    cascade() is kept for legacy graph scenarios. This function follows the
    WTECM convention: 40x36 raw matrix -> 36x40 predator rows, node id based
    extinction state, and cascade-extinct species are skipped as primary seeds.
    """
    from src.wtecm import PREY_NAMES, PREY_TO_IDX, load_matrix, run_wtecm_sequence

    if isinstance(matrix_or_path, (str, bytes, os.PathLike)):
        matrix = load_matrix(matrix_or_path)
    else:
        matrix = matrix_or_path

    ranking = [
        PREY_TO_IDX[node] if isinstance(node, str) else int(node)
        for node in removal_order
    ]
    limit = max_removals if max_removals is not None else len(ranking)
    waves = run_wtecm_sequence(ranking, matrix, threshold, limit)

    extinct = set()
    converted = []
    for wave in waves:
        extinct.update(wave["removed"])
        converted.append({
            "seed": wave["seed"],
            "removed_this_wave": wave["removed"],
            "cascade": wave["cascade"],
            "n_alive": wave["n_alive"],
            "n_edges": None,
            "secondary_this_wave": wave["secondary_this_wave"],
            "depth": wave["depth"],
        })

    final_alive = [name for name in PREY_NAMES if name not in extinct]
    return {"waves": converted, "final_alive": final_alive}


def run_simulation(G: nx.DiGraph, bc_order: list[str],
                   ci_order: list[str], scc_order: list[str],
                   n_random: int = 10,
                   threshold: float = 0.7,
                   scenario_removals: int = 5) -> dict:
    """
    3가지 시나리오 실행.

    robustness curve용: max_removals=None (전체)
    핵심종 효과 분석용: max_removals=scenario_removals (top-N만 제거)
    """
    all_nodes = list(G.nodes())
    results = {}

    # Random baseline (robustness curve용 — 전체 제거)
    random_waves_list = []
    for _ in range(n_random):
        order = all_nodes[:]
        random.shuffle(order)
        random_waves_list.append(cascade(G, order, threshold)["waves"])
    results["random"] = random_waves_list

    # BC / CI / SCC targeted — top-N만 제거 (핵심종 시나리오)
    results["bc"]  = cascade(G, bc_order,  threshold, max_removals=scenario_removals)
    results["ci"]  = cascade(G, ci_order,  threshold, max_removals=scenario_removals)
    results["scc"] = cascade(G, scc_order, threshold, max_removals=scenario_removals)

    # robustness curve용 전체 제거 결과도 별도 보관
    results["bc_full"]  = cascade(G, bc_order,  threshold)
    results["ci_full"]  = cascade(G, ci_order,  threshold)
    results["scc_full"] = cascade(G, scc_order, threshold)

    _print_summary(results, len(all_nodes), scenario_removals)
    return results


def _print_summary(results: dict, total: int, k: int):
    print(f"\n[핵심종 top-{k} 제거 후 연쇄멸종 결과]")
    for key in ["bc", "ci", "scc"]:
        waves = results[key]["waves"]
        alive = results[key]["final_alive"]
        extinct = total - len(alive)
        print(f"  {key.upper():4s} targeted : {len(alive)}/{total}종 생존  "
              f"(직접제거 {k} + 연쇄멸종 {extinct - k}종)")

    rand_final = [
        w[-1]["n_alive"] if w else total
        for w in results["random"]
    ]
    avg = sum(rand_final) / len(rand_final)
    print(f"  Random (avg): {avg:.1f}/{total}종 생존")


def build_robustness_curve(waves: list[dict], total: int) -> tuple:
    removed_frac = [0.0]
    alive_frac   = [1.0]
    removed = 0
    for w in waves:
        removed += len(w["removed_this_wave"])
        removed_frac.append(min(removed / total, 1.0))
        alive_frac.append(w["n_alive"] / total)
    return removed_frac, alive_frac


if __name__ == "__main__":
    import sys; sys.path.insert(0, ".")
    from src.graph import build_graph
    from src.centrality import compute_bc
    from src.ci import compute_ci
    random.seed(42)
    G = build_graph("data/parana_edgelist.csv")
    bc_df = compute_bc(G)
    ci_df = compute_ci(G)
    run_simulation(G, list(bc_df["species"]), list(ci_df["species"]))
