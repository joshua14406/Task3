"""Rebuild docs/diagrams (PDA/DFA diagrams and parse trees). Needs Graphviz (`dot`)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pda_cases.cases import (COMMENT_DPDA, G1, G1_REVISED, G3, HAIRPIN_NPDA,  # noqa: E402
                             IJK_NPDA)
from pda_cases.grammar import tree_to_dot  # noqa: E402

OUT = ROOT / "docs" / "diagrams"
OUT.mkdir(parents=True, exist_ok=True)


def save(name, dot):
    (OUT / f"{name}.dot").write_text(dot, encoding="utf-8")
    subprocess.run(["dot", "-Tsvg", "-o", str(OUT / f"{name}.svg")], input=dot.encode(), check=True)
    subprocess.run(["dot", "-Gdpi=170", "-Tpng", "-o", str(OUT / f"{name}.png")],
                   input=dot.encode(), check=True)
    print("wrote", name)


save("pda_comments", COMMENT_DPDA.to_dot(labels={
    ("q0", "q0"): ["t, Z / Z"], ("q0", "q1"): ["O, Z / OZ"],
    ("q1", "q1"): ["t, O / O", "O, O / OO", "C, O / ε"], ("q1", "q0"): ["ε, Z / Z"]}))
save("dfa_c_comments", """digraph C {
  rankdir=LR; bgcolor=white;
  node [shape=circle fontname="Helvetica" fontsize=12];
  edge [fontname="Helvetica" fontsize=10];
  start [shape=point width=0.08];
  out [shape=doublecircle label="out"]; in [label="in"];
  start -> out;
  out -> out [label="t"]; out -> in [label="O (/*)"];
  in -> in [label="t, O"]; in -> out [label="C (*/)"];
}""")
save("npda_hairpin", HAIRPIN_NPDA.to_dot(labels={
    ("s", "q"): ["x, Z / xZ"], ("q", "q"): ["x, X / xX"],
    ("q", "l0"): ["ε, X / X  (guess: loop starts)"],
    ("l0", "l1"): ["x, X / X"], ("l1", "l2"): ["x, X / X"], ("l2", "l3"): ["x, X / X"],
    ("l3", "l3"): ["x, X / X"], ("l3", "p"): ["ε, X / X  (guess: loop ends)"],
    ("p", "p"): ["x̄, x / ε"], ("p", "f"): ["ε, Z / Z"]}))
save("npda_ijk", IJK_NPDA.to_dot(labels={
    ("s", "a1"): ["ε, Z / Z  (guess i = j)"], ("s", "a2"): ["ε, Z / Z  (guess j = k)"],
    ("a1", "a1"): ["a, Y / XY"], ("a1", "b1"): ["b, X / ε"], ("b1", "b1"): ["b, X / ε"],
    ("a1", "c1"): ["ε, Z / Z"], ("b1", "c1"): ["ε, Z / Z"], ("c1", "c1"): ["c, Z / Z"],
    ("a2", "a2"): ["a, Z / Z"], ("a2", "b2"): ["ε, Z / Z"], ("b2", "b2"): ["b, Y / XY"],
    ("b2", "c2"): ["c, X / ε"], ("c2", "c2"): ["c, X / ε"],
    ("b2", "f2"): ["ε, Z / Z"], ("c2", "f2"): ["ε, Z / Z"]}))

for k, t in enumerate(G1.trees(list("a|b*")), 1):
    save(f"tree_regex_ambiguous_{k}", tree_to_dot(t, f"G1, tree {k} of a|b*"))
save("tree_regex_revised", tree_to_dot(G1_REVISED.trees(list("a|b*"))[0], "G1′ (only tree)"))
for k, t in enumerate(G3.trees(list("gcuuuugc")), 1):
    save(f"tree_hairpin_{k}", tree_to_dot(t, f"G3, folding {k} of gcuuuugc"))
