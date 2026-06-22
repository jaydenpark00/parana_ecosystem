"""STEP 6-b — 붕괴 평가 지표"""
import networkx as nx
import pandas as pd
from src.simulation import cascade


def compute_metrics(G: nx.DiGraph, removal_order: list[str],
                    threshold: float = 0.7,
                    max_removals: int = None,
                    label: str = "") -> dict:
    """
    단일 시나리오에 대해 SE / FSR / R50 / SCC Fragmentation / LCL 계산.
    """
    total = G.number_of_nodes()
    init_sccs = nx.number_strongly_connected_components(G)
    init_lc   = max(len(c) for c in nx.weakly_connected_components(G))

    # ── 전체 제거 결과 (R50 계산용) ───────────────────────────────
    full_res = cascade(G, removal_order, threshold, max_removals=None)
    full_waves = full_res["waves"]

    # R50: 생존 종 비율이 처음으로 0.5 이하가 되는 직접 제거 종 수
    r50 = None
    direct_removed = 0
    # wave마다 직접 제거 1종 + 연쇄. 직접 제거 수를 추적하려면
    # 각 wave의 첫 번째 종 = 직접 제거, 나머지 = 연쇄
    # → cascade() 에서는 wave당 target 1개 + 연쇄를 묶어서 반환하므로
    #   직접 제거 카운트 = wave 인덱스 + 1
    for i, w in enumerate(full_waves):
        k = i + 1  # 직접 제거 누적 수
        if w["n_alive"] / total <= 0.5:
            r50 = k
            break

    # ── top-N 제거 후 최종 상태 ───────────────────────────────────
    res = cascade(G, removal_order, threshold, max_removals=max_removals)
    waves = res["waves"]
    final_alive = set(res["final_alive"])

    k_removed = min(max_removals or total, total)  # 직접 제거 수
    total_extinct = total - len(final_alive)
    se  = total_extinct - k_removed          # Secondary Extinction
    fsr = len(final_alive) / total           # Final Survival Ratio

    # ── 최종 생존 서브그래프 ──────────────────────────────────────
    H = G.subgraph(final_alive)

    # SCC Fragmentation
    after_sccs = nx.number_strongly_connected_components(H) if len(H) > 0 else 0
    scc_frag   = after_sccs - init_sccs

    # Largest Component Loss (weakly connected)
    if len(H) > 0:
        after_lc = max(len(c) for c in nx.weakly_connected_components(H))
    else:
        after_lc = 0
    lcl = (init_lc - after_lc) / init_lc

    return {
        "scenario":     label,
        "k_removed":    k_removed,
        "SE":           se,
        "FSR":          round(fsr, 4),
        "R50":          r50,
        "SCC_frag":     scc_frag,
        "LCL":          round(lcl, 4),
        "final_alive":  len(final_alive),
        "total":        total,
    }


def run_all_metrics(G: nx.DiGraph,
                    bc_order:  list[str],
                    ci_order:  list[str],
                    scc_order: list[str],
                    threshold: float = 0.7,
                    k: int = 5) -> pd.DataFrame:

    rows = []
    for label, order in [("BC", bc_order), ("CI", ci_order), ("SCC Bridge", scc_order)]:
        m = compute_metrics(G, order, threshold, max_removals=k, label=label)
        rows.append(m)

    df = pd.DataFrame(rows).set_index("scenario")
    cols = ["k_removed", "SE", "FSR", "R50", "SCC_frag", "LCL", "final_alive", "total"]
    df = df[cols]

    print("\n" + "=" * 60)
    print(f"붕괴 평가 지표 (top-{k} 제거, threshold={threshold})")
    print("=" * 60)
    print(df.to_string())
    print()
    print("SE       : Secondary Extinction (연쇄 멸종 수)")
    print("FSR      : Final Survival Ratio (최종 생존 비율)")
    print("R50      : 생존 50% 이하가 되는 최초 직접 제거 수")
    print("SCC_frag : SCC 개수 변화 (양수 = 분열)")
    print("LCL      : Largest Component Loss (연결 덩어리 축소 비율)")

    return df


def run_wtecm_metrics(algo_rankings: dict[str, list[int]],
                      matrix,
                      threshold: float = 0.7,
                      k: int = 5) -> pd.DataFrame:
    """Evaluate WTECM rankings with top-k secondary extinction and survival."""
    from src.wtecm import run_sequential, topk_secondary_extinction

    rows = []
    for label, ranking in algo_rankings.items():
        x, survival, auc, r50 = run_sequential(ranking, matrix, threshold)
        sec, depth = topk_secondary_extinction(ranking, matrix, threshold, k)
        rows.append({
            "scenario": label,
            "k_removed": k,
            "SE": sec,
            "Cascade_depth": depth,
            "Survival_AUC": round(auc, 4),
            "R50": round(r50, 4),
            "Final_survival": round(survival[-1], 4),
            "x_ticks": len(x),
        })

    df = pd.DataFrame(rows).set_index("scenario")
    print("\n" + "=" * 60)
    print(f"WTECM metrics (top-{k}, threshold={threshold})")
    print("=" * 60)
    print(df.to_string())
    return df


if __name__ == "__main__":
    import sys, random
    sys.path.insert(0, ".")
    random.seed(42)
    from src.graph import build_graph
    from src.centrality import compute_bc
    from src.ci import compute_ci
    from src.scc import run_scc_analysis

    G = build_graph("data/parana_edgelist.csv")
    bc_df = compute_bc(G)
    ci_df = compute_ci(G)
    _, _, bridges_df = run_scc_analysis(G)

    bc_order  = list(bc_df["species"])
    ci_order  = list(ci_df["species"])
    scc_order = list(bridges_df["species"]) + [
        n for n in G.nodes() if n not in set(bridges_df["species"])
    ]

    run_all_metrics(G, bc_order, ci_order, scc_order)
