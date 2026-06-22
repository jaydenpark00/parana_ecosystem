"""
Export simulation data → self-contained Cytoscape.js HTML
3개 시나리오(BC / CI_l2 / Kosaraju fragmentation) 동기화 비교
"""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def build_html(G, sim_results, bridges_order, bc_order, ci_order, out_path):
    import networkx as nx

    tl = nx.get_node_attributes(G, "trophic_level")
    nodes = list(G.nodes())
    edges = list(G.edges())

    # ── Cytoscape elements ─────────────────────────────────────────
    cy_nodes = []
    for n in nodes:
        cy_nodes.append({
            "data": {"id": n, "label": n, "tl": tl.get(n, 0)},
        })

    cy_edges = []
    for i, (s, t) in enumerate(edges):
        cy_edges.append({"data": {"id": f"e{i}", "source": s, "target": t}})

    # ── Wave 데이터 (각 시나리오별 wave → 멸종 종 누적) ──────────
    def waves_to_extinction_map(waves):
        # 1-based: Wave 1 = 첫 번째 제거, Wave 5 = 다섯 번째 제거
        result = {}
        for wave_idx, w in enumerate(waves):
            for sp in w["removed_this_wave"]:
                if sp not in result:
                    result[sp] = wave_idx + 1
        return result

    scenarios = {
        "BC Targeted":  waves_to_extinction_map(sim_results["bc"]["waves"]),
        "CI Targeted":  waves_to_extinction_map(sim_results["ci"]["waves"]),
        "Kosaraju Frag": waves_to_extinction_map(sim_results["scc"]["waves"]),
    }

    max_wave = max(
        max((v for v in s.values()), default=1)
        for s in scenarios.values()
    )

    cy_elements = json.dumps(cy_nodes + cy_edges)
    scenarios_json = json.dumps(scenarios)

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>파라나 강 먹이그물 Co-extinction 시뮬레이터</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Malgun Gothic',sans-serif;background:#0f0f1a;color:#e0e0e0;height:100vh;display:flex;flex-direction:column}}
header{{padding:10px 20px;background:#16162a;border-bottom:1px solid #2a2a4a;display:flex;align-items:center;justify-content:space-between}}
header h1{{font-size:15px;font-weight:500;color:#c8c8ff}}
.controls{{display:flex;align-items:center;gap:14px;flex-wrap:wrap}}
.controls label{{font-size:12px;color:#aaa}}
#wave-slider{{width:220px;accent-color:#7c6ff7}}
#wave-val{{font-size:13px;font-weight:600;color:#7c6ff7;min-width:60px}}
.btn{{padding:5px 14px;border:1px solid #3a3a6a;border-radius:5px;background:#1e1e3a;color:#c8c8ff;font-size:12px;cursor:pointer;transition:.15s}}
.btn:hover{{background:#2e2e5a}}
.btn.active{{background:#7c6ff7;border-color:#7c6ff7;color:#fff}}
.panels{{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;flex:1;padding:8px;min-height:0}}
.panel{{display:flex;flex-direction:column;background:#13132a;border-radius:8px;border:1px solid #2a2a4a;overflow:hidden}}
.panel-title{{padding:6px 12px;font-size:12px;font-weight:600;display:flex;justify-content:space-between;align-items:center}}
.panel-title.bc{{background:#1a2540;color:#60a5fa}}
.panel-title.ci{{background:#2a1a2a;color:#f472b6}}
.panel-title.scc{{background:#1a2a1a;color:#4ade80}}
.stat{{font-size:11px;opacity:.8}}
.cy-container{{flex:1;min-height:0}}
footer{{padding:6px 20px;background:#16162a;border-top:1px solid #2a2a4a;font-size:11px;color:#666;display:flex;gap:16px}}
.legend{{display:flex;align-items:center;gap:5px}}
.dot{{width:10px;height:10px;border-radius:50%}}
</style>
</head>
<body>

<header>
  <h1>파라나 강 먹이그물 WTECM Co-extinction 시뮬레이터 — 3가지 시나리오 비교</h1>
  <div class="controls">
    <label>Wave</label>
    <input type="range" id="wave-slider" min="0" max="{max_wave}" value="0" step="1">
    <span id="wave-val">초기 상태</span>
    <button class="btn" id="btn-play">▶ Play</button>
    <button class="btn" id="btn-reset">↺ Reset</button>
    <button class="btn" id="btn-final">최종 결과</button>
  </div>
</header>

<div class="panels">
  <div class="panel">
    <div class="panel-title bc">
      <span>BC Targeted</span>
      <span class="stat" id="stat-bc">40 / 40종 생존</span>
    </div>
    <div class="cy-container" id="cy-bc"></div>
  </div>
  <div class="panel">
    <div class="panel-title ci">
      <span>CI_l2 Targeted</span>
      <span class="stat" id="stat-ci">40 / 40종 생존</span>
    </div>
    <div class="cy-container" id="cy-ci"></div>
  </div>
  <div class="panel">
    <div class="panel-title scc">
      <span>Kosaraju Frag Targeted</span>
      <span class="stat" id="stat-scc">40 / 40종 생존</span>
    </div>
    <div class="cy-container" id="cy-scc"></div>
  </div>
</div>

<footer>
  <div class="legend"><div class="dot" style="background:#4ade80"></div> 생존</div>
  <div class="legend"><div class="dot" style="background:#ef4444"></div> 1차 멸종 (직접 제거)</div>
  <div class="legend"><div class="dot" style="background:#f97316"></div> 연쇄 멸종</div>
  <div class="legend"><div class="dot" style="background:#6b7280"></div> 이전 멸종</div>
  <span style="margin-left:auto">노드 크기 = in-degree | y축 = Trophic Level</span>
</footer>

<script>
const ELEMENTS = {cy_elements};
const SCENARIOS = {scenarios_json};
const MAX_WAVE = {max_wave};
const TOTAL = {len(nodes)};

const TL_LABELS = {{0:'Basal',1:'Primary',2:'Secondary',3:'Mesopredator',4:'Top predator'}};

function makeLayout(cy) {{
  const w = cy.container().offsetWidth;
  const h = cy.container().offsetHeight;
  const tls = [0,1,2,3,4];
  const groups = {{}};
  cy.nodes().forEach(n => {{
    const t = n.data('tl');
    if (!groups[t]) groups[t] = [];
    groups[t].push(n);
  }});
  const pos = {{}};
  tls.forEach(t => {{
    const group = groups[t] || [];
    const y = h - 40 - (t / 4) * (h - 80);
    group.forEach((n, i) => {{
      const x = (i + 1) / (group.length + 1) * w;
      pos[n.id()] = {{ x, y }};
    }});
  }});
  return pos;
}}

function initCy(containerId, scenario) {{
  const cy = cytoscape({{
    container: document.getElementById(containerId),
    elements: JSON.parse(JSON.stringify(ELEMENTS)),
    style: [
      {{
        selector: 'node',
        style: {{
          'label': 'data(label)',
          'font-size': '8px',
          'color': '#ffffff',
          'text-valign': 'bottom',
          'text-margin-y': '4px',
          'text-outline-width': '1px',
          'text-outline-color': '#000',
          'background-color': '#4ade80',
          'border-width': '1px',
          'border-color': '#ffffff30',
          'width': 'mapData(tl, 0, 4, 10, 20)',
          'height': 'mapData(tl, 0, 4, 10, 20)',
          'transition-property': 'background-color, opacity, width, height',
          'transition-duration': '400ms',
        }}
      }},
      {{
        selector: 'edge',
        style: {{
          'width': 0.6,
          'line-color': '#ffffff20',
          'target-arrow-color': '#ffffff20',
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          'arrow-scale': 0.5,
          'transition-property': 'opacity',
          'transition-duration': '400ms',
        }}
      }},
      {{
        selector: '.extinct-now',
        style: {{
          'background-color': '#ef4444',
          'border-color': '#ff0000',
          'border-width': '2px',
          'opacity': 0.9,
        }}
      }},
      {{
        selector: '.extinct-cascade',
        style: {{
          'background-color': '#f97316',
          'opacity': 0.85,
        }}
      }},
      {{
        selector: '.extinct-old',
        style: {{
          'background-color': '#374151',
          'opacity': 0.35,
        }}
      }},
      {{
        selector: '.extinct-old edge',
        style: {{ 'opacity': 0.05 }}
      }},
    ],
    layout: {{ name: 'preset', positions: () => {{}} }},
    userZoomingEnabled: true,
    userPanningEnabled: true,
    boxSelectionEnabled: false,
  }});
  cy._scenario = scenario;
  cy._containerId = containerId;
  return cy;
}}

const cyBC  = initCy('cy-bc',  SCENARIOS['BC Targeted']);
const cyCI  = initCy('cy-ci',  SCENARIOS['CI Targeted']);
const cySCC = initCy('cy-scc', SCENARIOS['Kosaraju Frag']);

function applyLayout(cy) {{
  const pos = makeLayout(cy);
  cy.nodes().forEach(n => {{
    if (pos[n.id()]) n.position(pos[n.id()]);
  }});
  cy.fit(cy.nodes(), 30);
}}

[cyBC, cyCI, cySCC].forEach(applyLayout);

function updateWave(wave, finalMode) {{
  const pairs = [
    [cyBC,  'stat-bc',  SCENARIOS['BC Targeted']],
    [cyCI,  'stat-ci',  SCENARIOS['CI Targeted']],
    [cySCC, 'stat-scc', SCENARIOS['Kosaraju Frag']],
  ];
  pairs.forEach(([cy, statId, scenario]) => {{
    let alive = 0;
    cy.nodes().forEach(n => {{
      const id = n.id();
      const extWave = scenario[id];
      n.removeClass('extinct-now extinct-cascade extinct-old');
      if (extWave === undefined) {{
        alive++;
      }} else if (finalMode || extWave < wave) {{
        n.addClass('extinct-old');
      }} else if (extWave === wave && wave > 0) {{
        n.addClass('extinct-now');
      }}
    }});
    cy.edges().forEach(e => {{
      const s = scenario[e.data('source')];
      const t = scenario[e.data('target')];
      const threshold = finalMode ? Infinity : wave;
      const dead = (s !== undefined && s <= threshold) || (t !== undefined && t <= threshold);
      e.style('opacity', dead ? 0.04 : 0.25);
    }});
    document.getElementById(statId).textContent = alive + ' / ' + TOTAL + '종 생존';
  }});
  if (finalMode) {{
    document.getElementById('wave-val').textContent = '최종 결과';
  }} else {{
    document.getElementById('wave-val').textContent = wave === 0 ? '초기 상태' : 'Wave ' + wave;
  }}
}};

document.getElementById('wave-slider').addEventListener('input', e => {{
  updateWave(+e.target.value, false);
}});

let playing = false;
let playInterval = null;
document.getElementById('btn-play').addEventListener('click', () => {{
  if (playing) {{
    clearInterval(playInterval);
    playing = false;
    document.getElementById('btn-play').textContent = '▶ Play';
  }} else {{
    playing = true;
    document.getElementById('btn-play').textContent = '⏸ Pause';
    playInterval = setInterval(() => {{
      const slider = document.getElementById('wave-slider');
      let v = +slider.value + 1;
      if (v > MAX_WAVE) {{ v = 0; }}
      slider.value = v;
      updateWave(v);
    }}, 700);
  }}
}});

document.getElementById('btn-reset').addEventListener('click', () => {{
  clearInterval(playInterval);
  playing = false;
  document.getElementById('btn-play').textContent = '▶ Play';
  document.getElementById('wave-slider').value = 0;
  updateWave(0, false);
}});

document.getElementById('btn-final').addEventListener('click', () => {{
  clearInterval(playInterval);
  playing = false;
  document.getElementById('btn-play').textContent = '▶ Play';
  document.getElementById('wave-slider').value = MAX_WAVE;
  updateWave(MAX_WAVE, true);
}});

updateWave(0, false);
</script>
</body>
</html>"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved {out_path}")


if __name__ == "__main__":
    import random
    random.seed(42)
    from src.graph import build_graph_from_matrix
    from src.simulation import cascade_wtecm
    from src.wtecm import build_analysis_bundle

    bundle = build_analysis_bundle("data/FW_001.csv", theta=0.7)
    G = build_graph_from_matrix("data/FW_001.csv", algorithm=False)

    bc_order = bundle["algo_rankings"]["BC"]
    ci_order = bundle["algo_rankings"]["CI_l2"]
    scc_order = bundle["algo_rankings"]["Kosaraju"]

    sim_results = {
        "bc":  cascade_wtecm(bundle["matrix"], bc_order,  max_removals=5),
        "ci":  cascade_wtecm(bundle["matrix"], ci_order,  max_removals=5),
        "scc": cascade_wtecm(bundle["matrix"], scc_order, max_removals=5),
    }

    out = "outputs/v5_2/cascade_compare.html"
    os.makedirs("outputs/v5_2", exist_ok=True)
    build_html(G, sim_results, scc_order, bc_order, ci_order, out)
