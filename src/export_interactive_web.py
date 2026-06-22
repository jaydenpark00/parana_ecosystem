"""
인터랙티브 먹이그물 시뮬레이션 웹
outputs/figures/interactive_sim.html 생성
"""
import json, os, sys, random
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def collect_data(G):
    import networkx as nx
    from src.centrality import compute_bc
    from src.ci import compute_ci
    from src.scc import kosaraju, tarjan, bridge_nodes
    from src.simulation import cascade

    bc_df     = compute_bc(G)
    ci_df     = compute_ci(G, l=2)
    k_sccs    = kosaraju(G)
    t_sccs    = tarjan(G)
    bridges_df = bridge_nodes(G, k_sccs)

    k_map = {n: i for i, scc in enumerate(k_sccs) for n in scc}
    t_map = {n: i for i, scc in enumerate(t_sccs) for n in scc}
    tl    = nx.get_node_attributes(G, "trophic_level")

    bc_rank  = {r["species"]: (int(r["rank"]),  round(float(r["bc_score"]), 6))
                for _, r in bc_df.iterrows()}
    ci_rank  = {r["species"]: (int(r["rank"]),  int(r["ci_score"]))
                for _, r in ci_df.iterrows()}
    scc_rank = {r["species"]: (int(r["rank"]),  int(r["cross_edges"]))
                for _, r in bridges_df.iterrows()}

    nodes_out = []
    for n in G.nodes():
        br, bs = bc_rank.get(n, (None, None))
        cr, cs = ci_rank.get(n, (None, None))
        sr, se = scc_rank.get(n, (None, None))
        nodes_out.append({
            "id": n, "tl": tl.get(n, 0),
            "bc_rank": br, "bc_score": bs,
            "ci_rank": cr, "ci_score": cs,
            "scc_bridge_rank": sr, "cross_edges": se,
            "k_scc": k_map.get(n, -1),
            "t_scc": t_map.get(n, -1),
            "in_deg":  G.in_degree(n),
            "out_deg": G.out_degree(n),
            "predators": [p for p in G.predecessors(n)],
            "preys":     [p for p in G.successors(n)],
        })

    edges_out = [
        {"id": f"e{i}", "source": s, "target": t,
         "weight": round(d.get("weight", 0), 4)}
        for i, (s, t, d) in enumerate(G.edges(data=True))
    ]

    bc_order  = list(bc_df["species"])
    ci_order  = list(ci_df["species"])
    scc_order = list(bridges_df["species"]) + [
        n for n in G.nodes() if n not in set(bridges_df["species"])
    ]

    def waves_map(order):
        res = cascade(G, order, max_removals=5)
        return [{"removed": sorted(w["removed_this_wave"]), "n_alive": w["n_alive"]}
                for w in res["waves"]]

    return {
        "nodes":  nodes_out,
        "edges":  edges_out,
        "waves":  {"bc": waves_map(bc_order), "ci": waves_map(ci_order), "scc": waves_map(scc_order)},
        "top5":   {"bc": list(bc_df["species"].head(5)),
                   "ci": list(ci_df["species"].head(5)),
                   "scc": list(bridges_df["species"].head(5))},
        "total":  G.number_of_nodes(),
    }


def build_html(data, out_path):
    DATA_JSON = json.dumps(data, ensure_ascii=False)

    html = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>ECO-SIM ENGINE — 파라나 강 먹이그물</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
:root{
  /* surface scale — Cybernetic Synthesis */
  --bg:#141218;
  --surface:#1d1b20;
  --surface-high:#2b292f;
  --card:#211f24;
  --card-high:#36343a;

  /* text */
  --text:#e6e0e9;
  --text-variant:#cbc4d2;
  --muted:#948e9c;
  --muted-dim:#494551;

  /* borders */
  --border:#494551;
  --border-subtle:rgba(148,142,156,.2);

  /* accent — primary */
  --accent:#cfbcff;
  --accent-container:#6750a4;

  /* semantic */
  --tertiary:#e7c365;   /* bridge / gold */
  --error:#ffb4ab;      /* extinct direct */
  --error-container:#93000a;

  /* method colors */
  --bc-col:#cfbcff;     /* primary */
  --ci-col:#cdc0e9;     /* secondary */
  --scc-col:#00C853;    /* emerald */

  /* sim states */
  --alive:#00E5FF;
  --dead-direct:#ffb4ab;
  --dead-cascade:#f97316;
  --dead-old:#36343a;

  --font:'Inter',sans-serif;
  --mono:'JetBrains Mono',monospace;
  --r:4px; --r-md:6px; --r-lg:8px;
}
html,body{height:100%;overflow:hidden;background:var(--bg);color:var(--text);
  font-family:var(--font);font-size:14px;line-height:20px}

