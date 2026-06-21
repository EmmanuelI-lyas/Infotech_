import pandas as pd
from pathlib import Path
import os
import re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt 
import numpy as np

def get_chunk_files(chunk_folder="chunks"):
    """Find all chunk CSV files inside the chunks folder."""
    return sorted(Path(chunk_folder).glob("*.csv"))


def calculate_missing_values(chunk_files):
    """Calculate total missing values across all chunks."""
    total_missing = None
    total_rows = 0

    for file in chunk_files:
        chunk = pd.read_csv(file)
        missing_in_chunk = chunk.isnull().sum()

        if total_missing is None:
            total_missing = missing_in_chunk
        else:
            total_missing += missing_in_chunk

        total_rows += len(chunk)

    return total_missing, total_rows


def get_unique_values_for_missing_columns(chunk_files):
    """For columns that contain missing values, collect unique NON-MISSING values."""
    unique_values = {}

    for file in chunk_files:
        chunk = pd.read_csv(file)
        missing_cols = chunk.columns[chunk.isnull().any()]

        for col in missing_cols:
            if col not in unique_values:
                unique_values[col] = set()
            unique_values[col].update(chunk[col].dropna().unique())

    return unique_values


def load_sampled_data(chunk_files, sample_frac=0.05, random_state=42):
    """
    Build a small, memory-friendly representative sample of the full dataset
    by taking a random fraction of rows from EACH chunk individually,
    then combining just those samples.

    This never loads more than one chunk into memory at a time beyond what's
    needed to sample from it, and the final combined sample is small enough
    to always fit in RAM, regardless of how large the original dataset is.

    Args:
        chunk_files: list of chunk file paths
        sample_frac: fraction of rows to keep from each chunk (default 5%)
        random_state: seed for reproducibility, so you get the same sample
                       every time you run this (important for consistent results)
    """
    samples = []

    for file in chunk_files:
        chunk = pd.read_csv(file)
        sampled_chunk = chunk.sample(frac=sample_frac, random_state=random_state)
        samples.append(sampled_chunk)
        # `chunk` (the full one) is discarded after sampling — only the
        # small sample is kept around in `samples`.

    return pd.concat(samples, ignore_index=True)
def load_full_data(chunk_files):
    """
    Combine all chunks into a single DataFrame using the FULL data,
    no sampling.

    Used specifically for outlier detection (IQR), where quartiles need
    to be computed from the complete, exact dataset rather than a sample —
    sampling introduces noise into Q1/Q3 estimates, which shifts the
    outlier bounds and can cause real outliers to be missed or false
    ones to appear.

    This is safe here because the dataset is small (891 rows total)
    and fits in memory easily. For a genuinely large dataset, this
    function would need to be replaced with an approximate/incremental
    quantile method instead — full-data loading would not scale.
    """
    return pd.concat([pd.read_csv(f) for f in chunk_files], ignore_index=True)


def extract_title(df):
    """
    Extract title from the 'Name' column into a new 'Title' column.
    e.g. "Braund, Mr. Owen Harris" -> "Mr"
    """
    df = df.copy()
    df["Title"] = df["Name"].str.extract(r",\s*([A-Za-z]+)\.", expand=False)
    return df


def calculate_age_medians(chunk_files, sample_frac=0.05):
    """
    Compute median Age grouped by (Pclass, Title), using a random SAMPLE
    of the data rather than the full dataset, to keep memory usage low
    even on very large files.

    Returns:
        pclass_title_median (Series): median age per (Pclass, Title) group
        title_median (Series): median age per Title only (fallback level 1)
        global_median (float): overall median age (fallback level 2)
    """
    df = load_sampled_data(chunk_files, sample_frac=sample_frac)
    df = extract_title(df)

    pclass_title_median = df.groupby(["Pclass", "Title"])["Age"].median()
    title_median = df.groupby("Title")["Age"].median()
    global_median = df["Age"].median()

    return pclass_title_median, title_median, global_median


def calculate_embarked_fill_value(chunk_files, sample_frac=0.05):
    """Most common Embarked value (mode), estimated from a random sample."""
    df = load_sampled_data(chunk_files, sample_frac=sample_frac)
    return df["Embarked"].mode()[0]
