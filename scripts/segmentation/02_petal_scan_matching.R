# 02_petal_scan_matching.R
#
# Purpose: build the accounting layer between the existing petal weight/ID
# spreadsheet (data/raw/plant/petal_weight_3.xlsx) and the raw scan images
# (Petal_scans/), BEFORE any image segmentation is written. This script does
# not measure petal area itself — it produces a derived table with empty
# columns ready for a segmentation script to fill in, plus an audit of where
# images and spreadsheet rows do/don't line up.
#
# READ-ONLY on inputs: data/raw/plant/petal_weight_3.xlsx and everything
# under Petal_scans/ are only ever read here, never written to. All outputs
# go to data/processed/.
#
# Grain: date + population identify a *collection day for one population*
# ("a bucket"). Plant number is recorded in the spreadsheet, but nothing in
# the scan filenames or folder names encodes which image belongs to which
# plant — that information only exists as handwriting on each scan. So this
# script matches at the bucket level (how many images exist vs. how many
# plants are expected for that date+population) and leaves plant-level
# image assignment for a human (or a later OCR/transcription pass) rather
# than guessing from file order.

suppressPackageStartupMessages({
  library(tidyverse)
  library(readxl)
})

root      <- here::here()
xlsx_path <- file.path(root, "data", "raw", "plant", "petal_weight_3.xlsx")
scans_dir <- file.path(root, "Petal_scans")
out_dir   <- file.path(root, "data", "processed")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

# ---------------------------------------------------------------------------
# 1. Read the spreadsheet (read-only) and export a clean CSV key table.
#    Do not treat this CSV as the new master datasheet — the xlsx remains
#    the live file for weighing entry. This is a derived, read-only mirror.
# ---------------------------------------------------------------------------

raw <- read_excel(xlsx_path, sheet = "Petal_2025_low", col_types = "text")

# The date column is mixed-type in the source file: row 1 is literal text
# ("2025-03-26"), every other row is a genuine Excel date serial read back
# as a numeric string (e.g. "45744"). Handle both without guessing.
parse_mixed_date <- function(x) {
  is_iso <- str_detect(x, "^\\d{4}-\\d{2}-\\d{2}$")
  out <- as.Date(rep(NA_character_, length(x)))
  out[is_iso]  <- as.Date(x[is_iso])
  out[!is_iso] <- as.Date(suppressWarnings(as.numeric(x[!is_iso])), origin = "1899-12-30")
  out
}

# A few cells in the source sheet hold a researcher's text note instead of
# a number (e.g. "note: only 1 other petal" in the `length` column for
# 2025-05-23 / Pt. Conception / plant 8). Coercing straight to numeric would
# silently turn that into NA and lose the note — capture it instead.
length_numeric <- suppressWarnings(as.numeric(raw$length))
length_note <- if_else(!is.na(raw$length) & is.na(length_numeric), raw$length, NA_character_)

key <- raw %>%
  transmute(
    date          = parse_mixed_date(date),
    block         = as.integer(Block),
    population    = population,
    plant         = as.integer(plant),
    wet_wgt_g     = as.numeric(wet_wgt),
    petal_flower  = petal_flower,
    length_mm     = length_numeric,
    source_note   = length_note,
    hand_area_cm2 = as.numeric(area),   # pre-existing hand ImageJ measurements (n = 5)
    dry_wgt_g     = as.numeric(dry_wgt),
    water_mg      = as.numeric(water_mg),
    water_pct     = as.numeric(`water_%`)
  ) %>%
  filter(!is.na(date) | !is.na(population) | !is.na(plant))  # drop fully-blank trailing rows

write_csv(key, file.path(out_dir, "petal_weight_3_key.csv"))

stopifnot(all(!is.na(key$date)))  # fail loudly rather than silently mis-parsing a date

# ---------------------------------------------------------------------------
# 2. Inventory every raw scan image (read-only walk of Petal_scans/).
# ---------------------------------------------------------------------------

img_paths <- list.files(scans_dir, recursive = TRUE, full.names = TRUE,
                         pattern = "\\.(png|jpe?g|tiff?)$", ignore.case = TRUE)

