import re

file_path = r"c:\Users\b2400\OneDrive\Desktop\stellar_prod_new\db_cluster-24-10-2025@06-27-32.backup\db_cluster-24-10-2025@06-27-32.backup"

with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

# Split the dump into blocks based on "-- Name: " comments
blocks = text.split("\n--\n-- Name: ")

public_blocks = []

for block in blocks[1:]: # skip the first block before any Name header
    header_line = block.split("\n")[0]
    if "Schema: public" in header_line and "Type: TABLE DATA" not in header_line:
        # It's a schema object in public schema
        public_blocks.append("-- Name: " + block.strip() + "\n")

out_sql = "\n".join(public_blocks)
with open(r"c:\Users\b2400\OneDrive\Desktop\stellar_prod_new\public_schema.sql", "w", encoding="utf-8") as f:
    f.write(out_sql)

print(f"Extracted {len(public_blocks)} objects to public_schema.sql")