def check_dtype_consistency(chunk_files):
    """
    Check that every column has the SAME dtype across all chunk files.

    This matters specifically because of chunked reading: pandas infers
    dtype per chunk based only on that chunk's data. If, say, chunk 1 has
    no missing Age values, pandas might infer it as int64 — but chunk 3,
    which DOES have missing Age values, gets float64 (NaN forces float).
    Same column, two different types across chunks — a silent bug source
    when you later concat or process chunks together.

    Returns a DataFrame: column -> dtype per chunk, with a 'consistent' flag.
    """
    dtype_records = {}

    for file in chunk_files:
        chunk = pd.read_csv(file)
        dtype_records[file.name] = chunk.dtypes.astype(str)

    dtype_df = pd.DataFrame(dtype_records)
    dtype_df["consistent"] = dtype_df.nunique(axis=1) == 1
    return dtype_df


def check_column_name_consistency(chunk_files):
    """
    Check that every chunk file has the exact same set of column names.
    Catches issues like a typo'd header, an extra/missing column, or
    different column ordering between chunk files.
    """
    column_sets = {}
    for file in chunk_files:
        chunk = pd.read_csv(file, nrows=0)  # just read header, no data
        column_sets[file.name] = list(chunk.columns)

    reference_cols = set(next(iter(column_sets.values())))
    mismatches = {}
    for file_name, cols in column_sets.items():
        if set(cols) != reference_cols:
            mismatches[file_name] = {
                "missing_columns": list(reference_cols - set(cols)),
                "extra_columns": list(set(cols) - reference_cols),
            }

    return column_sets, mismatches


def check_categorical_consistency(chunk_files, columns=None):
    """
    For text/categorical columns, detect formatting inconsistencies that
    would silently create duplicate categories, e.g.:
      - Case differences: 'Mr' vs 'MR' vs 'mr'
      - Whitespace differences: 'S' vs 'S ' vs ' S'

    Works by comparing the raw unique value count vs. the unique count
    after normalizing (lowercasing + stripping whitespace). If normalizing
    REDUCES the count, that means some values that should be identical
    are currently being treated as different categories.

    If `columns` is None, automatically checks all object/text columns.
    """
    # Collect all unique raw values per column across every chunk
    raw_values = {}

    for file in chunk_files:
        chunk = pd.read_csv(file)
        text_cols = columns or chunk.select_dtypes(include="object").columns

        for col in text_cols:
            if col not in chunk.columns:
                continue
            if col not in raw_values:
                raw_values[col] = set()
            raw_values[col].update(chunk[col].dropna().unique())

    results = []
    for col, values in raw_values.items():
        values = list(values)
        normalized = {str(v).strip().lower() for v in values}

        raw_count = len(values)
        normalized_count = len(normalized)

        results.append({
            "column": col,
            "raw_unique_count": raw_count,
            "normalized_unique_count": normalized_count,
            "potential_duplicates": raw_count - normalized_count,
            "needs_cleanup": raw_count != normalized_count,
        })

    return pd.DataFrame(results)


