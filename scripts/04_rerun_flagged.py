"""
Targeted re-run for terms flagged in the review as truncated, noisy, or
using the wrong search phrase. Each entry can override the search term
and/or require the result's LOINC_SYSTEM to contain a substring — that
second option is what fixes "myelocyte" (collides with promyelocyte/
metamyelocyte) and "bacteria"/"yeast" (drowned in unrelated systems).

Usage:
    python3 04_rerun_flagged.py http://localhost:3031/loincscratch/sparql rerun_report.md
"""
import sys
import json
import urllib.parse
import urllib.request


def sparql_select(endpoint: str, query: str) -> list:
    url = endpoint + "?query=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={"Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))["results"]["bindings"]


QUERY = """
PREFIX lnc: <http://purl.bioontology.org/ontology/LNC/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT DISTINCT ?s ?val ?system WHERE {{
    ?s lnc:LOINC_SCALE_TYP ?scale .
    {{ ?s lnc:LOINC_COMPONENT ?val }} UNION {{ ?s skos:prefLabel ?val }}
    OPTIONAL {{ ?s lnc:LOINC_SYSTEM ?system }}
    FILTER(CONTAINS(LCASE(STR(?val)), "{term}"))
    {sysfilter}
}} ORDER BY STRLEN(?val) LIMIT 60
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


# label, search term, optional required substring in LOINC_SYSTEM
RERUN_TERMS = [
    ("platelet count",  "platelet",   None),
    ("platelets",       "platelets",  None),
    ("leukocyte",       "leukocytes", None),
    ("neutrophil (segmented)", "neutrophils.segmented", None),
    ("lymphocyte",       "lymphocytes", None),
    ("monocyte",         "monocytes",   None),
    ("basophil",         "basophils",   None),
    ("bacteria (urine)", "bacteria",    "urine"),
    ("yeast (urine)",    "yeast",       "urine"),
    ("myelocyte (bone marrow)", "myelocytes", "bone mar"),
]


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 04_rerun_flagged.py <endpoint> <output.md>")
        sys.exit(1)
    endpoint, out_path = sys.argv[1], sys.argv[2]

    report = ["# Re-run: flagged terms (higher limit, shortest-match-first)", ""]
    for label, term, sys_req in RERUN_TERMS:
        report.append(f"\n## \"{label}\"  (search term: \"{term}\""
                       + (f", System contains \"{sys_req}\"" if sys_req else "") + ")")
        sysfilter = f'FILTER(CONTAINS(LCASE(STR(?system)), "{sys_req}"))' if sys_req else ""
        rows = sparql_select(endpoint, QUERY.format(term=term, sysfilter=sysfilter))
        seen = set()
        if not rows:
            report.append("  No matches even with the relaxed query — likely genuinely absent.")
            continue
        for row in rows[:20]:  # cap what we print even if 60 came back
            subj = row["s"]["value"]
            if subj in seen:
                continue
            seen.add(subj)
            report.append(f"\n  **Candidate:** `{subj}`  (matched: \"{row['val']['value'][:60]}\")")
            report.append(dump_subject(endpoint, subj))
        print(f"{label}: {len(seen)} unique candidates")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
