"""
Terminal demo for the four Task 3 case studies.

  python -m pda_cases.cli regex      regular-expression syntax (ambiguity, CFG -> PDA, LL(1))
  python -m pda_cases.cli comments   nested block comments vs C-style comments
  python -m pda_cases.cli rna        RNA hairpin: foldings, maximal-stem grammar, NPDA
  python -m pda_cases.cli ijk        a^i b^j c^k with i = j or j = k (inherent ambiguity)
  python -m pda_cases.cli ambiguity  bounded ambiguity check of every grammar
  python -m pda_cases.cli all        everything above (default)
"""
import sys

from .cases import (ALL_GRAMMARS, CODE_LINES, COMMENT_DPDA, COMMENT_STRINGS, G1, G1_LL1,
                    G1_REVISED, G2, G2_REVISED, G3, G3_REVISED, G4, HAIRPIN_NPDA,
                    HAIRPIN_STRINGS, IJK_NPDA, IJK_STRINGS, REGEX_PDA, REGEX_STRINGS,
                    comment_tokens, count_accepting_runs, flat_comment_ok, foldings,
                    regex_language, tree_to_python_regex)
from .grammar import EPS
from .ll1 import ll1_table, predictive_parse

COLOUR = sys.stdout.isatty() or "--color" in sys.argv
GREEN, RED, BOLD, DIM, END = ("\033[32m", "\033[31m", "\033[1m", "\033[2m", "\033[0m") \
    if COLOUR else ("",) * 5


def heading(text):
    print(f"\n{BOLD}{'=' * 74}\n{text}\n{'=' * 74}{END}")


def sub(text):
    print(f"\n{BOLD}-- {text}{END}")


def yes(ok):
    return f"{GREEN}ACCEPT{END}" if ok else f"{RED}REJECT{END}"


def pad(text, width):
    return text + " " * max(0, width - len(text.replace(GREEN, "").replace(RED, "").replace(END, "")))


def grammar(g):
    print(f"   {g.name}")
    for line in g.productions_text():
        print(f"     {line}")


def show_moves(pda, tokens):
    r = pda.run(tokens)
    print("   " + pda.show_run(r["path"]))
    return r


def readable(pattern):
    """Turn the generated (?:...) groups back into plain parentheses for display."""
    out = pattern
    for _ in range(12):
        out = out.replace("(?:a)", "a").replace("(?:b)", "b")
    return out.replace("(?:", "(")


# ---------------------------------------------------------------------------
def regex():
    heading("CASE STUDY 1 - Regular-expression syntax")
    for g in (G1, G1_REVISED, G1_LL1):
        grammar(g)
    for text, probe in (("a|b*", "ab"), ("ab*", "abab"), ("a|ba", "aa")):
        sub(f"G1 on {text}: what does each tree mean? (probe word: {probe})")
        for k, t in enumerate(G1.trees(list(text)), 1):
            pat = tree_to_python_regex(t)
            lang = sorted(regex_language(pat, 3), key=lambda w: (len(w), w))
            inside = probe in regex_language(pat, len(probe))
            print(f"   tree {k}: {readable(pat):<28} words ≤ 3: {{{', '.join(w or EPS for w in lang)}}}"
                  f"   {probe} ∈ L: {inside}")
    t = G1_REVISED.trees(list("a|b*"))
    sub(f"G1′ on a|b*: {len(t)} tree")
    print("   LMD: " + " ⇒ ".join(G1_REVISED.show_form(f) for f in G1_REVISED.leftmost(t[0])))
    sub("CFG → PDA construction from G1′")
    for line in REGEX_PDA.transitions_text():
        print("   " + line)
    r = REGEX_PDA.run(list("a|b*"))
    print(f"   deterministic: {REGEX_PDA.is_deterministic()}; configurations explored on a|b*: "
          f"{r['explored']} -> {yes(r['accepted'])}")
    sub("LL(1) conflicts per grammar")
    for g in (G1, G1_REVISED, G1_LL1):
        print(f"   {g.name:<52}{len(ll1_table(g)[1])} conflicting cell(s)")
    _, _, first, follow = ll1_table(G1_LL1)
    for A in G1_LL1.prods:
        print(f"   FIRST({A}) = {{{', '.join(sorted(first[A]))}}}   "
              f"FOLLOW({A}) = {{{', '.join(sorted(follow[A]))}}}")
    ok, steps = predictive_parse(G1_LL1, list("a|b*"))
    sub(f"Predictive parser on a|b* -> {yes(ok)} in {len(steps)} steps")
    print(f"   {'stack (top at left)':<26}{'input':<14}action")
    for st, inp, act in steps:
        print(f"   {st:<26}{inp:<14}{act}")
    sub("Test strings")
    print(f"   {'input':<12}{'G1′':<9}{'PDA':<9}{'LL(1)':<9}trees in G1")
    for s in REGEX_STRINGS["accept"] + REGEX_STRINGS["reject"]:
        t = list(s)
        print(f"   {s or 'ε':<12}{pad(yes(G1_REVISED.derives(t)), 9)}{pad(yes(REGEX_PDA.accepts(t)), 9)}"
              f"{pad(yes(predictive_parse(G1_LL1, t)[0]), 9)}{G1.count_parse_trees(t)}")


