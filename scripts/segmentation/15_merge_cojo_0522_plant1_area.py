#!/usr/bin/env python3
"""
15_merge_cojo_0522_plant1_area.py

Follow-up to scripts/segmentation/12_link_weighed_petal.py for the one plant
it left as two rows: 2025-05-22 Cojo plant 1. Both rows already carry
petal_number = 1 (so script 12's "base row has blank petal_number" mask
never picked it up):
  - the weighed row: wet/dry weight, no area
  - the segmentation row added by script 11: area_cm2 / otsu_chroma, no weight

Researcher-confirmed (see script 12) that the weighed petal in this bucket
is petal 1, so this applies the same merge script 12 applied to the other
plants: copy the area fields into the weighed row, append a note, and drop
the area-only duplicate.

Guards: stops without writing unless there are exactly two petal-1 rows for
this plant, one with weights and no area and one with area and no weights.

Output: petal_area_master.csv rewritten in place (derived file), after
writing a timestamped backup next to it.
"""

import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

MASTER_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "petal_area_master.csv"

AREA_COLS = ["area_cm2", "area_cm2_otsu_chroma", "area_flag", "measured_by"]
WEIGHT_COLS = ["wet_wgt_g", "dry_wgt_g"]


def main() -> None:
    # Read every field as text and write it back unchanged (CRLF, integers
    # without ".0"), so only the merged row and the dropped row differ.
    m = pd.read_csv(MASTER_PATH, dtype=str, keep_default_na=False)

    mask = ((m["date"] == "5/22/25") & (m["population"] == "Cojo") & (m["plant"] == "1") &
            (m["petal_flower"] == "petal") & (m["petal_number"] == "1"))
    rows = m[mask]
    if len(rows) != 2:
        raise SystemExit(f"Expected 2 petal-1 rows for 2025-05-22 Cojo plant 1, found {len(rows)}")

    has_weight = (rows[WEIGHT_COLS] != "").all(axis=1)
    has_area = rows["area_cm2"] != ""
    weight_rows = rows[has_weight & ~has_area]
    area_rows = rows[has_area & ~(rows[WEIGHT_COLS] != "").any(axis=1)]
    if len(weight_rows) != 1 or len(area_rows) != 1:
        raise SystemExit("Rows are not one weight-only row + one area-only row; not merging.")

    keep_idx, drop_idx = weight_rows.index[0], area_rows.index[0]
    for col in AREA_COLS:
        m.loc[keep_idx, col] = m.loc[drop_idx, col]
    m.loc[keep_idx, "notes"] = m.loc[keep_idx, "notes"] + " [area merged from separate petal-1 measurement row; weighed petal confirmed = petal 1.]"
    m = m.drop(index=drop_idx)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = MASTER_PATH.with_name(f"petal_area_master_BACKUP_before_cojo0522_p1_merge_{stamp}.csv")
    shutil.copy2(MASTER_PATH, backup)
    m.to_csv(MASTER_PATH, index=False, lineterminator="\r\n")

    print(f"Backup written: {backup.name}")
    print(f"Merged area_cm2 = {m.loc[keep_idx, 'area_cm2']} into the weighed row; dropped the duplicate.")
    print(f"Final row count: {len(m)}")


if __name__ == "__main__":
    main()
