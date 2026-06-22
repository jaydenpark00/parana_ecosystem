"""STEP 1 — 그래프 구성"""
import pandas as pd
import networkx as nx
from collections import deque

TROPHIC_LEVELS = {
    "Detritus": 0, "Phytoplankton": 0, "Aquatic macrophytes": 0, "Periphyton": 0,
    "Zooplankton": 1, "Insects": 1, "Benthos": 1,
    "Prochilodus lineatus": 1, "Steindachnerina insculpta": 1,
    "Cyphocharax modestus": 1, "Hypophthalmus edentatus": 1,
    "Hypostomus sp": 1, "Loricariichthys platymetopon": 1,
    "Schizodon altoparanae": 1, "Schizodon borellii": 1,
    "Trachydoras paraguayensis": 1, "Other detritus feeders": 1,
    "Astyanax altiparanae": 2, "Auchenipterus nuchalis": 2,
    "Brycon orbignyanus": 2, "Hoplosternum littorale": 2,
    "Iheringichthys labrosus": 2, "Leporinus friderici": 2,
    "Leporinus obtusidens": 2, "Other benthos feeders": 2,
    "Other insectivores": 2, "Other omnivores": 2,
    "Parauchenipterus galeatus": 2, "Pimelodus maculatus": 2,
    "Pterodoras granulosus": 2,
    "Serrasalmus marginatus": 3, "Serrasalmus spilopleura": 3,
    "Acestrorhyncus lacustris": 4, "Hemisorubin platyrhynchos": 4,
    "Hoplias malabaricus": 4, "Other piscivores": 4,
    "Plagioscion squamosissimus": 4, "Pseudoplatystoma corruscans": 4,
    "Rhaphiodon vulpinus": 4, "Salminus brasiliensis": 4,
}

def build_graph(edgelist_path: str) -> nx.DiGraph:
    df = pd.read_csv(edgelist_path)
    G = nx.DiGraph()
    G.add_edges_from(zip(df["source"], df["target"]))
    for node in G.nodes():
        G.nodes[node]["trophic_level"] = TROPHIC_LEVELS.get(node, _bfs_trophic(G, node))
        G.nodes[node]["species_name"] = node
    return G


def build_graph_from_matrix(matrix_path: str = "data/FW_001.csv",
                            algorithm: bool = False) -> nx.DiGraph:
    """Build the WTECM graph from the raw 40x36 diet matrix.

    The returned graph uses prey -> predator edges. Self-loops are preserved for
    WTECM, and removed only when algorithm=True.
    """
    from src.wtecm import build_wtecm_graph, load_matrix, make_algorithm_graph

    matrix = load_matrix(matrix_path)
    graph = build_wtecm_graph(matrix, labels="name")
    return make_algorithm_graph(graph) if algorithm else graph


def _bfs_trophic(G: nx.DiGraph, node: str) -> float:
    visited = {node: 0}
    queue = deque([node])
    while queue:
        cur = queue.popleft()
        for nxt in G.successors(cur):
            if nxt not in visited:
                visited[nxt] = visited[cur] + 1
                queue.append(nxt)
    return max(visited.values()) if len(visited) > 1 else 0


def print_stats(G: nx.DiGraph):
    n = G.number_of_nodes()
    e = G.number_of_edges()
    density = nx.density(G)
    in_deg  = [d for _, d in G.in_degree()]
    out_deg = [d for _, d in G.out_degree()]
    print(f"Nodes   : {n}")
    print(f"Edges   : {e}")
    print(f"Density : {density:.4f}")
    print(f"In-degree  mean={sum(in_deg)/n:.2f}  max={max(in_deg)}")
    print(f"Out-degree mean={sum(out_deg)/n:.2f}  max={max(out_deg)}")
    print(f"Is directed: {nx.is_directed(G)}")
    return G


if __name__ == "__main__":
    G = build_graph("data/parana_edgelist.csv")
    print_stats(G)
