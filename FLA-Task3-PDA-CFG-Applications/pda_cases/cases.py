"""
The four Task 3 case studies.

  1. Regular-expression syntax   - the notation of this course parsed by a CFG:
                                   precedence ambiguity changes the described language
  2. Nested block comments       - /* ... /* ... */ ... */ as in Rust, Swift, Haskell;
                                   C-style (non-nested) comments are regular, nested are not
  3. RNA hairpin (stem-loop)     - complementary stem around a loop of >= 3 bases;
                                   ambiguity = alternative foldings; NPDA guesses the loop
  4. a^i b^j c^k, i = j or j = k - an inherently ambiguous language: no grammar fix exists
"""
import re
from collections import deque

from .grammar import CFG, EPS
from .pda import PDA, cfg_to_pda

# =========================================================================
# 1. Regular-expression syntax over a, b, |, *, ( )
# =========================================================================
RE_T = {"a", "b", "|", "*", "(", ")"}

G1 = CFG("G1 regex (ambiguous)", "R",
         {"R": [["R", "|", "R"], ["R", "R"], ["R", "*"], ["(", "R", ")"], ["a"], ["b"]]},
         RE_T)

G1_REVISED = CFG("G1' regex (precedence: * > concatenation > |)", "R",
                 {"R": [["R", "|", "C"], ["C"]],
                  "C": [["C", "S"], ["S"]],
                  "S": [["S", "*"], ["P"]],
                  "P": [["(", "R", ")"], ["a"], ["b"]]},
                 RE_T)

G1_LL1 = CFG("G1'' regex (LL(1))", "R",
             {"R": [["C", "R'"]],
              "R'": [["|", "C", "R'"], []],
              "C": [["S", "C'"]],
              "C'": [["S", "C'"], []],
              "S": [["P", "S'"]],
              "S'": [["*", "S'"], []],
              "P": [["(", "R", ")"], ["a"], ["b"]]},
             RE_T)

REGEX_PDA = cfg_to_pda(G1_REVISED, "PDA from G1' (one state, empty stack)")

REGEX_STRINGS = {
    "accept": ["a", "a|b*", "ab*", "(a|b)*abb", "a**", "((a)b)|b"],
    "reject": ["", "|a", "a|", "*a", "()", "(a|b", "a||b"],
}


def tree_to_python_regex(node):
    """Fully parenthesised Python regex for a parse tree: every inner node becomes
    a (?: ) group, so the tree alone fixes the meaning."""
    sym, kids, _ = node
    if not kids:
        return "" if sym == EPS else sym
    inner = "".join(tree_to_python_regex(k) for k in kids)
    return f"(?:{inner})"


def words(max_len):
    out = [""]
    for n in range(1, max_len + 1):
        out += [w + c for w in out if len(w) == n - 1 for c in "ab"]
    return out


def regex_language(pattern, max_len=6):
    """The set of words up to max_len that a Python regex accepts."""
    rx = re.compile(pattern)
    return {w for w in words(max_len) if rx.fullmatch(w)}


# =========================================================================
# 2. Nested block comments
# =========================================================================
# Tokens: O = "/*", C = "*/", t = a run of ordinary text
CM_T = {"O", "C", "t"}

G2 = CFG("G2 comments (ambiguous)", "P",
         {"P": [["P", "P"], ["O", "P", "C"], ["O", "C"], ["t"]]}, CM_T)

G2_REVISED = CFG("G2' comments (revised)", "P",
                 {"P": [["X", "P"], []],
                  "X": [["t"], ["O", "P", "C"]]}, CM_T)


def _comment_dpda():
    d = {("q0", "t", "Z"): [("q0", ("Z",))],
         ("q0", "O", "Z"): [("q1", ("O", "Z"))],
         ("q1", "t", "O"): [("q1", ("O",))],
         ("q1", "O", "O"): [("q1", ("O", "O"))],
         ("q1", "C", "O"): [("q1", ())],
         ("q1", "ε", "Z"): [("q0", ("Z",))]}
    return PDA("M2: DPDA for nested comments", ["q0", "q1"], ["O", "C", "t"], ["O", "Z"], d,
               "q0", "Z", final={"q0"})


COMMENT_DPDA = _comment_dpda()


