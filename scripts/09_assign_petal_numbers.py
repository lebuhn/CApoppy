#!/usr/bin/env python3
"""
09_assign_petal_numbers.py
============================

Purpose
-------
For the four "4 petals per scan" buckets (2025-05-20 Perry, 2025-05-22
Cojo, 2025-05-23 Percos, 2025-05-23 Pt. Conception), each image contains 4
petals from one plant, and area needs to be reported per PETAL, not just
per plant: 4 rows per plant, each carrying a petal_number matching the
physical layout convention confirmed by direct inspection of labeled
example images (IMG_20250522_cojo_0001.png, IMG_20250520_perry_0001.png):

    top-left = petal 4     top-right = petal 3
    bottom-left = petal 2  bottom-right = petal 1

Most images in these buckets have NO visible handwritten petal-position
label (confirmed directly — only a minority of scans, like the two above,
are labeled at all) — so this convention is applied by PHYSICAL LAYOUT
POSITION, not by reading a number off every image.

Orientation matters: some scans in this dataset are stored upright, some
rotated 180 degrees (see scripts/07_segment_petal_area.py's
detect_orientation — uses the handwritten date/population label block's
vertical position as the cue, since every reviewed scan places that label
in the upper portion when upright). Quadrant assignment below is always
done in the ORIENTATION-CORRECTED frame, never the raw pixel frame.

Quadrant split point: NOT the image's own geometric midline. Petals in
this dataset are often scanned off-center (e.g. the ruler strip crowds
them into one side of the frame), so splitting on image_height_px/2 and
image_width_px/2 misclassifies quadrants when the 4 petals themselves
aren't centered in the frame (observed directly: several 2025-05-22 Cojo
images). Instead, the split point is the MEDIAN row/col of the image's
own 4 detected petal centroids — adaptive per image, and for exactly 4
points this always yields a clean 2-vs-2 split on each axis. Quadrant
assignment can still fail (and correctly gets flagged for review) if the
4 petals aren't laid out in a roughly 2x2 arrangement at all — e.g. 3
petals genuinely cluster on one side — since that's a real ambiguity, not
a measurement artifact.

This script does NOT re-run segmentation — it reads the region-level
output already produced by scripts/07_segment_petal_area.py
(petal_area_segmentation_results.csv, which must include centroid_row/
centroid_col/orientation_upright/image_height_px/image_width_px — run
07 after pulling this script if those columns are missing).

Conservative by design: an image is only auto-assigned if exactly 4
"OK"-flagged regions were found by a method AND orientation was
confidently detected. Anything else (wrong region count, no orientation
signal, a region that doesn't clearly fall in one quadrant) is flagged
for manual review rather than guessed at — see FLAG_* constants below.

Exception — genuinely partial scans (see KNOWN_PARTIAL_PETAL_IMAGES):
two images in these buckets have FEWER than 4 petals because a petal
wasn't collected, not because segmentation missed one:
  - IMG_20250520_perry_0001.png (3 petals; petal 4 not collected) — this
    is one of only two scans with visible handwritten position labels, so
    the mapping below was read directly off the card, matching each
    detected region to its nearest label (confirmed by the researcher
    2026-09-15 after an initial mismatch — an automated nearest-label
    read got this wrong, so don't re-derive it, trust the hardcoded map).
  - ptcon_20250523_0008.png (2 petals; petals 3 and 4 not collected) — no
    visible labels; identity confirmed directly by the researcher via
    position relative to the ruler (2026-09-15).
A region count that doesn't match the KNOWN_PARTIAL_PETAL_IMAGES entry
for these two images (e.g. after a re-segmentation) is NOT silently
trusted — it's flagged for review same as any other image, since the
verified mapping is tied to these specific detected regions.

Inputs (read-only)
------------------
- data/processed/segmentation/petal_area_segmentation_results.csv
- data/processed/petal_area_master.csv (for date/population/plant identity
  behind each image_file_used)

Outputs (new files, data/processed/segmentation/)
------------------------------------------------------------------------------
- petal_area_per_petal.csv   4 rows per plant for the 4-petal buckets,
                              each with a petal_number and its own area.
- petal_number_review_needed.csv   Any image that could not be confidently
                              auto-assigned, with the reason — for manual
                              review, not silently dropped.
"""

from __future__ import annotations

import statistics
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUT_DIR = PROJECT_ROOT / "data" / "processed" / "segmentation"
MASTER_PATH = PROJECT_ROOT / "data" / "processed" / "petal_area_master.csv"
RESULTS_PATH = OUT_DIR / "petal_area_segmentation_results.csv"