/* ══ TOP NAV ══════════════════════════════════════════════════════ */
#topnav{
  height:48px;background:var(--surface);border-bottom:1px solid var(--border);
  display:flex;align-items:center;padding:0 16px;flex-shrink:0;position:relative;z-index:10;
}
.logo{
  font-family:var(--mono);font-size:11px;font-weight:500;color:var(--accent);
  letter-spacing:.12em;white-space:nowrap;padding-right:20px;
  border-right:1px solid var(--border);margin-right:4px;
}
.nav-tabs{display:flex;height:100%}
.nav-tab{
  height:100%;padding:0 16px;font-size:12px;font-weight:700;letter-spacing:.08em;
  text-transform:uppercase;color:var(--muted);cursor:pointer;border:none;
  background:transparent;font-family:var(--font);
  display:flex;align-items:center;border-bottom:2px solid transparent;transition:.12s;
}
.nav-tab:hover{color:var(--text-variant)}
.nav-tab.active{color:var(--text);border-bottom-color:var(--accent)}
.nav-right{margin-left:auto;display:flex;align-items:center;gap:8px}
.search-box{
  display:flex;align-items:center;gap:6px;
  background:var(--card);border:1px solid var(--border);border-radius:var(--r);
  padding:4px 10px;width:200px;
}
.search-box input{
  background:transparent;border:none;outline:none;
  color:var(--text);font-size:12px;width:100%;font-family:var(--font);
}
.search-box input::placeholder{color:var(--muted-dim)}
.search-box:focus-within{border-color:var(--accent)}
.icon-btn{
  width:28px;height:28px;border-radius:var(--r);border:1px solid var(--border);
  background:var(--card);color:var(--muted);cursor:pointer;
  display:flex;align-items:center;justify-content:center;font-size:13px;transition:.12s;
}
.icon-btn:hover{color:var(--text);border-color:var(--muted)}

/* ══ BODY ══════════════════════════════════════════════════════════ */
#body{display:flex;height:calc(100vh - 48px - 48px)}

/* ══ LEFT SIDEBAR ══════════════════════════════════════════════════ */
#sidebar{
  width:60px;background:var(--surface);border-right:1px solid var(--border);
  display:flex;flex-direction:column;align-items:center;padding:12px 0;gap:4px;flex-shrink:0;
}
.sidebar-section{
  font-family:var(--mono);font-size:9px;font-weight:700;letter-spacing:.1em;
  color:var(--muted-dim);padding:8px 0 4px;width:100%;text-align:center;
}
.sidebar-label{font-family:var(--mono);font-size:8px;font-weight:700;letter-spacing:.08em;color:var(--muted-dim);margin-top:2px}
.side-btn{
  width:44px;height:44px;border-radius:var(--r-lg);border:1px solid transparent;
  background:transparent;color:var(--muted);cursor:pointer;
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;
  transition:.12s;font-size:17px;
}
.side-btn:hover{background:var(--card);color:var(--text-variant);border-color:var(--border)}
.side-btn.active{
  background:rgba(207,188,255,.08);color:var(--accent);
  border-color:rgba(207,188,255,.25);
}
.side-divider{width:28px;height:1px;background:var(--border);margin:4px 0}

/* ══ CENTER ════════════════════════════════════════════════════════ */
#center{flex:1;position:relative;overflow:hidden;display:flex;flex-direction:column}
#cy-main{flex:1;min-height:0}

/* trophic ruler */
#tl-ruler{
  position:absolute;left:68px;top:0;bottom:0;width:24px;
  display:flex;flex-direction:column;justify-content:space-between;
  padding:20px 0;pointer-events:none;z-index:4;
}
.tl-label{font-family:var(--mono);font-size:9px;font-weight:500;color:var(--muted-dim)}

/* floating panels — glassmorphism */
.float-panel{
  position:absolute;top:12px;left:12px;z-index:5;
  background:rgba(29,27,32,.75);backdrop-filter:blur(20px);
  border:1px solid var(--border);border-radius:var(--r-lg);
  padding:14px 16px;min-width:220px;
}
.float-title{
  font-family:var(--mono);font-size:9px;font-weight:700;letter-spacing:.12em;
  text-transform:uppercase;color:var(--muted);margin-bottom:12px;
}
.float-badge{
  position:absolute;top:12px;right:12px;z-index:5;
  background:rgba(0,200,83,.1);border:1px solid rgba(0,200,83,.3);
  border-radius:9999px;padding:4px 12px;
  font-family:var(--mono);font-size:9px;font-weight:700;letter-spacing:.08em;color:var(--scc-col);
  display:flex;align-items:center;gap:6px;
}
.float-badge .dot{width:6px;height:6px;border-radius:50%;background:var(--scc-col)}
.btn-row{display:flex;gap:6px;margin-bottom:8px}
.pill{
  padding:4px 12px;border-radius:var(--r);border:1px solid var(--border);
  background:transparent;color:var(--muted);font-size:12px;font-weight:700;
  letter-spacing:.04em;cursor:pointer;font-family:var(--font);transition:.12s;
}
.pill:hover{color:var(--text-variant);border-color:var(--muted)}
.pill.active{background:var(--accent-container);border-color:var(--accent);color:var(--accent)}
.pill-scc.active{background:rgba(0,200,83,.12);border-color:var(--scc-col);color:var(--scc-col)}
.pill-bc.active{background:rgba(207,188,255,.12);border-color:var(--bc-col);color:var(--bc-col)}
.pill-ci.active{background:rgba(205,192,233,.12);border-color:var(--ci-col);color:var(--ci-col)}
#scc-stat-text{font-family:var(--mono);font-size:10px;color:var(--muted);margin-top:4px}

/* sim panels */
#sim-container{display:none;flex:1;flex-direction:column;min-height:0}
#sim-panels{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;flex:1;padding:8px;min-height:0}
.sim-card{display:flex;flex-direction:column;background:var(--card);
  border:1px solid var(--border);border-radius:var(--r-lg);overflow:hidden}
