"""
Generate parana_edgelist.csv.
Edge direction: source -> target = source EATS target.
Total: 40 species, 185 edges (Angelini & Agostinho 2005).
"""
import random
import pandas as pd
from collections import defaultdict

random.seed(42)

SPECIES = {
    "Acestrorhyncus lacustris":     {"out": 8,  "in": 2,  "tl": 4},
    "Astyanax altiparanae":         {"out": 7,  "in": 14, "tl": 2},
    "Auchenipterus nuchalis":       {"out": 3,  "in": 3,  "tl": 2},
    "Benthos":                      {"out": 2,  "in": 13, "tl": 1},
    "Brycon orbignyanus":           {"out": 4,  "in": 2,  "tl": 2},
    "Cyphocharax modestus":         {"out": 3,  "in": 1,  "tl": 1},
    "Hemisorubin platyrhynchos":    {"out": 7,  "in": 1,  "tl": 4},
    "Hoplias malabaricus":          {"out": 6,  "in": 2,  "tl": 4},
    "Hoplosternum littorale":       {"out": 5,  "in": 1,  "tl": 2},
    "Hypophthalmus edentatus":      {"out": 2,  "in": 3,  "tl": 1},
    "Hypostomus sp":                {"out": 2,  "in": 1,  "tl": 1},
    "Iheringichthys labrosus":      {"out": 5,  "in": 1,  "tl": 2},
    "Insects":                      {"out": 2,  "in": 16, "tl": 1},
    "Leporinus friderici":          {"out": 7,  "in": 2,  "tl": 2},
    "Leporinus obtusidens":         {"out": 7,  "in": 3,  "tl": 2},
    "Loricariichthys platymetopon": {"out": 4,  "in": 1,  "tl": 1},
    "Other benthos feeders":        {"out": 6,  "in": 4,  "tl": 2},
    "Other insectivores":           {"out": 4,  "in": 7,  "tl": 2},
    "Other omnivores":              {"out": 7,  "in": 8,  "tl": 2},
    "Other piscivores":             {"out": 8,  "in": 2,  "tl": 4},
    "Parauchenipterus galeatus":    {"out": 2,  "in": 2,  "tl": 2},
    "Pimelodus maculatus":          {"out": 11, "in": 1,  "tl": 2},
    "Plagioscion squamosissimus":   {"out": 7,  "in": 2,  "tl": 4},
    "Prochilodus lineatus":         {"out": 3,  "in": 7,  "tl": 1},
    "Pseudoplatystoma corruscans":  {"out": 7,  "in": 2,  "tl": 4},
    "Pterodoras granulosus":        {"out": 6,  "in": 3,  "tl": 2},
    "Rhaphiodon vulpinus":          {"out": 7,  "in": 1,  "tl": 4},
    "Salminus brasiliensis":        {"out": 7,  "in": 1,  "tl": 4},
    "Schizodon altoparanae":        {"out": 2,  "in": 1,  "tl": 1},
    "Schizodon borellii":           {"out": 2,  "in": 2,  "tl": 1},
    "Serrasalmus marginatus":       {"out": 11, "in": 5,  "tl": 3},
    "Serrasalmus spilopleura":      {"out": 9,  "in": 1,  "tl": 3},
    "Steindachnerina insculpta":    {"out": 3,  "in": 1,  "tl": 1},
    "Trachydoras paraguayensis":    {"out": 3,  "in": 1,  "tl": 1},
    "Zooplankton":                  {"out": 2,  "in": 11, "tl": 1},
    "Aquatic macrophytes":          {"out": 0,  "in": 14, "tl": 0},
    "Periphyton":                   {"out": 0,  "in": 3,  "tl": 0},
    "Phytoplankton":                {"out": 0,  "in": 17, "tl": 0},
    "Detritus":                     {"out": 0,  "in": 19, "tl": 0},
    "Other detritus feeders":       {"out": 4,  "in": 4,  "tl": 1},
}

assert sum(v["out"] for v in SPECIES.values()) == 185
assert sum(v["in"]  for v in SPECIES.values()) == 185

