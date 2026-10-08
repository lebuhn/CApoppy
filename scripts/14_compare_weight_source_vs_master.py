#!/usr/bin/env python3
"""
14_compare_weight_source_vs_master.py

Crosscheck: does petal_area_master.csv still agree with the raw weight
source it was originally built from, data/raw/plant/petal_weight_2025.csv?
petal_area_master.csv has since been reshaped by scripts/09-13 (per-petal
splitting, segmentation-area integration, petal-1 identification, hand-area
corrections), so a naive row-count or row-order comparison is meaningless.
This script reconstructs a matching key instead.

Key reconstruction (mirrors scripts/11 and scripts/12 exactly, so the join
lines up with what master actually did):
  1. Parse "petal N" out of petal_flower into petal_number, normalizing
     petal_flower back to "petal" (scripts/11 step 1).
  2. In the four known 4-petals-per-image buckets, a base "petal" row with
     petal_number still blank is petal 1 -- but ONLY when it's the single
     such row for that plant. Ambiguous plants (>1 candidate) are left
     unresolved, exactly as scripts/12 leaves them in master (it reports
     them rather than guessing).
  3. Dates normalized to ISO (raw source is M/D/YY; master is already ISO).

Join key: (date, population, plant, petal_flower, petal_number).

What gets reported:
  - Weight rows with no matching master row at all: data lost while
    building master -- should not happen; treated as an error condition.
  - Master rows carrying weight data with no matching weight row: also
    should not happen.
  - Master rows with no weight data and no matching weight row: expected
    -- these are the area-only rows scripts/09+11 added for petals that
    were imaged but never individually weighed.
  - For every matched pair, each shared measurement field is compared
    numerically (water_% is parsed from "89%" text to a 0-1 fraction
    first). Differences beyond a tolerance are written to a flags CSV.

Known, expected source of hand_area_cm2 mismatches: the raw "area" column
in petal_weight_2025.csv is the original hand measurement; master's
hand_area_cm2 includes the Wand-tool re-measurement corrections applied by
scripts/13 (see data/processed/petal_area_weight_data_crosscheck_flags.csv
for the earlier version of this same finding, against the xlsx). Those
rows are expected to differ here and are not a defect in either file --
they are still surfaced below so the researcher can see the full set.

Inputs (read-only): petal_weight_2025.csv, petal_area_master.csv
Output: data/processed/petal_weight_vs_area_master_crosscheck.csv
        (one row per field-level mismatch; empty file with header only if
        everything matches)
"""

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
WEIGHT_PATH = ROOT / "data" / "raw" / "plant" / "petal_weight_2025.csv"
MASTER_PATH = ROOT / "data" / "processed" / "petal_area_master.csv"
OUT_PATH = ROOT / "data" / "processed" / "petal_weight_vs_area_master_crosscheck.csv"

# Same four buckets as scripts/12_link_weighed_petal.py.
FOUR_PETAL_BUCKETS = {("2025-05-20", "Perry"), ("2025-05-22", "Cojo"),
                       ("2025-05-23", "Percos"), ("2025-05-23", "Pt. Conception")}

PETAL_N_RE = re.compile(r"^petal\s+(\d+)$", re.IGNORECASE)

# master_column -> (weight_column, abs_tolerance)
# water_pct tolerance is loose because the raw column is text rounded to the
# nearest whole percent ("89%"); master stores the unrounded fraction.
# hand_area_cm2 tolerance is tight on purpose -- see docstring above for why
# mismatches here are expected, not treated as a special case.
COMPARE_COLS = {
    "wet_wgt_g": ("wet_wgt", 1e-4),
    "dry_wgt_g": ("dry_wgt", 1e-4),
    "length_mm": ("length", 1e-4),
    "water_mg": ("water_mg", 1e-4),
    "water_pct": ("water_pct", 0.006),  # weight-side value is the parsed fraction, not the raw "89%" text
    "hand_area_cm2": ("area", 1e-3),
}

NO_PETAL_NUMBER = -1  # sentinel so NaN petal_number still matches NaN petal_number on merge


def for_display(df: pd.DataFrame) -> pd.DataFrame:
    """Swap the NO_PETAL_NUMBER sentinel back to blank for printing."""
    out = df.copy()
    out["petal_number"] = out["petal_number"].mask(out["petal_number"] == NO_PETAL_NUMBER)
    return out


def load_weight_source() -> pd.DataFrame:
    w = pd.read_csv(WEIGHT_PATH)
    w["date"] = pd.to_datetime(w["date"], format="mixed", dayfirst=False).dt.strftime("%Y-%m-%d")
    w["petal_flower"] = w["petal_flower"].str.strip()
    w["petal_number"] = pd.NA

    for idx, val in w["petal_flower"].items():
        m = PETAL_N_RE.match(val) if isinstance(val, str) else None
        if m:
            w.loc[idx, "petal_number"] = int(m.group(1))
            w.loc[idx, "petal_flower"] = "petal"

    in_bucket = w.apply(lambda r: (r["date"], r["population"]) in FOUR_PETAL_BUCKETS, axis=1)
    base_mask = in_bucket & (w["petal_flower"] == "petal") & w["petal_number"].isna()
    base_counts = w[base_mask].groupby(["date", "population", "plant"]).size()
    unambiguous_plants = set(base_counts[base_counts == 1].index)
    for idx in w[base_mask].index:
        key = tuple(w.loc[idx, ["date", "population", "plant"]])
        if key in unambiguous_plants:
            w.loc[idx, "petal_number"] = 1

    w["water_pct"] = w["water_%"].str.rstrip("%").astype(float) / 100
    w["petal_number"] = w["petal_number"].fillna(NO_PETAL_NUMBER).astype(int)
    return w


