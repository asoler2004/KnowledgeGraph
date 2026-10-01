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


SEARCH_QUERY_PRECISE = """
PREFIX lnc: <http://purl.bioontology.org/ontology/LNC/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT DISTINCT ?s WHERE {{
    ?s lnc:LOINC_SCALE_TYP ?scale .
    {{ ?s lnc:LOINC_COMPONENT ?val }} UNION {{ ?s skos:prefLabel ?val }}
    FILTER(CONTAINS(LCASE(STR(?val)), "{term}"))
}} LIMIT 15
"""

SEARCH_QUERY_BROAD = """
SELECT DISTINCT ?s WHERE {{
    ?s ?p ?o .
    FILTER(isLiteral(?o))
    FILTER(CONTAINS(LCASE(STR(?o)), "{term}"))
}} LIMIT 15
"""

DUMP_QUERY = "SELECT ?p ?o WHERE {{ <{subject}> ?p ?o }}"

PART_SEARCH_QUERY = """
PREFIX lnc: <http://purl.bioontology.org/ontology/LNC/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT DISTINCT ?s WHERE {{
    ?s lnc:PART_TYPE "{part_type}" .
    ?s skos:prefLabel ?val .
    FILTER(CONTAINS(LCASE(STR(?val)), "{term}"))
}} LIMIT 15
"""


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
                precise = sparql_select(endpoint, SEARCH_QUERY_PRECISE.format(term=escaped))
            except Exception as e:
                report.append(f"  PRECISE QUERY FAILED: {e}")
                precise = []

            if precise:
                report.append(f"  *{len(precise)} precise match(es) — matched LOINC_COMPONENT or "
                               f"prefLabel on an actual result code (has LOINC_SCALE_TYP).*")
                subjects = precise
            else:
                report.append("  *No precise match (no result code with this in its Component/label). "
                               "Falling back to a broad literal search — results may include LOINC "
                               "Parts, Answer values, or unrelated matches; verify carefully.*")
                try:
                    subjects = sparql_select(endpoint, SEARCH_QUERY_BROAD.format(term=escaped))
                except Exception as e:
                    report.append(f"  BROAD QUERY FAILED: {e}")
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


# --- Separate pass: LOINC Parts (System axis) for anatomic sites ---
# Needed for module 5's anatomic-site standardization — you want the
# System *Part* (e.g. "Skin", "Ear"), not a full result/observation code.
# PART_TYPE value below is "SYSTEM", inferred from the COMPONENT example
# seen in introspection (all-caps convention) — verify against your own
# data if this returns nothing; run:
#   SELECT DISTINCT ?t WHERE { ?s lnc:PART_TYPE ?t } (via introspection)
# to confirm the exact string used for the System axis in this release.
ANATOMIC_SITE_TERMS = [
    "skin", "subcutis", "lymph node", "mediastinum", "intestine",
    "spleen", "liver", "oral cavity", "mammary gland", "perianal",
    "thyroid", "peripheral nerve", "digit", "ear", "blood", "urine",
    "pleural", "peritoneal",
]


def search_anatomic_parts(endpoint, out_path):
    report = ["# LOINC System-axis Part candidates (anatomic sites)", ""]
    for term in ANATOMIC_SITE_TERMS:
        report.append(f"\n### \"{term}\"")
        try:
            subjects = sparql_select(endpoint, PART_SEARCH_QUERY.format(part_type="SYSTEM", term=term))
        except Exception as e:
            report.append(f"  QUERY FAILED: {e}")
            continue
        if not subjects:
            report.append("  No matches under PART_TYPE \"SYSTEM\" — confirm the exact PART_TYPE "
                           "string for this axis in your release before concluding it's absent.")
            continue
        for row in subjects:
            subj = row["s"]["value"]
            report.append(f"\n  **Candidate:** `{subj}`")
            report.append(dump_subject(endpoint, subj))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    print(f"Wrote anatomic Part report to {out_path}")


if __name__ == "__main__":
    main()
    if len(sys.argv) >= 4:
        endpoint = sys.argv[1]
        anatomic_out = sys.argv[3].rsplit(".", 1)[0] + "_anatomic_parts.md"
        search_anatomic_parts(endpoint, anatomic_out)
