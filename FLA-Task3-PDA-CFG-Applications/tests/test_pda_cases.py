"""
27 checks for the Task 3 case studies. Independent oracles: Python's `re`
module for regex meaning, a depth counter for comments, a brute-force stem
search for RNA hairpins and a regex + length comparison for a^i b^j c^k.
"""
import random
import re
import sys
from itertools import product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pda_cases.cases import (  # noqa: E402
    CODE_LINES, COMMENT_DPDA, COMMENT_STRINGS, G1, G1_LL1, G1_REVISED, G2, G2_REVISED, G3,
    G3_REVISED, G4, HAIRPIN_NPDA, HAIRPIN_STRINGS, IJK_NPDA, IJK_STRINGS, REGEX_PDA,
    REGEX_STRINGS, comment_tokens, count_accepting_runs, flat_comment_ok, foldings,
    hairpin_oracle, ijk_oracle, regex_language, tree_to_python_regex)
from pda_cases.ll1 import ll1_table, predictive_parse  # noqa: E402


def all_strings(symbols, max_len):
    for n in range(max_len + 1):
        for t in product(symbols, repeat=n):
            yield list(t)


# ============================================================ 1. regex syntax
def test_regex_listed_strings():                                      # 1
    for s in REGEX_STRINGS["accept"]:
        t = list(s)
        assert G1_REVISED.derives(t) and REGEX_PDA.accepts(t) and predictive_parse(G1_LL1, t)[0], s
    for s in REGEX_STRINGS["reject"]:
        t = list(s)
        assert not (G1_REVISED.derives(t) or REGEX_PDA.accepts(t) or predictive_parse(G1_LL1, t)[0]), s


def test_regex_grammars_agree_exhaustively():                         # 2
    """All 55 987 token strings up to length 6 over {a, b, |, *, (, )}."""
    count = 0
    for t in all_strings(["a", "b", "|", "*", "(", ")"], 6):
        count += 1
        ref = G1.derives(t)
        assert G1_REVISED.derives(t) == ref and G1_LL1.derives(t) == ref, t
        assert predictive_parse(G1_LL1, t)[0] == ref, t
    assert count == 55987


def test_regex_ambiguity_changes_the_language():                      # 3
    for text, word in (("a|b*", "ab"), ("ab*", "abab"), ("a|ba", "aa")):
        trees = G1.trees(list(text))
        assert len(trees) == 2
        verdicts = {word in regex_language(tree_to_python_regex(t), len(word)) for t in trees}
        assert verdicts == {True, False}, text


def test_revised_regex_tree_matches_python_precedence():              # 4
    """For random valid regexes, the single G1' tree means what Python's `re` means."""
    rnd = random.Random(273)
    toks = ["a", "b", "|", "*", "(", ")"]
    checked = 0
    while checked < 300:
        t = [rnd.choice(toks) for _ in range(rnd.randint(1, 7))]
        if not G1_REVISED.derives(t) or "**" in "".join(t):
            continue
        (tree,) = G1_REVISED.trees(t)
        assert regex_language(tree_to_python_regex(tree), 5) == regex_language("".join(t), 5), t
        checked += 1


def test_regex_pda_random():                                          # 5
    rnd = random.Random(5)
    toks = ["a", "b", "|", "*", "(", ")"]
    for _ in range(1500):
        t = [rnd.choice(toks) for _ in range(rnd.randint(0, 6))]
        assert REGEX_PDA.accepts(t) == G1_REVISED.derives(t), t


def test_regex_ll1_and_pda_numbers():                                 # 6
    assert [len(ll1_table(g)[1]) for g in (G1, G1_REVISED, G1_LL1)] == [3, 9, 0]
    assert not REGEX_PDA.is_deterministic()
    run = REGEX_PDA.run(list("a|b*"))
    assert run["accepted"] and run["explored"] == 120
    ok, steps = predictive_parse(G1_LL1, list("a|b*"))
    assert ok and len(steps) == 19


# ===================================================== 2. nested comments
def depth_oracle(tokens):
    depth = 0
    for t in tokens:
        depth += t == "O"
        depth -= t == "C"
        if depth < 0:
            return False
    return depth == 0