.sim-header{
  padding:8px 12px;font-size:12px;font-weight:700;letter-spacing:.06em;
  display:flex;justify-content:space-between;align-items:center;
  border-bottom:1px solid var(--border);
}
.sim-header.bc{color:var(--bc-col)}
.sim-header.ci{color:var(--ci-col)}
.sim-header.scc{color:var(--scc-col)}
.sim-stat{font-family:var(--mono);font-size:10px;font-weight:400;color:var(--muted)}
.cy-sim{flex:1;min-height:0}

/* ══ RIGHT PANEL ═══════════════════════════════════════════════════ */
#right-panel{
  width:320px;background:var(--surface);border-left:1px solid var(--border);
  display:flex;flex-direction:column;flex-shrink:0;overflow:hidden;
}
.rp-tabs{display:flex;border-bottom:1px solid var(--border)}
.rp-tab{
  flex:1;padding:12px 0;font-size:11px;font-weight:700;font-family:var(--mono);
  letter-spacing:.08em;text-transform:uppercase;text-align:center;
  color:var(--muted);cursor:pointer;border-bottom:2px solid transparent;transition:.12s;
}
.rp-tab:hover{color:var(--text-variant)}
.rp-tab.active{color:var(--text);border-bottom-color:var(--accent)}
.rp-body{flex:1;overflow-y:auto;padding:0}
.rp-body::-webkit-scrollbar{width:3px}
.rp-body::-webkit-scrollbar-track{background:transparent}
.rp-body::-webkit-scrollbar-thumb{background:var(--muted-dim);border-radius:2px}

/* info panel */
.info-empty{padding:32px 16px;font-size:13px;color:var(--muted);text-align:center;line-height:1.8}
.info-hero{padding:16px 16px 0}
.hero-id{
  font-family:var(--mono);font-size:9px;font-weight:700;letter-spacing:.12em;
  text-transform:uppercase;color:var(--muted);margin-bottom:4px;
}
.hero-name{font-size:16px;font-weight:600;color:var(--text);line-height:1.3;margin-bottom:12px}
.hero-tl-bar{
  background:var(--card);border:1px solid var(--border);border-radius:var(--r);
  padding:8px 12px;margin-bottom:12px;display:flex;align-items:center;gap:10px;
}
.tl-num{font-family:var(--mono);font-size:20px;font-weight:500;color:var(--accent)}
.tl-desc{font-family:var(--mono);font-size:10px;color:var(--muted)}
.metric-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;padding:0 16px 12px}
.metric-card{background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:8px 10px}
.mc-label{
  font-family:var(--mono);font-size:9px;font-weight:700;letter-spacing:.08em;
  text-transform:uppercase;color:var(--muted);margin-bottom:4px;
}
.mc-val{font-family:var(--mono);font-size:16px;font-weight:500;line-height:18px}
.mc-val.bc{color:var(--bc-col)}
.mc-val.ci{color:var(--ci-col)}
.mc-val.scc{color:var(--scc-col)}
.mc-val.neutral{color:var(--text)}

/* collapsible */
.section-toggle{
  display:flex;align-items:center;justify-content:space-between;
  padding:8px 16px;border-top:1px solid var(--border);cursor:pointer;transition:.1s;
}
.section-toggle:hover{background:var(--card)}
.section-name{
  font-family:var(--mono);font-size:9px;font-weight:700;
  letter-spacing:.1em;text-transform:uppercase;color:var(--muted);
}
.section-chevron{font-size:10px;color:var(--muted-dim);transition:.2s}
.section-chevron.open{transform:rotate(180deg)}
.section-content{padding:0 16px 8px;display:none}
.section-content.open{display:block}
.relation-item{
  padding:5px 8px;margin-bottom:2px;border-radius:var(--r);
  border-left:2px solid var(--muted-dim);background:var(--card);
  font-size:12px;color:var(--text-variant);line-height:20px;
}
.no-relations{
  font-family:var(--mono);font-size:10px;color:var(--muted);
  padding:4px 0;font-style:italic;
}

/* keystone list */
.ks-method-row{display:flex;gap:6px;padding:12px 16px 8px;border-bottom:1px solid var(--border)}
.ks-list{padding:8px 16px}
.ks-item{
  display:flex;align-items:center;gap:10px;padding:8px 10px;margin-bottom:4px;
  background:var(--card);border:1px solid var(--border);border-radius:var(--r);cursor:pointer;transition:.1s;
}
.ks-item:hover{border-color:var(--muted);background:var(--surface-high)}
.ks-rank{font-family:var(--mono);font-size:12px;font-weight:500;color:var(--accent);width:22px}
.ks-name{font-size:13px;color:var(--text);flex:1;line-height:20px}
.ks-score{font-family:var(--mono);font-size:10px;color:var(--muted)}

