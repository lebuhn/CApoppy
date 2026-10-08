# 04_apply_resolutions.R
#
# Applies the researcher's answers to the open questions raised after
# 03_apply_visual_checks.R (see chat/notes dated 2026-09-14):
#   1. 2025-03-28 Pt. Conception plant 1: two images exist (IMG_...0016.png,
#      IMG_...0017.png) — both valid; 0017 is a retake, used as the primary
#      image, 0016 kept on record as the original.
#   2. 2025-03-28 Pt. Conception plant 15: IMG_...0031.png confirmed.
#   3. 2025-05-23 "percos_..." images: population confirmed as Percos (the
#      card insert visible in the scans was simply wrong; not Pt. Conception,
#      not Perry). Label conflict flag cleared.
#   4. 2025-07-05 Cojo & Perry shortfall: researcher is checking for the
#      missing scans elsewhere. No change — stays flagged.
#   5. ptcon_20250523_0008.png: confirmed only 2 petals present because the
#      other petals were damaged and deliberately not scanned. Recorded as
#      an image-level note so it isn't later mistaken for a segmentation
#      error.
#
# Only touches data/processed/ outputs. Does not modify raw inputs.

suppressPackageStartupMessages({
  library(tidyverse)
})

root    <- here::here()
out_dir <- file.path(root, "data", "processed")

master <- read_csv(file.path(out_dir, "petal_area_master.csv"), show_col_types = FALSE, na = c("", "NA"))

# ---------------------------------------------------------------------------
# 1 & 2. 2025-03-28 Pt. Conception, plants 1 and 15
# ---------------------------------------------------------------------------

master <- master %>%
  mutate(
    image_file_used = case_when(
      date == as.Date("2025-03-28") & population == "Pt. Conception" & plant == 1 ~
        "2025_03_28/IMG_20250328_0017.png",
      date == as.Date("2025-03-28") & population == "Pt. Conception" & plant == 15 ~
        "2025_03_28/IMG_20250328_0031.png",
      TRUE ~ image_file_used
    ),
    match_flag = case_when(
      date == as.Date("2025-03-28") & population == "Pt. Conception" & plant %in% c(1, 15) ~
        "IMAGE_ASSIGNED_FROM_VISUAL_CHECK",
      TRUE ~ match_flag
    ),
    notes = case_when(
      date == as.Date("2025-03-28") & population == "Pt. Conception" & plant == 1 ~
        "Two scans exist for this plant (IMG_20250328_0016.png, IMG_20250328_0017.png); both confirmed valid, 0017 is a retake and used as the primary image here. 0016 kept on record — see petal_scan_image_notes.csv.",
      date == as.Date("2025-03-28") & population == "Pt. Conception" & plant == 15 ~
        "Population was illegible on the card; plant number 15 was readable and confirmed by researcher as Pt. Conception.",
      TRUE ~ notes
    )
  )

# ---------------------------------------------------------------------------
# 3. 2025-05-23 Percos: label conflict resolved, population confirmed.
# ---------------------------------------------------------------------------

master <- master %>%
  mutate(
    area_flag = if_else(date == as.Date("2025-05-23") & population == "Percos" &
                           area_flag == "POPULATION_LABEL_CONFLICT_UNCONFIRMED",
                         NA_character_, area_flag),
    notes = if_else(date == as.Date("2025-05-23") & population == "Percos" &
                       str_detect(coalesce(notes, ""), "POPULATION_LABEL_CONFLICT|Population unconfirmed|do not assign a population"),
                     "Card insert in these scans incorrectly read 'Pt. Conception'; population confirmed as Percos by researcher (resolves earlier label conflict).",
                     notes)
  )

# (4. 2025-07-05 Cojo/Perry: no change — researcher is checking, stays flagged.)

write_csv(master, file.path(out_dir, "petal_area_master.csv"))

# ---------------------------------------------------------------------------
# 5. Image-level notes: facts that belong to a specific scan file rather than
#    a specific plant row (retakes, originals, known partial scans). Kept
#    separate from petal_area_master.csv because master is one-row-per-plant
#    and these don't all resolve to a known plant yet.
# ---------------------------------------------------------------------------

image_notes <- tribble(
  ~image_path, ~note,
  "2025_03_28/IMG_20250328_0016.png", "Original scan of Pt. Conception plant 1; superseded by retake IMG_20250328_0017.png (both confirmed valid; retake used as primary image_file_used).",
  "2025_03_28/IMG_20250328_0017.png", "Retake of Pt. Conception plant 1 (original: IMG_20250328_0016.png). Used as primary image_file_used for plant 1.",
  "ptcon_20250523_0008.png", "Only 2 petals present in this scan (confirmed by researcher) — the other petals on this flower were damaged and deliberately not scanned. A petal count of 2 here reflects the sample, not a segmentation or matching error."
)

write_csv(image_notes, file.path(out_dir, "petal_scan_image_notes.csv"))

message("petal_area_master.csv updated; petal_scan_image_notes.csv written.")
message("2025-03-28 Pt. Conception plants 1 and 15: assigned.")
message("2025-05-23 Percos: label conflict cleared, population confirmed.")
message("2025-07-05 Cojo/Perry: left flagged, unchanged, per researcher (checking elsewhere).")
message("ptcon_20250523_0008.png: recorded in petal_scan_image_notes.csv.")
