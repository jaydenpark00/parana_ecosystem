"""Export WTECM method comparison as a self-contained HTML report."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.wtecm import PREY_NAMES, build_analysis_bundle


def build_html(bundle: dict, out_path: str, theta: float = 0.7):
    rows = []
    for name, result in bundle["algo_results"].items():
        rows.append({
            "Algorithm": name,
            "Top1": result["top1_name"],
            "RefRank": round(float(result["top1_ref_rank"]), 2),
            "Top1Sec": result["top1_sec"],
            "Top5Sec": result["top5_sec"],
            "AUC": round(result["auc"], 4),
            "AUCGap": result["auc_gap"],
            "R50": round(result["r50"], 4),
            "Spearman": result["spearman"],
            "Top5Overlap": result["top5_overlap"],
        })

    rank_rows = []
    ref_order = list(bundle["ref_df"]["node"])
    for rank in range(10):
        row = {"Rank": rank + 1, "Reference": PREY_NAMES[ref_order[rank]]}
        for name, ranking in bundle["algo_rankings"].items():
            row[name] = PREY_NAMES[ranking[rank]]
        rank_rows.append(row)

    rows_json = json.dumps(rows, ensure_ascii=False)
    ranks_json = json.dumps(rank_rows, ensure_ascii=False)
    ref_auc = bundle["ref_auc"]
    ref_r50 = bundle["ref_r50"]
    rand = bundle["random_result"]

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>WTECM Method Comparison</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;padding:24px;background:#f7f7f5;color:#1f2933;font-family:'Malgun Gothic','Segoe UI',sans-serif}}
h1{{font-size:20px;margin:0 0 4px}}
.sub{{color:#667085;font-size:13px;margin-bottom:20px}}
.grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:20px}}
.card{{background:white;border:1px solid #d9dee5;border-radius:8px;padding:12px}}
.label{{font-size:11px;color:#667085;text-transform:uppercase;letter-spacing:.04em}}
.value{{font-size:22px;font-weight:700;margin-top:4px}}
table{{width:100%;border-collapse:collapse;background:white;border:1px solid #d9dee5;border-radius:8px;overflow:hidden;margin-bottom:20px}}
th,td{{border-bottom:1px solid #e5e7eb;padding:8px 10px;font-size:12px;text-align:left}}
th{{background:#eef2f6;color:#344054;font-weight:700}}
tr:last-child td{{border-bottom:none}}
.num{{font-family:'Consolas','Courier New',monospace;text-align:right}}
.good{{color:#0f6e56;font-weight:700}}
.bad{{color:#993c1d;font-weight:700}}
</style>
</head>
<body>
<h1>WTECM Method Comparison</h1>
<div class="sub">theta={theta} | Reference AUC={ref_auc:.4f}, R50={ref_r50:.4f} | Random AUC={rand['auc_mean']:.4f}+/-{rand['auc_std']:.4f}</div>

<div class="grid" id="cards"></div>

<h2>Performance Summary</h2>
<table id="perf"></table>

<h2>Top-10 Ranking</h2>
<table id="rank"></table>

<script>
const ROWS = {rows_json};
const RANKS = {ranks_json};

function td(v, cls='') {{ return `<td class="${{cls}}">${{v}}</td>`; }}
function th(v) {{ return `<th>${{v}}</th>`; }}

const cards = document.getElementById('cards');
ROWS.forEach(r => {{
  cards.innerHTML += `
    <div class="card">
      <div class="label">${{r.Algorithm}}</div>
      <div class="value">${{r.Top1Sec}}</div>
      <div class="label">Top-1 secondary extinction</div>
      <div style="font-size:12px;margin-top:8px">${{r.Top1}}</div>
      <div style="font-size:11px;color:#667085">Ref# ${{r.RefRank}}</div>
    </div>`;
}});

const perf = document.getElementById('perf');
perf.innerHTML = `<thead><tr>
  ${{['Algorithm','Top1','Ref#','Sec1','Sec5','AUC','Gap','R50','rho','Top5'].map(th).join('')}}
</tr></thead><tbody>` + ROWS.map(r => `
  <tr>
    ${{td(r.Algorithm)}}
    ${{td(r.Top1)}}
    ${{td(r.RefRank, 'num')}}
    ${{td(r.Top1Sec, 'num')}}
    ${{td(r.Top5Sec, 'num')}}
    ${{td(r.AUC, 'num')}}
    ${{td(r.AUCGap, 'num ' + (r.AUCGap <= 0 ? 'good' : 'bad'))}}
    ${{td(r.R50, 'num')}}
    ${{td(r.Spearman, 'num')}}
    ${{td(r.Top5Overlap, 'num')}}
  </tr>`).join('') + `</tbody>`;

const rank = document.getElementById('rank');
const rankHeaders = Object.keys(RANKS[0]);
rank.innerHTML = `<thead><tr>${{rankHeaders.map(th).join('')}}</tr></thead><tbody>` +
  RANKS.map(row => `<tr>${{rankHeaders.map(h => td(row[h], h === 'Rank' ? 'num' : '')).join('')}}</tr>`).join('') +
  `</tbody>`;
</script>
</body>
</html>"""

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved {out_path}")


if __name__ == "__main__":
    bundle = build_analysis_bundle("data/FW_001.csv", theta=0.7)
    build_html(bundle, "outputs/v5_2/method_comparison.html", theta=0.7)