def save_reports(total_missing, total_rows, unique_values,
                  embarked_fill_value, pclass_title_median,
                  title_median, global_median,deck_counts,check_dtype_consistency_result,
                  categorical_consistency_result,
                  report_folder="reports"):
    """
    Save all computed statistics into CSV files inside a 'reports' folder,
    so the analysis is documented and can be shared (e.g. with a manager)
    without re-running the script or relying on terminal output.
    """
    os.makedirs(report_folder, exist_ok=True)

    # --- Report 1: missing values summary ---
    missing_df = total_missing[total_missing > 0].rename("missing_count").to_frame()
    missing_df["missing_percentage"] = ((missing_df["missing_count"] / total_rows) * 100).round(2)
    missing_df["total_rows"] = total_rows
    missing_path = os.path.join(report_folder, "missing_values_summary.csv")
    missing_df.to_csv(missing_path, index_label="column")
    print(f"Saved: {missing_path}")

    # --- Report 2: unique values for columns with missing data ---
    unique_rows = []
    for col, values in unique_values.items():
        values = sorted(list(values), key=str)
        unique_rows.append({
            "column": col,
            "unique_count": len(values),
            "sample_values": ", ".join(map(str, values[:10]))
        })
    unique_df = pd.DataFrame(unique_rows)
    unique_path = os.path.join(report_folder, "unique_values_summary.csv")
    unique_df.to_csv(unique_path, index=False)
    print(f"Saved: {unique_path}")

    # --- Report 3: imputation reference values (Age medians + Embarked fill) ---
    age_medians_df = pclass_title_median.reset_index()
    age_medians_df.columns = ["Pclass", "Title", "median_age"]
    age_path = os.path.join(report_folder, "age_median_by_pclass_title.csv")
    age_medians_df.to_csv(age_path, index=False)
    print(f"Saved: {age_path}")

    title_median_df = title_median.reset_index()
    title_median_df.columns = ["Title", "median_age"]
    title_path = os.path.join(report_folder, "age_median_by_title.csv")
    title_median_df.to_csv(title_path, index=False)
    print(f"Saved: {title_path}")

    # --- Report 4: single-row summary of key fallback values ---
    summary_df = pd.DataFrame([{
        "embarked_fill_value": embarked_fill_value,
        "global_median_age": global_median,
        "total_rows": total_rows
    }])
    summary_path = os.path.join(report_folder, "imputation_summary.csv")
    summary_df.to_csv(summary_path, index=False)
    print(f"Saved: {summary_path}")
    
    # --- Report 5: deck distribution (Cabin -> Deck mapping evidence) ---
    deck_df = deck_counts.rename("count").to_frame()
    deck_df["percentage"] = ((deck_df["count"] / total_rows) * 100).round(2)
    deck_path = os.path.join(report_folder, "deck_distribution.csv")
    deck_df.to_csv(deck_path, index_label="deck")
    print(f"Saved: {deck_path}")
    # --- Report 6: dtype consistency across chunks ---
    dtype_df = check_dtype_consistency_result  # passed in from main()
    dtype_path = os.path.join(report_folder, "dtype_consistency.csv")
    dtype_df.to_csv(dtype_path, index_label="column")
    print(f"Saved: {dtype_path}")

    # --- Report 7: categorical value consistency ---
    categorical_df = categorical_consistency_result  # passed in from main()
    categorical_path = os.path.join(report_folder, "categorical_consistency.csv")
    categorical_df.to_csv(categorical_path, index=False)
    print(f"Saved: {categorical_path}")
def calculate_outlier_bounds(chunk_files, columns=None, df=None):
    """
    Compute IQR-based outlier bounds for numeric columns, using the
    FULL dataset (no sampling).

    If `df` is already loaded (e.g. by the caller, to avoid loading it
    twice), pass it in directly. Otherwise this loads it itself.

    IQR method:
        Q1 = 25th percentile, Q3 = 75th percentile, IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        Any value outside [lower_bound, upper_bound] is an outlier.
    """
    if columns is None:
        columns = ["Age", "Fare", "SibSp", "Parch"]

    if df is None:
        df = load_full_data(chunk_files)

    rows = []
    for col in columns:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        rows.append({
            "column": col,
            "Q1": Q1,
            "Q3": Q3,
            "IQR": IQR,
            "lower_bound": Q1 - 1.5 * IQR,
            "upper_bound": Q3 + 1.5 * IQR,
        })

    return pd.DataFrame(rows)
def count_outliers(chunk_files, bounds_df):
    """
    Using the precomputed IQR bounds, count how many rows fall outside
    them — processed chunk by chunk, so only one chunk is in memory at
    a time, same pattern as every other chunked check in this file.
    """
    outlier_counts = {row["column"]: 0 for _, row in bounds_df.iterrows()}
    total_rows = 0

    for file in chunk_files:
        chunk = pd.read_csv(file)
        total_rows += len(chunk)

        for _, row in bounds_df.iterrows():
            col = row["column"]
            is_outlier = (chunk[col] < row["lower_bound"]) | (chunk[col] > row["upper_bound"])
            outlier_counts[col] += is_outlier.sum()

    return pd.DataFrame([
        {"column": col, "outlier_count": int(count),
         "percentage": round((count / total_rows) * 100, 2)}
        for col, count in outlier_counts.items()
    ])
