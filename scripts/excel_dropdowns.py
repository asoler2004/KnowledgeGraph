import rdflib
import pandas as pd
from openpyxl import load_workbook
from openpyxl.worksheet.datavalidation import DataValidation

def create_validated_spreadsheet(owl_file_path, output_excel_path):
    # 1. Initialize and load the Turtle schema file
    g = rdflib.Graph()
    g.parse(owl_file_path, format="turtle")
    
    # 2. Query individuals and capture human-readable names
    query = """
    PREFIX rdf: <http://w3.org>
    PREFIX rdfs: <http://w3.org>

    SELECT ?className ?label WHERE {
        ?individual rdf:type ?class .
        ?class rdfs:label ?className .
        ?individual rdfs:label ?label .
    }
    """
    
    # Dynamically match properties generated in our Turtle architecture
    dropdown_lists = {
        "Species": [], 
        "Grade": [], 
        "CellSize": [], 
        "Chromatin": [], 
        "Nucleoli": [], 
        "AnatomicalForm": [],
        "Immunophenotype": [],
        "ConfirmatoryTest": []
    }
    
    for row in g.query(query):
        class_name = str(row.className)
        label = str(row.label)
        if class_name in dropdown_lists:
            dropdown_lists[class_name].append(label)

    # 3. Establish structure and generate the Excel Writer pipeline
    with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
        # Form template columns designed around clinical discovery requirements
        # Note: Unbounded text properties (like exact numbers or raw text) are left open for free-form input
        df_entry = pd.DataFrame(columns=[
            'Disease Subtype (Name)', 
            'Species', 
            'Biological Behavior (Grade)', 
            'Anatomical Form', 
            'Cell Size', 
            'Nuclear Chromatin',
            'Nucleoli Distinctiveness',
            'Immunophenotype Profile',
            'Recommended Confirmatory Test',
            'Median Survival Time (Months with treatment)', # Free-form integer column
            'Pathology Notes & Visual Clues', # Free-form textual context column
            'NCIT/Ontology Code (Optional)'
        ])
        df_entry.to_excel(writer, sheet_name='Data Entry', index=False)
        
        # Populate hidden lists page mapping dictionary components
        max_len = max(len(v) for v in dropdown_lists.values()) if dropdown_lists.values() else 0
        padded_data = {k: v + [''] * (max_len - len(v)) for k, v in dropdown_lists.items()}
        df_lists = pd.DataFrame(padded_data)
        df_lists.to_excel(writer, sheet_name='DropdownLists', index=False)

    # 4. Attach strict validation formulas row-by-row targeting hidden references
    wb = load_workbook(output_excel_path)
    entry_ws = wb['Data Entry']
    
    # Validation bindings mapping target sheet row references ($A=Species, $B=Grade, etc.)
    validations = {
        "B2:B500": DataValidation(type="list", formula1=f"DropdownLists!$A$2:$A${len(dropdown_lists['Species'])+1}", allow_blank=True),
        "C2:C500": DataValidation(type="list", formula1=f"DropdownLists!$B$2:$B${len(dropdown_lists['Grade'])+1}", allow_blank=True),
        "D2:D500": DataValidation(type="list", formula1=f"DropdownLists!$F$2:$F${len(dropdown_lists['AnatomicalForm'])+1}", allow_blank=True),
        "E2:E500": DataValidation(type="list", formula1=f"DropdownLists!$C$2:$C${len(dropdown_lists['CellSize'])+1}", allow_blank=True),
        "F2:F500": DataValidation(type="list", formula1=f"DropdownLists!$D$2:$D${len(dropdown_lists['Chromatin'])+1}", allow_blank=True),
        "G2:G500": DataValidation(type="list", formula1=f"DropdownLists!$E$2:$E${len(dropdown_lists['Nucleoli'])+1}", allow_blank=True),
        "H2:H500": DataValidation(type="list", formula1=f"DropdownLists!$G$2:$G${len(dropdown_lists['Immunophenotype'])+1}", allow_blank=True),
        "I2:I500": DataValidation(type="list", formula1=f"DropdownLists!$H$2:$H${len(dropdown_lists['ConfirmatoryTest'])+1}", allow_blank=True),
    }
    
    for cells, dv_obj in validations.items():
        entry_ws.add_data_validation(dv_obj)
        dv_obj.add(cells)

    # Save output spreadsheet
    wb.save(output_excel_path)
    print(f"Operational data validation form built at: {output_excel_path}")

# Run generation script directly
if __name__ == "__main__":
    # Ensure you create the 'lymphoma_schema.ttl' text file prior to evaluation
    create_validated_spreadsheet('/home/antonia/GrafoLinfomaVet/scripts/lymphoma_schema.ttl', 'diagnostic_template.xlsx')