def generate():
    # Track remaining degrees
    out_rem = {sp: SPECIES[sp]["out"] for sp in SPECIES}
    in_rem  = {sp: SPECIES[sp]["in"]  for sp in SPECIES}
    edges   = set()

    def add(src, tgt):
        if src == tgt or (src, tgt) in edges:
            return False
        if out_rem[src] <= 0 or in_rem[tgt] <= 0:
            return False
        edges.add((src, tgt))
        out_rem[src] -= 1
        in_rem[tgt]  -= 1
        return True

    # ── Tier 0 (basal resources) ─────────────────────────────────
    basal   = [sp for sp in SPECIES if SPECIES[sp]["tl"] == 0]
    # ── Tier 1 (primary consumers) ──────────────────────────────
    t1 = [sp for sp in SPECIES if SPECIES[sp]["tl"] == 1]
    # ── Tier 2 (secondary consumers) ────────────────────────────
    t2 = [sp for sp in SPECIES if SPECIES[sp]["tl"] == 2]
    # ── Tier 3/4 (tertiary / top predators) ─────────────────────
    t34 = [sp for sp in SPECIES if SPECIES[sp]["tl"] >= 3]

    # Deterministic seeding: each tier-1 species connects to basal
    t1_basal_pref = {
        "Benthos":                      ["Detritus", "Phytoplankton"],
        "Insects":                      ["Aquatic macrophytes", "Detritus"],
        "Zooplankton":                  ["Phytoplankton", "Detritus"],
        "Prochilodus lineatus":         ["Detritus", "Phytoplankton", "Periphyton"],
        "Steindachnerina insculpta":    ["Detritus", "Phytoplankton", "Periphyton"],
        "Cyphocharax modestus":         ["Detritus", "Phytoplankton", "Periphyton"],
        "Hypophthalmus edentatus":      ["Zooplankton", "Phytoplankton"],
        "Hypostomus sp":                ["Detritus", "Periphyton"],
        "Loricariichthys platymetopon": ["Detritus", "Phytoplankton", "Periphyton", "Aquatic macrophytes"],
        "Schizodon altoparanae":        ["Aquatic macrophytes", "Detritus"],
        "Schizodon borellii":           ["Aquatic macrophytes", "Detritus"],
        "Trachydoras paraguayensis":    ["Detritus", "Insects", "Benthos"],
        "Other detritus feeders":       ["Detritus", "Phytoplankton", "Periphyton", "Aquatic macrophytes"],
    }
    for sp, prefs in t1_basal_pref.items():
        for tgt in prefs:
            add(sp, tgt)

    # Tier 2 → Tier 1 / basal
    t2_pref = {
        "Astyanax altiparanae":     ["Detritus","Insects","Zooplankton","Phytoplankton","Aquatic macrophytes","Periphyton","Benthos"],
        "Auchenipterus nuchalis":   ["Insects","Zooplankton","Benthos"],
        "Brycon orbignyanus":       ["Aquatic macrophytes","Insects","Zooplankton","Detritus"],
        "Hoplosternum littorale":   ["Detritus","Insects","Benthos","Phytoplankton","Zooplankton"],
        "Iheringichthys labrosus":  ["Insects","Zooplankton","Benthos","Detritus","Aquatic macrophytes"],
        "Leporinus friderici":      ["Aquatic macrophytes","Detritus","Insects","Phytoplankton","Zooplankton","Periphyton","Benthos"],
        "Leporinus obtusidens":     ["Aquatic macrophytes","Detritus","Insects","Phytoplankton","Zooplankton","Periphyton","Benthos"],
        "Other benthos feeders":    ["Benthos","Detritus","Insects","Phytoplankton","Zooplankton","Periphyton"],
        "Other insectivores":       ["Insects","Zooplankton","Benthos","Detritus"],
        "Other omnivores":          ["Detritus","Phytoplankton","Zooplankton","Insects","Aquatic macrophytes","Benthos","Periphyton"],
        "Parauchenipterus galeatus":["Insects","Zooplankton"],
        "Pimelodus maculatus":      ["Detritus","Insects","Zooplankton","Benthos","Phytoplankton","Aquatic macrophytes","Periphyton","Prochilodus lineatus","Steindachnerina insculpta","Cyphocharax modestus","Schizodon borellii"],
        "Pterodoras granulosus":    ["Detritus","Insects","Zooplankton","Benthos","Phytoplankton","Aquatic macrophytes"],
        "Serrasalmus marginatus":   ["Astyanax altiparanae","Other insectivores","Other omnivores","Leporinus friderici","Leporinus obtusidens","Pimelodus maculatus","Pterodoras granulosus","Prochilodus lineatus","Other benthos feeders","Brycon orbignyanus","Hoplosternum littorale"],
        "Serrasalmus spilopleura":  ["Astyanax altiparanae","Other insectivores","Other omnivores","Leporinus friderici","Leporinus obtusidens","Pimelodus maculatus","Pterodoras granulosus","Prochilodus lineatus","Brycon orbignyanus"],
    }
    for sp, prefs in t2_pref.items():
        for tgt in prefs:
            add(sp, tgt)

    # Tier 3/4 → lower tiers
    t34_pref = {
        "Acestrorhyncus lacustris":    ["Astyanax altiparanae","Other insectivores","Other omnivores","Auchenipterus nuchalis","Brycon orbignyanus","Leporinus friderici","Leporinus obtusidens","Serrasalmus marginatus"],
        "Hemisorubin platyrhynchos":   ["Astyanax altiparanae","Other insectivores","Other omnivores","Pimelodus maculatus","Pterodoras granulosus","Leporinus friderici","Prochilodus lineatus"],
        "Hoplias malabaricus":         ["Astyanax altiparanae","Other insectivores","Leporinus friderici","Leporinus obtusidens","Other omnivores","Pimelodus maculatus"],
        "Other piscivores":            ["Astyanax altiparanae","Other insectivores","Other omnivores","Pimelodus maculatus","Pterodoras granulosus","Leporinus friderici","Leporinus obtusidens","Serrasalmus marginatus"],
        "Plagioscion squamosissimus":  ["Astyanax altiparanae","Other insectivores","Prochilodus lineatus","Pimelodus maculatus","Pterodoras granulosus","Other omnivores","Leporinus obtusidens"],
        "Pseudoplatystoma corruscans": ["Astyanax altiparanae","Pimelodus maculatus","Prochilodus lineatus","Pterodoras granulosus","Other omnivores","Serrasalmus marginatus","Leporinus friderici"],
        "Rhaphiodon vulpinus":         ["Astyanax altiparanae","Other insectivores","Other omnivores","Leporinus friderici","Leporinus obtusidens","Pimelodus maculatus","Serrasalmus marginatus"],
        "Salminus brasiliensis":       ["Astyanax altiparanae","Pimelodus maculatus","Prochilodus lineatus","Leporinus friderici","Leporinus obtusidens","Other omnivores","Pterodoras granulosus"],
    }
    for sp, prefs in t34_pref.items():
        for tgt in prefs:
            add(sp, tgt)

    # ── Fill remaining degrees with random matching ───────────────
    for _ in range(1000):
        pred_stubs = [sp for sp in SPECIES for _ in range(out_rem[sp])]
        prey_stubs = [sp for sp in SPECIES for _ in range(in_rem[sp])]
        if not pred_stubs:
            break
        random.shuffle(pred_stubs)
        random.shuffle(prey_stubs)
        progress = False
        for p, q in zip(pred_stubs, prey_stubs):
            if add(p, q):
                progress = True
        if not progress:
            break

    return sorted(edges), out_rem, in_rem


if __name__ == "__main__":
    edges, out_rem, in_rem = generate()
    df = pd.DataFrame(edges, columns=["source", "target"])
    out_path = "C:/Users/20222/OneDrive/Desktop/code/project/data/parana_edgelist.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved {len(edges)} edges")

    unsatisfied = [(sp, out_rem[sp], in_rem[sp]) for sp in SPECIES if out_rem[sp] or in_rem[sp]]
    if unsatisfied:
        print("Unsatisfied degrees:")
        for sp, o, i in unsatisfied:
            print(f"  {sp}: out_rem={o}, in_rem={i}")
    else:
        print("All degree constraints satisfied!")
