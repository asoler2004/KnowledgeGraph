import os
import re
import subprocess

# Define absolute paths
IMPORT_DIR = "/home/antonia/GrafoLinfomaVet/import"
INPUT_OWL = os.path.join(IMPORT_DIR, "Thesaurus.owl")
TEMP_TTL = os.path.join(IMPORT_DIR, "ncit_subset_temp.ttl")
OUTPUT_TTL = os.path.join(IMPORT_DIR, "ncit_subset.ttl")

# Explicit OBO-style targets 
TARGET_CODES = [
    "C4328", "C133604", "C133276", "C4518", "C8500", "C34443", "C34828", 
    "C116342", "C84964", "C35028", "C35029", "C121098", "C34661", "C36184", 
    "C120894", "C120897", "C62507", "C120888", "C37071", "C117180", 
    "C117181", "C117182", "C117183", "C117184", "C117185", "C117186", 
    "C117187", "C117188", "C117189", "C117190"
]

TARGET_URIS = {f"http://purl.obolibrary.org/obo/NCIT_{code}" for code in TARGET_CODES}

print("Step 1: Mapping subClassOf strings via low-memory regex stream...")
parent_map = {}

# Regular expressions to extract subjects and object targets regardless of XML layout or indentation
class_rdf_about_regex = re.compile(r'<(?:owl:)?Class\s+[^>]*rdf:about=["\'](http://purl\.obolibrary\.org/obo/NCIT_[A-Za-z0-9_]+)["\']')
subclass_resource_regex = re.compile(r'<(?:rdfs:)?subClassOf\s+[^>]*rdf:resource=["\'](http://purl\.obolibrary\.org/obo/NCIT_[A-Za-z0-9_]+)["\']')
label_regex = re.compile(r'<(?:rdfs:)?label[^>]*>(.*?)<\/(?:rdfs:)?label>')

labels_cache = {}
current_class = None

with open(INPUT_OWL, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        # Match class declaration blocks
        class_match = class_rdf_about_regex.search(line)
        if class_match:
            current_class = class_match.group(1)
            continue
            
        if current_class:
            # Look for structural parent class anchors
            subclass_match = subclass_resource_regex.search(line)
            if subclass_match:
                parent_uri = subclass_match.group(1)
                if current_class not in parent_map:
                    parent_map[current_class] = []
                parent_map[current_class].append(parent_uri)
                
            # Look for matching lexical names
            label_match = label_regex.search(line)
            if label_match:
                labels_cache[current_class] = label_match.group(1).strip()

print("Step 2: Resolving hierarchical ancestors for the target URIs...")
all_needed_uris = set(TARGET_URIS)
queue = list(TARGET_URIS)

while queue:
    current = queue.pop(0)
    parents = parent_map.get(current, [])
    for p in parents:
        if p not in all_needed_uris:
            all_needed_uris.add(p)
            queue.append(p)

print(f"-> Linked a total of {len(all_needed_uris)} self + ancestor structural entities.")

print("Step 3: Exporting localized structural axioms to a clean temporary file...")
with open(TEMP_TTL, "w", encoding="utf-8") as outfile:
    outfile.write("@prefix rdfs: <http://w3.org> .\n")
    outfile.write("@prefix rdf: <http://w3.org> .\n")
    outfile.write("@prefix owl: <http://w3.org> .\n\n")

    for uri in all_needed_uris:
        outfile.write(f"<{uri}> rdf:type owl:Class .\n")
        
        # Write extracted subclass relationships
        for parent in parent_map.get(uri, []):
            outfile.write(f"<{uri}> rdfs:subClassOf <{parent}> .\n")
            
        # Write human-readable labels if captured
        if uri in labels_cache:
            clean_label = labels_cache[uri].replace('"', '\\"')
            outfile.write(f"<{uri}> rdfs:label \"{clean_label}\" .\n")

print("Step 4: Compiling temporary data with ROBOT into structural TTL format...")
try:
    # This runs using virtually no memory since the intermediate file is tiny
    result = subprocess.run(
        ["robot", "convert", "--input", TEMP_TTL, "--output", OUTPUT_TTL],
        check=True,
        text=True,
        capture_output=True
    )
    print(f"Success! Final output saved to: {OUTPUT_TTL}")
except subprocess.CalledProcessError as e:
    print(f"ROBOT layout compilation failed:\n{e.stderr}")
finally:
    # Clean up intermediate files
    if os.path.exists(TEMP_TTL):
        os.remove(TEMP_TTL)
