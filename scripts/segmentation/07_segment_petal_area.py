#!/usr/bin/env python3
"""
07_segment_petal_area.py
=========================

Purpose
-------
Measure Eschscholzia californica (California poppy) petal area from flatbed
scans, using an automated image-segmentation method, and compare it against
the hand-measured (manual ImageJ) areas already recorded in
data/processed/petal_area_master.csv (`hand_area_cm2` column, n=5, from
data/raw/plant/petal_weight_3.xlsx).

Segmentation method
--------------------
  "otsu_chroma": threshold on an "excess orange" chromatic index
  (R - (G+B)/2), with the cut point chosen automatically per image by
  Otsu's method (Otsu, 1979, IEEE Trans. SMC). No fixed color range is
  assumed; the threshold adapts to each image's own brightness/contrast.

  A fixed-hue-range method ("hsv_hue") was run alongside this one through
  2026-09-15 as a cross-check, but was retired: it fragmented on petals
  with a red-toned center (a real color pattern in this species — solidity
  0.54-0.74 vs. 0.93-0.98 for otsu_chroma on the same images, see git
  history of this file for the removed implementation), producing
  unreliable region counts/shapes on a meaningful fraction of images.
  Accuracy is now checked against hand measurements only (see
  paired_hand_vs_automated below) rather than inter-method agreement.

Processing steps:
  1. read each image's embedded scanner DPI to convert pixels to cm^2
     (no ruler detection needed — see calibration note below);
  2. threshold, clean up the mask (remove small specks, fill small holes,
     light morphological closing);
  3. label connected regions and take region properties (area, shape);
  4. write one row per detected region to a tidy results table;
  5. save a QC overlay image (the method's outline drawn on a COPY of
     the original) so every measurement can be visually re-checked without
     ever touching the source file.

Data provenance / FAIR notes
-----------------------------
- Findable:   every output row carries the source image's relative path,
              so results always trace back to one named file.
- Accessible: outputs are plain CSV (petal_area_segmentation_results.csv)
              and PNG — no proprietary formats.
- Interoperable: column names and units are declared once, at the top of
              this file (see COLUMN_DICTIONARY), and area is always in cm^2.
- Reusable:   this file documents its own parameters, package versions
              (scripts/segmentation/requirements.txt, pinned), and writes a
              run_metadata.json sidecar (timestamp, package versions, git
              commit) with every run, so a result can always be traced back
              to the exact code and environment that produced it.

Inputs (READ-ONLY — this script never writes into Petal_scans/ or data/raw/)
------------------------------------------------------------------------------
- Petal_scans/<...>.png            raw scans (untouched)
- data/processed/petal_area_master.csv   plant identity + hand_area_cm2

Outputs (all new files, under data/processed/segmentation/)
------------------------------------------------------------------------------
- petal_area_segmentation_results.csv   one row per detected petal region
                                         (image-grain, not yet linked to a
                                         specific plant unless the image is
                                         single-petal AND identity-confirmed
                                         — see caveat in
                                         compare_to_hand_measurements()).
- qc_overlays/<image_stem>_qc.png       original image + the method's
                                         outline, for visual verification.
- hand_vs_automated_comparison.csv      comparison against the 5 existing
                                         hand-measured values.
- run_metadata.json                     reproducibility sidecar.

Usage
-----
    .venv/bin/python3 scripts/07_segment_petal_area.py

Run from the project root (paths below are relative to it, resolved via
the script's own location so it works regardless of the caller's cwd).
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from skimage import measure, morphology
from skimage.filters import threshold_otsu

import matplotlib
matplotlib.use("Agg")  # no display needed; we only save PNGs
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Column dictionary (Interoperable/Reusable, FAIR) — the single source of
# truth for what each output column means and what units it is in.
# ---------------------------------------------------------------------------
COLUMN_DICTIONARY = {
    "image_path": "Path to the source scan, relative to Petal_scans/. Read-only source; never modified.",
    "method": "Segmentation method: 'otsu_chroma' (see module docstring).",
    "region_id": "1-indexed region label within this image, largest area first.",
    "area_cm2": "Region area in cm^2, computed from pixel count and the image's own embedded scanner DPI (cm_per_pixel = 2.54 / dpi).",
    "area_px": "Region area in pixels (raw segmentation output, before unit conversion).",
    "dpi": "Scanner resolution read from the PNG's embedded metadata (pHYs chunk). Expected 300 for this project; flagged if missing or different.",
    "major_axis_length_cm": "Longest axis of the best-fit ellipse for the region, in cm — a Feret-diameter-like size descriptor.",
    "solidity": "Region area / convex hull area (0-1). Low solidity flags a ragged/merged/torn segmentation worth a visual check.",
    "eccentricity": "0 (circle) to 1 (line) — shape descriptor, not used to filter, kept for QC review.",
    "n_regions_in_image": "How many separate regions this method found in the image after cleanup — informs whether an image was single- or multi-petal.",
    "area_flag": "'OK', or 'IMPLAUSIBLY_LARGE' if area_cm2 exceeds MAX_PLAUSIBLE_PETAL_AREA_CM2 (no real poppy petal is that large — flags a segmentation that likely merged in background/bag/card; never silently dropped, always kept in this table for audit).",
    "shape_flag": "'OK', or 'LOW_SOLIDITY_CHECK_OVERLAY' if solidity < MIN_SOLIDITY_OK — flags a likely fragmented/incomplete mask for a visual check against the QC overlay before trusting the number.",
    "is_primary_candidate": "True for the largest region per (image_path, method) among those NOT flagged IMPLAUSIBLY_LARGE. This is the region used for single-petal-per-image comparisons; all detected regions are still kept in this table.",
    "dpi_cm_per_pixel": "cm-per-pixel computed from the image's embedded scanner DPI (2.54/dpi). This is the value actually used to compute area_cm2.",
    "ruler_cm_per_pixel": "cm-per-pixel computed independently from the physical ruler's own tick spacing in this image (see estimate_scale_from_ruler). None if no confidently periodic tick pattern was found. NOT used to compute area_cm2 — reported as a cross-check on dpi_cm_per_pixel.",
    "ruler_tick_period_px": "Detected pixel spacing between adjacent 1mm ruler ticks, via autocorrelation. None if ruler not detected.",
    "ruler_confidence": "Normalized autocorrelation peak height (0-1) for the detected tick period — higher means more confidently periodic (i.e. more likely a real ruler, not a coincidental texture). None if ruler not detected.",
    "ruler_strip_orientation": "'vertical' or 'horizontal' — which axis the detected ruler's tick marks run along in this image. None if ruler not detected.",
    "ruler_strip_coord": "Pixel coordinate (column if vertical, row if horizontal) where the detected ruler strip starts — drawn as a yellow band on the QC overlay for visual audit. None if ruler not detected.",
    "scale_pct_diff": "100 * (ruler_cm_per_pixel - dpi_cm_per_pixel) / dpi_cm_per_pixel — how far the ruler-based estimate differs from the DPI-based one. None if ruler not detected.",
    "scale_flag": "'OK' (agree within SCALE_MISMATCH_PCT_TOLERANCE), 'SCALE_MISMATCH' (disagree beyond tolerance — investigate before trusting area_cm2), or 'RULER_NOT_DETECTED'.",
    "batch": "'validation_2025_03_26' (distribution-level hand-measurement check, identity not confirmed) or 'resolved' (identity confirmed via petal_area_master.csv, results written back to that file per plant).",
    "centroid_row": "Region centroid row (y, pixels) in the RAW (as-scanned) image, before any orientation correction.",
    "centroid_col": "Region centroid column (x, pixels) in the RAW image, before any orientation correction.",
    "image_height_px": "Raw image height in pixels (as scanned, before any orientation correction) — needed to convert centroid_row to an orientation-corrected quadrant.",
    "image_width_px": "Raw image width in pixels, as above.",
    "orientation_upright": "True if the scan is right-side-up (detected from the handwritten date/population label block's vertical position — every scan reviewed in this project places that label in the upper portion when upright), False if rotated 180 degrees, None if no text block was confidently found. Used by scripts/09_assign_petal_numbers.py to map detected regions to the correct physical quadrant.",
    "orientation_confidence": "Fraction of image area occupied by the detected label-text block used for the orientation call. Not a statistical confidence — a bigger, clearer block is generally more trustworthy, but always spot-check via the QC overlay before trusting an automated call on this.",
    "orientation_note": "Human-readable detail behind the orientation_upright call (label block's row position vs. image height).",
}

# ---------------------------------------------------------------------------
# Calibrated parameters. These were chosen by visual inspection of sample
# scans in this dataset (bright orange/yellow petals on a white background,
# 300 DPI flatbed scans). If this script is applied to photos taken under
# different lighting/equipment, re-check these against a handful of known
# images before trusting the output — see the QC overlays for exactly that.
# ---------------------------------------------------------------------------
# Otsu's method picks a per-image threshold by maximizing between-class
# variance, which assumes a roughly bimodal histogram. On a scan that's
# mostly background, a shadow, gray card, or bag wrinkle can pull the
# automatic split down far enough that half the background gets included
# as "petal" (observed directly on 6/15 images in the 2025-03-26 batch:
# areas of 200-535 cm^2, physically impossible for one poppy petal). A
# floor keeps the method adaptive per-image while preventing that specific
# failure: background excess-orange is near 0 for a neutral white/gray
# background, so a real petal edge should sit well above a modest floor
# regardless of image-to-image lighting differences.
OTSU_MIN_THRESHOLD = 25         # floor on the 0-255 excess-orange scale

# Sanity ceiling: no single California poppy petal is anywhere near this
# large. Used only to FLAG implausible regions (e.g. a segmentation that
# still merges in background/bag/card) for visual review — never used to
# silently discard data. See area_flag in the results table.
MAX_PLAUSIBLE_PETAL_AREA_CM2 = 100

# Below this solidity (region area / convex-hull area), a region is likely
# an incomplete segmentation rather than a genuinely non-convex petal shape.
# Flagged, never silently trusted — always check the QC overlay.
MIN_SOLIDITY_OK = 0.85

MIN_PETAL_AREA_CM2 = 0.3       # regions smaller than this are treated as noise/debris, not a petal
CLOSING_RADIUS_PX = 3          # small morphological closing to smooth ragged mask edges
HOLE_FILL_MAX_PX = 400         # fill interior holes (vein shadows etc.) up to this many pixels

EXPECTED_DPI = 300


# ---------------------------------------------------------------------------
# Scale calibration
# ---------------------------------------------------------------------------

def get_cm_per_pixel(pil_image: Image.Image, image_path: Path) -> tuple[float, float]:
    """Return (cm_per_pixel, dpi) using the PNG's own embedded scanner DPI.

    This is the PRIMARY calibration used to convert measured areas to cm^2.
    A second, fully independent estimate is derived per-image from the
    physical ruler visible in every scan (see estimate_scale_from_ruler
    below) and reported alongside every measurement — not as a fallback,
    but as a genuine cross-check: DPI metadata could in principle be wrong
    (a re-export, a scanner misconfiguration) without anyone noticing, and
    the ruler is ground truth printed on a physical object in the frame.
    Large, systematic disagreement between the two is exactly the kind of
    thing that should block trusting either one until resolved.
    """
    dpi = pil_image.info.get("dpi")
    if not dpi:
        raise ValueError(f"No DPI metadata found in {image_path} — cannot calibrate scale.")
    dpi_x, dpi_y = dpi
    if abs(dpi_x - dpi_y) > 1:
        raise ValueError(f"Non-square DPI ({dpi_x} x {dpi_y}) in {image_path} — unexpected, needs review.")
    if abs(dpi_x - EXPECTED_DPI) > 1:
        print(f"  WARNING: {image_path.name} has DPI={dpi_x}, expected {EXPECTED_DPI}. Proceeding, but flag for review.")
    cm_per_pixel = 2.54 / dpi_x
    return cm_per_pixel, dpi_x


# Ruler ticks are expected at ~1 mm spacing. At ~300 DPI that's ~11.81 px
# between ticks. A wide-open search (originally 6-22 px) turned out to be
# too permissive: on a mostly-smooth image, generic pixel-level noise
# produces weak local autocorrelation peaks almost anywhere, and a wide
# search sometimes latched onto one of those instead of the real ruler
# (observed directly: 4/15 images gave physically-inconsistent periods —
# see git history of this file / run notes for the diagnostic images).
# Narrowing the search to a physically-informed neighborhood around the
# DPI-implied period turns this from "find any periodicity anywhere" into
# "does the ruler confirm the DPI-implied spacing, searched nearby" — a
# less ambitious but far more reliable independent check, and still very
# capable of catching a genuinely wrong DPI (it would show up as no
# confident peak in this neighborhood at all).
RULER_SEARCH_HALF_WIDTH_PX = 3  # +/- pixels around the DPI-implied tick period
RULER_STRIP_WIDTH_PX = 90
RULER_STRIP_STEP_PX = 45
RULER_MIN_CONFIDENCE = 0.30  # normalized autocorrelation peak height to accept a candidate as periodic


def _strongest_periodic_lag(signal_1d: np.ndarray, min_lag: int, max_lag: int) -> tuple[int, float] | None:
    """Find the lag (in samples) of the strongest periodic repeat in a 1D
    signal within [min_lag, max_lag], via normalized autocorrelation.
    Returns (lag, confidence in [0,1]) or None if the signal is too flat,
    or has no genuine local peak in range (see note below).

    IMPORTANT: autocorrelation of a smooth/blurry natural-image signal
    decays roughly monotonically with lag even with NO periodic structure
    at all — nearby pixels are just generally more similar than far-apart
    ones. Taking argmax over a truncated lag window without checking for
    an actual local peak will always return the window's nearest edge,
    which is a real bug this function had in an earlier version (it was
    silently reporting the search floor as "the ruler" on every image).
    Requiring a genuine local maximum (higher than both neighbors) avoids
    that failure mode.
    """
    signal_1d = signal_1d - signal_1d.mean()
    if signal_1d.std() < 3.0:  # essentially flat — not a ruler
        return None
    autocorr = np.correlate(signal_1d, signal_1d, mode="full")
    autocorr = autocorr[len(autocorr) // 2:]
    if autocorr[0] == 0:
        return None
    autocorr = autocorr / autocorr[0]

    # Need one extra sample on each side of [min_lag, max_lag] to check
    # for a genuine local maximum at the window boundaries too.
    lo, hi = max(min_lag - 1, 1), min(max_lag + 1, len(autocorr) - 2)
    if hi <= lo:
        return None

    best_lag, best_val = None, -np.inf
    for lag in range(lo, hi + 1):
        if min_lag <= lag <= max_lag and autocorr[lag] > autocorr[lag - 1] and autocorr[lag] > autocorr[lag + 1]:
            if autocorr[lag] > best_val:
                best_lag, best_val = lag, autocorr[lag]

    if best_lag is None:
        return None
    return best_lag, float(best_val)


def estimate_scale_from_ruler(gray: np.ndarray, expected_period_px: float) -> dict:
    """Independently estimate cm_per_pixel from the ruler's own printed tick
    spacing, by finding the most strongly periodic dark-tick pattern in a
    thin strip of the image, searched within RULER_SEARCH_HALF_WIDTH_PX of
    expected_period_px (the DPI-implied tick spacing). Tries both vertical
    strips (ruler's long axis running top-to-bottom) and horizontal strips
    (ruler rotated 90 degrees) since both orientations occur in this
    dataset, and keeps whichever candidate is most confidently periodic.

    Returns a dict with cm_per_pixel (or None if nothing confidently
    periodic was found near the expected spacing), plus the strip
    location/orientation and a confidence score, so the result can be
    drawn on the QC overlay and audited visually rather than trusted
    blindly.
    """
    min_lag = max(int(round(expected_period_px)) - RULER_SEARCH_HALF_WIDTH_PX, 2)
    max_lag = int(round(expected_period_px)) + RULER_SEARCH_HALF_WIDTH_PX

    best = None  # (confidence, cm_per_pixel, period_px, orientation, coord)

    for orientation, arr in (("vertical", gray), ("horizontal", gray.T)):
        h, w = arr.shape
        for x0 in range(0, max(w - RULER_STRIP_WIDTH_PX, 1), RULER_STRIP_STEP_PX):
            strip = arr[:, x0:x0 + RULER_STRIP_WIDTH_PX]
            if strip.shape[1] < RULER_STRIP_WIDTH_PX // 2:
                continue
            # Ticks are dark lines crossing the ruler -> the darkest pixel
            # in each row (or column, for the transposed search) dips
            # periodically at each tick.
            signal_1d = strip.min(axis=1).astype(np.float64)
            result = _strongest_periodic_lag(signal_1d, min_lag, max_lag)
            if result is None:
                continue
            period_px, confidence = result
            if confidence < RULER_MIN_CONFIDENCE:
                continue
            if best is None or confidence > best[0]:
                cm_per_pixel = 0.1 / period_px  # ticks are 1 mm = 0.1 cm apart
                best = (confidence, cm_per_pixel, period_px, orientation, x0)

    if best is None:
        return {"ruler_cm_per_pixel": None, "ruler_tick_period_px": None,
                "ruler_confidence": None, "ruler_strip_orientation": None,
                "ruler_strip_coord": None}

    confidence, cm_per_pixel, period_px, orientation, coord = best
    return {
        "ruler_cm_per_pixel": round(cm_per_pixel, 6),
        "ruler_tick_period_px": period_px,
        "ruler_confidence": round(confidence, 3),
        "ruler_strip_orientation": orientation,
        "ruler_strip_coord": coord,
    }


# ---------------------------------------------------------------------------
# Segmentation: Otsu threshold on an excess-orange chromatic index
# ---------------------------------------------------------------------------

def segment_otsu_chroma(rgb: np.ndarray) -> np.ndarray:
    r = rgb[..., 0].astype(np.float64)
    g = rgb[..., 1].astype(np.float64)
    b = rgb[..., 2].astype(np.float64)
    excess_orange = r - (g + b) / 2.0
    t = max(threshold_otsu(excess_orange), OTSU_MIN_THRESHOLD)
    return excess_orange > t


# ---------------------------------------------------------------------------
# Shared cleanup + region measurement
# ---------------------------------------------------------------------------

def clean_and_measure(mask: np.ndarray, cm_per_pixel: float) -> list[dict]:
    min_area_px = int(MIN_PETAL_AREA_CM2 / (cm_per_pixel ** 2))
    hole_fill_px = max(HOLE_FILL_MAX_PX, min_area_px // 20)

    # NOTE: skimage>=0.26 renamed min_size/area_threshold to max_size on these
    # two functions (same meaning: the size at/below which a region is
    # dropped) — using the current names here to match the pinned version in
    # scripts/segmentation/requirements.txt without deprecation warnings.
    cleaned = morphology.remove_small_objects(mask, max_size=min_area_px)
    cleaned = morphology.remove_small_holes(cleaned, max_size=hole_fill_px)
    cleaned = morphology.closing(cleaned, morphology.disk(CLOSING_RADIUS_PX))

    labeled = measure.label(cleaned)
    regions = measure.regionprops(labeled)
    regions = [r for r in regions if r.area >= min_area_px]
    regions.sort(key=lambda r: r.area, reverse=True)

    out = []
    for region in regions:
        area_cm2 = round(region.area * (cm_per_pixel ** 2), 4)
        out.append({
            "area_px": int(region.area),
            "area_cm2": area_cm2,
            "major_axis_length_cm": round(region.axis_major_length * cm_per_pixel, 3),
            "solidity": round(region.solidity, 4),
            "eccentricity": round(region.eccentricity, 4),
            "area_flag": "IMPLAUSIBLY_LARGE" if area_cm2 > MAX_PLAUSIBLE_PETAL_AREA_CM2 else "OK",
            "shape_flag": "LOW_SOLIDITY_CHECK_OVERLAY" if region.solidity < MIN_SOLIDITY_OK else "OK",
            "centroid_row": round(region.centroid[0], 1),
            "centroid_col": round(region.centroid[1], 1),
            "bbox": region.bbox,
        })
    return out, labeled, cleaned


# ---------------------------------------------------------------------------
# Orientation detection: some scans are upright, some are rotated 180
# degrees (confirmed directly — e.g. the 2025_09_15 folder's filenames vs
# folder-date mismatch traced earlier to exactly this). For the 4-petals-
# per-image buckets, knowing "which corner is really top-left" matters
# because petal numbering follows a fixed physical-layout convention
# (top-left=4, top-right=3, bottom-left=2, bottom-right=1 — confirmed by
# reading labeled examples directly: IMG_20250522_cojo_0001.png). Detect
# orientation from the handwritten date/population label block, which
# every scan reviewed in this project places in the UPPER portion of the
# card when upright: find the largest cluster of small, irregular dark
# marks (handwriting) that isn't the ruler or a petal, and check whether
# its vertical center sits in the top or bottom half of the frame.
# ---------------------------------------------------------------------------

def detect_orientation(gray: np.ndarray, petal_mask: np.ndarray, ruler_mask: np.ndarray | None) -> dict:
    h, w = gray.shape
    dark = gray < 140  # handwriting/printed text: dark marks on white background
    dark = dark & ~petal_mask
    if ruler_mask is not None:
        dark = dark & ~ruler_mask
    dark = morphology.remove_small_objects(dark, max_size=15)
    dark = morphology.closing(dark, morphology.disk(8))  # merge nearby strokes into one blob per word/line

    labeled = measure.label(dark)
    regions = [r for r in measure.regionprops(labeled) if r.solidity < 0.9 or r.area < (h * w * 0.05)]
    # text blocks are irregular (low solidity) and modest in size, unlike
    # large filled shapes; this excludes anything that slipped through as
    # a big solid blob (e.g. a mis-thresholded shadow).
    if not regions:
        return {"orientation_upright": None, "orientation_confidence": None, "orientation_note": "no text block found"}

    regions.sort(key=lambda r: r.area, reverse=True)
    label_region = regions[0]
    upright = bool(label_region.centroid[0] < h / 2)
    return {
        "orientation_upright": upright,
        "orientation_confidence": round(label_region.area / (h * w), 4),
        "orientation_note": f"label block centroid row={label_region.centroid[0]:.0f} of {h}",
    }


# ---------------------------------------------------------------------------
# Per-image driver
# ---------------------------------------------------------------------------

SCALE_MISMATCH_PCT_TOLERANCE = 5.0  # DPI vs. ruler-derived cm_per_pixel disagreement beyond this % is flagged


def measure_image(image_path: Path, qc_dir: Path) -> list[dict]:
    with Image.open(image_path) as im:
        cm_per_pixel, dpi = get_cm_per_pixel(im, image_path)
        rgb = np.array(im.convert("RGB"))

    gray = np.array(Image.fromarray(rgb).convert("L"))
    expected_tick_period_px = 0.1 / cm_per_pixel  # DPI-implied px per 1mm ruler tick
    ruler = estimate_scale_from_ruler(gray, expected_tick_period_px)

    scale_flag = "RULER_NOT_DETECTED"
    scale_pct_diff = None
    if ruler["ruler_cm_per_pixel"] is not None:
        scale_pct_diff = round(100 * (ruler["ruler_cm_per_pixel"] - cm_per_pixel) / cm_per_pixel, 2)
        scale_flag = "SCALE_MISMATCH" if abs(scale_pct_diff) > SCALE_MISMATCH_PCT_TOLERANCE else "OK"

    mask = segment_otsu_chroma(rgb)
    regions, labeled, cleaned = clean_and_measure(mask, cm_per_pixel)

    ruler_bool_mask = np.zeros(gray.shape, dtype=bool)
    if ruler["ruler_cm_per_pixel"] is not None:
        coord = ruler["ruler_strip_coord"]
        if ruler["ruler_strip_orientation"] == "vertical":
            ruler_bool_mask[:, coord:coord + RULER_STRIP_WIDTH_PX] = True
        else:
            ruler_bool_mask[coord:coord + RULER_STRIP_WIDTH_PX, :] = True
    orientation = detect_orientation(gray, cleaned, ruler_bool_mask)

    # Primary candidate = largest region that is NOT flagged implausible.
    # Picking blindly by raw area would let a background-merged blob
    # masquerade as "the petal" for a single-petal image; this is a
    # deliberate, documented choice, not automatic.
    ok_areas = [r["area_cm2"] for r in regions if r["area_flag"] == "OK"]
    primary_area = max(ok_areas) if ok_areas else None

    rows = []
    for i, r in enumerate(regions, start=1):
        row = {
            "image_path": str(image_path.relative_to(SCANS_DIR)),
            "method": "otsu_chroma",
            "region_id": i,
            "dpi": dpi,
            "dpi_cm_per_pixel": round(cm_per_pixel, 6),
            **ruler,
            "scale_pct_diff": scale_pct_diff,
            "scale_flag": scale_flag,
            "image_height_px": gray.shape[0],
            "image_width_px": gray.shape[1],
            **orientation,
            "n_regions_in_image": len(regions),
            **{k: v for k, v in r.items() if k != "bbox"},
            "is_primary_candidate": (r["area_flag"] == "OK" and r["area_cm2"] == primary_area),
        }
        rows.append(row)

    save_qc_overlay(rgb, cleaned, image_path, qc_dir, ruler)
    return rows


def save_qc_overlay(rgb: np.ndarray, mask: np.ndarray,
                     image_path: Path, qc_dir: Path, ruler: dict) -> None:
    """Save a NEW annotated PNG for visual QC. Never touches the source file."""
    fig, ax = plt.subplots(figsize=(6, 8))
    ax.imshow(rgb)
    for contour in measure.find_contours(mask.astype(float), 0.5):
        ax.plot(contour[:, 1], contour[:, 0], linewidth=1.5, color="magenta", label="otsu_chroma")

    # Draw the detected ruler strip so the automated tick-spacing detection
    # can be visually audited, not just trusted from a number.
    if ruler["ruler_cm_per_pixel"] is not None:
        h, w = rgb.shape[:2]
        coord = ruler["ruler_strip_coord"]
        if ruler["ruler_strip_orientation"] == "vertical":
            ax.axvspan(coord, coord + RULER_STRIP_WIDTH_PX, color="yellow", alpha=0.25)
        else:
            ax.axhspan(coord, coord + RULER_STRIP_WIDTH_PX, color="yellow", alpha=0.25)
        ax.text(0.02, 0.02,
                f"ruler tick period: {ruler['ruler_tick_period_px']}px "
                f"(conf {ruler['ruler_confidence']}) -> {ruler['ruler_cm_per_pixel']:.5f} cm/px",
                transform=ax.transAxes, fontsize=6, color="black",
                bbox=dict(facecolor="yellow", alpha=0.7, pad=1))
    else:
        ax.text(0.02, 0.02, "ruler NOT detected", transform=ax.transAxes,
                 fontsize=6, color="white", bbox=dict(facecolor="red", alpha=0.7, pad=1))

    ax.set_title(image_path.name, fontsize=8)
    ax.axis("off")
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc="lower right", fontsize=7)

    qc_dir.mkdir(parents=True, exist_ok=True)
    out_path = qc_dir / f"{image_path.stem}_qc.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Paired comparison (identity confirmed as of scripts/06 for 2025-03-26)
# ---------------------------------------------------------------------------

def paired_hand_vs_automated(master_path: Path) -> pd.DataFrame:
    """A genuine plant-by-plant comparison: petal_area_master.csv now has
    both hand_area_cm2 (pre-existing manual ImageJ measurement) and
    area_cm2 (this script's automated measurement) on the SAME row for any
    plant where both exist. Unlike compare_to_hand_measurements below
    (which predates 2025-03-26 identity resolution and is distribution-
    level only), this is a real paired validation.
    """
    master = pd.read_csv(master_path)
    paired = master[master["hand_area_cm2"].notna() & master["area_cm2"].notna()].copy()
    paired["pct_diff_hand_vs_auto"] = round(
        100 * (paired["area_cm2"] - paired["hand_area_cm2"]) / paired["hand_area_cm2"], 1)
    paired["ratio_hand_to_auto"] = round(paired["hand_area_cm2"] / paired["area_cm2"], 2)
    return paired[["date", "population", "plant", "hand_area_cm2", "area_cm2",
                    "area_cm2_otsu_chroma",
                    "pct_diff_hand_vs_auto", "ratio_hand_to_auto"]]


# ---------------------------------------------------------------------------
# Distribution-level comparison (kept as a fallback for any future batch
# where hand measurements exist but per-plant identity is still
# unresolved — not currently the case for 2025-03-26, see
# paired_hand_vs_automated above for the real comparison).
# ---------------------------------------------------------------------------

def compare_to_hand_measurements(results: pd.DataFrame, master_path: Path) -> pd.DataFrame:
    """Distribution-level comparison: do the hand values fall within the
    range the automated methods produce for this batch? Superseded by
    paired_hand_vs_automated() now that 2025-03-26 identity is resolved
    (scripts/06) — kept here only as a fallback pattern for a future batch
    that has hand measurements but unresolved identity.
    """
    master = pd.read_csv(master_path)
    hand = master[(master["date"] == "2025-03-26") & (master["population"] == "Percos")
                  & master["hand_area_cm2"].notna()][["plant", "hand_area_cm2"]]

    auto = results[(results["image_path"].str.startswith("2025_03_26/"))]

    rows = []
    for method in ["otsu_chroma"]:
        m = auto[(auto["method"] == method) & (auto["is_primary_candidate"])]
        rows.append({
            "comparison": f"hand (n={len(hand)}) vs {method} primary-candidate-per-image (n={len(m)})",
            "hand_mean_cm2": round(hand["hand_area_cm2"].mean(), 3),
            "hand_min_cm2": round(hand["hand_area_cm2"].min(), 3),
            "hand_max_cm2": round(hand["hand_area_cm2"].max(), 3),
            "auto_mean_cm2": round(m["area_cm2"].mean(), 3),
            "auto_min_cm2": round(m["area_cm2"].min(), 3),
            "auto_max_cm2": round(m["area_cm2"].max(), 3),
            "hand_mean_within_auto_range": bool(m["area_cm2"].min() <= hand["hand_area_cm2"].mean() <= m["area_cm2"].max()),
        })
    summary = pd.DataFrame(rows)

    # Tentative nearest-value pairing (NOT a confirmed identity match — see caveat above).
    tentative = []
    for method in ["otsu_chroma"]:
        m = auto[(auto["method"] == method) & (auto["is_primary_candidate"])].copy()
        for _, hrow in hand.iterrows():
            m["diff"] = (m["area_cm2"] - hrow["hand_area_cm2"]).abs()
            best = m.loc[m["diff"].idxmin()]
            tentative.append({
                "method": method,
                "hand_plant": int(hrow["plant"]),
                "hand_area_cm2": hrow["hand_area_cm2"],
                "nearest_auto_image": best["image_path"],
                "nearest_auto_area_cm2": best["area_cm2"],
                "pct_diff": round(100 * (best["area_cm2"] - hrow["hand_area_cm2"]) / hrow["hand_area_cm2"], 1),
                "note": "TENTATIVE nearest-value match only — image identity for this batch is not confirmed.",
            })
    tentative_df = pd.DataFrame(tentative)

    return summary, tentative_df


# ---------------------------------------------------------------------------
# Reproducibility metadata sidecar (FAIR: Reusable)
# ---------------------------------------------------------------------------

def write_run_metadata(out_dir: Path, n_images: int) -> None:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        commit = None

    import numpy, skimage, pandas, PIL, matplotlib as mpl
    metadata = {
        "script": "scripts/07_segment_petal_area.py",
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": commit,
        "python_version": sys.version,
        "package_versions": {
            "numpy": numpy.__version__,
            "scikit-image": skimage.__version__,
            "pandas": pandas.__version__,
            "pillow": PIL.__version__,
            "matplotlib": mpl.__version__,
        },
        "parameters": {
            "MIN_PETAL_AREA_CM2": MIN_PETAL_AREA_CM2,
            "CLOSING_RADIUS_PX": CLOSING_RADIUS_PX,
            "HOLE_FILL_MAX_PX": HOLE_FILL_MAX_PX,
            "EXPECTED_DPI": EXPECTED_DPI,
        },
        "n_images_processed": n_images,
        "column_dictionary": COLUMN_DICTIONARY,
    }
    with open(out_dir / "run_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SCANS_DIR = PROJECT_ROOT / "Petal_scans"
OUT_DIR = PROJECT_ROOT / "data" / "processed" / "segmentation"
QC_DIR = OUT_DIR / "qc_overlays"
MASTER_PATH = PROJECT_ROOT / "data" / "processed" / "petal_area_master.csv"

# Two image groups, processed for different purposes:
#
# RESOLVED_IMAGES: every image with a confirmed plant identity already
# recorded in petal_area_master.csv's image_file_used column (filled in by
# scripts/03, 04, 05, 06, from the researcher's visual reading of each
# card). These get their measurements written BACK into
# petal_area_master.csv, keyed on image_file_used, per plant row.
#
# VALIDATION_IMAGES (2025_03_26/): any image in that folder NOT already
# covered by RESOLVED_IMAGES. Originally this was all 15 files (identity
# unresolved, so only a distribution-level hand-measurement check was
# possible). As of scripts/06, 2025-03-26 identity IS resolved, so this
# list is computed as a set difference and should normally be empty —
# kept as a fallback so nothing silently goes unmeasured if identity for
# some file in this folder is ever un-resolved again.
def get_resolved_images(master_path: Path) -> list[Path]:
    master = pd.read_csv(master_path)
    rel_paths = sorted(master["image_file_used"].dropna().unique())
    return [SCANS_DIR / p for p in rel_paths]


def write_back_to_master(results: pd.DataFrame, master_path: Path) -> pd.DataFrame:
    """Fold segmentation results into petal_area_master.csv, keyed on
    image_file_used. Only writes a per-plant area when exactly one plant
    row shares that image (single-petal-per-image case, e.g. 2025-03-28).
    When multiple plant rows share one image (e.g. 2025-07-05, 5 plants
    per scan), NO area is guessed at — the region-to-plant position within
    the image hasn't been resolved yet — instead every detected region's
    area is recorded in notes so a person can finish that assignment later
    without re-running segmentation.
    """
    master = pd.read_csv(master_path)
    today = datetime.now().date().isoformat()

    # area_cm2_hsv_hue and pct_diff_methods are obsolete now that hsv_hue has
    # been retired (single method has nothing to diff against) — drop them
    # rather than leave stale hsv-based values sitting in the file.
    master = master.drop(columns=[c for c in ("area_cm2_hsv_hue", "pct_diff_methods")
                                   if c in master.columns])

    # Text columns that start out entirely blank load as float64 (all-NaN)
    # in pandas; writing a string into them then raises rather than
    # silently upcasting (pandas >= 2.x). Cast to object dtype up front so
    # the assignments below work regardless of which rows already have
    # values.
    for col in ["area_flag", "measured_by", "notes", "date_measured"]:
        if col in master.columns:
            master[col] = master[col].astype(object)

    primary = results[results["is_primary_candidate"]].copy()
    by_image = primary.groupby("image_path")

    # NOTE: must count DISTINCT PLANTS sharing an image, not master rows.
    # Several dates record more than one row per plant (a "petal" row and
    # a "flower" row, or — 2025-05-20 — up to four "petal 2"/"petal
    # 3"/"petal 4" rows), all pointing at the SAME single scanned image.
    # Counting rows instead of distinct (date, population, plant) turned
    # 155 genuinely single-plant images into false "multi-plant" cases
    # (e.g. 2025-05-22 Cojo: 2 rows/plant -> wrongly read as 2 plants
    # sharing an image). This mirrors the same row-vs-plant distinction
    # scripts/02's bucket audit had to correct for earlier.
    plant_keys = master[["date", "population", "plant", "image_file_used"]].drop_duplicates()
    sharing_counts = plant_keys["image_file_used"].value_counts()

    for image_path, group in by_image:
        mask = master["image_file_used"] == image_path
        n_sharing = int(sharing_counts.get(image_path, 0))
        if n_sharing == 0:
            continue  # this image isn't linked to any master row (shouldn't happen, but don't guess)

        # If this image has already been split into per-petal rows downstream
        # (scripts/09 + 11, for the 4-petal buckets), mask matches all of
        # those rows even though n_sharing (distinct PLANTS) is still 1 —
        # don't blanket-overwrite each petal's individually resolved area
        # with one whole-image "primary candidate" value. Leave already-split
        # images alone; re-run 09/11/12 after this script if you want their
        # per-petal values refreshed too.
        if "petal_number" in master.columns and master.loc[mask, "petal_number"].dropna().nunique() > 1:
            continue

        # Same idea for images where several DISTINCT PLANTS share one scan
        # (e.g. 2025-07-05, 5 plants/scan): scripts/10 already assigns each
        # plant its own region by position. If that already happened
        # (area_flag moved off the MULTI_PLANT_IMAGE_NOT_ASSIGNED
        # placeholder), don't reset it back to the placeholder here.
        if n_sharing > 1:
            current_flags = master.loc[mask, "area_flag"].dropna().unique()
            if any(f != "MULTI_PLANT_IMAGE_NOT_ASSIGNED" for f in current_flags):
                continue

        otsu_row = group[group["method"] == "otsu_chroma"]
        area_otsu = float(otsu_row["area_cm2"].iloc[0]) if len(otsu_row) else None

        if n_sharing == 1:
            shape_notes = []
            if len(otsu_row) and otsu_row["shape_flag"].iloc[0] != "OK":
                shape_notes.append(f"otsu_chroma: {otsu_row['shape_flag'].iloc[0]} — check QC overlay")

            master.loc[mask, "area_cm2_otsu_chroma"] = area_otsu
            master.loc[mask, "area_cm2"] = area_otsu
            master.loc[mask, "n_petals_in_image"] = 1
            master.loc[mask, "area_flag"] = "; ".join(shape_notes) if shape_notes else "OK"
            master.loc[mask, "measured_by"] = "automated: otsu_chroma (scripts/07_segment_petal_area.py)"
            master.loc[mask, "date_measured"] = today
        else:
            all_otsu = group[group["method"] == "otsu_chroma"]["area_cm2"].tolist()
            master.loc[mask, "n_petals_in_image"] = n_sharing
            master.loc[mask, "area_flag"] = "MULTI_PLANT_IMAGE_NOT_ASSIGNED"
            master.loc[mask, "measured_by"] = "automated: otsu_chroma (scripts/07_segment_petal_area.py)"
            master.loc[mask, "date_measured"] = today
            existing_notes = master.loc[mask, "notes"].fillna("")
            addendum = (f" [{n_sharing} plants share this scan; per-plant region assignment not yet "
                        f"done. Detected primary regions: otsu_chroma={all_otsu} cm2.]")
            master.loc[mask, "notes"] = existing_notes + addendum

    master.to_csv(master_path, index=False)
    return master


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    resolved_images = get_resolved_images(MASTER_PATH)
    resolved_set = set(resolved_images)
    validation_images = [p for p in sorted((SCANS_DIR / "2025_03_26").glob("*.png"))
                          if p not in resolved_set]
    all_images = [("validation_2025_03_26", p) for p in validation_images] + \
                 [("resolved", p) for p in resolved_images]
    print(f"Processing {len(validation_images)} validation-only images (2025_03_26/, "
          f"identity still unresolved) + {len(resolved_images)} identity-resolved images ...")

    all_rows = []
    for batch, path in all_images:
        print(f" - [{batch}] {path.relative_to(SCANS_DIR)}")
        rows = measure_image(path, QC_DIR)
        for r in rows:
            r["batch"] = batch
        all_rows.extend(rows)

    results = pd.DataFrame(all_rows)
    results_path = OUT_DIR / "petal_area_segmentation_results.csv"
    results.to_csv(results_path, index=False)
    print(f"\nWrote {len(results)} region rows to {results_path}")

    resolved_results = results[results["batch"] == "resolved"]
    updated_master = write_back_to_master(resolved_results, MASTER_PATH)
    n_written = updated_master["area_cm2"].notna().sum()
    n_multi_flagged = (updated_master["area_flag"] == "MULTI_PLANT_IMAGE_NOT_ASSIGNED").sum()
    print(f"\nWrote area_cm2 for {n_written} plant rows in petal_area_master.csv "
          f"({n_multi_flagged} rows flagged MULTI_PLANT_IMAGE_NOT_ASSIGNED, not guessed).")

    per_image_scale = results.drop_duplicates("image_path")[
        ["image_path", "dpi", "dpi_cm_per_pixel", "ruler_cm_per_pixel",
         "ruler_confidence", "scale_pct_diff", "scale_flag"]
    ]
    scale_summary_path = OUT_DIR / "ruler_vs_dpi_scale_check.csv"
    per_image_scale.to_csv(scale_summary_path, index=False)
    n_detected = per_image_scale["ruler_cm_per_pixel"].notna().sum()
    print(f"\n=== Ruler vs. DPI scale cross-check ({n_detected}/{len(per_image_scale)} rulers detected) ===")
    print(per_image_scale.to_string(index=False))
    print(f"Wrote {scale_summary_path}")

    paired = paired_hand_vs_automated(MASTER_PATH)
    paired_path = OUT_DIR / "hand_vs_automated_paired.csv"
    paired.to_csv(paired_path, index=False)
    print(f"\n=== Hand vs. automated: PAIRED comparison (identity confirmed, n={len(paired)}) ===")
    print(paired.to_string(index=False))
    print(f"Wrote {paired_path}")

    summary, tentative = compare_to_hand_measurements(results, MASTER_PATH)
    summary_path = OUT_DIR / "hand_vs_automated_comparison.csv"
    tentative_path = OUT_DIR / "hand_vs_automated_tentative_pairing.csv"
    summary.to_csv(summary_path, index=False)
    tentative.to_csv(tentative_path, index=False)

    print("\n=== Hand vs. automated (distribution-level fallback view; superseded by the paired comparison above) ===")
    print(summary.to_string(index=False))
    print(f"\nWrote comparison to {summary_path}")
    print(f"Wrote tentative nearest-value pairing (NOT a confirmed match) to {tentative_path}")

    write_run_metadata(OUT_DIR, len(all_images))
    print(f"\nQC overlays: {QC_DIR}/ ({len(all_images)} images)")
    print("Run metadata: ", OUT_DIR / "run_metadata.json")


if __name__ == "__main__":
    main()
