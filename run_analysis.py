"""Main WTECM analysis pipeline for the Parana floodplain food web."""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import matplotlib
matplotlib.use("Agg")

from src.visualization import run_wtecm_all
from src.metrics import run_wtecm_metrics
from src.wtecm import (
    N,
    N_PRED,
    PREY_NAMES,
    build_analysis_bundle,
    save_csv_outputs,
)


OUTDIR = "outputs/v5_2"


def print_reference_top5(bundle: dict):
    print("\nReference Top-5")
    for _, row in bundle["ref_df"].head(5).iterrows():
        print(
            f"  rank={row['ref_rank']:.1f}: {row['name']} "
            f"(sec={int(row['secondary_extinction'])}, "
            f"depth={int(row['cascade_depth'])})"
        )


def print_algorithm_summary(bundle: dict):
    print("\nAlgorithm performance")
    for name, result in bundle["algo_results"].items():
        print(
            f"  {name:<10} "
            f"AUC={result['auc']:.4f} Gap={result['auc_gap']:+.4f} "
            f"R50={result['r50']:.3f} rho={result['spearman']:.3f} "
            f"Top5={result['top5_overlap']} "
            f"Top1Sec={result['top1_sec']} "
            f"(Ref#{result['top1_ref_rank']:.1f})"
        )


def print_final_table(bundle: dict):
    rand = bundle["random_result"]
    print("\n" + "=" * 88)
    print("Final performance summary")
    print("=" * 88)
    header = (
        f"  {'Algorithm':<10} {'Top-1 Species':<30} "
        f"{'Ref#':>6} {'Sec1':>5} {'Sec5':>5} "
        f"{'AUC':>8} {'Gap':>8} {'R50':>7} {'rho':>7} {'Top5':>5}"
    )
    print(header)
    print("  " + "-" * 86)
    for name, result in bundle["algo_results"].items():
        print(
            f"  {name:<10} {result['top1_name']:<30} "
            f"{result['top1_ref_rank']:>6.1f} "
            f"{result['top1_sec']:>5} "
            f"{result['top5_sec']:>5} "
            f"{result['auc']:>8.4f} "
            f"{result['auc_gap']:>+8.4f} "
            f"{result['r50']:>7.3f} "
            f"{result['spearman']:>7.4f} "
            f"{result['top5_overlap']:>5}"
        )
    print(
        f"  {'Random':<10} {'100-run mean':<30} "
        f"{'-':>6} "
        f"{rand['top1_sec_mean']:>5.1f} "
        f"{rand['top5_sec_mean']:>5.1f} "
        f"{rand['auc_mean']:>8.4f} "
        f"{rand['auc_mean'] - bundle['ref_auc']:>+8.4f} "
        f"{rand['r50_mean']:>7.3f} "
        f"{'-':>7} {'-':>5}"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/FW_001.csv", help="Raw 40x36 diet matrix")
    parser.add_argument("--theta", type=float, default=0.7, help="WTECM threshold")
    parser.add_argument("--outdir", default=OUTDIR, help="CSV and figure output directory")
    parser.add_argument("--random-repeats", type=int, default=100,
                        help="Random baseline repeat count")
    args = parser.parse_args()

    sensitivity_thetas = [round(t * 0.1, 1) for t in range(1, 11)]

    print("=" * 70)
    print(f"Parana floodplain WTECM analysis [theta={args.theta}]")
    print("=" * 70)
    print(f"  data: {args.data}")
    print(f"  raw matrix shape: ({N}, {N_PRED})")
    print(f"  species: {len(PREY_NAMES)}")

    bundle = build_analysis_bundle(
        data_path=args.data,
        theta=args.theta,
        sensitivity_thetas=sensitivity_thetas,
        random_repeats=args.random_repeats,
    )

    graph_wtecm = bundle["graph_wtecm"]
    graph_alg = bundle["graph_alg"]
    print("\nData loaded")
    print(f"  G_wtecm edges (self-loop included): {graph_wtecm.number_of_edges()}")
    print(f"  G_alg edges (self-loop removed):    {graph_alg.number_of_edges()}")
    self_loops = sum(1 for source, target in graph_wtecm.edges() if source == target)
    print(f"  self-loops:                         {self_loops}")
    print(f"  Reference AUC={bundle['ref_auc']:.4f}, R50={bundle['ref_r50']:.4f}")

    print_reference_top5(bundle)
    print_algorithm_summary(bundle)

    metrics_df = run_wtecm_metrics(
        bundle["algo_rankings"],
        bundle["matrix"],
        threshold=args.theta,
        k=5,
    )

    print("\nSaving CSV outputs")
    save_csv_outputs(
        outdir=args.outdir,
        theta=args.theta,
        ref_df=bundle["ref_df"],
        ref_auc=bundle["ref_auc"],
        ref_r50=bundle["ref_r50"],
        algo_rankings=bundle["algo_rankings"],
        algo_results=bundle["algo_results"],
        random_result=bundle["random_result"],
        sensitivity_df=bundle["sensitivity_df"],
    )
    metrics_df.to_csv(
        os.path.join(args.outdir, "metrics_wtecm.csv"),
        encoding="utf-8-sig",
    )

    print("\nCreating figures")
    run_wtecm_all(bundle, theta=args.theta, outdir=args.outdir)

    print_final_table(bundle)

    print("\nSaved files")
    for filename in sorted(os.listdir(args.outdir)):
        print(f"  {args.outdir}/{filename}")


if __name__ == "__main__":
    main()