def plot_boxplots(chunk_files, columns=None, save_path="reports/boxplots.png", df=None):
    """
    Create box plots for the given numeric columns, using the FULL dataset.
    Saves to PNG instead of opening a display window.

    If `df` is already loaded, pass it in directly to avoid loading
    the full dataset a second time.
    """
   

    if columns is None:
        columns = ["Age", "Fare", "SibSp", "Parch"]

    if df is None:
        df = load_full_data(chunk_files)

    fig, axes = plt.subplots(1, len(columns), figsize=(4 * len(columns), 5))
    if len(columns) == 1:
        axes = [axes]

    for ax, col in zip(axes, columns):
        ax.boxplot(df[col].dropna(), vert=True)
        ax.set_title(col)
        ax.set_ylabel(col)

    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=150)
    plt.close(fig)
    print(f"Saved: {save_path}")
def plot_fare_before_after(chunk_files, df=None, save_path="reports/fare_before_after.png"):
    """
    Box plot of Fare before and after log transformation, side by side.
    Visual confirmation that log transform reduces skew/outlier extremity.
    """
    

    if df is None:
        df = load_full_data(chunk_files)

    fare = df["Fare"].dropna()
    fare_log = np.log1p(fare)  # log1p = log(x + 1), handles Fare=0 safely

    fig, axes = plt.subplots(1, 2, figsize=(8, 5))
    axes[0].boxplot(fare, vert=True)
    axes[0].set_title("Fare (original)")

    axes[1].boxplot(fare_log, vert=True)
    axes[1].set_title("Fare (log-transformed)")

    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=150)
    plt.close(fig)
    print(f"Saved: {save_path}")
def extract_ticket_prefix(ticket):
    """
    Extract the alphabetic prefix from a Ticket value, or 'Numeric' if
    the ticket is purely numeric (e.g. '110100' -> 'Numeric', 
    'CT101' -> 'CT', 'A/5 21171' -> 'A5', 'PC 17599' -> 'PC').

    Punctuation (/, ., spaces) is stripped so that variations like
    'A/5' and 'A./5.' collapse into the same prefix 'A5' rather than
    being treated as different categories.
    """
    ticket = str(ticket).strip()
    parts = ticket.split()

    # If the whole ticket is just digits, there's no prefix
    if len(parts) == 1 and parts[0].isdigit():
        return "Numeric"

    # Otherwise, drop the trailing numeric part (the ticket number itself)
    # and keep whatever's left as the prefix
    if parts and parts[-1].isdigit():
        prefix_parts = parts[:-1]
    else:
        prefix_parts = parts  # rare case: no numeric suffix at all

    prefix = "".join(prefix_parts)
    prefix = re.sub(r"[^A-Za-z]", "", prefix).upper()  # strip punctuation, uppercase

    return prefix if prefix else "Numeric"


def calculate_ticket_prefix_distribution(chunk_files):
    """Count how often each Ticket prefix occurs across the full dataset."""
    prefix_counts = pd.Series(dtype=int)

    for file in chunk_files:
        chunk = pd.read_csv(file)
        prefixes = chunk["Ticket"].apply(extract_ticket_prefix)
        prefix_counts = prefix_counts.add(prefixes.value_counts(), fill_value=0)

    return prefix_counts.astype(int).sort_values(ascending=False)
def calculate_deck_distribution(chunk_files):
    """
    Compute the distribution of cabin deck letters across the full dataset,
    including how many rows would fall into 'Unknown' (originally missing Cabin).
    This is reporting only — it shows WHY collapsing Cabin into Deck makes sense
    (i.e., it shows the real counts behind the 77% missing figure, broken into
    decks A-G/T plus Unknown).
    """
    deck_counts = pd.Series(dtype=int)

    for file in chunk_files:
        chunk = pd.read_csv(file)
        deck = chunk["Cabin"].str[0]
        deck = deck.fillna("Unknown")
        deck_counts = deck_counts.add(deck.value_counts(), fill_value=0)

    deck_counts = deck_counts.astype(int).sort_values(ascending=False)
    return deck_counts


