import pandas as pd
import numpy as np
import os
from pathlib import Path

import eda_analysis  # reuse get_chunk_files, extract_title, and stat calculations


def fill_embarked(df, fill_value):
    """
    Fill missing values in the 'Embarked' column using a precomputed
    fill value (the mode, calculated once in eda_analysis.py from a sample
    of the full dataset).
    """
    df = df.copy()
    df["Embarked"] = df["Embarked"].fillna(fill_value)
    return df


def impute_age(df, pclass_title_median, title_median, global_median):
    """
    Impute missing Age values using PRECOMPUTED grouped medians
    (calculated once in eda_analysis.py from a sample of the full dataset).
    Fallback chain: (Pclass, Title) -> Title -> global median.
    Does not drop Name or Pclass.
    """
    df = df.copy()

    df["Age_missing"] = df["Age"].isnull()
    df = eda_analysis.extract_title(df)

    def get_fill_value(row):
        pclass = row["Pclass"]
        title = row["Title"]

        group_median = pclass_title_median.get((pclass, title), np.nan)
        if pd.notna(group_median):
            return group_median

        t_median = title_median.get(title, np.nan)
        if pd.notna(t_median):
            return t_median

        return global_median

    missing_mask = df["Age"].isnull()
    df.loc[missing_mask, "Age"] = df.loc[missing_mask].apply(get_fill_value, axis=1)

    return df


def engineer_cabin_features(df):
    """
    Transform the high-cardinality, mostly-missing 'Cabin' column into a
    single low-cardinality feature: Deck.

    Deck = first letter of the cabin code (e.g. 'C85' -> 'C'), or 'Unknown'
    if Cabin was missing. This collapses 147 near-unique cabin values down
    to ~9 meaningful categories.

    A separate Has_Cabin flag is not needed — Deck == 'Unknown' already
    captures that exact same signal, so adding both would be redundant.

    The raw 'Cabin' column is dropped afterward, since its useful signal
    has been extracted into Deck in a much lower-cardinality form.
    """
    df = df.copy()

    df["Deck"] = df["Cabin"].str[0]
    df["Deck"] = df["Deck"].fillna("Unknown")

    df = df.drop(columns=["Cabin"])

    return df
def engineer_ticket_features(df):
    """
    Extract Ticket_Prefix from the raw Ticket column.

    Tickets like 'CT101' carry a real alphabetic prefix; tickets like
    '110100' are purely numeric. This isn't formatting noise to clean up
    (CT101 and 110100 are genuinely different tickets) — it's structural
    signal, possibly indicating ticket office/agency, similar to how
    Cabin's first letter (Deck) was extracted from a high-cardinality field.

    Raw Ticket itself is dropped afterward, since the exact ticket number
    is unlikely to generalize (near-unique per row) while the prefix
    category is low-cardinality and reusable.
    """
    df = df.copy()
    df["Ticket_Prefix"] = df["Ticket"].apply(eda_analysis.extract_ticket_prefix)
    df = df.drop(columns=["Ticket"])
    return df
def normalize_fare(df):
    """
    Apply log transformation to Fare to reduce right-skew and compress
    the influence of extreme high-fare outliers, without deleting any rows.

    log1p(x) = log(x + 1) — the "+1" safely handles Fare=0 (log(0) is
    undefined). This doesn't need any precomputed global stats (unlike
    Age medians or outlier bounds) since the log formula is fixed and
    applies identically to every row regardless of dataset size — so
    it can be applied directly per chunk with no cross-chunk dependency.
    """
    df = df.copy()
    df["Fare_log"] = np.log1p(df["Fare"])
    return df

def main():
    chunk_files = eda_analysis.get_chunk_files("chunks")
    print(f"Found {len(chunk_files)} chunk files")

    # --- Step 1: Compute reference statistics ONCE, from a sample of the
    # full dataset (not recomputed per chunk — keeps imputation consistent) ---
    print("\nComputing reference statistics (from 5% sample)...")
    embarked_fill_value = eda_analysis.calculate_embarked_fill_value(chunk_files)
    pclass_title_median, title_median, global_median = eda_analysis.calculate_age_medians(chunk_files)

    print(f"Embarked fill value: {embarked_fill_value}")
    print(f"Global median age:   {global_median}")

    # --- Step 2: Apply transformations to each chunk individually ---
    output_folder = "chunks_cleaned"
    os.makedirs(output_folder, exist_ok=True)

    for file in chunk_files:
        chunk = pd.read_csv(file)

        age_missing_before = chunk["Age"].isnull().sum()
        embarked_missing_before = chunk["Embarked"].isnull().sum()
        cabin_missing_before = chunk["Cabin"].isnull().sum()

        chunk = fill_embarked(chunk, embarked_fill_value)
        chunk = impute_age(chunk, pclass_title_median, title_median, global_median)
        chunk = engineer_cabin_features(chunk)
        chunk = engineer_ticket_features(chunk)
        chunk = normalize_fare(chunk)

        print(f"\n{file.name}")
        print(f"  Embarked missing: {embarked_missing_before} -> {chunk['Embarked'].isnull().sum()}")
        print(f"  Age missing:      {age_missing_before} -> {chunk['Age'].isnull().sum()}")
        print(f"  Cabin ({cabin_missing_before} missing) -> replaced with Deck column")
        print(f"  Deck value counts:\n{chunk['Deck'].value_counts().to_string()}")
        print(f"  Ticket -> replaced with Ticket_Prefix column")
        print(f"  Ticket_Prefix value counts:\n{chunk['Ticket_Prefix'].value_counts().to_string()}")
        save_path = Path(output_folder) / file.name
        chunk.to_csv(save_path, index=False)
        print(f"  Saved to: {save_path}")


if __name__ == "__main__":
    main()