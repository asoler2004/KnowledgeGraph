import pandas as pd
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, SKOS

# Define SNOMED CT Namespace
SNO = Namespace("http://snomed.info/id/")

BASE = "/home/antonia/GrafoLinfomaVet/import"

# International Edition (base/core) files
INT_CONCEPT = f"{BASE}/sct2_Concept_Snapshot_INT_20260101.txt"
INT_DESC    = f"{BASE}/sct2_Description_Snapshot-en_INT_20260101.txt"
INT_REL     = f"{BASE}/sct2_Relationship_Snapshot_INT_20260101.txt"

# VET Extension files 
VET_CONCEPT = f"{BASE}/sct2_Concept_Snapshot_INT1000009_20260331.txt"
VET_DESC    = f"{BASE}/sct2_Description_Snapshot-en_INT1000009_20260331.txt"
VET_REL     = f"{BASE}/sct2_Relationship_Snapshot_INT1000009_20260331.txt"


g = Graph()
g.bind("snomed", SNO)
g.bind("skos", SKOS)

# # Update file names to match your directory
# #CONCEPT_FILE = "Snapshot/Terminology/sct2_Concept_Snapshot_INT1000009_20260331.txt"
# CONCEPT_FILE = "/home/antonia/GrafoLinfomaVet/import/sct2_Concept_Snapshot_INT1000009_20260331.txt" 
# #DESC_FILE = "Snapshot/Terminology/sct2_Description_Snapshot-en_INT1000009_20260331.txt"
# DESC_FILE = "/home/antonia/GrafoLinfomaVet/import/sct2_Description_Snapshot-en_INT1000009_20260331.txt"
# #REL_FILE = "Snapshot/Terminology/sct2_Relationship_Snapshot_INT1000009_20260331.txt"
# REL_FILE = "/home/antonia/GrafoLinfomaVet/import/sct2_Relationship_Snapshot_INT1000009_20260331.txt"


print("1. Loading and merging Concepts (International + VET Extension)...")
df_concepts = pd.concat([
    pd.read_csv(INT_CONCEPT, sep="\t", dtype=str),
    pd.read_csv(VET_CONCEPT, sep="\t", dtype=str),
])
active_concepts = set(df_concepts[df_concepts["active"] == "1"]["id"])
print(f"Loaded {len(active_concepts)} active concepts.")


# print("1. Filtering Active Concepts...")
# df_concepts = pd.read_csv(CONCEPT_FILE, sep="\t", dtype=str)
# active_concepts = set(df_concepts[df_concepts["active"] == "1"]["id"])

# print(f"Loaded {len(active_concepts)} active concepts.")

# print("2. Mapping Terms & Descriptions...")
# df_desc = pd.read_csv(DESC_FILE, sep="\t", dtype=str)
# df_desc = df_desc[(df_desc["active"] == "1") & (df_desc["conceptId"].isin(active_concepts))]

# for _, row in df_desc.iterrows():
#     concept_uri = SNO[row["conceptId"]]
#     label_text = Literal(row["term"], lang="en")
    
#     # typeId '900000000000003001' indicates Fully Specified Name (FSN)
#     if row["typeId"] == "900000000000003001":
#         g.add((concept_uri, RDFS.label, label_text))
#     else:
#         g.add((concept_uri, SKOS.altLabel, label_text))


print("2. Loading and merging Descriptions...")
df_desc = pd.concat([
    pd.read_csv(INT_DESC, sep="\t", dtype=str),
    pd.read_csv(VET_DESC, sep="\t", dtype=str),
])
df_desc = df_desc[(df_desc["active"] == "1") & (df_desc["conceptId"].isin(active_concepts))]

for _, row in df_desc.iterrows():
    concept_uri = SNO[row["conceptId"]]
    label_text = Literal(row["term"], lang="en")
    if row["typeId"] == "900000000000003001":
        g.add((concept_uri, RDFS.label, label_text))
    else:
        g.add((concept_uri, SKOS.altLabel, label_text))

# print("3. Building Relationships...")
# df_rel = pd.read_csv(REL_FILE, sep="\t", dtype=str)
# df_rel = df_rel[(df_rel["active"] == "1") & (df_rel["sourceId"].isin(active_concepts))]

# for _, row in df_rel.iterrows():
#     source_uri = SNO[row["sourceId"]]
#     target_uri = SNO[row["destinationId"]]
#     rel_type = row["typeId"]
    
#     # typeId '116680003' indicates 'is_a' (rdfs:subClassOf)
#     if rel_type == "116680003":
#         g.add((source_uri, RDFS.subClassOf, target_uri))
#     else:
#         # Map custom relationships (finding site, morphology, etc.)
#         g.add((source_uri, SNO[rel_type], target_uri))

print("3. Loading and merging Relationships...")
df_rel = pd.concat([
    pd.read_csv(INT_REL, sep="\t", dtype=str),
    pd.read_csv(VET_REL, sep="\t", dtype=str),
])
df_rel = df_rel[(df_rel["active"] == "1") & (df_rel["sourceId"].isin(active_concepts))]

for _, row in df_rel.iterrows():
    source_uri = SNO[row["sourceId"]]
    target_uri = SNO[row["destinationId"]]
    rel_type = row["typeId"]
    if rel_type == "116680003":
        g.add((source_uri, RDFS.subClassOf, target_uri))
    else:
        g.add((source_uri, SNO[rel_type], target_uri))

print("4. Serializing to Turtle...")
g.serialize("vetsno_merged.ttl", format="turtle")
print("Done.")



# print("4. Serializing to Turtle for Fuseki...")
# g.serialize("vetsno_snapshot.ttl", format="turtle")
# print("Done! Upload 'vetsno_snapshot.ttl' to target graph <http://digpatho.vet/graphs/vetsno>.")