def main():
    chunk_files = get_chunk_files("chunks")

    print(f"Found {len(chunk_files)} chunk files:")
    for file in chunk_files:
        print(f"  {file}")

    # --- Missing values ---
    total_missing, total_rows = calculate_missing_values(chunk_files)

    print("\n" + "=" * 40)
    print(f"Total rows checked: {total_rows}")
    print("\nMissing values:")
    print(total_missing[total_missing > 0])

    print("\nMissing percentages:")
    print(((total_missing / total_rows) * 100)[total_missing > 0].round(2))

    # --- Unique values in columns with missing data ---
    unique_values = get_unique_values_for_missing_columns(chunk_files)

    print("\n" + "=" * 40)
    print("Unique values from columns that contain missing data:\n")
    for col, values in unique_values.items():
        values = sorted(list(values), key=str)
        print(f"{col}")
        print(f"Unique count: {len(values)}")
        print(f"Sample values: {values[:10]}")
        print("-" * 40)

    # --- Imputation reference values (computed from a 5% sample) ---
    print("\n" + "=" * 40)
    print("Imputation reference values (computed from 5% random sample):")

    embarked_fill_value = calculate_embarked_fill_value(chunk_files)
    print(f"Embarked fill value (mode): {embarked_fill_value}")

    pclass_title_median, title_median, global_median = calculate_age_medians(chunk_files)
    print(f"\nGlobal median age: {global_median}")
    print("\nMedian age by (Pclass, Title):")
    print(pclass_title_median)
    # --- Deck distribution (for Cabin -> Deck engineering evidence) ---
    deck_counts = calculate_deck_distribution(chunk_files)
    print("\nDeck distribution:")
    print(deck_counts)
    # --- Schema/dtype consistency across chunks ---
    print("\n" + "=" * 40)
    print("Checking dtype consistency across chunks...")
    dtype_df = check_dtype_consistency(chunk_files)
    inconsistent_dtypes = dtype_df[~dtype_df["consistent"]]
    if len(inconsistent_dtypes) > 0:
        print("WARNING: inconsistent dtypes found:")
        print(inconsistent_dtypes)
    else:
        print("All dtypes consistent across chunks.")

    column_sets, mismatches = check_column_name_consistency(chunk_files)
    if mismatches:
        print("WARNING: column name mismatches found:")
        print(mismatches)
    else:
        print("All chunk files have matching column names.")

    # --- Categorical value consistency (case/whitespace issues) ---
    print("\n" + "=" * 40)
    print("Checking categorical value consistency...")
    categorical_df = check_categorical_consistency(chunk_files)
    print(categorical_df)

    needs_cleanup = categorical_df[categorical_df["needs_cleanup"]]
    if len(needs_cleanup) > 0:
        print("\nWARNING: these columns have case/whitespace inconsistencies:")
        print(needs_cleanup)
    # --- Outlier detection (IQR method, full dataset) ---
    print("\n" + "=" * 40)
    print("Detecting outliers (IQR method, full dataset)...")
    full_df = load_full_data(chunk_files)  # loaded once, reused below

    bounds_df = calculate_outlier_bounds(chunk_files, df=full_df)
    print(bounds_df)

    outlier_summary = count_outliers(chunk_files, bounds_df)
    print("\nOutlier counts per column:")
    print(outlier_summary)

    plot_boxplots(chunk_files, df=full_df)
    plot_fare_before_after(chunk_files, df=full_df)

    # --- Save everything to CSV for reporting ---
    print("\n" + "=" * 40)
    print("Saving reports...")
    save_reports(
    total_missing, total_rows, unique_values,
    embarked_fill_value, pclass_title_median,
    title_median, global_median, deck_counts,
    dtype_df, categorical_df
    )


if __name__ == "__main__":
    main()