def test_comments_listed_strings():                                   # 7
    for s in COMMENT_STRINGS["accept"]:
        assert COMMENT_DPDA.accepts(list(s)) and G2_REVISED.derives(list(s)), s
    for s in COMMENT_STRINGS["reject"]:
        assert not COMMENT_DPDA.accepts(list(s)) and not G2_REVISED.derives(list(s)), s


def test_comments_exhaustive():                                       # 8
    """All 88 573 token strings up to length 10 over {O, C, t}."""
    count = 0
    for t in all_strings("OCt", 10):
        count += 1
        ref = depth_oracle(t)
        assert COMMENT_DPDA.accepts(t) == ref, t
        if len(t) <= 8:
            assert G2_REVISED.derives(t) == ref, t
            assert G2.derives(t) == (ref and len(t) > 0), t
    assert count == 88573


def test_comment_tree_counts():                                       # 9
    assert [G2.count_parse_trees(list("t" * k)) for k in range(1, 7)] == [1, 1, 2, 5, 14, 42]
    assert all(G2_REVISED.count_parse_trees(s) == 1 for s in G2_REVISED.strings_up_to(8))


def test_nested_vs_c_style_on_source_lines():                         # 10
    for line in CODE_LINES["accept"]:
        assert COMMENT_DPDA.accepts(comment_tokens(line)), line
    for line in CODE_LINES["reject"]:
        assert not COMMENT_DPDA.accepts(comment_tokens(line)), line
    # the two rules disagree on these lines, in both directions
    assert not flat_comment_ok(comment_tokens("/* outer /* inner */ still outer */ run();"))
    assert flat_comment_ok(comment_tokens("/* outer /* inner */ forgot outer"))


def test_comment_dpda_deterministic():                                # 11
    assert COMMENT_DPDA.is_deterministic() and COMMENT_DPDA.states == ["q0", "q1"]
    run = COMMENT_DPDA.run(list("OtOtCC"))
    assert COMMENT_DPDA.show_run(run["path"]) == (
        "(q0,OtOtCC,Z) ⊢ (q1,tOtCC,OZ) ⊢ (q1,OtCC,OZ) ⊢ (q1,tCC,OOZ) ⊢ (q1,CC,OOZ) ⊢ "
        "(q1,C,OZ) ⊢ (q1,ε,Z) ⊢ (q0,ε,Z)")


def test_pumping_lemma_for_nested_comments():                         # 12
    for p in range(1, 9):
        s = ["O"] * p + ["C"] * p
        for i in range(p):
            for j in range(i + 1, p + 1):
                assert not COMMENT_DPDA.accepts(s[:i] + s[i:j] * 2 + s[j:])


# ========================================================== 3. RNA hairpin
def test_hairpin_listed_strings():                                    # 13
    for s in HAIRPIN_STRINGS["accept"]:
        assert HAIRPIN_NPDA.accepts(list(s)) and G3_REVISED.derives(list(s)), s
    for s in HAIRPIN_STRINGS["reject"]:
        assert not HAIRPIN_NPDA.accepts(list(s)) and not G3_REVISED.derives(list(s)), s


def test_hairpin_exhaustive():                                        # 14
    """All 21 845 sequences up to length 7 over {a, c, g, u}."""
    count = 0
    for t in all_strings("acgu", 7):
        count += 1
        s = "".join(t)
        ref = hairpin_oracle(s)
        assert HAIRPIN_NPDA.accepts(t) == ref, s
        assert G3.count_parse_trees(t) == len(foldings(s)), s
        assert G3_REVISED.count_parse_trees(t) == (1 if ref else 0), s
    assert count == 21845


