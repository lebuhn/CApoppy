#!/usr/bin/env python3
"""
12_link_weighed_petal.py

Researcher-confirmed 2026-09-15: in the 4-petals-per-image buckets
(2025-05-20 Perry, 2025-05-22 Cojo, 2025-05-23 Percos, 2025-05-23
Pt. Conception), the single petal that was weighed (the base "petal" row,
petal_number previously blank) was always petal 1.

For each plant in these buckets:
  - set petal_number = 1 on the base weight row
  - if a separate petal_number=1 row already exists (added by
    scripts/segmentation/11_integrate_per_petal_data.py, area only, no weight), copy
    its area_cm2 fields into the (now identified) weight row and drop
    the now-redundant duplicate row
  - if no petal_number=1 area exists yet (image still pending manual
    review), just set the identity — nothing to merge

Scope: the 4-petal buckets only. Every other bucket is already 1 image =
1 plant = 1 petal via image_file_used, so there's no equivalent ambiguity
to resolve there.

Output: petal_area_master.csv rewritten in place (derived file).
"""

import pandas as pd
from pathlib import Path

MASTER_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "petal_area_master.csv"

FOUR_PETAL_BUCKETS = {("2025-05-20", "Perry"), ("2025-05-22", "Cojo"),
                       ("2025-05-23", "Percos"), ("2025-05-23", "Pt. Conception")}


def main() -> None:
    m = pd.read_csv(MASTER_PATH)
    for col in ["area_flag", "measured_by", "notes"]:
        m[col] = m[col].astype(object)

    in_bucket = m.apply(lambda r: (r["date"], r["population"]) in FOUR_PETAL_BUCKETS, axis=1)
    base_mask = in_bucket & (m["petal_flower"] == "petal") & m["petal_number"].isna()

    n_identified = 0
    n_merged = 0
    rows_to_drop = []
    skipped = []

    # Skip plants with more than one candidate base "petal" row (can't tell
    # which one is the weighed petal without guessing) — report, don't guess.
    base_counts = m[base_mask].groupby(["date", "population", "plant"]).size()
    ambiguous_plants = set(base_counts[base_counts > 1].index)

    for idx in m[base_mask].index:
        date, population, plant = m.loc[idx, ["date", "population", "plant"]]
        if (date, population, plant) in ambiguous_plants:
            skipped.append({"date": date, "population": population, "plant": plant,
                             "reason": "multiple base 'petal' rows for this plant — can't tell which is petal 1"})
            continue

        m.loc[idx, "petal_number"] = 1
        n_identified += 1

        dup_mask = (in_bucket & (m["date"] == date) & (m["population"] == population) &
                    (m["plant"] == plant) & (m["petal_number"] == 1) & (m.index != idx))
        dup_rows = m[dup_mask]
        if len(dup_rows) == 1:
            dup_idx = dup_rows.index[0]
            for col in ["area_cm2", "area_cm2_otsu_chroma", "area_flag", "measured_by"]:
                m.loc[idx, col] = dup_rows.iloc[0][col]
            existing = m.loc[idx, "notes"]
            existing = "" if pd.isna(existing) else str(existing)
            m.loc[idx, "notes"] = existing + " [area merged from separate petal-1 measurement row; weighed petal confirmed = petal 1.]"
            rows_to_drop.append(dup_idx)
            n_merged += 1
        elif len(dup_rows) > 1:
            raise SystemExit(f"Ambiguous: {len(dup_rows)} petal_number=1 rows for {date} {population} plant {plant}")

    m = m.drop(index=rows_to_drop)
    m = m.sort_values(["date", "population", "plant", "petal_number"], na_position="first")
    m.to_csv(MASTER_PATH, index=False)

    print(f"Identified petal_number=1 on {n_identified} base weight rows.")
    print(f"Merged area from a duplicate petal-1 row into {n_merged} of those (and dropped the duplicate).")
    print(f"{n_identified - n_merged} had no petal-1 area yet (still pending manual review) — identity set, no area to merge.")
    if skipped:
        print(f"\n{len(skipped)} plant(s) skipped (ambiguous, not guessed):")
        print(pd.DataFrame(skipped).to_string(index=False))
    print(f"\nFinal row count: {len(m)}")


if __name__ == "__main__":
    main()
