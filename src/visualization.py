"""STEP 7 — Full Visualization"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")          # Backend setup: call before pyplot import
import matplotlib.pyplot as plt

# Korean font setup
try:
    import koreanize_matplotlib
except ImportError:
    pass
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import matplotlib.font_manager as fm
import seaborn as sns
import networkx as nx
import plotly.graph_objects as go

plt.rcParams["axes.unicode_minus"] = False

# Register NanumGothic font directly to avoid rcParams override issues
_nanum_path = fm.findfont(fm.FontProperties(family="NanumGothic"))
if "NanumGothic" in _nanum_path:
    fm.fontManager.addfont(_nanum_path)
    plt.rcParams["font.family"] = "NanumGothic"

FIGURES = "outputs/figures"
os.makedirs(FIGURES, exist_ok=True)

TROPHIC_LABELS = {0: "Basal", 1: "Primary", 2: "Secondary", 3: "Mesopredator", 4: "Top predator"}

WTECM_COLORS = {
    "Kosaraju": "#534AB7",
    "BC": "#0F6E56",
    "CI_l1": "#993C1D",
    "CI_l2": "#C4651A",
    "CoreHD": "#854F0B",
    "Ref": "#1a1a1a",
}

WTECM_LS = {
    "Kosaraju": "-",
    "BC": "--",
    "CI_l1": "-.",
    "CI_l2": (0, (3, 1, 1, 1, 1, 1)),
    "CoreHD": ":",
    "Ref": "-",
}


def _compact_species_label(name: str) -> str:
    parts = name.split()
    if len(parts) == 1:
        return name[:13]
    if name.startswith("Other"):
        return f"Other\n{parts[1][:10]}"
    return f"{parts[0][0]}. {parts[1][:10]}"


INSTRUCTIONAL_METHODS = ["Kosaraju", "BC"]
EXTENDED_METHODS = ["Kosaraju", "BC", "CI_l1", "CI_l2", "CoreHD"]


def _method_label(name: str) -> str:
    return {
        "CI_l1": "CI L1",
        "CI_l2": "CI L2",
    }.get(name, name)


def _select_methods(methods: list[str], algo_rankings: dict) -> list[str]:
    return [name for name in methods if name in algo_rankings]


def _grouped_bar_width(method_count: int) -> float:
    return min(0.72 / max(method_count, 1), 0.32)


def _annotate_bars(ax, bars, fmt: str = "{:.3f}", offset: float = 0.008):
    for bar in bars:
        value = bar.get_height()
        if np.isnan(value):
            continue
        va = "bottom" if value >= 0 else "top"
        y = value + offset if value >= 0 else value - offset
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            y,
            fmt.format(value),
            ha="center",
            va=va,
            fontsize=8,
        )


def _plot_top5_rank_heatmap(theta: float,
                            algo_rankings: dict,
                            methods: list[str],
                            outdir: str):
    from src.wtecm import PREY_NAMES

    methods = _select_methods(methods, algo_rankings)
    top_k = 5
    top_nodes = {name: list(algo_rankings[name][:top_k]) for name in methods}

    selection_count = {}
    for nodes in top_nodes.values():
        for node in nodes:
            selection_count[node] = selection_count.get(node, 0) + 1

    rank_maps = {
        name: {node: rank + 1 for rank, node in enumerate(algo_rankings[name])}
        for name in methods
    }
    union_nodes = sorted(
        selection_count,
        key=lambda node: (
            -selection_count[node],
            min(rank_maps[name][node] for name in methods),
            PREY_NAMES[node],
        ),
    )
    heatmap_values = pd.DataFrame(
        [[rank_maps[name][node] for node in union_nodes] for name in methods],
        index=[_method_label(name) for name in methods],
        columns=[
            f"{_compact_species_label(PREY_NAMES[node])}\n(n={selection_count[node]})"
            for node in union_nodes
        ],
    )
    heatmap_labels = heatmap_values.apply(lambda col: col.map(lambda value: f"{int(value)}"))

    fig_width = max(9, len(union_nodes) * 0.95)
    fig, ax = plt.subplots(figsize=(fig_width, 4.8))
    fig.suptitle(
        f"Fig.1  Instructional Algorithms Top-5 Union Rank Heatmap  [theta={theta}]",
        fontsize=12,
        fontweight="bold",
    )
    sns.heatmap(
        heatmap_values,
        ax=ax,
        cmap="YlOrRd_r",
        vmin=1,
        vmax=max(len(ranking) for ranking in algo_rankings.values()),
        annot=heatmap_labels,
        fmt="",
        linewidths=1,
        linecolor="white",
        cbar_kws={"label": "Full ranking position (1 = highest)"},
        annot_kws={"size": 9, "fontweight": "bold"},
    )
    for text in ax.texts:
        value = float(text.get_text())
        text.set_color("white" if value <= top_k else "#1a1a1a")
    ax.set_xlabel("Unique species selected by Kosaraju or BC Top-5")
    ax.set_ylabel("Algorithm")
    ax.set_title(
        "Cells show each method's full-rank position for the instructional Top-5 union",
        fontsize=10,
        pad=10,
    )
    ax.tick_params(axis="x", rotation=35)
    ax.tick_params(axis="y", rotation=0)
    plt.tight_layout(rect=[0, 0, 1, 0.94])

    path = f"{outdir}/fig1_instructional_algorithm_heatmap.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close()
    print(f"Saved {path}")


def _plot_rank_alignment(theta: float,
                         algo_results: dict,
                         methods: list[str],
                         fig_no: int,
                         title_scope: str,
                         outdir: str):
    methods = [name for name in methods if name in algo_results]
    labels = [_method_label(name) for name in methods]
    colors = [WTECM_COLORS[name] for name in methods]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.4))
    fig.suptitle(
        f"Fig.{fig_no}  {title_scope} Spearman Rho + Top-K Overlap vs Reference  [theta={theta}]",
        fontsize=12,
        fontweight="bold",
    )

    ax = axes[0]
    rho_vals = [algo_results[name]["spearman"] for name in methods]
    bars = ax.bar(labels, rho_vals, color=colors, alpha=0.9, edgecolor="white")
    _annotate_bars(ax, bars, "{:.3f}", offset=0.018)
    ax.axhline(0, color="gray", linewidth=0.8)
    ax.set_ylim(-0.3, 1.0)
    ax.set_ylabel("Spearman rho (higher = closer to Reference)")
    ax.set_title("(a) Rank correlation")
    ax.grid(True, alpha=0.3, axis="y")
    if len(methods) > 3:
        ax.tick_params(axis="x", rotation=20)

    ax = axes[1]
    ks = [3, 5, 10]
    x_pos = np.arange(len(ks))
    width = _grouped_bar_width(len(methods))
    for i, name in enumerate(methods):
        overlaps = [
            algo_results[name]["top3_overlap"],
            algo_results[name]["top5_overlap"],
            algo_results[name]["top10_overlap"],
        ]
        offset = (i - (len(methods) - 1) / 2) * width
        bars = ax.bar(
            x_pos + offset,
            overlaps,
            width,
            label=_method_label(name),
            color=WTECM_COLORS[name],
            alpha=0.85,
            edgecolor="white",
        )
        _annotate_bars(ax, bars, "{:.0f}", offset=0.12)
    ax.plot(
        x_pos,
        ks,
        color=WTECM_COLORS["Ref"],
        linewidth=1.8,
        linestyle="--",
        marker="o",
        label="Reference maximum",
        zorder=10,
    )
    ax.set_xticks(x_pos)
    ax.set_xticklabels([f"Top-{k}" for k in ks])
    ax.set_ylabel("Overlap count")
    ax.set_ylim(0, 10.8)
    ax.set_title("(b) Top-K overlap")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    filename = (
        "fig2_instructional_spearman_topk.png"
        if fig_no == 2
        else "fig4_extended_spearman_topk.png"
    )
    path = f"{outdir}/{filename}"
    fig.savefig(path, bbox_inches="tight")
    plt.close()
    print(f"Saved {path}")


def _plot_extinction_performance(theta: float,
                                 ref_x: list[float],
                                 ref_s: list[float],
                                 ref_auc: float,
                                 ref_r50: float,
                                 ref_topk_secs: dict[int, int],
                                 algo_results: dict,
                                 random_result: dict,
                                 methods: list[str],
                                 fig_no: int,
                                 title_scope: str,
                                 outdir: str):
    methods = [name for name in methods if name in algo_results]
    labels = [_method_label(name) for name in methods]
    colors = [WTECM_COLORS[name] for name in methods]
    rand = random_result

    fig, axes = plt.subplots(2, 2, figsize=(15.8, 9.4))
    fig.suptitle(
        f"Fig.{fig_no}  {title_scope} Cascade Performance vs Reference  [theta={theta}]",
        fontsize=12,
        fontweight="bold",
    )

    ax = axes[0, 0]
    if {"curve_x", "survival_mean", "survival_std"}.issubset(rand):
        rand_x = np.array(rand["curve_x"], dtype=float)
        rand_mean = np.array(rand["survival_mean"], dtype=float)
        rand_std = np.array(rand["survival_std"], dtype=float)
        ax.plot(rand_x, rand_mean, color="gray", linewidth=1.8,
                linestyle="-", label="Random mean")
        ax.fill_between(rand_x,
                        np.maximum(0, rand_mean - rand_std),
                        np.minimum(1, rand_mean + rand_std),
                        color="gray", alpha=0.15, label="Random +/- std")
    ax.plot(ref_x, ref_s, color=WTECM_COLORS["Ref"], linewidth=3,
            linestyle=WTECM_LS["Ref"], label="Reference", zorder=10)
    for name in methods:
        result = algo_results[name]
        ax.plot(result["x"], result["sc"],
                color=WTECM_COLORS[name],
                linewidth=1.9,
                linestyle=WTECM_LS[name],
                label=_method_label(name))
    ax.axhline(0.5, color="gray", linestyle="--", linewidth=0.8, alpha=0.45)
    ax.set_xlabel("Primary seed removal fraction")
    ax.set_ylabel("Survival ratio after cascade")
    ax.set_title("(a) Survival curve")
    ax.legend(fontsize=8)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)

    ax = axes[0, 1]
    auc_den = rand["auc_mean"] - ref_auc
    auc_scores = [
        (rand["auc_mean"] - algo_results[name]["auc"]) / auc_den
        if abs(auc_den) > 1e-12 else np.nan
        for name in methods
    ]
    bars = ax.bar(labels, auc_scores, color=colors, alpha=0.9, edgecolor="white")
    _annotate_bars(ax, bars, "{:.2f}", offset=0.025)
    ax.axhline(1, color=WTECM_COLORS["Ref"], linewidth=1.6,
               linestyle="--", label="Reference=1")
    ax.axhline(0, color="gray", linewidth=1.2,
               linestyle=":", label="Random=0")
    y_min = min(-0.15, min(auc_scores) - 0.12)
    y_max = max(1.1, max(auc_scores) + 0.12)
    ax.set_ylim(y_min, y_max)
    ax.set_ylabel("(Random AUC - Algorithm AUC) / (Random AUC - Reference AUC)")
    ax.set_title("(b) Normalized AUC score")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")

    ax = axes[1, 0]
    r50_ratios = [
        algo_results[name]["r50"] / ref_r50
        if ref_r50 > 1e-12 else np.nan
        for name in methods
    ]
    bars = ax.bar(labels, r50_ratios, color=colors, alpha=0.9, edgecolor="white")
    _annotate_bars(ax, bars, "{:.1f}x", offset=0.12)
    if ref_r50 > 1e-12:
        rand_r50_ratio = rand["r50_mean"] / ref_r50
        rand_r50_std = rand["r50_std"] / ref_r50
        ax.axhspan(rand_r50_ratio - rand_r50_std,
                   rand_r50_ratio + rand_r50_std,
                   alpha=0.11, color="gray",
                   label=f"Random {rand_r50_ratio:.1f}x+/-{rand_r50_std:.1f}x")
    ax.axhline(1, color=WTECM_COLORS["Ref"], linewidth=1.6,
               linestyle="--", label="Reference=1x")
    ax.set_ylabel("R50 / Reference R50 (lower better)")
    ax.set_title("(c) R50 ratio")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")

    ax = axes[1, 1]
    ref_top5_sec = ref_topk_secs[5]
    bar_labels = ["Reference", "Random"] + [_method_label(name) for name in methods]
    bar_values = [ref_top5_sec, rand["top5_sec_mean"]] + [
        algo_results[name]["top5_sec"] for name in methods
    ]
    bar_colors = [WTECM_COLORS["Ref"], "#8c8c8c"] + [
        WTECM_COLORS[name] for name in methods
    ]
    x_pos = np.arange(len(bar_labels))
    bars = ax.bar(
        x_pos,
        bar_values,
        color=bar_colors,
        alpha=0.9,
        edgecolor="white",
        linewidth=0.8,
    )
    ax.errorbar(
        x_pos[1],
        rand["top5_sec_mean"],
        yerr=rand["top5_sec_std"],
        fmt="none",
        ecolor="#555555",
        elinewidth=1.2,
        capsize=4,
        zorder=10,
    )
    ax.axhline(ref_top5_sec, color=WTECM_COLORS["Ref"], linewidth=1.6,
               linestyle="--", label=f"Reference={ref_top5_sec}")
    for idx, (bar, value) in enumerate(zip(bars, bar_values)):
        if idx == 0:
            label = f"{value:.0f}\n100%"
        elif idx == 1:
            capture = value / ref_top5_sec if ref_top5_sec > 0 else np.nan
            label = f"{value:.1f}\n{capture:.0%}"
        else:
            capture = value / ref_top5_sec if ref_top5_sec > 0 else np.nan
            label = f"{value:.0f}\n{capture:.0%}"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + max(ref_top5_sec * 0.03, 0.35),
            label,
            ha="center",
            va="bottom",
            fontsize=8,
        )
    ax.set_xticks(x_pos)
    ax.set_xticklabels(bar_labels)
    ax.set_ylabel("Secondary extinct species count")
    ax.set_title("(d) Top-5 simultaneous removal impact")
    ax.set_ylim(0, max(ref_top5_sec, max(bar_values) + rand["top5_sec_std"]) * 1.22)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")
    if len(bar_labels) > 4:
        ax.tick_params(axis="x", rotation=20)

    for ax in axes.flat:
        if len(methods) > 3:
            ax.tick_params(axis="x", rotation=20)

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    filename = (
        "fig3_instructional_survival_aucscore_r50ratio_capture.png"
        if fig_no == 3
        else "fig5_extended_survival_aucscore_r50ratio_capture.png"
    )
    path = f"{outdir}/{filename}"
    fig.savefig(path, bbox_inches="tight")
    plt.close()
    print(f"Saved {path}")


def plot_wtecm_figures(theta: float,
                       ref_df: pd.DataFrame,
                       ref_auc: float,
                       ref_r50: float,
                       ref_x: list[float],
                       ref_s: list[float],
                       ref_topk_secs: dict[int, int],
                       algo_rankings: dict,
                       algo_results: dict,
                       random_result: dict,
                       sensitivity_df: pd.DataFrame,
                       outdir: str = "outputs/v5_2"):
    """Create WTECM result figures from the matrix-based analysis pipeline."""
    os.makedirs(outdir, exist_ok=True)
    if "NanumGothic" in _nanum_path:
        fm.fontManager.addfont(_nanum_path)
        plt.rcParams["font.family"] = "NanumGothic"
    plt.rcParams.update({
        "font.size": 10,
        "axes.titlesize": 11,
        "figure.dpi": 150,
    })

    _plot_top5_rank_heatmap(
        theta=theta,
        algo_rankings=algo_rankings,
        methods=INSTRUCTIONAL_METHODS,
        outdir=outdir,
    )

    _plot_rank_alignment(
        theta=theta,
        algo_results=algo_results,
        methods=INSTRUCTIONAL_METHODS,
        fig_no=2,
        title_scope="Instructional Algorithms",
        outdir=outdir,
    )
    _plot_extinction_performance(
        theta=theta,
        ref_x=ref_x,
        ref_s=ref_s,
        ref_auc=ref_auc,
        ref_r50=ref_r50,
        ref_topk_secs=ref_topk_secs,
        algo_results=algo_results,
        random_result=random_result,
        methods=INSTRUCTIONAL_METHODS,
        fig_no=3,
        title_scope="Instructional Algorithms",
        outdir=outdir,
    )
    _plot_rank_alignment(
        theta=theta,
        algo_results=algo_results,
        methods=EXTENDED_METHODS,
        fig_no=4,
        title_scope="Instructional + Extended Algorithms",
        outdir=outdir,
    )
    _plot_extinction_performance(
        theta=theta,
        ref_x=ref_x,
        ref_s=ref_s,
        ref_auc=ref_auc,
        ref_r50=ref_r50,
        ref_topk_secs=ref_topk_secs,
        algo_results=algo_results,
        random_result=random_result,
        methods=EXTENDED_METHODS,
        fig_no=5,
        title_scope="Instructional + Extended Algorithms",
        outdir=outdir,
    )


def run_wtecm_all(bundle: dict, theta: float, outdir: str = "outputs/v5_2"):
    plot_wtecm_figures(
        theta=theta,
        ref_df=bundle["ref_df"],
        ref_auc=bundle["ref_auc"],
        ref_r50=bundle["ref_r50"],
        ref_x=bundle["ref_x"],
        ref_s=bundle["ref_s"],
        ref_topk_secs=bundle["ref_topk_secs"],
        algo_rankings=bundle["algo_rankings"],
        algo_results=bundle["algo_results"],
        random_result=bundle["random_result"],
        sensitivity_df=bundle["sensitivity_df"],
        outdir=outdir,
    )


# ── 7-1. SCC 네트워크 그래프 ──────────────────────────────────────
def plot_scc_network(G: nx.DiGraph, k_sccs, t_sccs, bridges_df: pd.DataFrame):
    """
    SCC 그룹을 색상으로, 브릿지 노드를 크기+테두리로 시각화.
    한 그림에 Kosaraju / Tarjan 나란히 표시.
    y축 = trophic level (하위→상위 레이아웃).
    SCC 크기가 큰 그룹은 이름 레이블, 브릿지 노드는 항상 레이블.
    """
    fig, axes = plt.subplots(1, 2, figsize=(24, 12), facecolor="#1a1a2e")

    bridge_set = set(bridges_df.head(10)["species"])
    tl = nx.get_node_attributes(G, "trophic_level")

    # 공통 레이아웃 (trophic level y, spring x)
    base_pos = nx.spring_layout(G, seed=42, k=1.5, iterations=100)
    pos = {n: (base_pos[n][0] * 2, tl.get(n, 0)) for n in G.nodes()}

    # x 약간 흔들어서 같은 trophic level끼리 겹침 방지
    rng = np.random.default_rng(0)
    for n in pos:
        x, y = pos[n]
        pos[n] = (x + rng.uniform(-0.15, 0.15), y)

    for ax, sccs, title in [(axes[0], k_sccs, "Kosaraju"), (axes[1], t_sccs, "Tarjan")]:
        ax.set_facecolor("#1a1a2e")

        # SCC 크기 기준 상위 N개 색깔 구분, 나머지는 회색
        scc_sizes   = sorted([(len(s), i, s) for i, s in enumerate(sccs)], reverse=True)
        top_colored = 8
        scc_palette = matplotlib.colormaps["tab10"].resampled(top_colored)
        node_to_color = {}
        node_to_scc_id = {}
        for rank, (sz, orig_idx, scc) in enumerate(scc_sizes):
            for n in scc:
                node_to_scc_id[n] = orig_idx
                if rank < top_colored:
                    node_to_color[n] = scc_palette(rank)
                else:
                    node_to_color[n] = (0.35, 0.35, 0.35, 0.7)

        # 엣지 먼저
        nx.draw_networkx_edges(
            G, pos, ax=ax,
            edge_color="#ffffff", alpha=0.08,
            arrows=True, arrowsize=6, width=0.4,
            connectionstyle="arc3,rad=0.1"
        )

        # 일반 노드
        normal_nodes  = [n for n in G.nodes() if n not in bridge_set]
        normal_colors = [node_to_color[n] for n in normal_nodes]
        nx.draw_networkx_nodes(
            G, pos, ax=ax,
            nodelist=normal_nodes,
            node_color=normal_colors,
            node_size=180,
            linewidths=0.5,
            edgecolors="#888888"
        )

        # 브릿지 노드 (크기 3배, 두꺼운 테두리, 흰색 테두리)
        bridge_colors = [node_to_color[n] for n in bridge_set if n in G.nodes()]
        nx.draw_networkx_nodes(
            G, pos, ax=ax,
            nodelist=[n for n in bridge_set if n in G.nodes()],
            node_color=bridge_colors,
            node_size=700,
            linewidths=2.5,
            edgecolors="#FFD700"
        )

        # 브릿지 노드 레이블
        bridge_labels = {n: n.replace(" ", "\n") for n in bridge_set if n in G.nodes()}
        for n, label in bridge_labels.items():
            x, y = pos[n]
            ax.text(
                x, y + 0.18, label,
                fontsize=5.5, color="white", ha="center", va="bottom",
                fontweight="bold",
                path_effects=[pe.withStroke(linewidth=1.5, foreground="black")]
            )

        # trophic level 가이드라인
        for lvl, name in TROPHIC_LABELS.items():
            ax.axhline(lvl, color="white", alpha=0.06, lw=0.8, ls="--")
            ax.text(-2.8, lvl + 0.05, f"TL {lvl}: {name}",
                    fontsize=7, color="#aaaaaa", va="bottom")

        # SCC 크기 레전드
        legend_handles = []
        for rank, (sz, orig_idx, scc) in enumerate(scc_sizes[:top_colored]):
            sample = next(iter(scc))
            label = f"SCC {rank+1} (n={sz}): {sample[:18]}..."  if sz > 1 else f"SCC {rank+1}: {sample[:20]}"
            patch = mpatches.Patch(color=scc_palette(rank), label=label)
            legend_handles.append(patch)
        legend_handles.append(
            mpatches.Patch(color=(0.35, 0.35, 0.35, 0.9), label=f"기타 SCC (n≤1)")
        )
        legend_handles.append(
            mpatches.Patch(facecolor="gray", edgecolor="#FFD700", linewidth=2,
                           label="브릿지 노드 (top-10)")
        )
        leg = ax.legend(handles=legend_handles, loc="lower left",
                        fontsize=6.5, framealpha=0.3,
                        labelcolor="white", facecolor="#111111")

        ax.set_title(f"{title} SCC Analysis  —  {len(sccs)} SCCs",
                     fontsize=14, color="white", pad=12)
        ax.set_ylabel("Trophic Level", color="#cccccc", fontsize=9)
        ax.tick_params(colors="#cccccc")
        ax.spines["bottom"].set_color("#555555")
        ax.spines["left"].set_color("#555555")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_yticks([0, 1, 2, 3, 4])
        ax.set_yticklabels([f"TL{i}" for i in range(5)], color="#cccccc")
        ax.set_xticks([])

    plt.suptitle("파라나 강 먹이그물 — SCC Analysis\n(Golden border = Bridge keystone species top-10)",
                 fontsize=16, color="white", y=1.01)
    plt.tight_layout()
    path = f"{FIGURES}/7-1_scc_network.png"
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor="#1a1a2e")
    plt.close()
    print(f"Saved {path}")


def plot_scc_summary(G: nx.DiGraph, k_sccs, bridges_df: pd.DataFrame):
    """SCC Summary Bar Chart"""
    # SCC 크기 분포
    sizes = sorted([len(s) for s in k_sccs], reverse=True)
    tl = nx.get_node_attributes(G, "trophic_level")

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 왼쪽: SCC 크기 분포 막대
    ax = axes[0]
    colors = ["#e74c3c" if s > 1 else "#3498db" for s in sizes]
    ax.bar(range(len(sizes)), sizes, color=colors, edgecolor="white", linewidth=0.3)
    ax.set_xlabel("SCC 인덱스 (크기 내림차순)")
    ax.set_ylabel("Number of Species")
    ax.set_title(f"SCC Size Distribution — Total {len(k_sccs)} SCCs\n(빨강=다중species, 파랑=단일species)")
    ax.grid(axis="y", alpha=0.3)

    # 오른쪽: 브릿지 노드 top-10 cross_edges 막대
    ax2 = axes[1]
    top10 = bridges_df.head(10)
    colors2 = plt.cm.YlOrRd(np.linspace(0.4, 0.9, len(top10)))[::-1]
    bars = ax2.barh(range(len(top10)), top10["cross_edges"].values,
                    color=colors2, edgecolor="white", linewidth=0.4)
    ax2.set_yticks(range(len(top10)))
    ax2.set_yticklabels(top10["species"].values, fontsize=9)
    ax2.invert_yaxis()
    ax2.set_xlabel("Cross-SCC 엣지 수")
    ax2.set_title("브릿지 노드 top-10\n(SCC 경계를 넘는 엣지 수 기준)")
    ax2.grid(axis="x", alpha=0.3)
    for bar, val in zip(bars, top10["cross_edges"].values):
        ax2.text(val + 0.1, bar.get_y() + bar.get_height()/2,
                 str(val), va="center", fontsize=8)

    plt.tight_layout()
    path = f"{FIGURES}/7-1b_scc_summary.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {path}")


# ── 7-2. 핵심species 3자 비교 히트맵 ──────────────────────────────────
def plot_comparison_heatmap(heatmap_df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7, max(6, len(heatmap_df) * 0.42)))
    data = heatmap_df.astype(float)
    mask = data.isna()
    sns.heatmap(data, ax=ax, cmap="YlOrRd_r", annot=True, fmt=".0f",
                linewidths=0.5, mask=mask, cbar_kws={"label": "Rank"},
                annot_kws={"size": 8})
    ax.set_title("핵심species 랭킹 비교\n(낮은 숫자 = 더 중요)", fontsize=12)
    ax.set_xlabel("")
    ax.set_ylabel("")
    plt.tight_layout()
    path = f"{FIGURES}/7-2_comparison_heatmap.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {path}")


# ── 7-3. Alluvial / Sankey ────────────────────────────────────────
def plot_sankey(bridges_df: pd.DataFrame, bc_df: pd.DataFrame,
                ci_df: pd.DataFrame, k: int = 10):
    top_b  = list(bridges_df.head(k)["species"])
    top_bc = list(bc_df.head(k)["species"])
    top_ci = list(ci_df.head(k)["species"])
    all_sp = list(dict.fromkeys(top_bc + top_b + top_ci))

    n = len(all_sp)
    idx = {sp: i for i, sp in enumerate(all_sp)}

    bc_labels  = [f"BC: {sp}"  for sp in all_sp]
    scc_labels = [f"SCC: {sp}" for sp in all_sp]
    ci_labels  = [f"CI: {sp}"  for sp in all_sp]
    all_labels = bc_labels + scc_labels + ci_labels

    src_list, tgt_list, val_list, col_list = [], [], [], []

    # BC → SCC Bridge
    for sp in top_bc:
        if sp in top_b:
            src_list.append(idx[sp])
            tgt_list.append(n + idx[sp])
            val_list.append(1)
            col_list.append("rgba(52,152,219,0.5)")

    # SCC Bridge → CI
    for sp in top_b:
        if sp in top_ci:
            src_list.append(n + idx[sp])
            tgt_list.append(2*n + idx[sp])
            val_list.append(1)
            col_list.append("rgba(231,76,60,0.5)")

    # BC → CI (directly, 공통이지만 SCC에 없는)
    for sp in top_bc:
        if sp in top_ci and sp not in top_b:
            src_list.append(idx[sp])
            tgt_list.append(2*n + idx[sp])
            val_list.append(1)
            col_list.append("rgba(46,204,113,0.4)")

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            label=all_labels, pad=20, thickness=18,
            color=(["rgba(52,152,219,0.8)"] * n +
                   ["rgba(231,76,60,0.8)"] * n +
                   ["rgba(46,204,113,0.8)"] * n),
            line=dict(color="white", width=0.5)
        ),
        link=dict(source=src_list, target=tgt_list,
                  value=val_list, color=col_list)
    ))
    fig.update_layout(
        title_text="Keystone Species Alluvial Diagram (BC ↔ SCC Bridge ↔ CI)<br>"
                   "<sup>파랑=BC, 빨강=SCC Bridge, 초록=CI</sup>",
        font_size=11, height=600
    )
    path = f"{FIGURES}/7-3_alluvial.html"
    fig.write_html(path)
    print(f"Saved {path}")


# ── 7-4. Cascade Heatmap ─────────────────────────────────────────
def plot_cascade_heatmap(G: nx.DiGraph, sim_results: dict):
    all_nodes = sorted(G.nodes())
    tl = nx.get_node_attributes(G, "trophic_level")
    all_nodes_sorted = sorted(all_nodes, key=lambda n: tl.get(n, 0))

    scenarios = {
        "BC Targeted":   sim_results["bc"]["waves"],
        "CI Targeted":   sim_results["ci"]["waves"],
        "Random (run1)": sim_results["random"][0],
    }
    fig, axes = plt.subplots(1, 3, figsize=(22, 13))

    cmap = matplotlib.colors.ListedColormap(["#c0392b", "#27ae60"])
    bounds = [0, 0.5, 1]
    norm   = matplotlib.colors.BoundaryNorm(bounds, cmap.N)

    for ax, (name, waves) in zip(axes, scenarios.items()):
        n_waves = len(waves)
        alive_at = {sp: n_waves for sp in all_nodes}
        for t, w in enumerate(waves):
            for sp in w["removed_this_wave"]:
                if sp in alive_at:
                    alive_at[sp] = min(alive_at[sp], t)

        matrix = np.ones((len(all_nodes_sorted), n_waves + 1))
        for i, sp in enumerate(all_nodes_sorted):
            t_gone = alive_at[sp]
            matrix[i, t_gone:] = 0

        im = ax.imshow(matrix, aspect="auto", cmap=cmap, norm=norm,
                       interpolation="nearest")
        ax.set_yticks(range(len(all_nodes_sorted)))
        ax.set_yticklabels(all_nodes_sorted, fontsize=6.5)
        ax.set_xlabel("Wave (제거 단계)", fontsize=9)
        ax.set_title(f"{name}", fontsize=11, fontweight="bold", pad=8)

        # trophic level 구분선
        prev_tl = tl.get(all_nodes_sorted[0], 0)
        for i, sp in enumerate(all_nodes_sorted[1:], 1):
            cur_tl = tl.get(sp, 0)
            if cur_tl != prev_tl:
                ax.axhline(i - 0.5, color="white", lw=1.2, alpha=0.8)
                ax.text(n_waves * 0.02, i - 0.7,
                        f"TL{cur_tl}", fontsize=6, color="white", alpha=0.7)
            prev_tl = cur_tl

    red_patch   = mpatches.Patch(color="#c0392b", label="Extinction")
    green_patch = mpatches.Patch(color="#27ae60", label="생존")
    fig.legend(handles=[green_patch, red_patch], loc="lower right", fontsize=10,
               framealpha=0.8)
    plt.suptitle("Co-extinction Cascade Heatmap\n(행=species, 열=제거 wave, y축 정렬=trophic level)",
                 fontsize=13, y=1.01)
    plt.tight_layout()
    path = f"{FIGURES}/7-4_cascade_heatmap.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {path}")


# ── 7-5. Robustness Curve ────────────────────────────────────────
def plot_robustness(G: nx.DiGraph, sim_results: dict):
    from src.simulation import build_robustness_curve
    total = G.number_of_nodes()
    fig, ax = plt.subplots(figsize=(8, 5))

    # Random
    xs_all, ys_all = [], []
    for waves in sim_results["random"]:
        x, y = build_robustness_curve(waves, total)
        xs_all.append(x); ys_all.append(y)
    max_len  = max(len(y) for y in ys_all)
    ys_pad   = [y + [y[-1]] * (max_len - len(y)) for y in ys_all]
    xs_pad   = [x + [x[-1]] * (max_len - len(x)) for x in xs_all]
    y_mean   = np.mean(ys_pad, axis=0)
    y_std    = np.std(ys_pad,  axis=0)
    ax.plot(xs_pad[0], y_mean, "k-", label="Random (평균±σ)", lw=2)
    ax.fill_between(xs_pad[0], y_mean - y_std, y_mean + y_std,
                    color="gray", alpha=0.25)

    for label, key, color in [("BC Targeted", "bc", "#2980b9"),
                               ("CI Targeted", "ci", "#e74c3c")]:
        x, y = build_robustness_curve(sim_results[key]["waves"], total)
        ax.plot(x, y, color=color, label=label, lw=2.2)

    ax.set_xlabel("Proportion of Removed Species")
    ax.set_ylabel("Proportion of Surviving Species")
    ax.set_title("Robustness Curve — Co-extinction Cascade")
    ax.legend(fontsize=10)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    path = f"{FIGURES}/7-5_robustness.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {path}")


# ── 7-6. 네트워크 붕괴 애니메이션 ────────────────────────────────
def plot_animation(G: nx.DiGraph, sim_results: dict):
    waves  = sim_results["bc"]["waves"]
    total  = G.number_of_nodes()
    tl     = nx.get_node_attributes(G, "trophic_level")
    pos    = nx.spring_layout(G, seed=42, k=1.2)
    nodes  = list(G.nodes())
    edges  = list(G.edges())

    node_x = [pos[n][0] for n in nodes]
    node_y = [tl.get(n, 0) + np.random.default_rng(hash(n) % 2**31).uniform(-0.1, 0.1) for n in nodes]
    edge_x, edge_y = [], []
    for u, v in edges:
        edge_x += [pos[u][0], pos[v][0], None]
        edge_y += [tl.get(u, 0), tl.get(v, 0), None]

    alive_over_time = []
    alive = set(nodes)
    alive_over_time.append(set(alive))
    for w in waves:
        for sp in w["removed_this_wave"]:
            alive.discard(sp)
        alive_over_time.append(set(alive))

    frames = []
    for t, alive_set in enumerate(alive_over_time):
        colors = ["#27ae60" if n in alive_set else "#c0392b" for n in nodes]
        sizes  = [14 if n in alive_set else 7 for n in nodes]
        frames.append(go.Frame(
            data=[
                go.Scatter(x=edge_x, y=edge_y, mode="lines",
                           line=dict(color="lightgray", width=0.5), hoverinfo="none"),
                go.Scatter(x=node_x, y=node_y, mode="markers+text",
                           text=nodes, textposition="top center",
                           textfont=dict(size=7),
                           marker=dict(color=colors, size=sizes,
                                       line=dict(color="white", width=0.5)),
                           hovertext=nodes, hoverinfo="text")
            ],
            name=str(t),
            layout=go.Layout(title_text=f"Wave {t} — Survive: {len(alive_set)}/{total}species")
        ))

    fig = go.Figure(
        data=frames[0].data,
        layout=go.Layout(
            title="BC-targeted Co-extinction Cascade",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=True, zeroline=False, title="Trophic Level",
                       tickvals=[0,1,2,3,4],
                       ticktext=["TL0 Basal","TL1 Primary","TL2 Secondary",
                                 "TL3 Meso","TL4 Top"]),
            plot_bgcolor="#1a1a2e", paper_bgcolor="#1a1a2e",
            font=dict(color="white"),
            updatemenus=[dict(type="buttons", showactive=False, x=0.1, y=0,
                              buttons=[
                                  dict(label="▶ Play", method="animate",
                                       args=[None, {"frame":{"duration":700},
                                                    "transition":{"duration":300}}]),
                                  dict(label="⏸ Pause", method="animate",
                                       args=[[None], {"frame":{"duration":0},
                                                      "mode":"immediate"}])
                              ])],
            sliders=[dict(
                steps=[dict(method="animate", args=[[str(t)]],
                            label=f"W{t}") for t in range(len(frames))],
                currentvalue={"prefix": "Wave: ", "font": {"color": "white"}},
                bgcolor="#333", activebgcolor="#666"
            )]
        ),
        frames=frames
    )
    path = f"{FIGURES}/7-6_animation.html"
    fig.write_html(path)
    print(f"Saved {path}")


def plot_method_comparison(G: nx.DiGraph, bc_df: pd.DataFrame,
                           ci_df: pd.DataFrame, bridges_df: pd.DataFrame,
                           n_timing: int = 50):
    """
    핵심species 식별 방법 비교 — 2개 패널
      (A) 런타임 bar chart (복잡도 주석 포함)
      (B) 평가 지표 grouped bar (SE / FSR×100 / R50 / LCL×100)
    """
    import time, statistics

    # ── 런타임 측정 ────────────────────────────────────────────────
    def _measure(fn, n=n_timing):
        ts = []
        for _ in range(n):
            t0 = time.perf_counter()
            fn()
            ts.append((time.perf_counter() - t0) * 1000)
        return statistics.mean(ts)

    from src.scc import run_scc_analysis as _run_scc
    from src.ci import compute_ci as _compute_ci
    rt_bc  = _measure(lambda: nx.betweenness_centrality(G.to_undirected(), normalized=True))
    rt_scc = _measure(lambda: _run_scc(G))
    rt_ci  = _measure(lambda: _compute_ci(G, l=2))

    # ── 평가 지표 ──────────────────────────────────────────────────
    from src.metrics import compute_metrics
    bc_order  = list(bc_df["species"])
    ci_order  = list(ci_df["species"])
    scc_order = list(bridges_df["species"]) + [
        n for n in G.nodes() if n not in set(bridges_df["species"])
    ]
    m_bc  = compute_metrics(G, bc_order,  max_removals=5, label="BC")
    m_ci  = compute_metrics(G, ci_order,  max_removals=5, label="CI")
    m_scc = compute_metrics(G, scc_order, max_removals=5, label="SCC Bridge")

    # ── 그림 ──────────────────────────────────────────────────────
    fig, (ax_rt, ax_met) = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("핵심species 식별 방법론 비교  (BC / SCC Bridge / CI)",
                 fontsize=13, fontweight="bold")

    COL = {"BC": "#3498db", "SCC Bridge": "#2ecc71", "CI": "#e74c3c"}

    # ── (A) 런타임 ─────────────────────────────────────────────────
    rt_labels  = ["SCC Bridge", "BC", "CI"]
    rt_vals    = [rt_scc, rt_bc, rt_ci]
    rt_cplx    = ["O(V+E)", "O(V·E)", "O(V·k²)"]
    rt_colors  = [COL[l] for l in rt_labels]

    bars = ax_rt.barh(rt_labels, rt_vals, color=rt_colors,
                      height=0.5, edgecolor="white", linewidth=0.5)
    for bar, v, cplx in zip(bars, rt_vals, rt_cplx):
        ax_rt.text(v + max(rt_vals) * 0.02,
                   bar.get_y() + bar.get_height() / 2,
                   f"{v:.2f} ms  [{cplx}]", va="center", fontsize=9)

    ax_rt.set_xlabel(f"평균 실행 시간 (ms,  {n_timing}회 평균)", fontsize=9)
    ax_rt.set_title("(A) 런타임 비교", fontsize=11)
    ax_rt.set_xlim(0, max(rt_vals) * 1.45)
    ax_rt.invert_yaxis()
    ax_rt.grid(axis="x", alpha=0.3)

    # ── (B) 평가 지표 grouped bar ──────────────────────────────────
    # FSR, LCL × 100 → % 단위
    se_vals  = [m_bc["SE"],          m_ci["SE"],          m_scc["SE"]]
    fsr_vals = [m_bc["FSR"] * 100,   m_ci["FSR"] * 100,   m_scc["FSR"] * 100]
    r50_vals = [m_bc["R50"] or 0,    m_ci["R50"] or 0,    m_scc["R50"] or 0]
    lcl_vals = [m_bc["LCL"] * 100,   m_ci["LCL"] * 100,   m_scc["LCL"] * 100]

    met_labels = ["SE\n(species)", "FSR\n(%)", "R50\n(Removals)", "LCL\n(%)"]
    groups     = [se_vals, fsr_vals, r50_vals, lcl_vals]
    met_colors = ["#e74c3c", "#3498db", "#f39c12", "#9b59b6"]

    x = np.arange(3)
    w = 0.18
    offsets = np.array([-1.5, 0, 1.5, 3.0]) * w

    for i, (name, vals_g, col) in enumerate(zip(met_labels, groups, met_colors)):
        bars_m = ax_met.bar(x + offsets[i], vals_g, width=w, label=name,
                            color=col, alpha=0.85, edgecolor="white", linewidth=0.4)
        for bar, v in zip(bars_m, vals_g):
            if v > 0:
                ax_met.text(bar.get_x() + bar.get_width() / 2,
                            bar.get_height() + 0.5,
                            f"{v:.0f}", ha="center", va="bottom", fontsize=8)

    ax_met.set_xticks(x)
    ax_met.set_xticklabels(["BC", "CI", "SCC Bridge"], fontsize=10)
    ax_met.set_ylabel("지표 값", fontsize=9)
    ax_met.set_title("(B) 평가 지표 비교\n(top-5 제거, threshold=0.7  |  FSR·LCL: ×100%)", fontsize=10)
    ax_met.legend(fontsize=8, ncol=2, loc="upper right")
    ax_met.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    path = f"{FIGURES}/7-8_method_comparison.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {path}")


def run_all(G, k_sccs, t_sccs, bridges_df, bc_df, ci_df, comparison, sim_results):
    plot_scc_network(G, k_sccs, t_sccs, bridges_df)
    plot_scc_summary(G, k_sccs, bridges_df)
    plot_comparison_heatmap(comparison["heatmap"])
    plot_sankey(bridges_df, bc_df, ci_df)
    plot_cascade_heatmap(G, sim_results)
    plot_robustness(G, sim_results)
    plot_animation(G, sim_results)

    plot_method_comparison(G, bc_df, ci_df, bridges_df)

    print("\nAll visualizations saved to outputs/figures/")