def comments():
    heading("CASE STUDY 2 - Nested block comments")
    grammar(G2)
    grammar(G2_REVISED)
    print(f"   trees of t^k in G2: {[G2.count_parse_trees(list('t' * k)) for k in range(1, 7)]}"
          f"   in G2′: {[G2_REVISED.count_parse_trees(list('t' * k)) for k in range(1, 7)]}")
    sub("DPDA M2 (accepts by final state q0)")
    for line in COMMENT_DPDA.transitions_text():
        print("   " + line)
    print(f"   deterministic: {COMMENT_DPDA.is_deterministic()}")
    for s in ["OtOtCC", "OtCC"]:
        sub(f"Stack moves on {s} -> {yes(COMMENT_DPDA.accepts(list(s)))}")
        show_moves(COMMENT_DPDA, list(s))
    sub("Source lines: nested rule (DPDA) versus C rule (2-state DFA)")
    print(f"   {'nested':<9}{'C-style':<9}tokens        line")
    for line in CODE_LINES["accept"] + CODE_LINES["reject"]:
        toks = comment_tokens(line)
        print(f"   {pad(yes(COMMENT_DPDA.accepts(toks)), 9)}{pad(yes(flat_comment_ok(toks)), 9)}"
              f"{''.join(toks):<14}{line}")
    sub("Token strings")
    for s in COMMENT_STRINGS["accept"] + COMMENT_STRINGS["reject"]:
        print(f"   {s or 'ε':<10} G2′: {yes(G2_REVISED.derives(list(s)))}   M2: {yes(COMMENT_DPDA.accepts(list(s)))}")


def rna():
    heading("CASE STUDY 3 - RNA hairpin (stem-loop)")
    grammar(G3)
    grammar(G3_REVISED)
    sub("Foldings: each parse tree of G3 is one stem length")
    print(f"   {'sequence':<14}{'stem lengths':<16}{'trees G3':>9}{'trees G3′':>11}")
    for s in HAIRPIN_STRINGS["accept"]:
        print(f"   {s:<14}{str(foldings(s)):<16}{G3.count_parse_trees(list(s)):>9}"
              f"{G3_REVISED.count_parse_trees(list(s)):>11}")
    sub("NPDA M3")
    for line in HAIRPIN_NPDA.transitions_text()[:8]:
        print("   " + line)
    print(f"   ... ({len(HAIRPIN_NPDA.transitions_text())} transition groups)")
    print(f"   deterministic: {HAIRPIN_NPDA.is_deterministic()}")
    for s in ["gcuuuugc", "gaaag"]:
        r = HAIRPIN_NPDA.run(list(s))
        sub(f"M3 on {s} -> {yes(r['accepted'])} ({r['explored']} configurations explored)")
        print("   " + HAIRPIN_NPDA.show_run(r["path"]))
    sub("Test strings")
    for s in HAIRPIN_STRINGS["accept"] + HAIRPIN_STRINGS["reject"]:
        print(f"   {s or 'ε':<14} G3′: {yes(G3_REVISED.derives(list(s)))}   M3: {yes(HAIRPIN_NPDA.accepts(list(s)))}")


def ijk():
    heading("CASE STUDY 4 - a^i b^j c^k with i = j or j = k")
    grammar(G4)
    sub("Parse trees and accepting PDA runs")
    print(f"   {'string':<10}{'trees G4':>9}{'accepting runs':>16}")
    for s in ["", "abc", "aabbcc", "aaabbbccc", "aabbc", "abccc"]:
        print(f"   {s or 'ε':<10}{G4.count_parse_trees(list(s)):>9}{count_accepting_runs(IJK_NPDA, s):>16}")
    sub("NPDA M4")
    for line in IJK_NPDA.transitions_text():
        print("   " + line)
    print(f"   deterministic: {IJK_NPDA.is_deterministic()}")
    for s in ["aabbcc", "abccc", "aabccc"]:
        r = IJK_NPDA.run(list(s))
        sub(f"M4 on {s} -> {yes(r['accepted'])}")
        print("   " + IJK_NPDA.show_run(r["path"]))
    sub("Test strings")
    for s in IJK_STRINGS["accept"] + IJK_STRINGS["reject"]:
        print(f"   {s or 'ε':<10} G4: {yes(G4.derives(list(s)))}   M4: {yes(IJK_NPDA.accepts(list(s)))}")


def ambiguity():
    heading("Bounded ambiguity check (parse trees of every short string)")
    print(f"   {'grammar':<48}{'len ≤':>6}{'strings':>9}{'>1 tree':>9}   worst case")
    for g, n in ALL_GRAMMARS:
        counts, worst = g.ambiguity_report(n)
        total = sum(counts.values())
        many = sum(v for k, v in counts.items() if k > 1)
        note = f"{RED}'{worst[0] or EPS}' has {worst[1]} trees{END}" if worst else f"{GREEN}one tree each{END}"
        print(f"   {g.name:<48}{n:>6}{total:>9}{many:>9}   {note}")
    print(f"   {DIM}Ambiguity is undecidable in general: this is evidence, not a proof.{END}")


def main(argv):
    args = [a for a in argv if a != "--color"] or ["all"]
    jobs = {"regex": regex, "comments": comments, "rna": rna, "ijk": ijk, "ambiguity": ambiguity}
    if args[0] == "all":
        for job in jobs.values():
            job()
        return 0
    if args[0] in jobs:
        jobs[args[0]]()
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
