import pandas as pd
import os

# Create the output folder if it doesn't already exist
output_folder = "chunks"
os.makedirs(output_folder, exist_ok=True)

# Count rows without loading the whole CSV
total_rows = sum(1 for _ in open(r"E:\Infotech_\19_jun\titanic\train.csv")) - 1  # subtract header

# Divide into 5 chunks
chunk_size = (total_rows + 4) // 5  # ceiling division

print(f"Total rows: {total_rows}")
print(f"Chunk size: {chunk_size}")

# Read in chunks
for i, chunk in enumerate(pd.read_csv(r"E:\Infotech_\19_jun\titanic\train.csv", chunksize=chunk_size), start=1):
    print(f"\nChunk {i}")
    print(f"Rows: {len(chunk)}")

    # Save each chunk into the "chunks" folder
    chunk_path = os.path.join(output_folder, f"chunk_{i}.csv")
    chunk.to_csv(chunk_path, index=False)
    print(f"Saved to: {chunk_path}")