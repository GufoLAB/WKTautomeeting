import os
import sys
import pandas as pd

# === Step 1: Get input path from argv ===
input_path = sys.argv[1]  # e.g., 'data/original.csv'

# === Step 2: Read input file ===
df = pd.read_csv(input_path)

# === Step 3: Drop title column and re-index chunk_id ===
df = df.drop(columns=['title', 'tags'])
df['chunk_id'] = range(1, len(df) + 1)

# === Step 4: Reorder columns ===
df = df[['chunk_id', 'summary']]

# === Step 5: Create output folder and path ===
input_dir = os.path.dirname(input_path)
input_file = os.path.basename(input_path)
filename_wo_ext = os.path.splitext(input_file)[0]
output_dir = os.path.join(input_dir, f"{filename_wo_ext}_output")
os.makedirs(output_dir, exist_ok=True)

output_path = os.path.join(output_dir, f"{filename_wo_ext}_reindexed.csv")

# === Step 6: Save output file ===
df.to_csv(output_path, index=False)
print(f"Saved: {output_path}")
