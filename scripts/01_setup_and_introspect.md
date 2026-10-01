# Step 1 — spin up a throwaway Fuseki instance over loinc.ttl

No persistent dataset needed for exploration. Fuseki's file-quickstart mode
loads a file into an in-memory dataset for the life of the process:

```bash
fuseki-server --file=loinc.ttl --port 3031 /loincscratch
```

(If `fuseki-server` isn't on your PATH, run it from wherever your Jena/Fuseki
distribution lives, e.g. `./fuseki-server` from the Fuseki install directory.)

This gives you a SPARQL endpoint at:

    http://localhost:3031/loincscratch/sparql

Leave it running in one terminal; run the scripts below from another.
Large file → first load may take a while and use real memory. If loinc.ttl
is too big to comfortably fit in-memory, load it into a persistent TDB2
dataset instead and point the scripts at that endpoint — same queries work
either way.

# Step 2 — introspect (run 02_introspect.py)

Before writing any keyword search, find out:
- What predicates this specific LOINC RDF release actually uses
- What a typical concept's full property set looks like (which property
  holds Component vs. System vs. Scale vs. Method vs. the display name)
- Roughly how many distinct predicates/types exist, so you're not
  surprised later

Run:
```bash
python3 02_introspect.py http://localhost:3031/loincscratch/sparql
```

It prints:
1. Every distinct predicate in the graph, with a usage count (most-used
   first) — tells you which one is the display name, which are the axis
   properties (Component/System/Property/Scale/Method), etc.
2. Every distinct `rdf:type` in the graph, with a count — tells you if
   LOINC Parts and LOINC "terms" (result codes) are typed differently,
   which matters for later queries.
3. A full property dump of 3 arbitrary sample subjects — the fastest way
   to see the actual shape of a concept without guessing.

Read this output before touching `03_candidate_search.py` — the keyword
search script assumes nothing about predicate names (it searches ALL
literals), so it'll work regardless, but you'll want the predicate names
from this step to make sense of the candidate dumps it produces.