inv <- tibble(path = img_paths) %>%
  mutate(
    rel_path = str_remove(path, fixed(paste0(scans_dir, "/"))),
    folder   = basename(dirname(path)),
    fname    = basename(path)
  ) %>%
  mutate(
    # Prior manual-processing artifacts (thresholded masks, old results CSVs
    # already saved as images) — not raw scans, excluded from matching.
    likely_artifact = str_detect(fname, regex("binary", ignore_case = TRUE)),

    # "petal_failure" photos document a single failing petal (confirmed by
    # visual check: 1 petal per image, not the usual 4) — a different kind
    # of record from the standard area-measurement card, so they're excluded
    # from bucket counts rather than inflating a population's image count.
    likely_documentation_photo = str_detect(fname, regex("petal_failure", ignore_case = TRUE)),

    exclude_from_matching = likely_artifact | likely_documentation_photo,

    folder_date = if_else(str_detect(folder, "^\\d{4}_\\d{2}_\\d{2}$"),
                           as.Date(folder, format = "%Y_%m_%d"), as.Date(NA))
  )

# Two filename date spellings are used across batches: "YYYYMMDD" (e.g.
# IMG_20250328_0001.png) and "D_mon_YY" (e.g. Pt_Con_13_sep_25_0001.png).
# The latter turns out to matter: for the 2025_09_15 folder, the filename
# date (13_sep_25) disagrees with the folder name (2025_09_15) — see the
# audit output. Filename dates are trusted over folder dates because
# they're per-file, researcher-written at scan time.
mon_lookup <- c(jan = 1, feb = 2, mar = 3, apr = 4, may = 5, jun = 6,
                 jul = 7, aug = 8, sep = 9, oct = 10, nov = 11, dec = 12)

dmy_match <- str_match(inv$fname, regex("(\\d{1,2})_([a-z]{3})_(\\d{2})(?:_|\\.)", ignore_case = TRUE))
dmy_month_num <- unname(mon_lookup[tolower(dmy_match[, 3])])
fname_date_dmy <- as.Date(ifelse(
  !is.na(dmy_match[, 1]) & !is.na(dmy_month_num),
  sprintf("20%s-%02d-%02d", dmy_match[, 4], dmy_month_num, as.integer(dmy_match[, 2])),
  NA
))

inv <- inv %>%
  mutate(
    fname_date_token = str_extract(fname, "\\d{8}"),
    fname_date_ymd = if_else(!is.na(fname_date_token),
                              as.Date(fname_date_token, format = "%Y%m%d"), as.Date(NA)),
    fname_date_dmy = fname_date_dmy,
    best_date = coalesce(fname_date_ymd, fname_date_dmy, folder_date),

    pop_token = case_when(
      str_detect(fname, regex("percos", ignore_case = TRUE))        ~ "Percos",
      str_detect(fname, regex("cojo",   ignore_case = TRUE))        ~ "Cojo",
      str_detect(fname, regex("pt_?con|ptcon", ignore_case = TRUE)) ~ "Pt. Conception",
      str_detect(fname, regex("perry",  ignore_case = TRUE))        ~ "Perry",
      TRUE ~ NA_character_
    )
  )

# Where filename doesn't carry a population, but the date maps to exactly
# ONE population in the spreadsheet, it's safe to infer it (e.g. 2025-03-26
# is Percos-only). Where a date has 2+ populations and the filename is
# silent (e.g. 2025-03-28: Perry + Pt. Conception, plain IMG_####.png
# names), population is left unresolved rather than guessed.
date_single_pop <- key %>%
  distinct(date, population) %>%
  add_count(date, name = "n_pop_that_date") %>%
  filter(n_pop_that_date == 1) %>%
  select(date, inferred_population = population)

inv <- inv %>%
  left_join(date_single_pop, by = c("best_date" = "date")) %>%
  mutate(
    population_resolved = coalesce(pop_token, inferred_population),
    population_source = case_when(
      !is.na(pop_token)                       ~ "filename",
      is.na(pop_token) & !is.na(inferred_population) ~ "inferred_single_population_date",
      TRUE                                     ~ "unresolved"
    )
  ) %>%
  select(-inferred_population)

write_csv(inv %>% select(-path), file.path(out_dir, "petal_scan_image_inventory.csv"))

# ---------------------------------------------------------------------------
# 3. Bucket-level audit: date x population, images found vs. plants expected.
# ---------------------------------------------------------------------------

# NOTE: expected count must be DISTINCT PLANTS, not raw xlsx row count.
# The source sheet records more than one row per plant on several dates —
# e.g. a separate "petal" + "flower" weight row, or (2025-05-20 Perry)
# individual "petal 2"/"petal 3"/"petal 4" rows for some plants. Counting
# rows made several buckets look like a "~2 petals per scan" pattern that
# wasn't real; counting distinct plants is the correct comparison against
# one-scan-per-plant image counts (confirmed against the visual check: each
# scan shows 4 petals from one flower — California poppies have 4 petals
# per flower — not 4 different plants).
xlsx_bucket <- key %>%
  distinct(date, population, plant) %>%
  count(date, population, name = "n_plants_expected")

