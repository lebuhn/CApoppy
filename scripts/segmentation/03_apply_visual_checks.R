# 03_apply_visual_checks.R
#
# Folds the researcher's completed visual-check answers
# (data/processed/petal_scan_visual_check_list_COMPLETED_*.csv) into
# petal_area_master.csv. Only applies an answer where the identification is
# unambiguous; anything with a conflict is left blank in image_file_used and
# recorded in area_flag / notes instead, for a person to resolve — nothing
# here is guessed silently.
#
# Reads inputs only; does not touch the completed checklist itself.
# Run 02_petal_scan_matching.R first (it must be the corrected version that
# expects DISTINCT PLANTS, not xlsx rows).

suppressPackageStartupMessages({
  library(tidyverse)
})

root    <- here::here()
out_dir <- file.path(root, "data", "processed")

completed_path <- sort(list.files(out_dir, pattern = "^petal_scan_visual_check_list_COMPLETED_.*\\.csv$",
                                   full.names = TRUE), decreasing = TRUE)[1]
stopifnot("No completed checklist file found in data/processed/" = !is.na(completed_path))
message("Using completed checklist: ", basename(completed_path))

checked <- read_csv(completed_path, show_col_types = FALSE, na = c("", "NA"))
master  <- read_csv(file.path(out_dir, "petal_area_master.csv"), show_col_types = FALSE, na = c("", "NA"))

# ---------------------------------------------------------------------------
# 1. POPULATION_AND_PLANT_ID answers (2025-03-28) -> assign image_file_used
# ---------------------------------------------------------------------------

pop_id <- checked %>%
  filter(category == "POPULATION_AND_PLANT_ID") %>%
  mutate(date = as.Date("2025-03-28"))

# Flag duplicates: more than one image claimed for the same (date, population, plant).
dupes <- pop_id %>%
  filter(!is.na(population_observed), !is.na(plant_number_observed)) %>%
  add_count(date, population_observed, plant_number_observed, name = "n_claims") %>%
  filter(n_claims > 1)

if (nrow(dupes) > 0) {
  message("\nDUPLICATE image claims for the same plant (not auto-assigned):")
  dupes %>% select(image_path, population_observed, plant_number_observed) %>% print(n = Inf)
}

unresolved_pop <- pop_id %>% filter(is.na(population_observed))
if (nrow(unresolved_pop) > 0) {
  message("\nImages where population itself was not read (left unassigned):")
  unresolved_pop %>% select(image_path, plant_number_observed, notes) %>% print(n = Inf)
}

# Only apply a claim when: population + plant number both present, AND it's
# not part of a duplicate pair. Duplicates and population-illegible rows are
# deliberately left out of the assignment and reported above instead.
clean_claims <- pop_id %>%
  filter(!is.na(population_observed), !is.na(plant_number_observed)) %>%
  anti_join(dupes, by = c("date", "population_observed", "plant_number_observed")) %>%
  transmute(
    date, population = population_observed, plant = as.integer(plant_number_observed),
    image_file_used = image_path
  )

master <- master %>%
  left_join(clean_claims, by = c("date", "population", "plant"), suffix = c("", "_new")) %>%
  mutate(
    image_file_used = coalesce(image_file_used_new, image_file_used),
    match_flag = if_else(!is.na(image_file_used_new), "IMAGE_ASSIGNED_FROM_VISUAL_CHECK", match_flag)
  ) %>%
  select(-image_file_used_new)

# ---------------------------------------------------------------------------
# 2. PETAL_COUNT answers -> confirms 4 petals/scan (1 flower = 4 petals for
#    Eschscholzia californica), not a plant-level assignment. Recorded as a
#    note on the relevant buckets rather than per-plant, since we still don't
#    know which image belongs to which specific plant in those buckets.
# ---------------------------------------------------------------------------

petal_count <- checked %>% filter(category == "PETAL_COUNT")

petal_count_summary <- petal_count %>%
  mutate(bucket = case_when(
    str_detect(image_path, "cojo") ~ "2025-05-22 Cojo",
    str_detect(image_path, "percos") ~ "2025-05-23 Percos",
    str_detect(image_path, "ptcon") ~ "2025-05-23 Pt. Conception",
    TRUE ~ "other"
  )) %>%
  group_by(bucket) %>%
  summarise(n_images = n(),
            petal_counts = paste(sort(unique(n_petals_observed)), collapse = ","),
            .groups = "drop")

message("\nPetal-count check summary (4 = one flower's full petal set, expected):")
print(petal_count_summary, n = Inf)

outliers <- petal_count %>% filter(n_petals_observed != 4)
if (nrow(outliers) > 0) {
  message("\nImages with a petal count other than 4 (worth a second look):")
  outliers %>% select(image_path, n_petals_observed, notes) %>% print(n = Inf)
}

# Flag the 2025-05-23 Percos bucket with the label conflict a checker noted:
# filename says "percos", the card insert in the image reads "Pt. Conception",
# and the checker's note says "Perry is correct". Three different answers —
# do not resolve this automatically. There are also zero Perry rows recorded
# in the spreadsheet for 2025-05-23 at all, so "Perry" can't even be applied
# without first figuring out where those rows would come from.
label_conflict_note <- unique(petal_count$notes[str_detect(coalesce(petal_count$notes, ""), "Perry")])

master <- master %>%
  mutate(
    area_flag = if_else(date == as.Date("2025-05-23") & population == "Percos" & is.na(area_flag),
                         "POPULATION_LABEL_CONFLICT_UNCONFIRMED", area_flag),
    notes = if_else(date == as.Date("2025-05-23") & population == "Percos" & is.na(notes),
                     paste0("Filename says Percos; card insert in the scans reads 'Pt. Conception'; ",
                            "visual checker's note says 'Perry is correct' (no Perry rows exist for ",
                            "2025-05-23 in the source sheet at all). Population unconfirmed — do not ",
                            "assign a population to this bucket until resolved."),
                     notes)
  )

# ---------------------------------------------------------------------------
# 3. Real, unresolved count shortfall (2025-07-05 Cojo & Perry: 3 of 15
#    images each) survives the distinct-plant-count fix, so it's a genuine
#    gap, not a counting artifact. Leave a note on those rows.
# ---------------------------------------------------------------------------

master <- master %>%
  mutate(
    notes = if_else(date == as.Date("2025-07-05") & population %in% c("Cojo", "Perry") & is.na(notes),
                     "Only 3 of 15 expected scans found for this date/population; filesystem timestamps show a complete, real scanning session of just 3 petals — likely genuinely unscanned or filed elsewhere, not a matching error.",
                     notes)
  )

write_csv(master, file.path(out_dir, "petal_area_master.csv"))

message("\npetal_area_master.csv updated.")
message(sum(!is.na(master$image_file_used)), " rows now have image_file_used assigned.")
message(sum(master$match_flag == "IMAGE_ASSIGNED_FROM_VISUAL_CHECK", na.rm = TRUE), " rows newly assigned from this pass.")
