import pandas as pd
import os

# --- Configuration ---
# Files to analyze and output file
ETF1_FILE = './files/Constituent_IE00BL25JM42.xlsx'
ETF2_FILE = './files/Constituent_IE0006WW1TQ4.xlsx'
OUTPUT_MD_FILE = 'Overlap.md'
OUTPUT_XLSX_FILE = 'Overlap.xlsx'
# Number of rows to skip before the header row (0-indexed) for each ETF file
ETF1_SKIP_ROWS = 3
ETF2_SKIP_ROWS = 3
# Set to True if weightings are stored as decimals (0.05 = 5%), False if already percentages
WEIGHTINGS_AS_DECIMALS = True
# Column names used for merging and calculation
ISIN_COL = 'ISIN'
NAME_COL = 'Name'
WEIGHTING_COL = 'Weighting'
OVERLAP_COL = 'Overlap'


def _extract_etf_label(filepath):
    """Extract a readable ETF label from the file path."""
    basename = os.path.splitext(os.path.basename(filepath))[0]
    # Strip common prefixes like 'Constituent_'
    if basename.startswith('Constituent_'):
        return basename[len('Constituent_'):]
    return basename


def _check_duplicates(df, label):
    """Check for duplicate ISINs and warn. Returns deduplicated DataFrame."""
    dupes = df[df[ISIN_COL].duplicated(keep=False)]
    if not dupes.empty:
        dupe_isins = dupes[ISIN_COL].unique()
        print(f"\n⚠ WARNING: {label} contains {len(dupe_isins)} duplicate ISIN(s): {list(dupe_isins[:5])}")
        print(f"  Aggregating duplicate weightings by summing them.")
        # Aggregate: sum weightings, keep first name
        df = df.groupby(ISIN_COL, as_index=False).agg({
            NAME_COL: 'first',
            WEIGHTING_COL: 'sum'
        })
    return df


def _check_weighting_sanity(df, label):
    """Warn if the total weightings don't sum to roughly 1.0 or 100."""
    total = df[WEIGHTING_COL].sum()
    if WEIGHTINGS_AS_DECIMALS:
        if not (0.95 <= total <= 1.05):
            print(f"\n⚠ WARNING: {label} weightings sum to {total:.4f} (expected ~1.0). Check SKIP_ROWS or WEIGHTINGS_AS_DECIMALS.")
    else:
        if not (95 <= total <= 105):
            print(f"\n⚠ WARNING: {label} weightings sum to {total:.2f} (expected ~100). Check SKIP_ROWS or WEIGHTINGS_AS_DECIMALS.")


def _build_summary(etf1_label, etf2_label, df1_count, df2_count, overlap_count,
                    etf1_overlap_weight_sum, etf2_overlap_weight_sum,
                    total_overlap_sum):
    """Build the summary report as a list of (metric, value) tuples."""
    multiplier = 100 if WEIGHTINGS_AS_DECIMALS else 1
    return [
        ('ETF1', etf1_label),
        ('ETF1 constituents', str(df1_count)),
        ('ETF2', etf2_label),
        ('ETF2 constituents', str(df2_count)),
        ('Overlapping', f'{overlap_count} ({100 * overlap_count / df1_count:.1f}% of ETF1, {100 * overlap_count / df2_count:.1f}% of ETF2)'),
        ('ETF1 overlapping weight', f'{multiplier * etf1_overlap_weight_sum:.2f}%'),
        ('ETF2 overlapping weight', f'{multiplier * etf2_overlap_weight_sum:.2f}%'),
        ('Total Common Exposure', f'{multiplier * total_overlap_sum:.2f}%'),
    ]


def _summary_to_console(summary):
    """Print the summary report to console."""
    print("\n--- Summary Report ---")
    for metric, value in summary:
        print(f"{metric}: {value}")
    print("----------------------")


def _summary_to_markdown(summary):
    """Format the summary report as a markdown table string."""
    lines = ['## Summary\n']
    lines.append('| Metric | Value |')
    lines.append('|--------|-------|')
    for metric, value in summary:
        lines.append(f'| {metric} | {value} |')
    return '\n'.join(lines) + '\n'