img_bucket <- inv %>%
  filter(!exclude_from_matching) %>%
  count(best_date, population_resolved, name = "n_images_found") %>%
  rename(date = best_date, population = population_resolved)

dates_in_xlsx <- unique(xlsx_bucket$date)
dates_with_unassigned_images <- img_bucket %>%
  filter(is.na(population), n_images_found > 0) %>%
  pull(date)

bucket_audit <- full_join(xlsx_bucket, img_bucket, by = c("date", "population")) %>%
  mutate(
    n_plants_expected = replace_na(n_plants_expected, 0L),
    n_images_found    = replace_na(n_images_found, 0L),
    image_to_plant_ratio = if_else(n_plants_expected > 0,
                                    n_images_found / n_plants_expected, NA_real_),
    date_in_xlsx = date %in% dates_in_xlsx,
    status = case_when(
      !date_in_xlsx & n_images_found > 0            ~ "OUT_OF_SCOPE_NO_XLSX_ROWS",
      is.na(population) & date_in_xlsx               ~ "POPULATION_UNRESOLVED_FROM_FILENAME",
      n_images_found == 0 & date %in% dates_with_unassigned_images ~
        "IMAGES_EXIST_BUT_POPULATION_UNASSIGNED",
      n_images_found == 0                            ~ "NO_IMAGES_FOUND",
      abs(image_to_plant_ratio - 1)   < 0.1          ~ "COUNT_OK_ONE_IMAGE_PER_PLANT",
      abs(image_to_plant_ratio - 0.5) < 0.1          ~ "HYPOTHESIS_TWO_PETALS_PER_SCAN",
      TRUE                                            ~ "COUNT_MISMATCH_NEEDS_REVIEW"
    )
  ) %>%
  select(-date_in_xlsx) %>%
  arrange(date, population)

write_csv(bucket_audit, file.path(out_dir, "petal_scan_match_audit.csv"))

# Candidate image folder(s) per bucket, so a person/segmentation script knows
# where to look even when plant-level assignment isn't resolved yet.
bucket_dirs <- inv %>%
  filter(!exclude_from_matching) %>%
  distinct(best_date, population_resolved, folder) %>%
  group_by(date = best_date, population = population_resolved) %>%
  summarise(candidate_image_folder = paste(sort(unique(folder)), collapse = "; "),
            .groups = "drop")

# Fallback for population-unresolved buckets: still point at the shared
# per-date folder even though which file is which population isn't known yet.
date_dirs <- inv %>%
  filter(!exclude_from_matching) %>%
  distinct(best_date, folder) %>%
  group_by(date = best_date) %>%
  summarise(date_folder = paste(sort(unique(folder)), collapse = "; "), .groups = "drop")

# ---------------------------------------------------------------------------
# 4. Main derived output: one row per petal (spreadsheet grain), with empty
#    columns ready for a segmentation script to fill in.
# ---------------------------------------------------------------------------

master <- key %>%
  left_join(bucket_audit %>% select(date, population, n_plants_expected,
                                     n_images_found, image_to_plant_ratio, status),
            by = c("date", "population")) %>%
  left_join(bucket_dirs, by = c("date", "population")) %>%
  left_join(date_dirs, by = "date") %>%
  mutate(
    candidate_image_folder = coalesce(candidate_image_folder, date_folder),
    match_flag = status,

    # --- columns for segmentation code / manual QC to fill in downstream ---
    image_file_used        = NA_character_,
    n_petals_in_image      = NA_integer_,
    area_cm2               = NA_real_,
    area_cm2_manual_check  = NA_real_,
    pct_diff_methods       = NA_real_,
    area_flag              = NA_character_,   # e.g. LOW_CONFIDENCE, BAG_GLARE, EDGE_BLUR
    measured_by            = NA_character_,
    date_measured          = as.Date(NA),
    notes                  = source_note   # preserves any researcher text note from the source sheet
  ) %>%
  select(-date_folder, -source_note) %>%
  arrange(date, population, plant)

write_csv(master, file.path(out_dir, "petal_area_master.csv"))

# ---------------------------------------------------------------------------
# 5. Images that don't belong to any matched, in-scope bucket — kept as a
#    separate list rather than silently dropped.
# ---------------------------------------------------------------------------