# The four "4 petals per scan" buckets this script applies to.
FOUR_PETAL_BUCKETS = {
    ("2025-05-20", "Perry"),
    ("2025-05-22", "Cojo"),
    ("2025-05-23", "Percos"),
    ("2025-05-23", "Pt. Conception"),
}

# Quadrant -> petal number, confirmed by direct inspection of labeled
# example scans (see module docstring). Quadrant is determined in the
# orientation-CORRECTED frame (row/col already flipped if upside-down).
QUADRANT_TO_PETAL_NUMBER = {
    ("top", "left"): 4,
    ("top", "right"): 3,
    ("bottom", "left"): 2,
    ("bottom", "right"): 1,
}

# Images confirmed to genuinely have fewer than 4 petals (see module
# docstring) — region identity keyed by (round(centroid_row),
# round(centroid_col)) in the RAW (as-scanned) frame, since that's a
# stable physical fact about this exact scan. region_id (rank by area) is
# NOT used as the key because it could reorder if segmentation parameters
# ever change slightly.
KNOWN_PARTIAL_PETAL_IMAGES = {
    "IMG_20250520_perry_0001.png": {
        (2031, 1795): 1,
        (1958, 1084): 2,
        (1405, 1713): 3,
        # petal 4: not collected for this plant
    },
    "ptcon_20250523_0008.png": {
        (1100, 639): 2,   # closest to the ruler
        (1045, 1043): 1,  # furthest from the ruler
        # petals 3, 4: not collected for this plant
    },
}


def orientation_corrected_centroid(row: pd.Series) -> tuple[float, float] | None:
    """Return (row, col) in the orientation-corrected frame, or None if
    orientation wasn't confidently detected for this image."""
    if pd.isna(row["orientation_upright"]):
        return None
    h, w = row["image_height_px"], row["image_width_px"]
    r, c = row["centroid_row"], row["centroid_col"]
    if not row["orientation_upright"]:
        # 180-degree rotation: (r, c) -> (h - r, w - c)
        r, c = h - r, w - c
    return (r, c)


def assign_for_method(group: pd.DataFrame) -> tuple[list[dict], str | None]:
    """group = all regions for one image, one method. Returns
    (assigned_rows, review_reason). review_reason is None on success."""
    ok = group[group["area_flag"] == "OK"]
    if len(ok) != 4:
        return [], f"found {len(ok)} OK-flagged regions, expected exactly 4"

    if ok["orientation_upright"].isna().any():
        return [], "orientation not confidently detected for this image"

    centroids = [orientation_corrected_centroid(r) for _, r in ok.iterrows()]
    # Split point = median of THIS image's own 4 centroids, not the image's
    # geometric midline (see module docstring) — for exactly 4 points this
    # always gives a clean 2-vs-2 split on each axis.
    row_mid = statistics.median(r for r, c in centroids)
    col_mid = statistics.median(c for r, c in centroids)

    assigned = []
    seen_quadrants = set()
    for r_row, (r, c) in zip(ok.iterrows(), centroids):
        _, r_data = r_row
        quad = ("top" if r < row_mid else "bottom", "left" if c < col_mid else "right")
        if quad in seen_quadrants:
            return [], (f"regions did not resolve to 4 distinct quadrants relative to their own "
                        f"layout (duplicate: {quad}) — petals may not be arranged in a 2x2 grid")
        seen_quadrants.add(quad)
        petal_number = QUADRANT_TO_PETAL_NUMBER[quad]
        assigned.append({
            "petal_number": petal_number,
            "area_cm2": r_data["area_cm2"],
            "centroid_row": r_data["centroid_row"],
            "centroid_col": r_data["centroid_col"],
            "quadrant": f"{quad[0]}-{quad[1]}",
        })

    if seen_quadrants != {("top", "left"), ("top", "right"), ("bottom", "left"), ("bottom", "right")}:
        return [], f"regions did not cover all 4 quadrants: {seen_quadrants}"

    return assigned, None