/* ══ BOTTOM BAR ════════════════════════════════════════════════════ */
#bottombar{
  height:48px;background:var(--surface);border-top:1px solid var(--border);
  display:flex;align-items:center;padding:0 16px;gap:16px;flex-shrink:0;
}
.legend-group{display:flex;gap:12px}
.leg-item{display:flex;align-items:center;gap:5px;font-size:11px;color:var(--muted)}
.leg-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.bottom-center{display:flex;align-items:center;gap:6px;margin:0 auto}
.ctrl-btn{
  width:32px;height:32px;border-radius:var(--r);border:1px solid var(--border);
  background:var(--card);color:var(--muted);cursor:pointer;
  display:flex;align-items:center;justify-content:center;font-size:13px;transition:.12s;
}
.ctrl-btn:hover{background:var(--surface-high);color:var(--text-variant);border-color:var(--muted)}
.ctrl-btn.play{
  background:var(--accent-container);border-color:var(--accent);color:var(--accent);
  width:38px;height:38px;font-size:15px;
}
.ctrl-btn.play:hover{background:#7c67c4}
.timeline-wrap{display:flex;align-items:center;gap:8px;margin-left:4px}
.t-label{font-family:var(--mono);font-size:9px;font-weight:700;letter-spacing:.1em;color:var(--muted-dim)}
#wave-slider{width:180px;accent-color:var(--accent);cursor:pointer;height:3px}
#wave-label{font-family:var(--mono);font-size:12px;font-weight:500;color:var(--accent);min-width:80px}
.bottom-right{display:flex;align-items:center;gap:10px;margin-left:auto}
.timeline-badge{
  font-family:var(--mono);font-size:9px;font-weight:700;letter-spacing:.12em;
  color:var(--scc-col);background:rgba(0,200,83,.08);
  border:1px solid rgba(0,200,83,.25);border-radius:var(--r);padding:3px 8px;
}
.sim-label{font-family:var(--mono);font-size:10px;font-weight:700;letter-spacing:.06em;color:var(--muted)}
</style>
</head>
<body>

<!-- ══ TOP NAV ══════════════════════════════════════════════════ -->
<div id="topnav">
  <div class="logo">ECO-SIM ENGINE v1.0</div>
  <nav class="nav-tabs">
    <button class="nav-tab active" id="ntab-explore"   onclick="setMode('explore')">Exploration</button>
    <button class="nav-tab"        id="ntab-scc"       onclick="setMode('scc')">SCC Analysis</button>
    <button class="nav-tab"        id="ntab-keystone"  onclick="setMode('keystone')">Keystone Species</button>
    <button class="nav-tab"        id="ntab-sim"       onclick="setMode('sim')">Simulation</button>
  </nav>
  <div class="nav-right">
    <div class="search-box">
      <span>&#9906;</span>
      <input type="text" id="search-input" placeholder="Search network nodes..." oninput="searchNode(this.value)">
    </div>
    <button class="icon-btn" title="Settings">&#9881;</button>
    <button class="icon-btn" title="Help">?</button>
  </div>
</div>

<!-- ══ BODY ═════════════════════════════════════════════════════ -->
<div id="body">

  <!-- LEFT SIDEBAR -->
  <div id="sidebar">
    <div class="sidebar-section">NET</div>
    <button class="side-btn" id="sbtn-nodes" onclick="setSideTab('nodes')" title="Nodes">
      <span>&#9711;</span>
      <span class="sidebar-label">NODES</span>
    </button>
    <button class="side-btn active" id="sbtn-analytics" onclick="setSideTab('analytics')" title="Analytics">
      <span>&#9783;</span>
      <span class="sidebar-label">ANLYTC</span>
    </button>
    <div class="side-divider"></div>
    <button class="side-btn" id="sbtn-filters" onclick="setSideTab('filters')" title="Filters">
      <span>&#9663;</span>
      <span class="sidebar-label">FILTER</span>
    </button>
    <button class="side-btn" id="sbtn-logs" onclick="setSideTab('logs')" title="Logs">
      <span>&#9776;</span>
      <span class="sidebar-label">LOGS</span>
    </button>
  </div>

  <!-- CENTER -->
  <div id="center">

    <!-- trophic level ruler -->
    <div id="tl-ruler">
      <div class="tl-label">TL4</div>
      <div class="tl-label">TL3</div>
      <div class="tl-label">TL2</div>
      <div class="tl-label">TL1</div>
      <div class="tl-label">TL0</div>
    </div>

    <!-- EXPLORE mode -->
    <div id="explore-container" style="flex:1;display:flex;flex-direction:column;min-height:0">
      <div id="cy-main" style="flex:1;min-height:0"></div>
    </div>

    <!-- SCC mode floating overlay -->
    <div class="float-panel" id="scc-panel" style="display:none">
      <div class="float-title">SCC 분석 (SCC Analysis)</div>
      <div class="btn-row">
        <button class="pill active" id="pill-kosaraju" onclick="setSccAlgo('kosaraju')">Kosaraju</button>
        <button class="pill"        id="pill-tarjan"   onclick="setSccAlgo('tarjan')">Tarjan</button>
      </div>
      <div class="btn-row">
        <button class="pill pill-scc active" id="pill-bridge" onclick="toggleBridge()">Bridge 강조 &#9737;</button>
      </div>
      <div style="font-family:var(--mono);font-size:10px;color:var(--muted);margin-top:4px" id="scc-stat-text"></div>
    </div>
    <div class="float-badge" id="scc-badge" style="display:none">
      <div class="dot"></div>Top-5 Bridge Identified
    </div>

    <!-- Keystone mode floating overlay -->
    <div class="float-panel" id="ks-panel" style="display:none">
      <div class="float-title">핵심종 (Keystone Species)</div>
      <div class="btn-row">
        <button class="pill pill-bc active" id="ks-pill-bc"  onclick="setKsMethod('bc')">BC top-5</button>
        <button class="pill pill-ci"        id="ks-pill-ci"  onclick="setKsMethod('ci')">CI top-5</button>
        <button class="pill pill-scc"       id="ks-pill-scc" onclick="setKsMethod('scc')">SCC Bridge</button>
      </div>
    </div>

    <!-- SIM mode -->
    <div id="sim-container">
      <div id="sim-panels">
        <div class="sim-card">
          <div class="sim-header bc"><span>BC Targeted</span><span class="sim-stat" id="stat-bc">40 / 40종</span></div>
          <div class="cy-sim" id="cy-sim-bc"></div>
        </div>
        <div class="sim-card">
          <div class="sim-header ci"><span>CI Targeted</span><span class="sim-stat" id="stat-ci">40 / 40종</span></div>
          <div class="cy-sim" id="cy-sim-ci"></div>
        </div>
        <div class="sim-card">
          <div class="sim-header scc"><span>SCC Bridge</span><span class="sim-stat" id="stat-scc">40 / 40종</span></div>
          <div class="cy-sim" id="cy-sim-scc"></div>
        </div>
      </div>
    </div>

  </div><!-- /center -->

  <!-- RIGHT PANEL -->
  <div id="right-panel">
    <div class="rp-tabs">
      <div class="rp-tab active" id="rp-tab-explore"   onclick="setRpTab('explore')">탐색 (Explore)</div>
      <div class="rp-tab"        id="rp-tab-keystone"  onclick="setRpTab('keystone')">핵심종 (Keystone)</div>
    </div>
    <div class="rp-body" id="rp-explore">
      <div class="info-empty">네트워크에서<br>종을 클릭하세요</div>
    </div>
    <div class="rp-body" id="rp-keystone" style="display:none">
      <div class="ks-method-row">
        <button class="pill pill-bc active" id="ks-rp-bc"  onclick="setKsRpMethod('bc')">BC</button>
        <button class="pill pill-ci"        id="ks-rp-ci"  onclick="setKsRpMethod('ci')">CI</button>
        <button class="pill pill-scc"       id="ks-rp-scc" onclick="setKsRpMethod('scc')">SCC</button>
      </div>
      <div class="ks-list" id="ks-rp-list"></div>
    </div>
  </div>

</div><!-- /body -->

<!-- ══ BOTTOM BAR ════════════════════════════════════════════════ -->
<div id="bottombar">
  <div class="legend-group">
    <div class="leg-item"><div class="leg-dot" style="background:#00E5FF"></div>생존</div>
    <div class="leg-item"><div class="leg-dot" style="background:#ffb4ab"></div>직접 제거</div>
    <div class="leg-item"><div class="leg-dot" style="background:#f97316"></div>연쇄 멸종</div>
    <div class="leg-item"><div class="leg-dot" style="background:#36343a;border:1px solid #494551"></div>이전 멸종</div>
  </div>
  <div class="bottom-center" id="sim-controls" style="display:none">
    <button class="ctrl-btn" onclick="resetWave()" title="Reset">&#8635;</button>
    <button class="ctrl-btn" onclick="stepWave(-1)" title="Prev">&#9664;</button>
    <button class="ctrl-btn play" id="play-btn" onclick="togglePlay()">&#9654;</button>
    <button class="ctrl-btn" onclick="stepWave(1)" title="Next">&#9654;&#9654;</button>
    <button class="ctrl-btn" onclick="showFinal()" title="Final" style="font-size:10px;letter-spacing:-.5px">END</button>
    <div class="timeline-wrap">
      <span class="t-label">STEP</span>
      <input type="range" id="wave-slider" min="0" max="5" value="0" step="1">
      <span id="wave-label">초기 상태</span>
    </div>
  </div>
  <div class="bottom-right">
    <span class="sim-label" id="bottom-mode-label">시뮬레이션 (SIMULATION)</span>
    <span class="timeline-badge" id="timeline-badge">NETWORK ACTIVE</span>
  </div>
</div>

<script>
const RAW = """ + DATA_JSON + """;

// ── index ──────────────────────────────────────────────────────────
const NODE_MAP = {};
RAW.nodes.forEach(n => NODE_MAP[n.id] = n);
const TL_LABEL = {0:'Basal',1:'Primary Consumer',2:'Secondary Consumer',3:'Mesopredator',4:'Top Predator'};
const SCC_PAL = ['#e74c3c','#3498db','#2ecc71','#9b59b6','#f39c12','#1abc9c','#e67e22',
  '#e91e63','#00bcd4','#8bc34a','#ff5722','#607d8b','#795548','#9c27b0','#03a9f4',
  '#cddc39','#ff9800','#673ab7','#009688','#f44336','#2196f3','#4caf50'];

// ── Cytoscape shared style ─────────────────────────────────────────
const CY_STYLE = [
  {selector:'node',style:{
    label:'data(label)','font-size':'8px','font-family':'JetBrains Mono, monospace',
    color:'#e6e0e9','text-valign':'bottom','text-margin-y':'4px',
    'text-outline-width':'1.5px','text-outline-color':'#141218',
    'background-color':'#00E5FF','border-width':0,'border-color':'#e7c365',
    width:'mapData(deg,0,24,9,24)',height:'mapData(deg,0,24,9,24)',
    'transition-property':'background-color,border-width,opacity,box-shadow',
    'transition-duration':'200ms',
  }},
  {selector:'edge',style:{
    width:.5,'line-color':'rgba(148,142,156,.18)',
    'target-arrow-color':'rgba(148,142,156,.18)','target-arrow-shape':'triangle',
    'curve-style':'bezier','arrow-scale':.4,
  }},
  {selector:'.bridge',style:{
    'border-width':'2.5px','border-color':'#e7c365',
    'background-color':'#e7c365',color:'#141218','text-outline-color':'#e7c365',
    width:'mapData(deg,0,24,14,28)',height:'mapData(deg,0,24,14,28)',
  }},
  {selector:'.dimmed',style:{opacity:.08}},
  {selector:'.extinct-now',    style:{'background-color':'#ffb4ab','border-width':'2px','border-color':'#ff6b6b',opacity:.9}},
  {selector:'.extinct-cascade',style:{'background-color':'#f97316',opacity:.8}},
  {selector:'.extinct-old',    style:{'background-color':'#36343a',opacity:.2}},
];

function makeEls() {
  const els = [];
  RAW.nodes.forEach(n => {
    const deg = n.in_deg + n.out_deg;
    els.push({data:{id:n.id,label:n.id,tl:n.tl,deg,...n}});
  });
  RAW.edges.forEach(e => els.push({data:{id:e.id,source:e.source,target:e.target,weight:e.weight}}));
  return els;
}

function posMap(cy) {
  const w = cy.container().offsetWidth, h = cy.container().offsetHeight;
  const groups = {};
  cy.nodes().forEach(n => { const t=n.data('tl'); if(!groups[t]) groups[t]=[]; groups[t].push(n); });
  const pos = {};
  [0,1,2,3,4].forEach(t => {
    const g = groups[t]||[];
    const y = h-30-(t/4)*(h-70);
    g.forEach((n,i) => pos[n.id()] = {x:(i+1)/(g.length+1)*w, y});
  });
  return pos;
}
function applyPos(cy) {
  const p = posMap(cy);
  cy.nodes().forEach(n => { if(p[n.id()]) n.position(p[n.id()]); });
  cy.fit(cy.nodes(),28);
}

// ── main cytoscape ──────────────────────────────────────────────────
let cyMain = null;
function initMain() {
  if (cyMain) return;
  cyMain = cytoscape({
    container:document.getElementById('cy-main'),
    elements:makeEls(), style:CY_STYLE,
    layout:{name:'preset',positions:()=>({})},
    userZoomingEnabled:true,userPanningEnabled:true,boxSelectionEnabled:false,
  });
  applyPos(cyMain);
  cyMain.on('tap','node', e => showNodeInfo(e.target.data()));
  cyMain.on('tap', e => { if(e.target===cyMain) clearNodeInfo(); });
}

// ── node info ───────────────────────────────────────────────────────
function showNodeInfo(d) {
  const n = NODE_MAP[d.id]; if(!n) return;
  const top5bc=new Set(RAW.top5.bc), top5ci=new Set(RAW.top5.ci), top5scc=new Set(RAW.top5.scc);
  const tags = [];
  if(top5bc.has(n.id))  tags.push('<span style="font-family:var(--mono);font-size:9px;color:var(--bc-col);background:rgba(96,165,250,.12);border:1px solid rgba(96,165,250,.3);border-radius:3px;padding:1px 6px">BC TOP5</span>');
  if(top5ci.has(n.id))  tags.push('<span style="font-family:var(--mono);font-size:9px;color:var(--ci-col);background:rgba(244,114,182,.12);border:1px solid rgba(244,114,182,.3);border-radius:3px;padding:1px 6px">CI TOP5</span>');
  if(top5scc.has(n.id)) tags.push('<span style="font-family:var(--mono);font-size:9px;color:var(--scc-col);background:rgba(74,222,128,.12);border:1px solid rgba(74,222,128,.3);border-radius:3px;padding:1px 6px">SCC TOP5</span>');

  const predHtml = n.predators.length
    ? n.predators.map(p=>`<div class="relation-item">${p}</div>`).join('')
    : '<div class="no-relations">No Natural Predators</div>';
  const preyHtml = n.preys.length
    ? n.preys.map(p=>`<div class="relation-item" onclick="focusNode('${p.replace(/'/g,"\\'")}');return false" style="cursor:pointer">${p} <span style="font-size:9px;color:var(--muted)">(${TL_LABEL[NODE_MAP[p]?.tl]||''})</span></div>`).join('')
    : '<div class="no-relations">No Prey</div>';

  document.getElementById('rp-explore').innerHTML = `
    <div class="info-hero">
      <div class="hero-id">ID: ${n.id.toUpperCase().replace(/ /g,'_')}</div>
      ${tags.length ? '<div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:6px">'+tags.join('')+'</div>' : ''}
      <div class="hero-name">${n.id}</div>
      <div class="hero-tl-bar">
        <span class="tl-num">${n.tl}.0</span>
        <div><div style="font-size:10px;color:var(--text)">${TL_LABEL[n.tl]||'Unknown'}</div>
          <div class="tl-desc">Trophic Level</div></div>
      </div>
    </div>
    <div class="metric-grid">
      <div class="metric-card"><div class="mc-label">BC Rank</div><div class="mc-val bc">${n.bc_rank ? '#'+n.bc_rank : '—'}</div></div>
      <div class="metric-card"><div class="mc-label">CI Rank</div><div class="mc-val ci">${n.ci_rank ? '#'+n.ci_rank : '—'}</div></div>
      <div class="metric-card"><div class="mc-label">SCC Bridge</div><div class="mc-val scc">${n.scc_bridge_rank ? '#'+n.scc_bridge_rank : '—'}</div></div>
      <div class="metric-card"><div class="mc-label">SCC Weight</div><div class="mc-val neutral">${n.cross_edges != null ? n.cross_edges : '—'}</div></div>
      <div class="metric-card"><div class="mc-label">Predators</div><div class="mc-val neutral">${n.in_deg}</div></div>
      <div class="metric-card"><div class="mc-label">Prey</div><div class="mc-val neutral">${n.out_deg}</div></div>
    </div>
    <div class="section-toggle" onclick="toggleSection(this)">
      <span class="section-name">Predators</span>
      <span class="section-chevron open">&#9650;</span>
    </div>
    <div class="section-content open">${predHtml}</div>
    <div class="section-toggle" onclick="toggleSection(this)">
      <span class="section-name">Prey List</span>
      <span class="section-chevron open">&#9650;</span>
    </div>
    <div class="section-content open">${preyHtml}</div>
  `;
  setRpTab('explore');

  // highlight neighbors
  if(cyMain) {
    cyMain.nodes().addClass('dimmed');
    cyMain.edges().addClass('dimmed');
    const sel = cyMain.getElementById(n.id);
    sel.removeClass('dimmed');
    sel.neighborhood().removeClass('dimmed');
  }
}
function clearNodeInfo() {
  if(cyMain){ cyMain.nodes().removeClass('dimmed'); cyMain.edges().removeClass('dimmed'); }
  document.getElementById('rp-explore').innerHTML='<div class="info-empty">네트워크에서<br>종을 클릭하세요</div>';
}
function focusNode(id) {
  if(cyMain) showNodeInfo({id});
}
function toggleSection(el) {
  const chev = el.querySelector('.section-chevron');
  const content = el.nextElementSibling;
  const open = content.classList.toggle('open');
  chev.classList.toggle('open', open);
}

// ── SCC mode ────────────────────────────────────────────────────────
let sccAlgo = 'kosaraju', bridgeOn = true;
function setSccAlgo(a) {
  sccAlgo = a;
  document.getElementById('pill-kosaraju').classList.toggle('active', a==='kosaraju');
  document.getElementById('pill-tarjan').classList.toggle('active', a==='tarjan');
  applySccs();
}
function toggleBridge() {
  bridgeOn = !bridgeOn;
  document.getElementById('pill-bridge').classList.toggle('active', bridgeOn);
  applySccs();
}
function applySccs() {
  if(!cyMain) return;
  const key = sccAlgo==='kosaraju' ? 'k_scc' : 't_scc';
  cyMain.nodes().forEach(n => {
    n.style('background-color', SCC_PAL[n.data(key) % SCC_PAL.length]||'#888');
    n.removeClass('bridge');
  });
  if(bridgeOn) RAW.top5.scc.forEach(sp => cyMain.getElementById(sp).addClass('bridge'));
  const nG = new Set(RAW.nodes.map(n=>n[key])).size;
  document.getElementById('scc-stat-text').textContent = `${nG} SCC groups identified`;
}

// ── Keystone mode ────────────────────────────────────────────────────
let ksMethod = 'bc';
const KS_COL = {bc:'#60a5fa',ci:'#f472b6',scc:'#4ade80'};
function setKsMethod(m) {
  ksMethod = m;
  ['bc','ci','scc'].forEach(k=>{
    document.getElementById(`ks-pill-${k}`).classList.toggle('active',k===m);
  });
  applyKs();
}
function applyKs() {
  if(!cyMain) return;
  const top5 = new Set(RAW.top5[ksMethod]), col = KS_COL[ksMethod];
  cyMain.nodes().forEach(n=>{
    const is = top5.has(n.id());
    n.style('background-color', is ? col : '#1e1e30');
    n.style('border-width', is ? '2.5px' : '0');
    n.style('border-color', col);
    n.style('opacity', is ? 1 : 0.2);
  });
  cyMain.edges().style('opacity',.05);
}

// ── Keystone right panel ─────────────────────────────────────────────
let ksRpMethod = 'bc';
function setKsRpMethod(m) {
  ksRpMethod = m;
  ['bc','ci','scc'].forEach(k => document.getElementById(`ks-rp-${k}`).classList.toggle('active',k===m));
  renderKsList();
}
function renderKsList() {
  const data = RAW.top5[ksRpMethod];
  const col  = KS_COL[ksRpMethod];
  const scoreKey = ksRpMethod==='bc' ? 'bc_score' : ksRpMethod==='ci' ? 'ci_score' : 'cross_edges';
  const scoreLabel = ksRpMethod==='bc' ? 'BC' : ksRpMethod==='ci' ? 'CI' : 'Cross';
  document.getElementById('ks-rp-list').innerHTML = data.map((sp,i)=>{
    const n = NODE_MAP[sp];
    const score = n?.[scoreKey] ?? '—';
    return `<div class="ks-item" onclick="focusNode('${sp.replace(/'/g,"\\'")}')">
      <span class="ks-rank" style="color:${col}">#${i+1}</span>
      <span class="ks-name">${sp}</span>
      <span class="ks-score">${scoreLabel}: ${score}</span>
    </div>`;
  }).join('');
}

// ── Sim cytoscape ─────────────────────────────────────────────────────
let cyBC=null, cyCI=null, cySCC=null, simReady=false;
function initSim() {
  if(simReady) return; simReady=true;
  ['bc','ci','scc'].forEach(k=>{
    const cy = cytoscape({
      container:document.getElementById(`cy-sim-${k}`),
      elements:makeEls(), style:CY_STYLE,
      layout:{name:'preset',positions:()=>({})},
      userZoomingEnabled:true,userPanningEnabled:true,boxSelectionEnabled:false,
    });
    applyPos(cy);
    if(k==='bc') cyBC=cy; else if(k==='ci') cyCI=cy; else cySCC=cy;
  });
}

function buildExtMap(waves) {
  const m={};
  waves.forEach((w,wi)=>{
    w.removed.forEach((sp,si)=>{ if(!(sp in m)) m[sp]={wave:wi+1,type:si===0?'direct':'cascade'}; });
  });
  return m;
}
const EXT={bc:buildExtMap(RAW.waves.bc),ci:buildExtMap(RAW.waves.ci),scc:buildExtMap(RAW.waves.scc)};

let curWave=0, playing=false, playTimer=null;
function updateSim(wave, final) {
  [[cyBC,'stat-bc',EXT.bc],[cyCI,'stat-ci',EXT.ci],[cySCC,'stat-scc',EXT.scc]].forEach(([cy,sid,em])=>{
    if(!cy) return;
    let alive=0;
    cy.nodes().forEach(n=>{
      const ext=em[n.id()];
      n.removeClass('extinct-now extinct-cascade extinct-old');
      if(!ext){ alive++; }
      else if(final||ext.wave<wave){ n.addClass('extinct-old'); }
      else if(ext.wave===wave&&wave>0){ n.addClass(ext.type==='direct'?'extinct-now':'extinct-cascade'); }
      else { alive++; }
    });
    cy.edges().forEach(e=>{
      const se=em[e.data('source')],te=em[e.data('target')];
      const thr=final?Infinity:wave;
      e.style('opacity',((se&&se.wave<=thr)||(te&&te.wave<=thr))?.03:.18);
    });
    document.getElementById(sid).textContent=`${alive} / ${RAW.total}종`;
  });
  const lbl=document.getElementById('wave-label');
  document.getElementById('wave-slider').value=wave;
  lbl.textContent=final?'최종 결과':wave===0?'초기 상태':`Wave ${wave}`;
  document.getElementById('timeline-badge').textContent=final?'SIMULATION ENDED':'TIMELINE ACTIVE';
}
function stepWave(d){ curWave=Math.max(0,Math.min(5,curWave+d)); updateSim(curWave,false); }
function resetWave(){ stopPlay(); curWave=0; updateSim(0,false); }
function showFinal(){ stopPlay(); updateSim(5,true); }
function stopPlay(){ clearInterval(playTimer);playing=false;document.getElementById('play-btn').innerHTML='&#9654;'; }
function togglePlay(){
  if(playing){ stopPlay(); }
  else {
    playing=true; document.getElementById('play-btn').innerHTML='&#9646;&#9646;';
    playTimer=setInterval(()=>{ curWave++; if(curWave>5){curWave=0;} updateSim(curWave,false); },900);
  }
}
document.getElementById('wave-slider').addEventListener('input',e=>{ curWave=+e.target.value; updateSim(curWave,false); });

// ── search ────────────────────────────────────────────────────────────
function searchNode(q) {
  if(!cyMain||!q) { cyMain&&cyMain.nodes().style('opacity',1); return; }
  const lq=q.toLowerCase();
  cyMain.nodes().forEach(n=>{
    n.style('opacity', n.id().toLowerCase().includes(lq)?1:0.1);
  });
}

// ── sidebar (cosmetic only for now) ───────────────────────────────────
function setSideTab(t){ ['nodes','analytics','filters','logs'].forEach(k=>document.getElementById(`sbtn-${k}`).classList.toggle('active',k===t)); }

// ── right panel tabs ─────────────────────────────────────────────────
function setRpTab(t) {
  document.getElementById('rp-tab-explore').classList.toggle('active',t==='explore');
  document.getElementById('rp-tab-keystone').classList.toggle('active',t==='keystone');
  document.getElementById('rp-explore').style.display=t==='explore'?'':'none';
  document.getElementById('rp-keystone').style.display=t==='keystone'?'':'none';
  if(t==='keystone'){ renderKsList(); }
}

// ── mode switching ────────────────────────────────────────────────────
let currentMode='explore';
function setMode(m) {
  currentMode=m;
  ['explore','scc','keystone','sim'].forEach(k=>{
    document.getElementById(`ntab-${k}`).classList.toggle('active',k===m);
  });
  if(!cyMain) initMain();

  // panels visibility
  document.getElementById('explore-container').style.display=m!=='sim'?'flex':'none';
  document.getElementById('sim-container').style.display=m==='sim'?'flex':'none';
  document.getElementById('scc-panel').style.display=m==='scc'?'block':'none';
  document.getElementById('scc-badge').style.display=m==='scc'?'flex':'none';
  document.getElementById('ks-panel').style.display=m==='keystone'?'block':'none';
  document.getElementById('sim-controls').style.display=m==='sim'?'flex':'none';

  document.getElementById('bottom-mode-label').textContent =
    m==='explore'?'탐색 (EXPLORE)':m==='scc'?'SCC 분석 (SCC ANALYSIS)':
    m==='keystone'?'핵심종 (KEYSTONE)':'시뮬레이션 (SIMULATION)';

  // reset node styles
  if(cyMain) {
    cyMain.nodes().style({'background-color':'#4ade80','border-width':0,opacity:1});
    cyMain.edges().style('opacity',.1);
    cyMain.nodes().removeClass('bridge dimmed');
  }

  if(m==='scc')      applySccs();
  else if(m==='keystone') applyKs();
  else if(m==='sim') { initSim(); updateSim(0,false); }
}

window.addEventListener('load',()=>setMode('explore'));
</script>
</body>
</html>"""

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved -> {out_path}")


if __name__ == "__main__":
    random.seed(42)
    from src.graph import build_graph
    G = build_graph("data/parana_edgelist.csv")
    data = collect_data(G)
    build_html(data, "outputs/figures/interactive_sim.html")
