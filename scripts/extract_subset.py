import sys

# 1. Define your target terms (extracted from your list)
target_ids = {
    "NCBITaxon:9615", "NCBITaxon:9685", "NCBITaxon:5671", "NCBITaxon:5866",
    "NCBITaxon:5867", "NCBITaxon:358", "NCBITaxon:948", "NCBITaxon:2093",
    "NCBITaxon:11723", "NCBITaxon:11892", "NCBITaxon:11210", "NCBITaxon:4882",
    "NCBITaxon:5741", "NCBITaxon:5723", "NCBITaxon:5762", "NCBITaxon:5759"
}

obo_path = "/home/antonia/GrafoLinfomaVet/import/ncbitaxon.obo"
output_path = "/home/antonia/GrafoLinfomaVet/import/ncbitaxon_subset.obo"

# 2. First pass: Map children to parents line-by-line
print("Scanning OBO file for relationships...")
parent_map = {}
with open(obo_path, "r", encoding="utf-8") as f:
    current_id = None
    for line in f:
        line = line.strip()
        if line.startswith("id:"):
            current_id = line.split("id:")[1].strip()
        elif line.startswith("is_a:") and current_id:
            parent_id = line.split("is_a:")[1].split("!")[0].strip()
            if current_id not in parent_map:
                parent_map[current_id] = []
            parent_map[current_id].append(parent_id)

# 3. Find all recursive ancestors for your target IDs
print("Finding all recursive ancestors...")
all_needed_ids = set(target_ids)
queue = list(target_ids)

while queue:
    current = queue.pop(0)
    parents = parent_map.get(current, [])
    for p in parents:
        if p not in all_needed_ids:
            all_needed_ids.add(p)
            queue.append(p)

print(f"Total terms to keep (self + ancestors): {len(all_needed_ids)}")

# 4. Second pass: Write only the needed stanzas to the output file
print("Writing subset OBO file...")
with open(obo_path, "r", encoding="utf-8") as infile, open(output_path, "w", encoding="utf-8") as outfile:
    inside_header = True
    inside_needed_stanza = False
    stanza_buffer = []

    for line in infile:
        if line.startswith("[Term]") or line.startswith("[Typedef]"):
            inside_header = False
            # Flush previous stanza if it was needed
            if inside_needed_stanza:
                outfile.write("".join(stanza_buffer))
            stanza_buffer = [line]
            inside_needed_stanza = False
            continue

        if inside_header:
            outfile.write(line)
        else:
            stanza_buffer.append(line)
            if line.startswith("id:"):
                term_id = line.split("id:")[1].strip()
                if term_id in all_needed_ids:
                    inside_needed_stanza = True

    # Flush the last stanza if needed
    if inside_needed_stanza:
        outfile.write("".join(stanza_buffer))

print(f"Finished! Saved to {output_path}")
