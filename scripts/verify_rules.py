#!/usr/bin/env python3
"""
verify_rules.py — check which Jena .rules actually fired, by testing
each rule's head-clause pattern against a Fuseki SPARQL endpoint.

Usage:
    python3 verify_rules.py --rules-dir ./rules --endpoint http://localhost:3030/VeterinaryInferred/query

No third-party dependencies (uses urllib), so it runs anywhere Python 3 is available.

How it works:
  1. Parses every .rules file in --rules-dir.
  2. Extracts @prefix declarations (for building valid SPARQL PREFIX lines).
  3. For each named rule, extracts ALL head clauses (the part after '->',
     before the closing ']') as a group — keeping each clause's original
     variable names (?case, ?obs, etc.) rather than checking them in
     isolation.
  4. Builds ONE conjunctive SPARQL query per rule: every head clause of
     that rule, joined together as a single WHERE block, so a clause with
     a constant predicate+object (e.g. vet:hasDiagnosis obo:MONDO_0005027)
     is required to co-occur, on the SAME bound subject, with every other
     clause in that rule's head. Counts DISTINCT bindings of the rule's
     primary subject variable (the subject of its first head clause).
  5. Prints a table: rule name -> fired? -> distinct-entity count.

This fixes a real ambiguity from checking clauses one at a time: two
different rules can produce head clauses that share a predicate+object
(e.g. several rules asserting the same status literal) — checking each
clause alone can't tell those apart, but requiring the WHOLE head to land
on one subject can, as long as the rule has at least one clause with a
constant object to anchor the join.

Caveats (read before trusting the output blindly):
  - Rules whose ENTIRE head is variables-only (no constant anywhere to
    anchor on) can't be meaningfully checked this way — reported as
    "SKIPPED (no constant in head)". This is rare; most diagnostic/status
    rules assert at least one fixed code or literal.
  - Still checks whether the CONCLUSION exists, not that these exact
    antecedents produced it — if two rules assert an IDENTICAL full set of
    head clauses (same predicates AND same objects, not just one shared
    predicate), this still can't tell them apart. That's a much narrower
    case than before.
  - Rules with zero hits could mean either "never fired" (no case in the
    KG currently matches the body) or "misparsed" — check server logs for
    that rule name if you expect it to have fired and it shows 0.
"""

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

RULE_BLOCK_RE = re.compile(r"\[\s*([A-Za-z_][A-Za-z0-9_]*)\s*:(.*?)\]", re.DOTALL)
PREFIX_RE = re.compile(r"@prefix\s+(\w+):\s*<([^>]+)>\s*\.")
TRIPLE_RE = re.compile(r"\(([^()]*)\)")


def tokenize_triple(s: str):
    """Split a triple's inner text into up to 3 tokens, respecting quoted strings."""
    tokens = []
    i = 0
    s = s.strip()
    while i < len(s):
        if s[i].isspace():
            i += 1
            continue
        if s[i] == '"':
            j = s.index('"', i + 1)
            tokens.append(s[i:j + 1])
            i = j + 1
        else:
            j = i
            while j < len(s) and not s[j].isspace():
                j += 1
            tokens.append(s[i:j])
            i = j
    return tokens


def parse_rules_file(path: Path):
    text = path.read_text(encoding="utf-8")
    prefixes = dict(PREFIX_RE.findall(text))
    # Strip whole-line comments before block matching so they don't
    # interfere with bracket matching; keep inline ones, we don't need
    # to evaluate them for this script.
    rules = []
    for m in RULE_BLOCK_RE.finditer(text):
        name, body_text = m.group(1), m.group(2)
        if "->" not in body_text:
            continue  # backward-chaining rule or malformed; skip
        head_text = body_text.split("->", 1)[1]
        head_triples = []
        for tm in TRIPLE_RE.finditer(head_text):
            toks = tokenize_triple(tm.group(1))
            if len(toks) == 3:
                head_triples.append(tuple(toks))
        rules.append((name, head_triples, str(path.name)))
    return prefixes, rules


