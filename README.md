# Common Exposure

A small Python script that compares the constituent holdings of two ETFs (or index funds) and calculates their **common exposure** This is the portion of your portfolio that would be duplicated if you held both funds. Specific for Xtrackers!

## Overview

`overlap_analyzer.py` reads two constituent files (as exported from fund provider Xtrackers), matches holdings by ISIN, and reports:

- Which constituents appear in **both** ETFs
- Each constituent's weighting in ETF1 and ETF2
- The **overlap** per constituent, defined as `min(weight_in_ETF1, weight_in_ETF2)` — i.e. the smaller of the two weightings, since that's the portion of exposure common to both funds
- A summary with the total number of overlapping constituents and the **total common exposure** (sum of all overlaps)
- A regional breakdown (`Region.md`) of each fund's weighting by country, rolled up into US / Europe / Rest, independent of the ISIN matching above

Results are written to a Markdown table (`Overlap.md`), an Excel file (`Overlap.xlsx`), and a regional breakdown (`Region.md`), and a summary is printed to the console.

The script also includes a few safety checks:

- **Duplicate ISINs** within a single file are detected and their weightings are summed (with a warning), instead of silently breaking the merge.
- **Weighting sanity checks** warn if a file's weightings don't sum to roughly 100% (or 1.0 if using decimals) — this usually indicates the wrong number of header rows was skipped, or the decimal/percentage setting is wrong.
- Missing required columns (`Name`, `ISIN`, `Weighting`) are reported per-file with the actual columns found, to make misconfigured input files easy to diagnose.

## Limitations

This tool is built specifically around the constituent file format exported by **Xtrackers** ETFs (column names `Name`, `ISIN`, `Weighting`, and a fixed number of header rows to skip). Constituent files from other providers (iShares, Vanguard, SPDR, etc.) use different layouts and column names and will need to be reformatted to match, or the script adjusted, before they can be used.

## Installation

Requires Python 3.8+.

```bash
pip install pandas openpyxl tabulate
```

## Usage

1. Place your two ETF constituent files (`.xlsx`) somewhere accessible, e.g. in the `constituents/` folder.
2. Open [overlap_analyzer.py](overlap_analyzer.py) and edit the configuration block at the top:

```python
ETF1_FILE = './constituents/Constituent_LU0592216393.xlsx'
ETF2_FILE = './constituents/Constituent_LU0274209237.xlsx'
OUTPUT_MD_FILE = 'Overlap.md'
OUTPUT_XLSX_FILE = 'Overlap.xlsx'
OUTPUT_REGION_MD_FILE = 'Region.md'

# Number of rows to skip before the header row (0-indexed) for each ETF file
ETF1_SKIP_ROWS = 3
ETF2_SKIP_ROWS = 3

# Set to True if weightings are stored as decimals (0.05 = 5%), False if already percentages
WEIGHTINGS_AS_DECIMALS = True

# Country names (as they appear in the Xtrackers 'Country' column) counted as
# "Europe" in the US / Europe / Rest summary in Region.md.
EUROPE_COUNTRIES = [
    'Austria', 'Belgium', 'Bulgaria', 'Croatia', 'Cyprus', 'Czech Republic',
    'Denmark', 'Estonia', 'Finland', 'France', 'Germany', 'Greece', 'Hungary',
    'Iceland', 'Ireland', 'Italy', 'Latvia', 'Liechtenstein', 'Lithuania',
    'Luxembourg', 'Malta', 'Netherlands', 'Norway', 'Poland', 'Portugal',
    'Romania', 'Serbia', 'Slovakia', 'Slovenia', 'Spain', 'Sweden',
    'Switzerland', 'Ukraine', 'United Kingdom',
]
```

   - `ETF1_SKIP_ROWS` / `ETF2_SKIP_ROWS`: many providers prepend a few title/metadata rows before the actual header row — set this to however many rows need to be skipped for each file.
   - `WEIGHTINGS_AS_DECIMALS`: set to `True` if the weighting column contains values like `0.0523`, or `False` if it already contains `5.23`.
   - Each input file must contain columns named `Name`, `ISIN`, and `Weighting` (after skipping rows) — rename columns in the source file if they differ.
   - The regional breakdown additionally uses a `Country` column, which Xtrackers constituent files include by default. If a file lacks it, the region breakdown is skipped (with a console message) but the ISIN overlap analysis still runs.
   - `EUROPE_COUNTRIES`: check this against the countries that show up in `Region.md` and adjust if you want a country classified differently (e.g. moved between "Europe" and "Rest").

3. Run the script:

```bash
python overlap_analyzer.py
```

### Example output

```
--- ETF Overlap Analysis: LU0592216393 vs LU0274209237 ---
Reading ./constituents/Constituent_LU0592216393.xlsx (skipping 3 rows)...
Reading ./constituents/Constituent_LU0274209237.xlsx (skipping 3 rows)...
Found 187 overlapping constituents.
Successfully saved overlap data to: Overlap.xlsx
Successfully saved overlap data to: Overlap.md
Successfully saved region breakdown to: Region.md

--- Summary Report ---
ETF1: LU0592216393
ETF1 constituents: 503
ETF2: LU0274209237
ETF2 constituents: 60
Overlapping: 187 (37.2% of ETF1, 311.7% of ETF2)
ETF1 overlapping weight: 41.23%
ETF2 overlapping weight: 58.90%
Total Common Exposure: 39.87%
----------------------
```

`Overlap.md` and `Overlap.xlsx` will each contain the full per-constituent breakdown (name, ISIN, weighting in each ETF, and overlap) sorted by overlap, descending, plus the summary table.

### Weighting by region

The Xtrackers constituent format carries a `Country` column per holding, so `Region.md` doesn't need any of the ISIN matching used above — it's a plain per-file groupby-sum on that column, outer-joined between the two funds:

- One row per country that appears in either fund, with each fund's total weighting in that country and the overlap (`min` of the two).
- A `## Summary: US / Europe / Rest` table underneath, rolling the same numbers up into three groups plus a `Total` row. Which countries count as "Europe" is controlled by the `EUROPE_COUNTRIES` list in the configuration block — check it against the countries you actually see in the per-region table and adjust if a country you care about is missing or misclassified.

Because this report is independent of the ISIN matching, its overlap numbers aren't directly comparable to `Overlap.md`'s — regional overlap only requires both funds to hold *something* in a country, not the same company, so it will generally be much higher than the holdings-level total common exposure.

### Analyzing a different pair of ETFs

Just point `ETF1_FILE` and `ETF2_FILE` at different files and re-run. To batch-compare many ETFs against each other, you could wrap `analyze_etf_overlap(...)` in a loop over file pairs (this isn't built in, but the function is already structured to be called directly with arguments).

## License

Released under [The Unlicense](LICENSE) — public domain, do whatever you want with it, no attribution required.

## A note on authorship

This code was primarily generated with **Google Gemini**. It has been reviewed, but treat it with the same scrutiny you'd give any AI-generated financial tooling — check that the overlap definition matches your intent and always sanity-check the totals against the underlying source data before relying on the numbers.