def load_master() -> pd.DataFrame:
    m = pd.read_csv(MASTER_PATH)
    m["petal_number"] = m["petal_number"].fillna(NO_PETAL_NUMBER).astype(int)
    return m


def main() -> None:
    w = load_weight_source()
    m = load_master()

    key_cols = ["date", "population", "plant", "petal_flower", "petal_number"]
    # Prefix every non-key column up front so the merge never has to guess
    # which frame a same-named column (water_mg, water_pct) came from.
    w = w.rename(columns={c: f"w_{c}" for c in w.columns if c not in key_cols})
    m = m.rename(columns={c: f"m_{c}" for c in m.columns if c not in key_cols})

    # A key shared by >1 row on either side (e.g. a plant where scripts/12
    # couldn't tell which "petal" row was petal 1, so both were left with
    # petal_number NaN) turns the merge into a cross product for that key --
    # every weight row would get compared against every master row sharing
    # it, producing mismatches that just reflect the wrong pairing rather
    # than a real data problem. Pull those keys out and report them as
    # unresolved instead of numerically diffing them.
    w_counts, m_counts = w.groupby(key_cols).size(), m.groupby(key_cols).size()
    ambiguous_keys = set(w_counts[w_counts > 1].index) | set(m_counts[m_counts > 1].index)

    merged = w.merge(m, on=key_cols, how="outer", indicator=True)
    is_ambiguous = merged[key_cols].apply(lambda r: tuple(r) in ambiguous_keys, axis=1)

    ambiguous = merged[is_ambiguous]
    weight_only = merged[(merged["_merge"] == "left_only") & ~is_ambiguous]
    master_only = merged[(merged["_merge"] == "right_only") & ~is_ambiguous]
    matched = merged[(merged["_merge"] == "both") & ~is_ambiguous]

    master_data_cols = [f"m_{c}" for c in COMPARE_COLS]
    master_has_data = master_only[master_data_cols].notna().any(axis=1)

    print(f"Weight source rows: {len(w)}")
    print(f"Master rows: {len(m)}")
    print(f"Matched on (date, population, plant, petal_flower, petal_number): {len(matched)}")
    print(f"Rows on an ambiguous key (shared by >1 row on one or both sides -- not diffed, see below): "
          f"{len(ambiguous)}")
    print(f"Weight rows with no master match (data lost building master -- unexpected): {len(weight_only)}")
    print(f"Master rows with weight data but no weight-row match (unexpected): {int(master_has_data.sum())}")
    print(f"Master rows with no weight data and no match (expected -- area-only petals): "
          f"{len(master_only) - int(master_has_data.sum())}")

    if len(ambiguous):
        print("\nAmbiguous keys (can't tell which weight row pairs with which master row):")
        print(for_display(ambiguous)[key_cols].drop_duplicates().to_string(index=False))
    if len(weight_only):
        print("\nUnmatched weight rows:")
        print(for_display(weight_only)[key_cols].to_string(index=False))
    if master_has_data.any():
        print("\nUnmatched master rows carrying weight data:")
        print(for_display(master_only[master_has_data])[key_cols].to_string(index=False))

    flags = []
    for master_col, (weight_col, tol) in COMPARE_COLS.items():
        wv = matched[f"w_{weight_col}"]
        mv = matched[f"m_{master_col}"]
        both_present = wv.notna() & mv.notna()
        diff = (wv - mv).abs()
        mismatch = both_present & (diff > tol)
        for idx in matched[mismatch].index:
            row = matched.loc[idx]
            flags.append({
                "date": row["date"], "population": row["population"], "plant": row["plant"],
                "petal_flower": row["petal_flower"],
                "petal_number": None if row["petal_number"] == NO_PETAL_NUMBER else row["petal_number"],
                "field": master_col, "weight_value": wv[idx], "master_value": mv[idx],
                "abs_diff": diff[idx],
            })

    flags_df = pd.DataFrame(flags, columns=["date", "population", "plant", "petal_flower", "petal_number",
                                             "field", "weight_value", "master_value", "abs_diff"])
    flags_df.to_csv(OUT_PATH, index=False)
    print(f"\n{len(flags_df)} field-level mismatch(es) beyond tolerance written to {OUT_PATH.relative_to(ROOT)}")
    if len(flags_df):
        print(flags_df["field"].value_counts().to_string())


if __name__ == "__main__":
    main()