def is_constant(tok: str) -> bool:
    return not tok.startswith("?")


def sparql_count_distinct(endpoint: str, prefixes: dict, var: str, patterns: list) -> int:
    prefix_lines = "\n".join(f"PREFIX {p}: <{u}>" for p, u in prefixes.items())
    where_clauses = " . ".join(f"{s} {p} {o}" for (s, p, o) in patterns)
    query = f"{prefix_lines}\nSELECT (COUNT(DISTINCT {var}) AS ?c) WHERE {{ {where_clauses} }}"
    data = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
    req = urllib.request.Request(endpoint, data=data, headers={
        "Accept": "application/sparql-results+json",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
    return int(result["results"]["bindings"][0]["c"]["value"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules-dir", required=True)
    ap.add_argument("--endpoint", required=True,
                     help="Inferred SPARQL query endpoint, e.g. http://localhost:3030/VeterinaryInferred/query")
    ap.add_argument("--raw-endpoint",
                     help="Raw (non-reasoned) SPARQL query endpoint, e.g. http://localhost:3030/Veterinary/query. "
                          "If given, subtracts raw matches so a rule only reads FIRED when the reasoner "
                          "genuinely added the pattern, not when it was already present in base data.")
    args = ap.parse_args()

    rules_dir = Path(args.rules_dir)
    files = sorted(rules_dir.glob("*.rules"))
    if not files:
        print(f"No .rules files found in {rules_dir}", file=sys.stderr)
        sys.exit(1)

    all_prefixes = {}
    all_rules = []
    for f in files:
        prefixes, rules = parse_rules_file(f)
        all_prefixes.update(prefixes)
        all_rules.extend(rules)

    if args.raw_endpoint:
        print(f"{'FILE':<28} {'RULE':<32} {'STATUS':<44} {'RAW':>6} {'INFER':>6} {'NEW':>6}")
    else:
        print(f"{'FILE':<28} {'RULE':<32} {'STATUS':<40} DISTINCT")
    print("-" * 130)

    for name, head_triples, fname in all_rules:
        if not head_triples:
            if args.raw_endpoint:
                print(f"{fname:<28} {name:<32} {'SKIPPED (no head triples)':<44} {'-':>6} {'-':>6} {'-':>6}")
            else:
                print(f"{fname:<28} {name:<32} {'SKIPPED (no head triples)':<40} -")
            continue

        has_constant_anchor = any(is_constant(p) and is_constant(o) for (s, p, o) in head_triples)
        if not has_constant_anchor:
            if args.raw_endpoint:
                print(f"{fname:<28} {name:<32} {'SKIPPED (no constant in head)':<44} {'-':>6} {'-':>6} {'-':>6}")
            else:
                print(f"{fname:<28} {name:<32} {'SKIPPED (no constant in head)':<40} -")
            continue

        subject_var = head_triples[0][0]
        try:
            infer_count = sparql_count_distinct(args.endpoint, all_prefixes, subject_var, head_triples)
            if args.raw_endpoint:
                try:
                    raw_count = sparql_count_distinct(args.raw_endpoint, all_prefixes, subject_var, head_triples)
                except Exception:
                    raw_count = 0
                new_count = max(infer_count - raw_count, 0)
                status = "FIRED (net new)" if new_count > 0 else (
                    "PRESENT BUT NOT NEW (already in raw data)" if infer_count > 0 else "NOT FOUND")
                print(f"{fname:<28} {name:<32} {status:<44} {raw_count:>6} {infer_count:>6} {new_count:>6}")
            else:
                status = "FIRED (all head clauses joined)" if infer_count > 0 else "NOT FOUND"
                print(f"{fname:<28} {name:<32} {status:<40} {infer_count}")
        except Exception as e:
            if args.raw_endpoint:
                print(f"{fname:<28} {name:<32} {'QUERY ERROR':<44} {'-':>6} {'-':>6} {str(e)[:30]:>6}")
            else:
                print(f"{fname:<28} {name:<32} {'QUERY ERROR':<40} {e}")


if __name__ == "__main__":
    main()