def assign_from_known_positions(group: pd.DataFrame, position_map: dict[tuple[int, int], int]
                                 ) -> tuple[list[dict], str | None]:
    """For KNOWN_PARTIAL_PETAL_IMAGES: match each OK region to its verified
    petal_number by RAW centroid position instead of quadrant math (too few
    points for that to be meaningful — see module docstring)."""
    ok = group[group["area_flag"] == "OK"]
    if len(ok) != len(position_map):
        return [], f"found {len(ok)} OK-flagged regions, expected exactly {len(position_map)} (verified partial scan)"

    assigned = []
    seen_petals = set()
    for _, r in ok.iterrows():
        key = (round(r["centroid_row"]), round(r["centroid_col"]))
        if key not in position_map:
            return [], f"region at raw centroid {key} doesn't match the verified position map for this scan"
        petal_number = position_map[key]
        if petal_number in seen_petals:
            return [], f"duplicate petal_number {petal_number} matched from position map"
        seen_petals.add(petal_number)
        assigned.append({
            "petal_number": petal_number,
            "area_cm2": r["area_cm2"],
            "centroid_row": r["centroid_row"],
            "centroid_col": r["centroid_col"],
            "quadrant": "verified_partial_scan",
        })

    return assigned, None


def main() -> None:
    results = pd.read_csv(RESULTS_PATH)
    master = pd.read_csv(MASTER_PATH)

    required_cols = {"centroid_row", "centroid_col", "orientation_upright",
                      "image_height_px", "image_width_px"}
    missing = required_cols - set(results.columns)
    if missing:
        raise SystemExit(
            f"petal_area_segmentation_results.csv is missing {missing} — "
            "re-run scripts/07_segment_petal_area.py first (it now writes these columns)."
        )

    # Which images belong to the 4-petal buckets, via master's identity link.
    # NOTE: must de-duplicate to one row per (date, population, plant) first
    # — several dates record more than one master row per plant (a "petal"
    # row and a "flower" row, or several "petal N" rows), which would
    # otherwise look like multiple PLANTS sharing one image (the same
    # row-vs-plant bug already fixed once in scripts/07's
    # write_back_to_master).
    bucket_master = master[master.apply(
        lambda r: (r["date"], r["population"]) in FOUR_PETAL_BUCKETS, axis=1
    )][["date", "population", "plant", "image_file_used"]].dropna(subset=["image_file_used"]).drop_duplicates()

    per_petal_rows = []
    review_rows = []

    for image_path, img_master in bucket_master.groupby("image_file_used"):
        if len(img_master) != 1:
            review_rows.append({"image_path": image_path, "reason":
                                 f"expected exactly 1 plant per image in these buckets, found {len(img_master)}"})
            continue
        date, population, plant = img_master.iloc[0][["date", "population", "plant"]]

        img_results = results[results["image_path"] == image_path]
        if img_results.empty:
            review_rows.append({"image_path": image_path, "reason": "no segmentation results found for this image"})
            continue

        otsu_group = img_results[img_results["method"] == "otsu_chroma"]
        if image_path in KNOWN_PARTIAL_PETAL_IMAGES:
            assigned, reason = assign_from_known_positions(otsu_group, KNOWN_PARTIAL_PETAL_IMAGES[image_path])
        else:
            assigned, reason = assign_for_method(otsu_group)
        if reason:
            review_rows.append({"image_path": image_path, "date": date, "population": population,
                                 "plant": plant, "reason": f"otsu_chroma: {reason}"})
            continue
        petal_areas = {a["petal_number"]: a["area_cm2"] for a in assigned}

        # Only emit rows for petals actually present — a verified partial
        # scan (see KNOWN_PARTIAL_PETAL_IMAGES) genuinely has no data for
        # its missing petal(s), which is different from "not yet resolved".
        for petal_number in sorted(petal_areas):
            per_petal_rows.append({
                "date": date, "population": population, "plant": plant,
                "petal_number": petal_number, "image_path": image_path,
                "area_cm2_otsu_chroma": petal_areas.get(petal_number),
            })

    per_petal = pd.DataFrame(per_petal_rows)
    if not per_petal.empty:
        per_petal["area_cm2"] = per_petal["area_cm2_otsu_chroma"]
    per_petal_path = OUT_DIR / "petal_area_per_petal.csv"
    per_petal.to_csv(per_petal_path, index=False)

    review = pd.DataFrame(review_rows)
    review_path = OUT_DIR / "petal_number_review_needed.csv"
    review.to_csv(review_path, index=False)

    print(f"Assigned petal numbers for {len(per_petal) // 4 if len(per_petal) else 0} images "
          f"({len(per_petal)} petal rows) -> {per_petal_path}")
    print(f"{len(review)} images need manual review -> {review_path}")
    if len(review):
        print(review.to_string(index=False))


if __name__ == "__main__":
    main()