out_of_scope <- inv %>%
  left_join(bucket_audit %>% select(date, population, status),
            by = c("best_date" = "date", "population_resolved" = "population")) %>%
  filter(likely_artifact | likely_documentation_photo | is.na(status) | status == "OUT_OF_SCOPE_NO_XLSX_ROWS") %>%
  mutate(
    reason = case_when(
      likely_artifact ~ "prior manual-processing artifact (binary mask / old results), not a raw scan",
      likely_documentation_photo ~ "petal-failure documentation photo (1 petal, before/after) — not a standard area-measurement card",
      is.na(status) | status == "OUT_OF_SCOPE_NO_XLSX_ROWS" ~
        "no spreadsheet rows for this date — likely a different sub-experiment (e.g. shrinkage, water-loss, petal-failure time series)",
      TRUE ~ NA_character_
    )
  ) %>%
  select(rel_path, folder, fname, best_date, pop_token, reason)

write_csv(out_of_scope, file.path(out_dir, "petal_scan_images_out_of_scope.csv"))

# ---------------------------------------------------------------------------
# 6. Visual-check worklist: every image where a human needs to look and
#    record something matching-by-filename can't resolve. Two categories:
#      - POPULATION_AND_PLANT_ID: 2025-03-28 images carry no population in
#        the filename, so both population and plant number must be read off
#        the handwritten card in the photo.
#      - PETAL_COUNT: images in the three buckets whose image:plant ratio
#        looks like ~2 petals per scan (a hypothesis, not yet confirmed) —
#        needs someone to open each scan and count the petals actually
#        present.
#    This file is the answer sheet: fill in the blank columns in place and
#    save it. Nothing here is written back into it automatically.
# ---------------------------------------------------------------------------

pop_unresolved_dates <- bucket_audit %>%
  filter(status == "POPULATION_UNRESOLVED_FROM_FILENAME") %>%
  pull(date)

multi_petal_buckets <- bucket_audit %>%
  filter(status == "HYPOTHESIS_TWO_PETALS_PER_SCAN") %>%
  select(date, population)

check_pop_id <- inv %>%
  filter(best_date %in% pop_unresolved_dates, is.na(population_resolved), !exclude_from_matching) %>%
  transmute(
    category = "POPULATION_AND_PLANT_ID",
    image_path = rel_path,
    question = "Read the handwritten label/card in this scan. Which population (Perry or Pt. Conception) and which plant number does it show?",
    population_observed = NA_character_,
    plant_number_observed = NA_integer_,
    n_petals_observed = NA_integer_,
    legible = NA_character_,      # Y / N
    notes = NA_character_
  )

check_petal_count <- inv %>%
  filter(!exclude_from_matching) %>%
  semi_join(multi_petal_buckets, by = c("best_date" = "date", "population_resolved" = "population")) %>%
  transmute(
    category = "PETAL_COUNT",
    image_path = rel_path,
    question = "Open this scan and count the distinct petals visible. How many are there?",
    population_observed = NA_character_,
    plant_number_observed = NA_integer_,
    n_petals_observed = NA_integer_,
    legible = NA_character_,
    notes = NA_character_
  )

check_list <- bind_rows(check_pop_id, check_petal_count) %>%
  arrange(category, image_path) %>%
  mutate(check_id = row_number(), .before = 1)

write_csv(check_list, file.path(out_dir, "petal_scan_visual_check_list.csv"))

# ---------------------------------------------------------------------------
# Console summary
# ---------------------------------------------------------------------------
cat("\n== petal_weight_3_key.csv ==\n")
cat(nrow(key), "petal rows,", sum(!is.na(key$hand_area_cm2)), "already have a hand-measured area.\n")

cat("\n== bucket audit (date x population) ==\n")
print(bucket_audit %>% count(status), n = Inf)

cat("\n== images excluded from matching ==\n")
print(out_of_scope %>% count(reason), n = Inf)

cat("\nOutputs written to", out_dir, "\n")
cat(" - petal_weight_3_key.csv           (read-only mirror of the xlsx sheet)\n")
cat(" - petal_scan_image_inventory.csv   (every raw image + parsed date/population)\n")
cat(" - petal_scan_match_audit.csv       (date x population match status)\n")
cat(" - petal_area_master.csv            (one row per petal, ready for segmentation output)\n")
cat(" - petal_scan_images_out_of_scope.csv (images that don't belong to a matched bucket)\n")
cat(" - petal_scan_visual_check_list.csv (", nrow(check_list), "images needing a human look, with blank answer columns)\n")