def flat_comment_ok(tokens):
    """C rule (regular): the first */ closes the comment; /* inside is plain text;
    a */ outside any comment is an error. Two states, no stack."""
    inside = False
    for t in tokens:
        if t == "O":
            inside = True
        elif t == "C":
            if not inside:
                return False
            inside = False
    return not inside


def comment_tokens(line):
    """Lexer: /* -> O, */ -> C, every run of other characters -> t."""
    out, k = [], 0
    while k < len(line):
        two = line[k:k + 2]
        if two == "/*":
            out.append("O")
            k += 2
        elif two == "*/":
            out.append("C")
            k += 2
        else:
            if not out or out[-1] != "t":
                out.append("t")
            k += 1
    return out


CODE_LINES = {
    "accept": ["x = 1; /* note */ y = 2;",
               "/* outer /* inner */ still outer */ run();",
               "/* /* /* deep */ */ */",
               "a /* b */ c /* d /* e */ f */ g",
               "return 0; // no block comment here"],
    "reject": ["x = 1; /* never closed",
               "y = 2; */ stray close",
               "/* outer /* inner */ forgot outer",
               "/* a */ */ b",
               "*/ /*"],
}

COMMENT_STRINGS = {
    "accept": ["", "t", "OC", "OtC", "tOOtCCt", "OtCtOC"],
    "reject": ["O", "C", "OOC", "OCC", "CO", "tOtOtC"],
}

# =========================================================================
# 3. RNA hairpin (stem-loop)
# =========================================================================
BASES = "acgu"
PAIR = {"a": "u", "u": "a", "g": "c", "c": "g"}       # Watson-Crick pairs

_pairs = [[x, "S", PAIR[x]] for x in BASES]
_closing = [[x, "L", PAIR[x]] for x in BASES]
G3 = CFG("G3 hairpin (ambiguous)", "S",
         {"S": _pairs + _closing,
          "L": [["N", "N", "N"], ["N", "L"]],
          "N": [[b] for b in BASES]}, set(BASES))

# Revised: the stem is as long as possible while the loop keeps >= 3 bases.
# A loop of 3 or 4 bases can never be shortened by another pair; a longer loop
# must not start and end with a complementary pair.
_unpaired_ends = [[x, "M", y] for x in BASES for y in BASES if PAIR[x] != y]
G3_REVISED = CFG("G3' hairpin (maximal stem)", "S",
                 {"S": [[x, "T", PAIR[x]] for x in BASES],
                  "T": [[x, "T", PAIR[x]] for x in BASES] + [["L"]],
                  "L": [["N", "N", "N"], ["N", "N", "N", "N"]] + _unpaired_ends,
                  "M": [["N", "N", "N"], ["N", "M"]],
                  "N": [[b] for b in BASES]}, set(BASES))


