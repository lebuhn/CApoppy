# R/project_setup.R
# Standard project initialization for CApoppy analyses

suppressPackageStartupMessages({
  library(here)
  library(tidyverse)
  library(lubridate)
  library(readr)
})

# ---- Project paths ----
paths <- list(
  root       = here(),
  
  data_raw   = here("data", "raw"),
  data_proc  = here("data", "processed"),
  
  references = here("references"),
  petal_scans= here("Petal_scans"),
  
  # Recommended unified outputs (create if missing)
  outputs    = here("outputs"),
  out_fig    = here("outputs", "figures"),
  out_tab    = here("outputs", "tables"),
  out_rep    = here("outputs", "reports"),
  
  # Legacy folders you currently have (kept for compatibility)
  legacy_fig = here("figures"),
  legacy_plot= here("plots"),
  docs       = here("docs")
)

# Create recommended output dirs (won't warn if already exist)
invisible(lapply(c(paths$outputs, paths$out_fig, paths$out_tab, paths$out_rep),
                 dir.create, recursive = TRUE, showWarnings = FALSE))

# ---- Global options ----
options(
  stringsAsFactors = FALSE,
  dplyr.summarise.inform = FALSE,
  readr.show_col_types = FALSE
)

# Print numbers nicely (optional)
options(scipen = 999)

# ---- Plot defaults ----
# Keep it simple and consistent across scripts
theme_set(theme_classic(base_size = 14))

# ---- Small helpers ----

#' Save a ggplot with consistent defaults (PNG 300 dpi)
save_fig <- function(plot, filename, width = 7, height = 5, dpi = 300,
                     dir = paths$out_fig, ...) {
  stopifnot(inherits(plot, "ggplot"))
  dir.create(dir, recursive = TRUE, showWarnings = FALSE)
  ggsave(
    filename = file.path(dir, filename),
    plot = plot,
    width = width, height = height, dpi = dpi, ...
  )
  invisible(file.path(dir, filename))
}

#' Save a data.frame/tibble as CSV to outputs/tables
save_table_csv <- function(x, filename, dir = paths$out_tab, ...) {
  dir.create(dir, recursive = TRUE, showWarnings = FALSE)
  readr::write_csv(x, file.path(dir, filename), ...)
  invisible(file.path(dir, filename))
}

#' Save an R object as RDS to outputs/tables (great for models)
save_rds <- function(x, filename, dir = paths$out_tab, ...) {
  dir.create(dir, recursive = TRUE, showWarnings = FALSE)
  saveRDS(x, file.path(dir, filename), ...)
  invisible(file.path(dir, filename))
}

#' Quick check: verify expected columns exist
require_cols <- function(df, cols) {
  missing <- setdiff(cols, names(df))
  if (length(missing) > 0) {
    stop("Missing required columns: ", paste(missing, collapse = ", "), call. = FALSE)
  }
  invisible(TRUE)
}

# Helpful message in console/logs
message("CApoppy setup loaded. Outputs -> ", paths$outputs)
