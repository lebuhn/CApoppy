# 06_apply_plant_id_batch2.R
#
# Applies the completed plant-ID checklist
# (data/processed/petal_scan_visual_check_list_plant_id.csv) to
# petal_area_master.csv for the 9 buckets that were still unresolved after
# scripts/03-05 (2025-03-26, 04-17, 05-20, 05-22, 05-23 x2, 07-02 x2,
# 09-13). Researcher-confirmed 2026-09-14:
#   - Cards showing 4 petals together label PETAL POSITION (1-4) within
#     that one flower, not plant identity — those numbers are NOT used
#     here for identity (they were already excluded from
#     plant_number_observed by the researcher).
#   - For every bucket in this checklist, plant number matches the file's
#     own sequence number, confirmed directly by the researcher (not
#     inferred from file order by this script).
#
# Sanity-checked before applying (see chat, 2026-09-14): no rows where
# plant_number_observed differs from the file's sequence number, no
# duplicate (date, population, plant) claims. 2025-05-23 Percos is
# genuinely short one image (plant 15) — left unresolved, not guessed.
#
# Only touches data/processed/ outputs. Does not modify raw inputs or the
# checklist file itself.

suppressPackageStartupMessages({
  library(tidyverse)
})

root    <- here::here()
out_dir <- file.path(root, "data", "processed")

checked <- read_csv(file.path(out_dir, "petal_scan_visual_check_list_plant_id.csv"),
                     show_col_types = FALSE, na = c("", "NA")) %>%
  mutate(date = as.Date(date, format = "%m/%d/%y"))

master <- read_csv(file.path(out_dir, "petal_area_master.csv"),
                    show_col_types = FALSE, na = c("", "NA"))

claims <- checked %>%
  transmute(date, population, plant = as.integer(plant_number_observed), image_path)

master <- master %>%
  left_join(claims, by = c("date", "population", "plant")) %>%
  mutate(
    image_file_used = coalesce(image_file_used, image_path),
    match_flag = if_else(!is.na(image_path) & is.na(match_flag),
                          "IMAGE_ASSIGNED_FROM_VISUAL_CHECK", match_flag)
  ) %>%
  select(-image_path)

write_csv(master, file.path(out_dir, "petal_area_master.csv"))

n_now_assigned <- sum(!is.na(master$image_file_used))
still_unresolved <- master %>% filter(is.na(image_file_used)) %>% count(date, population)

message(n_now_assigned, " of ", nrow(master), " master rows now have image_file_used.")
message("\nStill unresolved:")
print(still_unresolved, n = Inf)
