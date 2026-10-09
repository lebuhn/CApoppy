# 08_weight_area_correlation.R
#
# Purpose: test the relationship between petal wet weight (wet_wgt_g,
# measured on a balance) and petal area (area_cm2, from automated image
# segmentation in scripts/segmentation/07_segment_petal_area.py) using
# data/processed/petal_area_master.csv.
#
# Scope note: only plant rows with an UNAMBIGUOUS single-petal-per-image
# measurement are used. Rows flagged MULTI_PLANT_IMAGE_NOT_ASSIGNED (e.g.
# 2025-07-05, where 5 plants share one scan and per-plant region
# assignment hasn't been resolved yet) are excluded rather than guessed —
# see area_flag. As more images are identity-resolved and measured
# (scripts/segmentation/07), re-running this script will pick up more rows
# automatically; no changes needed here.
#
# READ-ONLY on petal_area_master.csv. Writes only to data/processed/ and
# outputs/figures/ (per project_initialization.R conventions).

source(here::here("scripts", "project_initialization.R"))

petals <- read_csv(file.path(paths$data_proc, "petal_area_master.csv"),
                    na = c("", "NA"))

# ---- Build the analysis set ----
# petal_flower == "petal" rows carry the petal weight used for this
# comparison (some dates also record a separate "flower"-row weight,
# which is not a petal measurement and is excluded here).
analysis_set <- petals %>%
  filter(petal_flower == "petal",
         !is.na(area_cm2),
         !is.na(wet_wgt_g),
         area_flag != "MULTI_PLANT_IMAGE_NOT_ASSIGNED" | is.na(area_flag))

n_excluded_multiplant <- petals %>%
  filter(petal_flower == "petal", !is.na(wet_wgt_g),
         area_flag == "MULTI_PLANT_IMAGE_NOT_ASSIGNED") %>%
  nrow()

cat("Analysis set:", nrow(analysis_set), "petals with both area_cm2 and wet_wgt_g.\n")
cat("Excluded (multi-plant scan, area not yet assigned to a specific plant):",
    n_excluded_multiplant, "\n")

if (nrow(analysis_set) < 4) {
  stop("Fewer than 4 petals have both area and weight measured — not enough to ",
       "test a correlation yet. Run scripts/segmentation/07_segment_petal_area.py on more ",
       "identity-resolved images first.")
}

# ---- Correlation ----
# Both Pearson (linear relationship, assumes ~normal residuals) and
# Spearman (monotonic relationship, robust to outliers/non-normality) are
# reported since n is still small and the shape of this relationship
# hasn't been established yet.
pearson  <- cor.test(analysis_set$area_cm2, analysis_set$wet_wgt_g, method = "pearson")
spearman <- cor.test(analysis_set$area_cm2, analysis_set$wet_wgt_g, method = "spearman")

correlation_summary <- tibble(
  n = nrow(analysis_set),
  pearson_r = round(unname(pearson$estimate), 3),
  pearson_ci_low = round(pearson$conf.int[1], 3),
  pearson_ci_high = round(pearson$conf.int[2], 3),
  pearson_p = signif(pearson$p.value, 3),
  spearman_rho = round(unname(spearman$estimate), 3),
  spearman_p = signif(spearman$p.value, 3)
)

print(correlation_summary)
save_table_csv(correlation_summary, "petal_weight_area_correlation_summary.csv")
save_table_csv(analysis_set, "petal_weight_area_analysis_set.csv")

# ---- Plot ----
# format.pval() prints tiny p-values as a long decimal string (e.g. a
# p ~ 1e-15 becomes "0.0000000000000036"), which overflows a plot
# subtitle. Use scientific notation below 0.001, as is standard.
fmt_p <- function(p) if (p < 0.001) sprintf("%.2e", p) else sprintf("%.3f", p)

p <- ggplot(analysis_set, aes(x = area_cm2, y = wet_wgt_g, color = population)) +
  geom_point(size = 2, alpha = 0.85) +
  geom_smooth(method = "lm", se = TRUE, color = "black", linewidth = 0.6) +
  labs(
    x = expression("Petal area (cm"^2*")"),
    y = "Petal wet weight (g)",
    color = "Population",
    title = "Petal wet weight vs. automated petal area",
    subtitle = sprintf("n = %d | Pearson r = %.2f (95%% CI %.2f-%.2f, p = %s)\nSpearman rho = %.2f (p = %s)",
                        correlation_summary$n, correlation_summary$pearson_r,
                        correlation_summary$pearson_ci_low, correlation_summary$pearson_ci_high,
                        fmt_p(correlation_summary$pearson_p),
                        correlation_summary$spearman_rho,
                        fmt_p(correlation_summary$spearman_p))
  )

save_fig(p, "petal_weight_area_correlation.png", width = 7, height = 5.5)

cat("\nOutputs:\n")
cat(" -", file.path(paths$out_tab, "petal_weight_area_correlation_summary.csv"), "\n")
cat(" -", file.path(paths$out_tab, "petal_weight_area_analysis_set.csv"), "\n")
cat(" -", file.path(paths$out_fig, "petal_weight_area_correlation.png"), "\n")