def analyze_etf_overlap(etf1_path, etf1_skip_rows, etf2_path, etf2_skip_rows, md_output_path, xlsx_output_path):
    """
    Reads two ETF constituent files, calculates the common exposure (minimum 
    weighting) for overlapping ISINs, and saves the results.
    """
    etf1_label = _extract_etf_label(etf1_path)
    etf2_label = _extract_etf_label(etf2_path)

    print(f"--- ETF Overlap Analysis: {etf1_label} vs {etf2_label} ---")
    
    try:
        # Read Data for ETF 1
        print(f"Reading {etf1_path} (skipping {etf1_skip_rows} rows)...")
        df1 = pd.read_excel(etf1_path, skiprows=etf1_skip_rows, engine='openpyxl')
        
        # Read Data for ETF 2
        print(f"Reading {etf2_path} (skipping {etf2_skip_rows} rows)...")
        df2 = pd.read_excel(etf2_path, skiprows=etf2_skip_rows, engine='openpyxl')

    except FileNotFoundError as e:
        print(f"\nError: One of the input files was not found. Please ensure both '{etf1_path}' and '{etf2_path}' exist.")
        print(f"Missing file: {e.filename}")
        return
    except Exception as e:
        print(f"\nAn error occurred during file reading: {e}")
        return

    # Per-DataFrame column validation with specific error reporting
    required_cols = [NAME_COL, ISIN_COL, WEIGHTING_COL]
    for label, df in [("ETF1", df1), ("ETF2", df2)]:
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            print(f"\nError: {label} is missing columns: {missing}. Found columns: {list(df.columns)}")
            return

    # Ensure ISINs are treated as strings to avoid merging issues with different data types
    df1[ISIN_COL] = df1[ISIN_COL].astype(str).str.strip()
    df2[ISIN_COL] = df2[ISIN_COL].astype(str).str.strip()

    # Check for and handle duplicate ISINs
    df1 = _check_duplicates(df1, f"ETF1 ({etf1_label})")
    df2 = _check_duplicates(df2, f"ETF2 ({etf2_label})")

    # Weighting sanity check
    _check_weighting_sanity(df1, f"ETF1 ({etf1_label})")
    _check_weighting_sanity(df2, f"ETF2 ({etf2_label})")

    # Perform Inner Join (Overlap)
    # An 'inner' merge ensures we only keep ISINs present in BOTH DataFrames (the overlap)
    merged_df = pd.merge(
        df1[[NAME_COL, ISIN_COL, WEIGHTING_COL]],
        df2[[ISIN_COL, WEIGHTING_COL]],
        on=ISIN_COL,
        how='inner',
        suffixes=('_ETF1', '_ETF2')
    )

    print(f"Found {len(merged_df)} overlapping constituents.")

    # Calculate Common Exposure (Overlap)
    # Overlap is defined as the minimum of the two weightings, 
    # representing the shared exposure/agreement.
    merged_df[OVERLAP_COL] = merged_df[[f'{WEIGHTING_COL}_ETF1', f'{WEIGHTING_COL}_ETF2']].min(axis=1)
    
    # Prepare Final Output DataFrame with both individual weightings for context
    final_df = merged_df[[NAME_COL, ISIN_COL, f'{WEIGHTING_COL}_ETF1', f'{WEIGHTING_COL}_ETF2', OVERLAP_COL]].copy()
    
    # Calculate sums BEFORE rounding to avoid accumulated rounding errors
    total_overlap_sum = final_df[OVERLAP_COL].sum()
    etf1_overlap_weight_sum = final_df[f'{WEIGHTING_COL}_ETF1'].sum()
    etf2_overlap_weight_sum = final_df[f'{WEIGHTING_COL}_ETF2'].sum()

    # Round weighting and overlap values to 4 decimal places for cleanliness
    for col in [f'{WEIGHTING_COL}_ETF1', f'{WEIGHTING_COL}_ETF2', OVERLAP_COL]:
        final_df[col] = final_df[col].round(4)

    # Sort the DataFrame by the Overlap column (DESCENDING)
    final_df.sort_values(by=OVERLAP_COL, ascending=False, inplace=True)

    # Build summary once, use for both outputs
    summary = _build_summary(
        etf1_label, etf2_label,
        len(df1), len(df2), len(final_df),
        etf1_overlap_weight_sum, etf2_overlap_weight_sum,
        total_overlap_sum
    )

    # Save to Excel
    try:
        final_df.to_excel(xlsx_output_path, index=False, sheet_name='Overlap Analysis', engine='openpyxl')
        print(f"Successfully saved overlap data to: {xlsx_output_path}")
    except Exception as e:
        print(f"\nError saving Excel file: {e}")
        return

    # Save to Markdown
    try:
        with open(md_output_path, 'w') as f:
            f.write(f'# ETF Overlap Analysis: {etf1_label} vs {etf2_label}\n\n')
            f.write(final_df.to_markdown(index=False))
            f.write('\n\n')
            f.write(_summary_to_markdown(summary))
        print(f"Successfully saved overlap data to: {md_output_path}")
    except Exception as e:
        print(f"\nError saving Markdown file: {e}")
        return

    # Print Summary to console
    _summary_to_console(summary)


if __name__ == '__main__':
    # You need to have pandas, openpyxl, and tabulate installed:
    # pip install pandas openpyxl tabulate

    analyze_etf_overlap(ETF1_FILE, ETF1_SKIP_ROWS, ETF2_FILE, ETF2_SKIP_ROWS, OUTPUT_MD_FILE, OUTPUT_XLSX_FILE)
