#!/usr/bin/env python3
"""
13_correct_xlsx_hand_areas.py

Writes the corrected hand-measured petal areas (Wand-tool re-measurements,
see chat log 2026-09-14/15) back into the ORIGINAL source spreadsheet,
data/raw/plant/petal_weight_3.xlsx, sheet "Petal_2025_low", column H
("area"). This is the one script in this pipeline that intentionally
writes to a raw input — done only because the researcher explicitly asked
for the correction to be written back, and only after:
  - confirming column H carries no formulas (J/K do: water_mg, water_% —
    those are left untouched, and recalculated after save since openpyxl
    strips ALL cached formula values sheet-wide on any save, not just the
    cells it touches)
  - backing up the original file to data/raw/plant/backups/

Scope: only the 12 values where an existing xlsx row can be identified
unambiguously by (date, population, plant) — the 11 corrected
2025-03-26 Percos measurements, and the 2025-05-23 Pt. Conception plant 13
"petal" (petal_number=1) row. The 3 new petal_number=2/3/4 rows for that
same plant are NOT written here — they have no corresponding row in the
xlsx at all (that petal-level structure doesn't exist in the source
sheet), so adding them would mean inserting new rows, not correcting
existing ones. Left for a separate, explicit decision.

Source of truth for the corrected values: petal_area_master.csv
(hand_area_cm2 column).
"""

import openpyxl
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
XLSX_PATH = ROOT / "data" / "raw" / "plant" / "petal_weight_3.xlsx"
MASTER_PATH = ROOT / "data" / "processed" / "petal_area_master.csv"

# (date, population, plant, petal_number) -> only rows with an existing xlsx counterpart.
# petal_number NaN/1 for the base "petal" row in each case (matches the original
# unnumbered "petal" xlsx row); explicitly excludes 2025-05-23 Pt.Con plant 13's
# petal_number 2/3/4 (no xlsx row exists for those).
TARGETS = [
    ("2025-03-26", "Percos", p, None) for p in range(1, 12)
] + [
    ("2025-05-23", "Pt. Conception", 13, 1.0),
]


def main() -> None:
    master = pd.read_csv(MASTER_PATH)
    master["date_p"] = pd.to_datetime(master["date"], format="mixed", dayfirst=False)

    wb = openpyxl.load_workbook(XLSX_PATH)  # formulas as formulas, not values
    ws = wb["Petal_2025_low"]
    header = [c.value for c in ws[1]]
    col = {name: i + 1 for i, name in enumerate(header) if name}
    date_col, pop_col, plant_col, area_col = col["date"], col["population"], col["plant"], col["area"]

    written = []
    for date, population, plant, petal_number in TARGETS:
        mrow = master[(master.date_p == pd.Timestamp(date)) & (master.population == population) &
                       (master.plant == plant) &
                       ((master.petal_number == petal_number) if petal_number is not None else master.petal_number.isna())]
        if len(mrow) != 1:
            raise SystemExit(f"Expected exactly 1 master row for {date} {population} plant {plant} "
                              f"petal {petal_number}, found {len(mrow)}")
        new_area = mrow.iloc[0]["hand_area_cm2"]

        # Find the matching xlsx row: same population/plant, date matching
        # either the ISO string or an Excel serial (mixed format in this sheet).
        xlsx_row = None
        for r in range(2, ws.max_row + 1):
            xdate, xpop, xplant = ws.cell(r, date_col).value, ws.cell(r, pop_col).value, ws.cell(r, plant_col).value
            if xpop != population or xplant != plant:
                continue
            try:
                if hasattr(xdate, "year"):  # openpyxl already parsed this cell as a datetime
                    parsed = pd.Timestamp(xdate)
                elif isinstance(xdate, str) and "-" in xdate:
                    parsed = pd.Timestamp(xdate)
                else:
                    parsed = pd.Timestamp("1899-12-30") + pd.to_timedelta(float(xdate), unit="D")
            except (ValueError, TypeError):
                continue
            if parsed == pd.Timestamp(date):
                xlsx_row = r
                break
        if xlsx_row is None:
            raise SystemExit(f"No xlsx row found for {date} {population} plant {plant}")

        old_area = ws.cell(xlsx_row, area_col).value
        ws.cell(xlsx_row, area_col).value = round(float(new_area), 4)
        written.append({"row": xlsx_row, "date": date, "population": population, "plant": plant,
                         "old_area": old_area, "new_area": round(float(new_area), 4)})

    wb.save(XLSX_PATH)
    print(f"Wrote {len(written)} corrected area values.")
    print(pd.DataFrame(written).to_string(index=False))


if __name__ == "__main__":
    main()
