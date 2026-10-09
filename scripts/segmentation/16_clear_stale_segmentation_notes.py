#!/usr/bin/env python3
"""
16_clear_stale_segmentation_notes.py

Researcher-requested 2026-10-08: remove the interim segmentation notes from
the 4-petals-per-image buckets (2025-05-20 Perry, 2025-05-22 Cojo,
2025-05-23 Percos, 2025-05-23 Pt. Conception). These were written by
scripts/segmentation/07 and 09 before per-petal assignment was finished
and no longer describe the data:
  - "[2 plants share this scan; per-plant region assignment not yet done.
     Detected primary regions: hsv_hue=[..] cm2, otsu_chroma=[..] cm2.]"
     (the hsv_hue method has since been removed)
  - "[value is the largest of N detected regions, NOT a verified
     single-petal measurement; per-petal assignment pending manual review,
     see petal_number_review_needed.csv.]"
     (petal-1 areas are now the per-petal values from scripts 09/11 and
     petal_number_review_needed.csv is empty)
  - "[area now reported per-petal in separate rows below; see
     petal_number 1-4 for this plant.]"
     (script 12 made the base row petal 1 itself)
  - a leading "cm2, otsu_chroma=[..] cm2.]" fragment: the tail of the first
    note above, left behind when its start was cut from some rows earlier

All other note text (label corrections, missing-flower notes, "New row: ..."
and "[area merged ...]" provenance) is kept.

Output: petal_area_master.csv rewritten in place (derived file), after
writing a timestamped backup next to it. Every field is read and written as
text so no other cell changes.
"""

import re
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

MASTER_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "petal_area_master.csv"

BUCKET_DATES = {"5/20/25", "5/22/25", "5/23/25"}

STALE_PATTERNS = [
    r"\[2 plants share this scan; per-plant region assignment not yet done\. "
    r"Detected primary regions: hsv_hue=\[[^\]]*\] cm2, otsu_chroma=\[[^\]]*\] cm2\.\]",
    r"\[value is the largest of \d+ detected regions, NOT a verified single-petal measurement; "
    r"per-petal assignment pending manual review, see petal_number_review_needed\.csv\.\]",
    r"\[area now reported per-petal in separate rows below; see petal_number 1-4 for this plant\.\]",
    r"^\s*cm2, otsu_chroma=\[[^\]]*\] cm2\.\]",
]


def clean(note: str) -> str:
    for pat in STALE_PATTERNS:
        note = re.sub(pat, "", note)
    return re.sub(r"\s+", " ", note).strip()


def main() -> None:
    m = pd.read_csv(MASTER_PATH, dtype=str, keep_default_na=False)

    in_scope = m["date"].isin(BUCKET_DATES)
    before = m.loc[in_scope, "notes"].copy()
    m.loc[in_scope, "notes"] = before.map(clean)
    changed = (m.loc[in_scope, "notes"] != before).sum()

    leftover = m.loc[in_scope, "notes"].str.contains(
        "region assignment not yet done|NOT a verified|area now reported per-petal|hsv_hue|otsu_chroma=\\[")
    if leftover.any():
        raise SystemExit(f"{leftover.sum()} note(s) still contain stale text in an unexpected form; not writing.")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = MASTER_PATH.with_name(f"petal_area_master_BACKUP_before_stale_note_removal_{stamp}.csv")
    shutil.copy2(MASTER_PATH, backup)
    m.to_csv(MASTER_PATH, index=False, lineterminator="\r\n")

    print(f"Backup written: {backup.name}")
    print(f"Cleaned notes on {changed} of {in_scope.sum()} rows dated {sorted(BUCKET_DATES)}.")


if __name__ == "__main__":
    main()