def hairpin_oracle(s):
    """Some stem length k >= 1 pairs the outer bases and leaves a loop of >= 3."""
    n = len(s)
    for k in range(1, (n - 3) // 2 + 1):
        if all(PAIR[s[i]] == s[n - 1 - i] for i in range(k)):
            return True
    return False


def foldings(s):
    """All stem lengths k that fold s into a hairpin (one per parse tree of G3)."""
    n = len(s)
    out = []
    for k in range(1, (n - 3) // 2 + 1):
        if all(PAIR[s[i]] == s[n - 1 - i] for i in range(k)):
            out.append(k)
        else:
            break
    return out


def _hairpin_npda():
    """Push the 5' half of the stem; guess where the loop starts (>= 1 pair pushed);
    read >= 3 loop bases; guess where the loop ends; pop complementary bases."""
    d = {}
    for x in BASES:
        d[("s", x, "Z")] = [("q", (x, "Z"))]                 # first stem base
        for X in BASES:
            d[("q", x, X)] = [("q", (x, X))]                  # more stem bases
    for X in BASES:
        d[("q", "ε", X)] = [("l0", (X,))]                     # guess: loop starts
        for x in BASES:
            d[("l0", x, X)] = [("l1", (X,))]
            d[("l1", x, X)] = [("l2", (X,))]
            d[("l2", x, X)] = [("l3", (X,))]
            d[("l3", x, X)] = [("l3", (X,))]                  # loop of >= 3
        d[("l3", "ε", X)] = [("p", (X,))]                     # guess: loop ends
        d[("p", PAIR[X], X)] = [("p", ())]                    # pop a complementary base
    d[("p", "ε", "Z")] = [("f", ("Z",))]
    return PDA("M3: NPDA for an RNA hairpin", ["s", "q", "l0", "l1", "l2", "l3", "p", "f"],
               list(BASES), list(BASES) + ["Z"], d, "s", "Z", final={"f"})


HAIRPIN_NPDA = _hairpin_npda()

HAIRPIN_STRINGS = {
    "accept": ["gaaac", "gcuuuugc", "acgaaacgu", "ggacuucggucc", "auaaaau", "gaaauc"],
    "reject": ["gac", "gaaag", "acgu", "gcaaagg", "", "aaaaa"],
}

# =========================================================================
# 4. a^i b^j c^k with i = j or j = k (inherently ambiguous)
# =========================================================================
G4 = CFG("G4 i = j or j = k", "S",
         {"S": [["X", "C"], ["A", "Y"]],
          "X": [["a", "X", "b"], []],
          "C": [["c", "C"], []],
          "A": [["a", "A"], []],
          "Y": [["b", "Y", "c"], []]},
         {"a", "b", "c"})


def _ijk_npda():
    """Guess the branch at the start: i = j (push a's, pop on b's, then any c's)
    or j = k (skip a's, push b's, pop on c's)."""
    d = {("s", "ε", "Z"): [("a1", ("Z",)), ("a2", ("Z",))]}
    for X in ("Z", "X"):
        d[("a1", "a", X)] = [("a1", ("X", X))]
    d[("a1", "b", "X")] = [("b1", ())]
    d[("b1", "b", "X")] = [("b1", ())]
    for st in ("a1", "b1"):
        d[(st, "ε", "Z")] = [("c1", ("Z",))]
    d[("c1", "c", "Z")] = [("c1", ("Z",))]
    d[("a2", "a", "Z")] = [("a2", ("Z",))]
    d[("a2", "ε", "Z")] = [("b2", ("Z",))]
    for X in ("Z", "X"):
        d[("b2", "b", X)] = [("b2", ("X", X))]
    d[("b2", "c", "X")] = [("c2", ())]
    d[("c2", "c", "X")] = [("c2", ())]
    for st in ("b2", "c2"):
        d[(st, "ε", "Z")] = [("f2", ("Z",))]
    return PDA("M4: NPDA for i = j or j = k", ["s", "a1", "b1", "c1", "a2", "b2", "c2", "f2"],
               ["a", "b", "c"], ["X", "Z"], d, "s", "Z", final={"c1", "f2"})


IJK_NPDA = _ijk_npda()


def ijk_oracle(s):
    m = re.fullmatch(r"(a*)(b*)(c*)", s)
    if not m:
        return False
    i, j, k = (len(g) for g in m.groups())
    return i == j or j == k


IJK_STRINGS = {
    "accept": ["", "a", "ab", "abccc", "aabbc", "bc", "abc", "aabbcc"],
    "reject": ["abb", "aabccc", "aaabcc", "ba", "acb", "aabbbc"],
}


def count_accepting_runs(pda, tokens, limit=10_000):
    """Number of distinct accepting computations (DFS over IDs)."""
    toks = list(tokens)
    n = len(toks)
    found = 0
    todo = deque([(pda.start, 0, (pda.bottom,))])
    seen_steps = 0
    while todo and seen_steps < limit:
        q, i, stack = todo.pop()
        seen_steps += 1
        if i == n and q in pda.final:
            found += 1
        if not stack:
            continue
        top = stack[0]
        moves = []
        if i < n:
            moves += [(p, i + 1, push) for p, push in pda.delta.get((q, toks[i], top), [])]
        moves += [(p, i, push) for p, push in pda.delta.get((q, "ε", top), [])]
        for p, j, push in moves:
            new = push + stack[1:]
            if len(new) <= 2 * n + 3:
                todo.append((p, j, new))
    return found


ALL_GRAMMARS = [(G1, 6), (G1_REVISED, 6), (G1_LL1, 6), (G2, 8), (G2_REVISED, 8),
                (G3, 8), (G3_REVISED, 8), (G4, 9)]