def test_hairpin_random_long():                                       # 15
    rnd = random.Random(15)
    pair = {"a": "u", "u": "a", "g": "c", "c": "g"}
    for _ in range(400):
        stem = "".join(rnd.choice("acgu") for _ in range(rnd.randint(1, 5)))
        loop = "".join(rnd.choice("acgu") for _ in range(rnd.randint(1, 6)))
        s = stem + loop + "".join(pair[x] for x in reversed(stem))
        if rnd.random() < 0.3:
            k = rnd.randrange(len(s))
            s = s[:k] + rnd.choice("acgu") + s[k + 1:]
        assert HAIRPIN_NPDA.accepts(list(s)) == hairpin_oracle(s), s
        assert G3_REVISED.count_parse_trees(list(s)) == (1 if hairpin_oracle(s) else 0), s


def test_hairpin_foldings_are_the_ambiguity():                        # 16
    assert foldings("ggacuucggucc") == [1, 2, 3, 4]
    assert G3.count_parse_trees(list("ggacuucggucc")) == 4
    assert G3_REVISED.count_parse_trees(list("ggacuucggucc")) == 1


def test_hairpin_npda_nondeterministic():                             # 17
    assert not HAIRPIN_NPDA.is_deterministic()
    reasons = {why for *_, why in HAIRPIN_NPDA.choice_points()}
    assert any("ε-move" in r for r in reasons)


# ================================================== 4. i = j or j = k
def test_ijk_listed_strings():                                        # 18
    for s in IJK_STRINGS["accept"]:
        assert IJK_NPDA.accepts(list(s)) and G4.derives(list(s)), s
    for s in IJK_STRINGS["reject"]:
        assert not IJK_NPDA.accepts(list(s)) and not G4.derives(list(s)), s


def test_ijk_exhaustive():                                            # 19
    """All 29 524 strings up to length 9 over {a, b, c}."""
    count = 0
    for t in all_strings("abc", 9):
        count += 1
        s = "".join(t)
        ref = ijk_oracle(s)
        assert IJK_NPDA.accepts(t) == ref, s
        assert G4.derives(t) == ref, s
    assert count == 29524


def test_ijk_ambiguous_exactly_on_anbncn():                           # 20
    for t in all_strings("abc", 9):
        s = "".join(t)
        m = re.fullmatch(r"(a*)(b*)(c*)", s)
        equal = bool(m) and len(m.group(1)) == len(m.group(2)) == len(m.group(3))
        assert (G4.count_parse_trees(t) == 2) == equal, s
        assert G4.count_parse_trees(t) <= 2


def test_ijk_pda_has_two_runs_on_anbncn():                            # 21
    for n in range(4):
        s = "a" * n + "b" * n + "c" * n
        assert count_accepting_runs(IJK_NPDA, s) == 2
    assert count_accepting_runs(IJK_NPDA, "aabbc") == 1
    assert count_accepting_runs(IJK_NPDA, "abccc") == 1


def test_ijk_npda_nondeterministic():                                 # 22
    assert not IJK_NPDA.is_deterministic()


# ================================================================ general
def test_revised_grammars_same_language():                            # 23
    assert G1.strings_up_to(6) == G1_REVISED.strings_up_to(6) == G1_LL1.strings_up_to(6)
    assert G2_REVISED.strings_up_to(8) == G2.strings_up_to(8) | {()}
    assert G3.strings_up_to(8) == G3_REVISED.strings_up_to(8)


def test_revised_grammars_unambiguous():                              # 24
    for g, n in ((G1_REVISED, 6), (G1_LL1, 6), (G2_REVISED, 8), (G3_REVISED, 8)):
        assert all(g.count_parse_trees(s) == 1 for s in g.strings_up_to(n)), g.name


def test_original_grammars_ambiguous():                               # 25
    for g, n in ((G1, 6), (G2, 8), (G3, 8), (G4, 9)):
        assert any(g.count_parse_trees(s) > 1 for s in g.strings_up_to(n)), g.name


def test_lexer_examples():                                            # 26
    assert comment_tokens("a /* b */ c") == ["t", "O", "t", "C", "t"]
    assert comment_tokens("/**/") == ["O", "C"]


def test_c_style_comments_are_regular():                              # 27
    """The flat (C) rule is decided by a 2-state scan; check it against a regex."""
    rx = re.compile(r"(t|O[tO]*C)*")
    for t in all_strings("OCt", 8):
        assert flat_comment_ok(t) == bool(rx.fullmatch("".join(t))), t
