# 05_apply_0705_resolution.R
#
# Resolves the 2025-07-05 Cojo/Perry "shortfall": it wasn't missing data.
# The researcher confirmed each scan holds one petal from each of 5 plants,
# with plant numbers written on a card in the same image (verified directly
# by reading all 6 images):
#   *_0001.png -> plants 1-5
#   *_0002.png -> plants 6-10
#   *_0003.png -> plants 11-15
# for both Cojo and Perry. 3 images x 5 plants = 15, matching the expected
# count exactly for both populations.
#
# Only touches data/processed/ outputs. Does not modify raw inputs.

suppressPackageStartupMessages({
  library(tidyverse)
})

root    <- here::here()
out_dir <- file.path(root, "data", "processed")

master <- read_csv(file.path(out_dir, "petal_area_master.csv"), show_col_types = FALSE, na = c("", "NA"))

image_for_plant <- function(plant) {
  case_when(
    plant %in% 1:5   ~ "0001.png",
    plant %in% 6:10  ~ "0002.png",
    plant %in% 11:15 ~ "0003.png",
    TRUE ~ NA_character_
  )
}

master <- master %>%
  mutate(
    image_file_used = case_when(
      date == as.Date("2025-07-05") & population == "Cojo"  ~ paste0("2025_07_05/Cojo_5_jul_25_", image_for_plant(plant)),
      date == as.Date("2025-07-05") & population == "Perry" ~ paste0("2025_07_05/Perry_5_jul_25_", image_for_plant(plant)),
      TRUE ~ image_file_used
    ),
    match_flag = if_else(date == as.Date("2025-07-05") & population %in% c("Cojo", "Perry"),
                          "IMAGE_ASSIGNED_FROM_VISUAL_CHECK", match_flag),
    area_flag = if_else(date == as.Date("2025-07-05") & population %in% c("Cojo", "Perry"),
                         "SHARED_IMAGE_MULTI_PLANT", area_flag),
    notes = if_else(date == as.Date("2025-07-05") & population %in% c("Cojo", "Perry"),
                     "Not a missing-scan gap: one petal from each of 5 plants is scanned together, with plant numbers on a card in the same image. This image is shared by 5 plant rows — read the numbered card in the image to match each petal blob to this specific plant before recording area.",
                     notes)
  )

write_csv(master, file.path(out_dir, "petal_area_master.csv"))

message("2025-07-05 Cojo/Perry: ", sum(master$date == as.Date("2025-07-05") & !is.na(master$image_file_used) &
                                          master$population %in% c("Cojo","Perry")), " of 30 rows assigned (shared images).")
