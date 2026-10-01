"""
Searches every literal in the loaded RDF graph for each keyword in
search_terms.json, and for every matching subject prints its full
property set — so a human (ideally with the pathologist) can pick the
right code among near-duplicates (LOINC very often has several codes
for "the same" analyte distinguished only by System/Scale/Method).

Deliberately does NOT try to identify "the" LOINC code per term
automatically — that decision needs a person, same as the vetSNOMED
SCTID lookups earlier. This script only narrows the haystack.

Usage:
    python3 03_candidate_search.py http://localhost:3031/loincscratch/sparql \
        search_terms.json candidates_report.md
"""
import sys
import json
import urllib.parse
import urllib.request


def sparql_select(endpoint: str, query: str) -> list:
    url = endpoint + "?query=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={"Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["results"]["bindings"]


SEARCH_QUERY = """
SELECT DISTINCT ?s WHERE {{
    ?s ?p ?o .
    FILTER(isLiteral(?o))
    FILTER(CONTAINS(LCASE(STR(?o)), "{term}"))
}} LIMIT 15
"""

DUMP_QUERY = "SELECT ?p ?o WHERE {{ <{subject}> ?p ?o }}"


def dump_subject(endpoint, subject):
    lines = []
    for row in sparql_select(endpoint, DUMP_QUERY.format(subject=subject)):
        obj = row["o"]
        val = obj["value"]
        if obj.get("type") == "literal" and len(val) > 140:
            val = val[:140] + "…"
        lines.append(f"    - `{row['p']['value']}` -> {val}")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 4:
        print("Usage: python3 03_candidate_search.py <endpoint> <search_terms.json> <output.md>")
        sys.exit(1)
    endpoint, terms_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]

    with open(terms_path, encoding="utf-8") as f:
        modules = json.load(f)

    report = ["# LOINC candidate search report", "",
              "Auto-generated — every match needs human verification against",
              "System/Scale/Method before it's added to the extraction seed list.", ""]

    for module, terms in modules.items():
        report.append(f"## {module}")
        for term in terms:
            report.append(f"\n### \"{term}\"")
            escaped = term.lower().replace('"', '\\"')
            try:
                subjects = sparql_select(endpoint, SEARCH_QUERY.format(term=escaped))
            except Exception as e:
                report.append(f"  QUERY FAILED: {e}")
                continue
            if not subjects:
                report.append("  **No matches found.** Likely absent from this LOINC release — "
                               "check whether this belongs in vetSNOMED/Mondo instead.")
                continue
            for row in subjects:
                subj = row["s"]["value"]
                report.append(f"\n  **Candidate:** `{subj}`")
                report.append(dump_subject(endpoint, subj))
        report.append("")
        print(f"Finished module: {module}")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    print(f"\nWrote report to {out_path}")


if __name__ == "__main__":
    main()
