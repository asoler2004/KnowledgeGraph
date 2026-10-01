"""
Introspects an RDF graph loaded in Fuseki: distinct predicates (with usage
counts), distinct rdf:type values (with counts), and a full property dump
of a few sample subjects. Run this before writing any keyword-matching
query against an unfamiliar dataset like a LOINC RDF release, where exact
predicate names vary by release version.

Usage:
    python3 02_introspect.py http://localhost:3031/loincscratch/sparql
"""
import sys
import urllib.parse
import urllib.request
import json


def sparql_select(endpoint: str, query: str) -> list:
    url = endpoint + "?query=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={"Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["results"]["bindings"]


PREDICATE_QUERY = """
SELECT ?p (COUNT(*) AS ?n) WHERE { ?s ?p ?o } GROUP BY ?p ORDER BY DESC(?n)
"""

TYPE_QUERY = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?type (COUNT(*) AS ?n) WHERE { ?s rdf:type ?type } GROUP BY ?type ORDER BY DESC(?n)
"""

SAMPLE_SUBJECTS_QUERY = """
SELECT DISTINCT ?s WHERE { ?s ?p ?o } LIMIT 3
"""

SUBJECT_DUMP_QUERY = """
SELECT ?p ?o WHERE {{ <{subject}> ?p ?o }}
"""


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 02_introspect.py <sparql-endpoint>")
        sys.exit(1)
    endpoint = sys.argv[1]

    print("=" * 70)
    print("DISTINCT PREDICATES (most-used first)")
    print("=" * 70)
    for row in sparql_select(endpoint, PREDICATE_QUERY):
        print(f"  {row['n']['value']:>8}  {row['p']['value']}")

    print()
    print("=" * 70)
    print("DISTINCT rdf:type VALUES")
    print("=" * 70)
    types = sparql_select(endpoint, TYPE_QUERY)
    if not types:
        print("  (no rdf:type triples found — this release may not type its concepts explicitly)")
    for row in types:
        print(f"  {row['n']['value']:>8}  {row['type']['value']}")

    print()
    print("=" * 70)
    print("SAMPLE SUBJECT DUMPS")
    print("=" * 70)
    samples = sparql_select(endpoint, SAMPLE_SUBJECTS_QUERY)
    for s in samples:
        subject = s["s"]["value"]
        print(f"\n--- {subject} ---")
        for row in sparql_select(endpoint, SUBJECT_DUMP_QUERY.format(subject=subject)):
            obj = row["o"]
            val = obj["value"]
            if obj.get("type") == "literal" and len(val) > 100:
                val = val[:100] + "…"
            print(f"  {row['p']['value']}  ->  {val}")


if __name__ == "__main__":
    main()
