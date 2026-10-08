# CApoppy Repository Audit Report
**Read-only audit — no files modified, moved, renamed, deleted, staged, committed, or rendered.**
Audited location: `~/GitHub/CApoppy` (confirmed as the git repository root)
Date of audit: 2026-09-11

---

## 1. Executive summary

**What CApoppy is (Confirmed).** This is Gretchen LeBuhn's active field-ecology research repository studying petal ecophysiology of California poppy (*Eschscholzia californica*) at the Dangermond Preserve, plus several older, separate strands of work (2022 SFSU campus petal-weight data; a Schoen & Ashman floral-longevity simulation; a "Differential Water Loss" manuscript with Kevin Simonin and student co-authors on nyctinasty/water loss). The core 2025 study (documented explicitly in `project_decisions_log.qmd`) measures petal water-content traits (RWC, DMC, water-per-dry-mass) across four populations (Pt. Conception, Percos, Perry, Cojo) in three seasonal blocks, and relates them to microclimate (temperature/RH loggers + Apogee PAR sensors) with the aim of publishing in *Oecologia* or *Oikos*.

**Organization (Confirmed).** The repository is only partly organized. `scripts/00_INDEX.qmd` and `scripts/01_PATH_FIXES.qmd` are self-aware meta-documents (evidently written by a prior AI-assisted session) that already diagnose most of the path/portability problems found independently in this audit — a good sign that the problems are known, a less good sign that they have not yet been fixed. There is no `R/`-based helper-function library in use yet (the folder exists but is empty), no package/version pinning (no `renv`, `DESCRIPTION`, or `_quarto.yml`), and several near-duplicate analysis scripts coexist without a clear "retire the old one" step.

**Can the workflow be reconstructed? (Strongly indicated / likely, with real gaps.)** Yes, in broad strokes: the decision log, `00_INDEX.qmd`, and the code itself agree on what each script is for. But several *specific* input files that current scripts try to read do not exist anywhere in the repository under the referenced name/path — most importantly `data/raw/plant/petal_weight.csv`, which is read by 6 different scripts (including one edited as recently as 2026-02-19) but was deliberately deleted from the repo on 2025-12-07 in favor of `petal_weight_2025.csv`. This is not a hypothetical risk — it is a currently-broken reference in scripts that appear to still be in active use.

**Is the necessary data present locally? (Mostly yes, with one important exception.)** Nearly all raw data referenced by current scripts exists somewhere on disk under `data/raw/`, though often at a different path than the code expects (case differences, wrong subfolder, or old filename). The one substantive local gap is the Pt. Conception RH/temp sensor failure for Block 3, which is a field data-collection gap, not a repository problem — it is explicitly documented in `project_decisions_log.qmd` as the single "CRITICAL" open item blocking final analysis.

**Is the necessary data present in GitHub? (No — this is the central reproducibility problem.)** The `data/raw/Apogee_PAR/` directory (PAR/light data for all four sites — one of the three microclimate variable classes central to the study's stated hypothesis) is present locally but is excluded by `.gitignore` and has **never been committed to git**. Anyone cloning from GitHub gets zero PAR data. Likewise, `Petal_scans/` (405 MB of raw petal images) and everything in `outputs/` and `docs/*.qmd`/`*.html` are gitignored and absent from a clean clone. The repository is reproducible-in-part from GitHub (trait data + RH/temp microclimate data are tracked) but not reproducible for the full microclimate analysis as currently coded.

**Most important problems found, in order of impact:**
1. **PAR microclimate data (`data/raw/Apogee_PAR/`) is git-ignored and untracked** — a clean GitHub clone cannot run any of the light/PAR analysis. *(Critical)*
2. **`petal_weight.csv` is referenced by 6 scripts but was deleted from the repo in Dec 2025**; the replacement (`petal_weight_2025.csv`) exists but not every script was updated to use it — including a script touched as recently as Feb 2026. *(Critical for those specific scripts)*
3. **Several scripts read files at the wrong relative path** (e.g., `opening_camera_2025.csv` expected in `data/raw/plant/` but actually lives in `data/raw/camera/`; `Flower_traits.xlsx` expected in `data/raw/plant/` but lives in `data/raw/porometer/`; `fl_shrinkage2.csv` expected directly under `data/raw/` but lives in `data/raw/plant/`). *(Important)*
4. **Hard-coded absolute paths tied to this specific Mac and user** appear in several older/legacy scripts (`~/GitHub/CApoppy/...`, `~/Dropbox/CApoppy/...`, one commented-out Box path, one commented-out Google Sheets URL). These will not work for any other user or machine, or even this user if the repo is cloned to a different folder. *(Important)*
5. **No package/version management** — no `renv`, no `DESCRIPTION`, no recorded R version. Package availability, not just code, is a reproducibility risk. *(Important, esp. before publication/archiving)*
6. **Five or more analysis scripts implement near-identical petal-trait pipelines** (`petal_microclimate_analysis.qmd`, `petal_microclimate_analysis_2.qmd`, `petal_physiology.qmd`, `archive/petal_ecophysiology_analysis.qmd`, `01_petal_xy_plots.qmd`) with git history showing a real, reconstructable lineage — but no single canonical "run this one" script is marked as such outside of `00_INDEX.qmd`'s informal "master candidates" list. *(Documentation gap, not fatal)*
7. **One hard-coded/manually-entered result** was found: `petal_physiology.qmd` recomputes an ICC table from data, then a later chunk silently re-defines the *same-named* `icc_table` object from typed-in numeric literals to make a bar chart — meaning that chart will not update if the underlying data changes. *(Potential scientific issue — flagged in §16)*

---

## 2. Repository map

```
CApoppy/
├── data/
│   ├── raw/                      Source data, mixed provenance (see §5)
│   │   ├── plant/                 Petal weight, shrinkage, plant-trait CSV/XLSX (2025 field season)
│   │   ├── rh_temp/                RH/temperature logger downloads per site, incl. a
│   │   │                           "downloads now combined" subfolder of raw per-download exports
│   │   ├── Apogee_PAR/             PAR/light logger CSVs — LOCAL ONLY, gitignored (see §6)
│   │   ├── fl_temp/                2022-era CR6/thermocouple logger data (older study)
│   │   ├── porometer/              LI-COR/porometer instrument exports (zips, xlsx, csv), one
│   │   │                           metadata workbook; messy nested folder-per-session structure
│   │   ├── camera/                 Flower-opening timelapse-camera-derived CSV/XLSX
│   │   └── (loose files)           2022 weight/water-content CSVs, 2024 student petal CSVs,
│   │                               flower_failure.xlsx, fl_shrinkage2.xlsx
│   └── processed/                 Only one file present: porometer_4pops.csv (tracked in git).
│                                  A nested .gitignore names 5 more processed files that are
│                                  expected but not present anywhere (see §6 Missing data).
├── Petal_scans/                  405 MB of raw petal photo scans (png/tif) + a couple of
│                                  ImageJ-derived CSVs. Entirely gitignored — never in git.
├── scripts/                      All analysis code (.qmd/.Rmd/.R) — see §4 for full inventory.
│   ├── archive/                   2 scripts explicitly moved here by the researcher (superseded)
│   ├── analysis/, manuscripts/    Empty placeholder directories (no content yet)
│   └── 00_INDEX.qmd, 01_PATH_FIXES.qmd   Self-authored meta-documentation of the codebase
├── R/                             Empty. `00_dummy_example.qmd` expects `R/project_setup.R`
│                                  here; the file exists instead, uncommitted, as
│                                  `scripts/project_initialization.R` (see §12/§15).
├── docs/                         Manuscript drafts (.qmd), rendered HTML/PDF, and Word/PDF
│                                  reference documents. Mixed git status — some old files are
│                                  tracked, current .qmd drafts and renders are gitignored.
├── outputs/                      figures/, plots/, tables/, reports/ — the new, recommended
│                                  output location. Only figures/ and plots/ have contents (3
│                                  PNGs, moved here from old root-level figures//plots/ folders
│                                  in commit ec49d82). tables/ and reports/ are empty.
├── references/                   references.bib support: one PDF reference (Roddy lab paper).
├── project_decisions_log.qmd     Rich, dated decision log for the 2025 microclimate study —
│                                  the single best provenance document in the repo (see §8/§13).
├── README.md                     Two lines: "# CApoppy" / "CA-poppy". No project description.
├── LICENSE                       CC0 1.0 Universal (public domain dedication).
└── .gitignore / nested .gitignore files   See §2a below.
```

### 2a. `.gitignore` findings and reproducibility implications

Root `.gitignore` (Confirmed, read directly) excludes, among standard R/RStudio housekeeping:
- `Petal_scans/` — all raw petal images (405 MB), never in git.
- `data/raw/Apogee_PAR` — **all PAR/light sensor data**, never in git. This is the most consequential exclusion in the repository (see §6/§15).
- `outputs/`, `*.html`, `*_files/`, `*.pdf` — all rendered analysis output. This is a defensible choice (outputs are regenerable) *provided* the inputs and code to regenerate them are otherwise complete — which, per finding above, they currently are not for the PAR-dependent analyses.
- `docs/` — as a bare directory pattern, this excludes the whole `docs/` tree from future commits. However, several files under `docs/` **are** tracked in git already (see below) — they were committed before this rule was added (confirmed via `git log -p .gitignore`, which shows `docs/` added in a later commit than some of these files' first appearance) and remain tracked because gitignore does not retroactively untrack committed files.
- `.positai` — added in the currently unstaged `.gitignore` modification (see §13).

Nested `.gitignore` files add finer-grained exclusions and are themselves informative "wish lists" of expected-but-currently-uncommitted processed files:
- `data/raw/.gitignore` → excludes `opening_camera_2025.xlsx` (its sibling `.csv` is tracked).
- `data/raw/Apogee_PAR/.gitignore` → contains only `~/GitHub/CApoppy/data/raw/` (an oddly-scoped absolute-path pattern that does not correspond to anything in that directory; likely a stray/leftover rule).
- `data/raw/fl_temp/.gitignore` → excludes 4 specific 2022-era duplicate-looking files (files with trailing " 2" in the name, i.e., macOS duplicate-file artifacts).
- `data/processed/.gitignore` → excludes `porometer_4pops.xlsx`, `PAR_data.csv`, `climate_allsites.csv`, `Combined_3pops_march.csv`, `Combined_3pops_march.xlsx` — **none of these five files exist anywhere in the repository.** This is strong, direct evidence that a processed-data layer the researcher expected to produce/keep was either never generated, or was generated and then deleted/never saved to disk. `research_plan.qmd` explicitly reads `Combined_3pops_march.csv` (see §5, §16).
- `scripts/.gitignore` → excludes `01_PATH_FIXES.qmd`, even though that exact file is already tracked in git (added before the rule). Future edits to it will not be captured by git unless force-added — worth asking the researcher if that's intentional (see §17 Q7).

**Local vs. GitHub reproducibility, stated plainly:** `git status --ignored` combined with `git status --porcelain --untracked-files=all` shows that on this machine, *every* file that exists locally is either tracked or explicitly gitignored — there are no stray untracked-and-not-ignored files. That means the gitignore rules are being applied deliberately and consistently; the gap is not accidental untracked cruft, it's a real, chosen split between "what's on this Mac" and "what's on GitHub."

---

## 3. Main scientific workflows

### Workflow A — Microgeographic petal ecophysiology & microclimate (core 2025 study; Confirmed via `project_decisions_log.qmd` + code)
**Purpose:** Test whether microclimate (VPD, temperature, PAR/fog) explains population-level variation in petal tissue-economics traits (RWC, DMC, water-per-dry-mass, fresh/dry weight) across 4 populations × 3 seasonal blocks at Dangermond Preserve.
**Primary scripts:** `petal_microclimate_analysis_2.qmd` (most complete: full-season + common-period microclimate PCA, Procrustes comparison, 4-day-window trait–climate mixed models), `petal_physiology.qmd` (condensed variant with ICC/variance-partitioning framing and narrative interpretation), `petal_microclimate_analysis.qmd` (heavily trimmed Feb-2026 version), `01_petal_xy_plots.qmd` (newest, narrowly-scoped exploratory XY-plot script, deliberately excludes the microclimate merge per the decision log).
**Main inputs:** `data/raw/plant/petal_weight_2025.csv` (current) or the missing `petal_weight.csv` (stale reference in several scripts); `data/raw/rh_temp/*_rhtemp_2025.csv` (4 sites); `data/raw/Apogee_PAR/*_PAR_2025.csv` (4 sites, **not in git**).
**Major outputs:** trait–microclimate correlation/regression tables, ICC variance-partitioning tables, PCA ordinations of microclimate, mixed-effects model summaries — all currently only as in-document (rendered PDF/HTML) tables/figures; none are written to `outputs/tables` or `outputs/figures` yet by these scripts.

### Workflow B — Sensor QA/QC and substitution (Confirmed)
**Purpose:** Determine whether new "TNC" RH/temperature sensors can substitute for the Pt. Conception and Cojo sensors during gaps (directly serves the Workflow A Block-3 data-quality problem).
**Scripts:** `sensor_comparison_analysis.qmd`, `rh_sensor_comparison.qmd`.
**Inputs:** old/new sensor RH-temp CSVs under `data/raw/rh_temp/` (all present and git-tracked).
**Outputs:** comparison time series, Bland–Altman-style bias plots, in-document only.

### Workflow C — Stomatal conductance (gsw) by population (Confirmed)
**Script:** `Gsw_comparison_bypop.qmd`. **Input:** `data/processed/porometer_4pops.csv` (present, tracked; read via a hard-coded absolute path). **Output:** in-document comparison plots/statistics.

### Workflow D — Flowering phenology / camera timing (Confirmed)
**Script:** `plant_flowering_analysis.qmd`. **Input:** intended to be `data/raw/camera/opening_camera_2025.csv` but coded as `data/raw/plant/opening_camera_2025.csv` (wrong subfolder — currently broken). **Output:** in-document timing/duration plots and tests.

### Workflow E — Flower shrinkage / water loss dynamics (Confirmed)
**Script:** `Shrinkage2.qmd`. **Input:** coded as `data/raw/fl_shrinkage2.csv`; actual file is `data/raw/plant/fl_shrinkage2.csv` (also `.xlsx` copies exist in two locations — see §14). **Output:** in-document shrinkage plots.

### Workflow F — Plant/flower trait integration (Confirmed, but broken)
**Scripts:** `petal_trait_analysis.qmd` (merges petal weight + plant traits + porometer), `plant_trait_analysis.qmd` (traits typed directly into the script as a `data.frame()` literal — not read from any file), `flower_trait_analysis.qmd` (Excel-based, exploratory). Multiple broken/mismatched file references (see §5).

### Workflow G — Theory/simulation, no field data (Confirmed)
**Script:** `Schoen and Ashman.qmd` — a from-scratch implementation of Schoen & Ashman floral-longevity optimization models (pure math/simulation, self-contained R functions, no external data). Unrelated to the field data workflows; likely feeds theoretical framing for a manuscript rather than being part of the empirical pipeline.

### Workflow H — Older / legacy 2022 prototypes (Confirmed via dates, git history, hard-coded paths)
**Scripts:** `CApoppy.wgt.Rmd` (2022, SFSU campus, dated title "2022-07-01", hard-codes a Box-Box cloud path via `setwd()`), `Petal_water_content.qmd` (references a commented-out Google Sheets URL and a Box path, then a hard-coded `~/GitHub/...` path), `Time_series.Rmd`, `Time_series_CR6_fltime.Rmd`, `Temp_time_series_CR6_ovary.Rmd` (all read CR6/thermocouple logger files via `~/Dropbox/CApoppy/...` absolute paths or bare filenames assuming a specific working directory). These predate the Dangermond study and use a different, no-longer-current file organization (Box/Dropbox, not this git repo).

### Workflow I — Differential water loss / nyctinasty manuscript (Confirmed via git history + text diff)
**Scripts/docs:** `scripts/archive/Differential_water_loss_paper.qmd` (the original, git-tracked stats+figures script — computes Dunn's tests, ovary/petal temperature plots, saves `dunn_test_results*.png` and `flower_ovary_temperatures.png`), plus two **never-committed** manuscript-prose drafts `docs/Differential_water_loss_paper.qmd` and `docs/Differential_water_loss_paper_2.qmd` (Abstract/Introduction/Methods narrative, minimal code, authored with a full student co-author byline list — this is Kevin Simonin's separate manuscript project, not the Dangermond microclimate study).

---

## 4. Script inventory

Evidence codes: **G**=git history, **C**=code content read directly, **D**=00_INDEX.qmd/decision log, **P**=file-path/existence check.

| Script | Purpose | Inputs (as coded) | Outputs | Depends on / sources | Likely status | Evidence & confidence |
|---|---|---|---|---|---|---|
| `scripts/01_petal_xy_plots.qmd` | Exploratory XY trait-relationship plots by population/block (RWC vs DMC, size scaling, seasonal trajectories, Percos outlier diagnostics) | `data/raw/plant/petal_weight_2025.csv` (exists) | In-document PDF plots + one sample-size table | none | **Current/core** | G: newest file in repo (2026-03-30). C: read directly, fully self-documented with inline "Decision:" comments. D: decision log explicitly describes its creation and rationale. High confidence. |
| `scripts/petal_microclimate_analysis_2.qmd` | Full manuscript-scale microclimate + petal-trait analysis: full-season & common-period microclimate summaries, PCA + Procrustes robustness check, 4-day-window trait–climate mixed models, petal-trait PCA | `../data/raw/plant/petal_weight.csv` (**MISSING**), `../data/raw/rh_temp/*.csv` (exist), `../data/raw/Apogee_PAR/*.csv` (exist locally, not in git) | In-document tables/figures only | none | **Likely current for the microclimate-modeling side, but currently broken** (missing input) | C: read headers/labels directly (1624 lines, most complete pipeline). G: created 2025-12-07, never touched since. P: input file confirmed absent. High confidence on structure; broken-input finding is Confirmed. |
| `scripts/petal_physiology.qmd` | Condensed version of the microclimate+trait pipeline with ICC (variance-partitioning) framing and written interpretation of results | `../data/raw/plant/petal_weight_2025.csv` (exists), same rh_temp/PAR inputs | In-document tables/figures; one bar chart built from **hand-typed** ICC values, not the ICC table computed earlier in the same document | none | **Likely current / most recently narratively developed** | C: read in full. G: last touched 2026-01-17 (more recent than `_analysis.qmd` and `_analysis_2.qmd`). D: decision log names this "the more recent version" of the 3 old scripts it summarizes. Confirmed re: hard-coded ICC values (see §16). |
| `scripts/petal_microclimate_analysis.qmd` | Same pipeline as above, heavily trimmed | `../data/raw/plant/petal_weight.csv` (**MISSING**) | In-document tables/figures | none | **Likely superseded / stale** | C: read in full — near-identical code to `petal_physiology.qmd` but references the missing file. G: last edited 2026-02-19 (commit `ec49d82` cut it from 1740→508 lines) yet the broken path was not fixed. Confirmed broken; superseded status is "likely" (no direct statement, but functionally duplicated by the other two). |
| `scripts/archive/petal_ecophysiology_analysis.qmd` | Full manuscript-style write-up (abstract/intro/methods/results prose) of the same petal-trait study, framed around coastal/inland comparison rather than continuous microclimate | `../data/raw/plant/petal_weight_2025.csv` (exists) | In-document | none | **Explicitly archived / superseded** | C: read header/methods. G: file lives under `scripts/archive/`, last touched 2026-01-17, i.e. archived *after* still being edited alongside the current scripts — the researcher moved it deliberately. Confirmed superseded by researcher's own filing action. |
| `scripts/archive/Differential_water_loss_paper.qmd` | Nyctinasty/differential water-loss statistics: ovary/petal temperature time series, Dunn's tests on adaxial/abaxial water loss | `~/GitHub/CApoppy/data/raw/fl_temp/cr6_Temp.28.May.22.csv` etc. (absolute path; case-mismatched vs. actual `CR6_Temp.28.may.22.csv`), `Petal_water.csv` (bare, no path — **not found**) | `~/GitHub/CApoppy/figures/dunn_test_results.png`, `dunn_test_results_mg.png`, `~/GitHub/CApoppy/plots/flower_ovary_temperatures.png` (paths since git-mv'd to `outputs/figures`, `outputs/plots` in commit `ec49d82`) | none | **Superseded / archived (by researcher's own move to `archive/`)**, separate manuscript track from the Dangermond study | G: full commit history from 2022 (`e801528`) through archiving; confirmed by `git log --follow`. C: absolute paths and stale filenames confirmed by direct read. High confidence. |
| `docs/Differential_water_loss_paper.qmd` | Manuscript prose (Abstract/Intro/Methods) for the same nyctinasty paper — narrative only, minimal/no code | none (prose document) | none | none | **Standalone manuscript draft, never version-controlled** | C: read directly — almost entirely prose. G: `git log --follow` returns **no history** — confirms this file has never been tracked in git (lives under gitignored `docs/`). High confidence. |
| `docs/Differential_water_loss_paper_2.qmd` | A second, textually different draft of the same manuscript (different author byline list, different phrasing throughout intro) | none | none | none | **Alternate/parallel draft, never version-controlled, relationship to `_1` unresolved** | C: diffed against the `_1` draft — substantially different prose, not a strict superset. G: no git history (gitignored). See §17 Q2 — cannot determine which is "the" current draft from repository evidence alone. |
| `scripts/rh_sensor_comparison.qmd` | Compares 3 RH sensors at Pt. Conception (old vs. 2 TNC sensors), tests aggregation methods | `data/raw/rh_temp/Pt_Con_rhtemp_2025.csv`, `Cojo_Pt_Con_rhtemp_2025_tncsensor.csv`, `pt-conception-alternate.csv` (all exist) | In-document plots | none | **Helper / data-preparation (feeds the sensor-substitution decision in Workflow A)** | C read directly; D confirmed by 00_INDEX Theme E. High confidence. |
| `scripts/sensor_comparison_analysis.qmd` | Broader old-vs-new sensor comparison at Pt. Conception and Cojo | `data/raw/rh_temp/Cojo_rhtemp_2025.csv`, `Pt_Con_rhtemp_2025.csv`, `Cojo_Pt_Con_rhtemp_2025_tncsensor.csv` (exist) | In-document plots | none | **Helper / data-preparation** | Same as above. High confidence. |
| `scripts/Gsw_comparison_bypop.qmd` | Compares stomatal conductance (gsw) among populations/leaf surfaces, with a hand-written Cojo/CojoHQ ID-merging rule | `~/GitHub/CApoppy/data/processed/porometer_4pops.csv` (absolute path; file exists) | In-document plots/stats | none | **Likely current, but not portable** | C read directly. Absolute path confirmed; also independently flagged in `01_PATH_FIXES.qmd`. High confidence. |
| `scripts/petal_trait_analysis.qmd` | Merges petal weight + plant traits + porometer data for combined trait analysis | `data/raw/plant/petal_weight.csv` (**MISSING**), `data/raw/plant/plant_traits.csv` (**MISSING** — actual file is `plant_traits_march25.csv`), `data/processed/porometer_4pops.csv` (exists) | In-document merged-dataset summaries | none | **Currently broken; status otherwise uncertain** | C read directly (2/3 inputs absent under the coded names). Confirmed broken. |
| `scripts/plant_trait_analysis.qmd` | Compares plant morphological traits (leaves/flowers/buds/fruits) among 3 populations on one sampling date | **None — data typed directly into the script** as a `data.frame()` literal | In-document ANOVA/post-hoc plots | none | **Standalone / data hand-entered, not reproducible from raw files** | C: confirmed no `read_*` call anywhere in file; a `data.frame(...)` literal at line 53 is the only data source. D matches 00_INDEX's own description ("traits entered directly in the file"). High confidence. |
| `scripts/flower_traits_fixed_block.qmd` | Draft manuscript template for the petal-trait/population study | `../data/raw/plant/petal_weight.csv` (**MISSING**) | In-document | none | **Template/incomplete draft** | C read directly — contains literal placeholder text `[results to be filled in based on your findings]` and `author: "Your Name"`. Confirmed unfinished template, not a completed analysis. |
| `scripts/flower_trait_analysis.qmd` | Exploratory analysis of an Excel flower-traits workbook plus one porometer export | `../data/raw/plant/Flower_traits.xlsx` (**wrong path** — actual file is `data/raw/porometer/Flower_traits.xlsx`), one specific porometer xlsx (exists) | In-document | none | **Exploratory, currently broken on one input** | C read directly (grep of read calls). Confirmed path mismatch. |
| `scripts/plant_flowering_analysis.qmd` | Flowering timing/duration analysis from camera data, 3 populations | `../data/raw/plant/opening_camera_2025.csv` (**wrong path** — actual file is `data/raw/camera/opening_camera_2025.csv`) | In-document plots/tests | none | **Likely current in intent, currently broken on path** | C read directly. Confirmed path mismatch (folder renamed to `camera/` at some point without updating this script). |
| `scripts/Shrinkage2.qmd` | Flower shrinkage (area/weight over time) analysis | `../data/raw/fl_shrinkage2.csv` (**wrong path** — actual file is `data/raw/plant/fl_shrinkage2.csv`) | In-document plots | none | **Likely current in intent, currently broken on path** | C read directly. Confirmed path mismatch. |
| `scripts/research_plan.qmd` | 3-week analysis roadmap document (hypotheses, required datasets, planned model structure, planned `ggsave()` figure outputs) | `data/processed/Combined_3pops_march.csv` (**MISSING, not found anywhere**), `data/raw/plant/plant_traits.csv` (**MISSING**), `data/processed/porometer_4pops.csv` (exists), `data/raw/plant/petal_weight.csv` (**MISSING**), `data/raw/fl_shrinkage2.csv` (wrong path) | Planned: `figures/Fig1_environment_WUE.pdf`, `Fig2_trait_syndrome.pdf`, `Fig3_mixed_model.pdf` (none currently exist) | none | **Planning document, not an executed analysis** | C read directly; also references future external data acquisition from PRISM/WorldClim (not yet obtained). This is a roadmap, evidence suggests it was never fully executed end-to-end as written. |
| `scripts/review_dataset.qmd` | Generic dataset-review utility (variable counts/types) | Uses a Quarto `params: data_file` mechanism but the actual code hard-codes `data/raw/plant/petal_weight.csv` (**MISSING**) instead of using the parameter | In-document summary | none | **Utility/QA, currently broken and internally inconsistent (param defined but unused)** | C read directly. Confirmed. |
| `scripts/00_dummy_example.qmd` | Worked template demonstrating the recommended `here()`-based project setup, `save_fig`/`save_table_csv`/`save_rds` helpers | Simulated data only (no real file read) | `outputs/figures/dummy_petal_area_vs_gsw.png`, `outputs/tables/dummy_summary_table.csv`, `outputs/tables/dummy_linear_model.rds` (none currently exist — never rendered) | `source(here::here("R","project_setup.R"))` — **this file does not exist** | **Template only, currently non-functional** | C read in full. Confirmed the sourced file is absent (see `scripts/project_initialization.R` finding, §12). |
| `scripts/project_initialization.R` | Draft of the standard project-setup script (paths, `save_fig`/`save_table_csv`/`save_rds` helpers, output-dir creation) — its own header comment says `# R/project_setup.R` | none (defines infrastructure, not an analysis) | Creates `outputs/{figures,tables,reports}` directories when sourced | none | **New / not yet integrated** — currently sits in `scripts/` but is written to be at `R/project_setup.R` | C read in full. G: currently *staged but uncommitted* (`git status` shows "new file"). Confirmed mismatch between intended location (per its own header comment and per `00_dummy_example.qmd`'s `source()` call) and actual location. |
| `scripts/00_INDEX.qmd` | Human-readable index of all analysis themes, master scripts, inputs, and outputs | none | Rendered HTML index (gitignored) | none | **Documentation, current** | C read in full. Confirms much of this audit's independent findings — a strong corroborating source. |
| `scripts/01_PATH_FIXES.qmd` | Self-diagnosed list of absolute-path problems and suggested fixes | none | Rendered HTML (gitignored) | none | **Documentation, current, not yet acted on** | C read in full. Directly corroborates §6 findings below; none of its suggested fixes have been applied yet (all flagged absolute paths are still present in the live scripts). |
| `project_decisions_log.qmd` (repo root) | Dated decision log/analysis tracker for the 2025 microclimate study: research questions, data-quality issues, model-building decisions, outstanding tasks | none | Rendered HTML/PDF (gitignored) | none | **Documentation, current, primary provenance source** | C read in full. Single richest evidence source in the repository; used throughout this report. |
| `scripts/Schoen and Ashman.qmd` | From-scratch implementation of Schoen & Ashman floral-longevity optimization models | none (parameter grids / simulation only) | In-document contour/isocline plots | none | **Standalone theory work, current** | C read header + confirmed self-contained functions, no data dependency. |
| `scripts/CApoppy.wgt.Rmd` | 2022 SFSU-campus petal weight/water-content analysis (different study system than Dangermond) | `CApoppy.weight.csv` via `setwd("/Users/gretchen/Library/CloudStorage/Box-Box/...")` (**not found under this name in the repo**; repo has `CApoppy.weight_2022.csv` instead) | In-document boxplots/Wilcoxon tests | none | **Legacy / superseded by the 2025 Dangermond study** | C read in full (56 lines). G: dated 2022 by title, uses Box path pattern flagged independently in `01_PATH_FIXES.qmd`. High confidence this is a distinct, earlier, unrelated study rather than a draft of the current one. |
| `scripts/Petal_water_content.qmd` | Petal water content across time-of-day, with a commented-out Google Sheets read | `~/GitHub/CApoppy/data/raw/Petal_water.csv` (absolute path; **not found** — repo has `Petal_water_2022.csv`) | In-document plots/tests | none | **Legacy, currently broken, not portable** | C read directly; absolute path independently flagged in `01_PATH_FIXES.qmd`. Confirmed. |
| `scripts/Time_series.Rmd` | Air/flower temperature time-series plots (2022 CR6 logger data) | `~/Dropbox/CApoppy/data/air_temp/55000000492FED21_052422.csv` (**no `air_temp` folder exists anywhere in this repo — external Dropbox dependency**), `~/Dropbox/CApoppy/data/fl_temp/cr6_Ten_min.csv` (repo has a same-named file under `data/raw/fl_temp/`, but the script does not point there) | In-document HTML plots | none | **Legacy prototype, not portable, one input possibly unrecoverable from this repo** | C read directly; independently flagged in `01_PATH_FIXES.qmd`. Confirmed. |
| `scripts/Time_series_CR6_fltime.Rmd` | Flower-time CR6 logger time series | `~/Dropbox/CApoppy/data/fl_temp/cr6_Temp.{28.May,31.May,5.Jun}.22.csv` (Dropbox path; repo has similarly-named but differently-cased files under `data/raw/fl_temp/`) | In-document HTML plots | none | **Legacy prototype, not portable** | C read directly; independently flagged in `01_PATH_FIXES.qmd`. Confirmed. |
| `scripts/Temp_time_series_CR6_ovary.Rmd` | Ovary-temperature CR6 logger time series | Bare filenames (`cr6_Temp.28.May.22.csv` etc.), implying a `setwd()`/working-directory assumption not present in the current file (no `setwd()` call was found in this particular file, so as coded it will fail unless run with the working directory manually set) | In-document HTML plots | none | **Legacy prototype, currently broken as coded** | C read directly (grep). Confirmed missing explicit path. |
| `scripts/references.bib` | Bibliography for Quarto documents using `bibliography: references.bib` | n/a | n/a | referenced by `petal_physiology.qmd`, `petal_microclimate_analysis*.qmd`, `flower_traits_fixed_block.qmd`, `archive/*.qmd` | **Supporting file, current** | C confirmed present and referenced by multiple `.qmd` YAML headers. |

**Not independently re-verified in full text** (purpose inferred from filename + directory context only, flagged per the evidence standard as *possible*, not confirmed): none remaining — every `.qmd`/`.Rmd`/`.R` file under `scripts/`, `docs/`, and the repo root was opened or grepped directly for this audit.

---

## 5. Master data inventory

### Raw/source data (field-collected, this study)
| File | Path | Exists locally? | Git tracked? | Used by |
|---|---|---|---|---|
| `petal_weight_2025.csv` / `.xlsx` | `data/raw/plant/` | Yes | Yes | `petal_physiology.qmd`, `01_petal_xy_plots.qmd`, `archive/petal_ecophysiology_analysis.qmd` |
| `petal_weight_3.xlsx`, `plant_traits_march25.csv` | `data/raw/plant/` | Yes | Yes | Not read by any script found in this audit (see §12 orphans) |
| `fl_shrinkage2.csv` / `.xlsx`, `fl_shrinkage_6_jun_25.xlsx`, `Petal_waterloss_time.xlsx` | `data/raw/plant/` | Yes | Yes | `Shrinkage2.qmd` (wrong path coded, see §4) |
| RH/temp per-site 2025 CSVs (`Cojo_rhtemp_2025.csv`, `Perry_rhtemp_2025.csv`, `Percos_rhtemp_2025.csv`, `Pt_Con_rhtemp_2025.csv`, plus TNC/alternate sensor files) | `data/raw/rh_temp/` | Yes | Yes | Workflow A & B scripts |
| `rh_temp/downloads now combined/*` | `data/raw/rh_temp/downloads now combined/` | Yes | Yes | Not directly read by any script found — appears to be raw per-download exports later hand-combined into the per-site `*_rhtemp_2025.csv` files (Type: raw/source feeding a manual combination step; see §12) |
| PAR per-site 2025 CSVs (`Cojo_PAR_2025.csv`, `Perry_PAR_2025.csv`, `Percos_PAR_2025.csv`, `Pt_con_PAR_2025.csv`) + `midseason/` subfolder | `data/raw/Apogee_PAR/` | **Yes, locally** | **No — gitignored** | Workflow A scripts |
| Porometer LI-COR exports (zips, per-session CSV/XLSX under nested date folders), `metadata_porometer.xlsx` | `data/raw/porometer/` | Yes | Yes | `petal_trait_analysis.qmd`, `flower_trait_analysis.qmd`, `research_plan.qmd`, `00_INDEX.qmd` (as a class, not every individual file is read) |
| `opening_camera_2025.csv` / `.xlsx` | `data/raw/camera/` | Yes (`.csv` tracked; `.xlsx` present but gitignored) | `.csv` yes / `.xlsx` no | `plant_flowering_analysis.qmd` (wrong path coded, see §4) |
| Petal image scans (png/tif) | `Petal_scans/` (405 MB) | Yes | **No — gitignored entirely** | Not read by any script in this audit; likely feeds ImageJ area measurements manually (see §12) |
| ImageJ-derived CSVs (`Percos2_binary.csv`, `Percos_26mar25_imagej.csv`) | `Petal_scans/` | Yes | Yes (tracked despite parent folder pattern — these specific files predate the `Petal_scans/` ignore rule) | Not read by any script found — likely feed manual area-column entry (see §12, §16) |
| `flower_failure.xlsx` | `data/raw/` | Yes | Yes | Not read by any script found (see §12) |

### 2022/legacy raw data (older, separate study)
| File | Path | Exists? | Tracked? | Used by |
|---|---|---|---|---|
| `CApoppy.weight_2022.csv` | `data/raw/` | Yes | Yes | Not read under this exact name — `CApoppy.wgt.Rmd` expects `CApoppy.weight.csv` (no year) via an external Box path (**MISSING** under coded name) |
| `Petal_water_2022.csv` | `data/raw/` | Yes | Yes | Not read under this exact name — `Petal_water_content.qmd` expects `Petal_water.csv` (**MISSING** under coded name) |
| `Petal_surface_area.csv` | `data/raw/` | Yes | Yes | Not read by any script found (orphan, see §12) |
| `Petals_AnnieDang_2024_03_08.csv`, `Petals_CamMiller_2024_03_15.csv`, `Petals_JR_2024_03_08.csv`, `Petals_KanchanGautam_2024_03_18.csv`, `Petals_KevinSimonin_2024_03_17.csv` | `data/raw/` | Yes | Yes | Not read by any script found — these look like individual student-collected datasets (2024) never yet merged/analyzed (orphan, see §12/§16) |
| `cr6_27May22.csv` (root of `data/raw/`) + numerous CR6/thermocouple CSVs and 2 metadata `.docx` files | `data/raw/fl_temp/` | Yes | Yes | `Time_series*.Rmd`, `Temp_time_series_CR6_ovary.Rmd`, `archive/Differential_water_loss_paper.qmd` — **all via wrong/external paths**, so effectively unused as currently coded |

### Manually created / hand-entered data
| Item | Location | Notes |
|---|---|---|
| Plant-trait `data.frame()` literal | inline in `scripts/plant_trait_analysis.qmd` | Confirmed no external file; data typed directly into the script (see §4, §16 for scientific-practice flag) |
| Hard-coded ICC table | inline in `scripts/petal_physiology.qmd` (second occurrence) | Confirmed re-entry of previously-computed model output as literals (see §16) |

### Intermediate / processed data
| File | Path | Exists? | Tracked? | Produced by | Consumed by |
|---|---|---|---|---|---|
| `porometer_4pops.csv` | `data/processed/` | Yes | Yes | **No script found that produces it** (see §16 "possible missing workflow component") | `petal_trait_analysis.qmd`, `research_plan.qmd`, `Gsw_comparison_bypop.qmd` |
| `porometer_4pops.xlsx`, `PAR_data.csv`, `climate_allsites.csv`, `Combined_3pops_march.csv`/`.xlsx` | `data/processed/` (per nested `.gitignore`) | **No — none exist locally** | N/A | Unknown | `research_plan.qmd` expects `Combined_3pops_march.csv` (**MISSING**) |

### Derived analytical data / outputs
See §7 below.

### External data / services referenced but not integrated
- PRISM / WorldClim (named in `research_plan.qmd` as a planned future environmental-data source; not yet obtained).
- Google Sheets (a `read_sheet()` call is commented out in `Petal_water_content.qmd` — a legacy access method, not currently used).

### Missing data — see the dedicated table in §6.
### Data with unclear provenance — see §8.

---

## 6. Missing-data report

| Missing or unavailable item | Required by | Why needed | Expected location/source | Severity | Evidence |
|---|---|---|---|---|---|
| `data/raw/Apogee_PAR/*.csv` (all 4 sites) — **on GitHub only**; present locally | `petal_microclimate_analysis.qmd`, `petal_microclimate_analysis_2.qmd`, `petal_physiology.qmd` | PAR/light is one of three core microclimate variable classes named in the study's central hypothesis | Present at `data/raw/Apogee_PAR/` on this Mac; excluded from git by `.gitignore` | **Critical** (for GitHub reproducibility) | Confirmed via `.gitignore` line `data/raw/Apogee_PAR`, `git status --ignored`, and direct filesystem check |
| `data/raw/plant/petal_weight.csv` | `petal_microclimate_analysis.qmd`, `petal_microclimate_analysis_2.qmd`, `petal_trait_analysis.qmd`, `flower_traits_fixed_block.qmd`, `research_plan.qmd`, `review_dataset.qmd` | Primary petal trait input for these scripts | Deleted from repo 2025-12-07 (commit `95da7b2`); replaced in intent by `petal_weight_2025.csv` | **Critical** for these 6 scripts | Confirmed via `git log` (create 2025-04-20, delete 2025-12-07) and current filesystem check |
| `data/raw/plant/plant_traits.csv` | `petal_trait_analysis.qmd`, `research_plan.qmd` | Plant morphological trait merge | Only `plant_traits_march25.csv` exists; not confirmed to be the same content/schema | **Important** | Confirmed absent under coded name |
| `data/processed/Combined_3pops_march.csv` | `research_plan.qmd` | Planned gsw-comparison merged dataset | Named in `data/processed/.gitignore` as an expected file; does not exist anywhere | **Important** (but `research_plan.qmd` is a planning doc, not a run pipeline — see §4) | Confirmed absent; corroborated by nested `.gitignore` listing it |
| `data/raw/plant/opening_camera_2025.csv` (wrong subfolder coded) | `plant_flowering_analysis.qmd` | Flowering timing data | Actual file at `data/raw/camera/opening_camera_2025.csv` | **Important** (one-line path fix) | Confirmed |
| `data/raw/plant/Flower_traits.xlsx` (wrong subfolder coded) | `flower_trait_analysis.qmd` | Flower trait data | Actual file at `data/raw/porometer/Flower_traits.xlsx` | **Important** | Confirmed |
| `data/raw/fl_shrinkage2.csv` (wrong subfolder coded) | `Shrinkage2.qmd`, `research_plan.qmd` | Shrinkage data | Actual file at `data/raw/plant/fl_shrinkage2.csv` | **Important** | Confirmed |
| `~/Dropbox/CApoppy/data/air_temp/55000000492FED21_052422.csv` | `Time_series.Rmd` | Air-temp time series | External Dropbox path; no `air_temp` folder exists anywhere in this repo, so this file's content may not be recoverable from the repo at all | **Minor** (legacy script, not part of the current study) but **Unclear** whether the data is lost or just unmigrated | Confirmed absent from repo; cannot determine if it still exists in Dropbox — outside audit scope |
| `~/Dropbox/CApoppy/data/fl_temp/cr6_Temp.*.22.csv` (3 files, case-mismatched names) | `Time_series_CR6_fltime.Rmd`, `Temp_time_series_CR6_ovary.Rmd` | 2022 CR6 logger data | Similarly-named files exist at `data/raw/fl_temp/CR6_Temp.*.may.22.csv` (different case) — **likely the same data**, but filename case differs so cannot be called an exact match | **Minor** (legacy) | Possible / not fully confirmed identity — flagged, not assumed |
| `CApoppy.weight.csv` (no year) | `CApoppy.wgt.Rmd` | 2022 weight data | `data/raw/CApoppy.weight_2022.csv` likely the intended file (different name) | **Minor** (legacy) | Possible, not confirmed identical content |
| `Petal_water.csv` (no year) | `Petal_water_content.qmd`, `archive/Differential_water_loss_paper.qmd` | 2022 water-content data | `data/raw/Petal_water_2022.csv` likely intended | **Minor** (legacy) | Possible, not confirmed identical content |
| `R/project_setup.R` | `scripts/00_dummy_example.qmd` | Shared project setup/helper functions | A near-identical, uncommitted file exists as `scripts/project_initialization.R` | **Minor** (only affects the template demo) | Confirmed by direct comparison of the two files' content and the `source()` call target |

---

## 7. External dependency report

| Dependency | Referenced by | Referenced path/resource | Why needed | Exists now? | Required for reproduction? | Provenance determinable? | Notes |
|---|---|---|---|---|---|---|---|
| This user's home directory / repo checkout location | `Petal_water_content.qmd`, `Gsw_comparison_bypop.qmd`, `archive/Differential_water_loss_paper.qmd` | `~/GitHub/CApoppy/...` | Absolute-path reads/writes | Yes, on this Mac, for this user | Not required if fixed to relative paths; currently yes, functionally | Fully determinable — hard-coded in the script text | Would break for any other user or a differently-located clone |
| Dropbox | `Time_series.Rmd`, `Time_series_CR6_fltime.Rmd` | `~/Dropbox/CApoppy/data/...` | 2022 CR6/air-temp logger source files | Cannot determine from repo evidence whether this Dropbox folder still exists | Only for the legacy 2022 time-series scripts, not the current study | Unclear — outside repo | Independently flagged already in `scripts/01_PATH_FIXES.qmd` |
| Box (Box-Box CloudStorage) | `CApoppy.wgt.Rmd`, `Petal_water_content.qmd` (commented reference) | `/Users/gretchen/Library/CloudStorage/Box-Box/1. Lab research/CApoppy/data` | Original 2022 SFSU data location, pre-dating this git repo | Cannot determine | No — legacy, superseded data now lives in `data/raw/` under different filenames | Unclear — outside repo | `setwd()` usage here also violates the "avoid setwd()" guidance the researcher's own `01_PATH_FIXES.qmd` recommends |
| Google Sheets API | `Petal_water_content.qmd` (commented out) | `https://docs.google.com/spreadsheets/d/1E-IBa1wWjJXVLBjhe6bojlOcMyZRfDINiFydXIVs17s/...` | Alternate/older way of pulling the same water-content data | Not invoked (commented out) | No | Unclear whether still valid/accessible | Dead code, not currently exercised |
| PRISM / WorldClim | `research_plan.qmd` | Named generically, no URL | Planned environmental covariates for a future analysis extension | Not yet obtained (explicitly stated as "to be obtained" in the doc) | No — not part of the current pipeline | N/A — planning only | Not a current blocker |
| No other repositories, network drives, external hard drives, or environment-variable dependencies were found in any script. | — | — | — | — | — | — | Confirmed by grep across all `.qmd`/`.Rmd`/`.R` files for `Volumes`, `OneDrive`, `iCloud`, other `~/GitHub` project names, and `Sys.getenv()` calls — none found. |

---

## 8. Data provenance report

| Dataset | Original source | Original filename | Acquisition method | Processing script | Derived products | Provenance confidence |
|---|---|---|---|---|---|---|
| Petal weight (2025, 4 pops × 3 blocks) | Field collection at Dangermond Preserve, per `project_decisions_log.qmd` sampling design | `petal_weight_2025.csv`/`.xlsx` (superseding a deleted `petal_weight.csv`) | Manual field weighing, entered to spreadsheet (method of entry into digital form not documented) | `01_petal_xy_plots.qmd`, `petal_physiology.qmd` | XY trait plots, ICC tables, mixed models (all in-document) | **High** — study design, dates, coordinates, and rationale are explicitly documented in `project_decisions_log.qmd` |
| RH/Temperature loggers, 2025 (4 sites) | Field-deployed loggers ("HOBO" per `petal_microclimate_analysis.qmd`'s narrative version) | site-specific `*_rhtemp_2025.csv` | Logger download, later combined from raw per-download exports (see `rh_temp/downloads now combined/`) | `petal_microclimate_analysis*.qmd`, sensor-comparison scripts | 4-day/7-day window microclimate metrics, VPD | **High** — sensor type, interval, placement, and known failure (Pt. Conception, Block 3) are explicitly documented |
| Apogee PAR sensors, 2025 (4 sites) | Field-deployed Apogee PAR sensors | `*_PAR_2025.csv` + `midseason/` interim exports | Logger download | `petal_microclimate_analysis*.qmd` | Daily PAR integrals, high-light hours | **High** for acquisition method; **Critical gap** for git availability (§6) |
| Porometer / LI-COR gsw data | Field porometer measurements, nested by session date | Session-specific export folders + `metadata_porometer.xlsx` | Instrument export (zips + xlsx/csv pairs) | `Gsw_comparison_bypop.qmd`, feeds `data/processed/porometer_4pops.csv` | `porometer_4pops.csv` | **Medium** — raw exports and a metadata workbook exist, but **no script in the repository was found that actually builds `porometer_4pops.csv` from these raw exports** (see §16) |
| Camera / flowering-timing data | Timelapse camera at field sites | `opening_camera_2025.csv`/`.xlsx` | Camera capture, manually reviewed for open/close times (inferred from column names seen in `plant_flowering_analysis.qmd`, e.g. dropped "image"/"note" columns) | `plant_flowering_analysis.qmd` | Timing/duration plots | **Medium** — acquisition instrument is clear, review/annotation method is not documented |
| Petal image scans (`Petal_scans/`) | Flatbed/photo scans of petals, organized by date folder | Many `IMG_*`, `Percos_*`, `ptcon_*`, `shrinkage_*` filenames | Scanning, some already binarized (`Percos1_binary.png`) and passed through ImageJ (`Percos_26mar25_imagej.csv`) | **No processing script found in the repository** | Presumably petal-area measurements that would feed the `area_cm2` column anticipated (but not found) in `01_petal_xy_plots.qmd` | **Provenance unclear** — the ImageJ workflow itself is described narratively in `docs/Petal_area ImageJ.docx` (a Word document, not machine-readable in this audit) but no R/Python script performs this measurement |
| 2022 SFSU campus data (`CApoppy.weight_2022.csv`, `Petal_water_2022.csv`) | SFSU campus, per `CApoppy.wgt.Rmd` narrative ("collected data on California poppies from SFSU campus") | Original names lost (files renamed with `_2022` suffix at some point) | Manual field weighing/measurement, as narrated in the 2022 Rmd | `CApoppy.wgt.Rmd`, `Petal_water_content.qmd` (both currently broken on path) | none currently regenerated | **Medium** — narrative context exists but exact acquisition dates/protocol beyond what's in the Rmd prose are not documented elsewhere |
| 2024 student petal CSVs (`Petals_AnnieDang...`, `Petals_CamMiller...`, etc.) | Presumably individual student projects/data collection, based on filenames and dates (March 2024) | As named | Unknown | **No script found reads these files** | None | **Provenance unclear** — filenames suggest student contributors but no code or documentation explains how or whether this data was intended to feed the current study |

---

## 9. Workflow / dependency graph

### Workflow A — Core microclimate × petal trait study
```
petal_weight_2025.csv (raw, tracked)              rh_temp/*_rhtemp_2025.csv (raw, tracked)         Apogee_PAR/*_PAR_2025.csv
        |                                                   |                    (raw, LOCAL ONLY — not in GitHub)
        v                                                   v                         |
  [inline cleaning:                                [load_rhtemp() function]           v
   outlier filter, petal-only                              |                  [load_par() function]
   filter, weight sanity checks]                            \___________________________/
        |                                                        |
        v                                                        v
  petal_data / petal_data_all                        rhtemp_all, par_all (VPD calculated,
   (in-memory only)                                    PAR QC'd: negatives→0, Cojo>3000→NA)
        |                                                        |
        |______________________ 4-day / 7-day window join _______|
                              |
                              v
                  petal_microclimate (in-memory)
                              |
              ______________/  \______________
             v                                v
   ICC / variance-partitioning        Mixed-effects climate–trait models
   tables (petal_physiology.qmd)      + microsite-level correlation plots
             |                                |
             v                                v
   In-document PDF/HTML tables & figures (petal_microclimate_analysis_2.qmd,
   petal_physiology.qmd) — NOT written to outputs/tables or outputs/figures
```
*Break points (flagged):* `petal_microclimate_analysis.qmd` and `petal_microclimate_analysis_2.qmd` point at `petal_weight.csv`, which no longer exists — this chain is broken for those two scripts specifically. The PAR branch is broken for anyone without local access to this exact Mac's `data/raw/Apogee_PAR/` folder.

### Workflow (parallel, narrower) — `01_petal_xy_plots.qmd`
```
petal_weight_2025.csv (raw, tracked)
        |
        v
[cleaning: outlier filter, petal-only filter,
 impossible-value filter incl. dry>=wet check]
        |
        v
   petal_data (in-memory)
        |
        v
Section A/B/C/D exploratory plots (PDF, in-document only; no microclimate join)
```

### Workflow B — Sensor substitution decision (feeds Workflow A's Block-3 gap)
```
rh_temp/Pt_Con_rhtemp_2025.csv (old sensor)
rh_temp/Cojo_Pt_Con_rhtemp_2025_tncsensor.csv (new TNC sensors)
rh_temp/pt-conception-alternate.csv
        |
        v
sensor_comparison_analysis.qmd / rh_sensor_comparison.qmd
        |
        v
In-document bias/agreement diagnostics → informs (manually, not by code)
whether/how to patch the Pt. Conception Block-3 gap in Workflow A
```
*No code was found that actually merges a substitute sensor back into `rhtemp_all` for Workflow A — the decision log describes this only as an outstanding, not-yet-implemented action item.*

### Workflow F — Processed porometer data (dependency chain with a missing link)
```
data/raw/porometer/  (many nested session folders,
   zips, xlsx/csv pairs — raw instrument exports)
        |
        ?  <-- NO SCRIPT FOUND THAT PERFORMS THIS STEP
        v
data/processed/porometer_4pops.csv  (tracked in git; used by 3 downstream scripts)
        |
        v
petal_trait_analysis.qmd, research_plan.qmd, Gsw_comparison_bypop.qmd
```
*This is the clearest "possible missing workflow component" in the repository — see §16.*

### Workflow I — Differential water loss / nyctinasty manuscript
```
data/raw/fl_temp/CR6_Temp*.csv, Petal_water_2022.csv (or similarly-named files)
        |  (referenced via stale/absolute paths — currently broken)
        v
scripts/archive/Differential_water_loss_paper.qmd
        |
        v
outputs/figures/dunn_test_results*.png, outputs/plots/flower_ovary_temperatures.png
   (present locally; moved here via git mv in commit ec49d82 from old figures//plots/)
        |
        v (manuscript text separately authored, not code-generated)
docs/Differential_water_loss_paper.qmd, docs/Differential_water_loss_paper_2.qmd
   (never version-controlled; relationship between the two drafts unresolved)
```

---

## 10. Recommended execution order

This reflects what the *code and its dependencies* indicate, not a numbering scheme (only `00_`/`01_` prefixes exist and they only cover 3 files).

| Stage | Script(s) | Required predecessor | Key input | Key output | Can it currently run end-to-end? |
|---|---|---|---|---|---|
| 1 | `rh_sensor_comparison.qmd`, `sensor_comparison_analysis.qmd` | none | `rh_temp/*.csv` | Sensor-substitution decision (manual, narrative) | **Yes** — all inputs present and tracked |
| 2 | `01_petal_xy_plots.qmd` | none | `petal_weight_2025.csv` | Exploratory trait plots | **Yes** |
| 3 | `petal_physiology.qmd` | Stage 1 decision (informally) | `petal_weight_2025.csv`, `rh_temp/*.csv`, `Apogee_PAR/*.csv` | ICC tables, mixed models, PCA | **No on GitHub** (PAR missing); **yes locally** |
| 3′ (parallel/overlapping) | `petal_microclimate_analysis_2.qmd` | Stage 1 | `petal_weight.csv` (**missing**), `rh_temp/*.csv`, `Apogee_PAR/*.csv` | Full-season + common-period microclimate PCA, Procrustes check, mixed models | **No — broken locally and on GitHub** (missing petal file; PAR also missing on GitHub) |
| 3″ | `petal_microclimate_analysis.qmd` | Stage 1 | `petal_weight.csv` (**missing**) | Trimmed version of Stage 3′ | **No — broken locally and on GitHub** |
| — | `plant_trait_analysis.qmd` | none (self-contained data) | none | Plant morphology comparison | **Yes** (data is hard-coded in the script) |
| — | `Shrinkage2.qmd` | none | `fl_shrinkage2.csv` (**wrong path coded**) | Shrinkage plots | **No — broken as coded** (one-line path fix) |
| — | `plant_flowering_analysis.qmd` | none | `opening_camera_2025.csv` (**wrong path coded**) | Flowering timing plots | **No — broken as coded** (one-line path fix) |
| — | `petal_trait_analysis.qmd` | Assumes `data/processed/porometer_4pops.csv` already built (Stage/workflow with no known producing script) | `petal_weight.csv` (**missing**), `plant_traits.csv` (**missing**), `porometer_4pops.csv` (present) | Merged trait dataset | **No — broken** (2 of 3 inputs missing) |
| — | `Gsw_comparison_bypop.qmd` | Same as above | `porometer_4pops.csv` (present, absolute path) | gsw comparison plots | **Yes, but only on this exact Mac** (absolute path) |
| — | `flower_trait_analysis.qmd` | none | `Flower_traits.xlsx` (**wrong path coded**) | Exploratory flower-trait analysis | **No — broken as coded** |
| — | `research_plan.qmd` | none (planning doc) | Multiple missing files | Planned figures (not yet produced) | **No** — by design, this is a roadmap, not a runnable pipeline |
| — | `review_dataset.qmd` | none | `petal_weight.csv` (**missing**) | Dataset-review summary | **No — broken as coded** |
| Legacy, independent of the above | `CApoppy.wgt.Rmd`, `Petal_water_content.qmd`, `Time_series*.Rmd`, `Temp_time_series_CR6_ovary.Rmd`, `archive/Differential_water_loss_paper.qmd` | none | Various absolute/external paths | Various legacy in-document outputs | **No — all broken as coded** (stale/absolute/external paths) |
| Independent | `Schoen and Ashman.qmd` | none | none (simulation) | Contour plots | **Yes** |

---

## 11. Duplicate/superseded script assessment

### Group 1 — Petal-trait × microclimate manuscript pipeline
- **`petal_microclimate_analysis_2.qmd`** (1624 lines) — most complete (full-season + common-period PCA, Procrustes robustness check). **Confidence: High** this is the most fully developed member of the group, based on direct content comparison.
- **`petal_physiology.qmd`** (576 lines) — a condensed variant that keeps the ICC/variance-partitioning framing and adds narrative interpretation of results; reads the *current* data file (`petal_weight_2025.csv`), unlike its siblings. **Confidence: High** this is the most recently *narratively* developed and currently-functional member (git-dated 2026-01-17; the only one of the three with a working data path).
- **`petal_microclimate_analysis.qmd`** (508 lines, after a Feb-2026 1740→508-line trim) — nearly identical code to `petal_physiology.qmd` but retains the stale `petal_weight.csv` reference. **Confidence: High** this is either an incompletely-updated trim of `petal_physiology.qmd`, or a parallel simplification that was not synced with it — the repository does not record which, but the broken path is Confirmed.
- **Important differences:** only `petal_microclimate_analysis_2.qmd` includes the full-season vs. common-period PCA/Procrustes comparison; only `petal_physiology.qmd` includes narrative interpretation and (problematically) the hard-coded ICC bar chart (§16).
- **Recommendation for the researcher to decide, not acted on here:** these three should likely converge into one "master" microclimate-trait script once the `petal_weight` path issue is resolved — see §17 Q1.

### Group 2 — Manuscript-style write-ups of the same petal-trait study
- **`scripts/archive/petal_ecophysiology_analysis.qmd`** — explicitly filed under `archive/` by the researcher; framed around coastal/inland categories rather than continuous microclimate. **Confidence: High (superseded)** — the researcher's own archival action, corroborated by `project_decisions_log.qmd`'s Decision 1 ("Frame the study around microclimate variation... rather than simple coastal/inland classifications"), which explains *why* this framing was abandoned.
- **`scripts/flower_traits_fixed_block.qmd`** — an earlier, unfinished template (placeholder text still present). **Confidence: High (earlier draft, not touched since)** — last git-modified 2025-12-07, never archived or finished.

### Group 3 — Differential water-loss / nyctinasty manuscript drafts
- **`scripts/archive/Differential_water_loss_paper.qmd`** — the git-tracked, code-bearing original.
- **`docs/Differential_water_loss_paper.qmd`** and **`docs/Differential_water_loss_paper_2.qmd`** — two never-committed, textually different prose drafts.
- **Cannot determine from repository evidence which of the two `docs/` drafts is "current"** — both are un-versioned, so there is no timestamp-in-git to compare, and file-modification times on disk are not reliable evidence of authorial intent. **Flagged as Question 2 in §17.**

### Group 4 — 2022 legacy prototypes vs. current study
- `CApoppy.wgt.Rmd`, `Petal_water_content.qmd`, `Time_series.Rmd`, `Time_series_CR6_fltime.Rmd`, `Temp_time_series_CR6_ovary.Rmd` are **not duplicates of the 2025 scripts** — they analyze a different, earlier dataset (2022, different location/campus per `CApoppy.wgt.Rmd`'s own text) and are best understood as **retired prototypes**, not competing current versions. **Confidence: High**, based on explicit dates in document titles and the distinct data referenced.

---

## 12. Orphan / unexplained files

*(Present, of plausible significance, but no consuming script was found in this audit. Not recommended for deletion — flagged for the researcher's judgment.)*

- `data/raw/plant/petal_weight_3.xlsx`, `data/raw/plant/plant_traits_march25.csv` — present, tracked, not read by any script found (the latter is very likely the intended replacement for the missing `plant_traits.csv` reference — see §17 Q3).
- `data/raw/Petal_surface_area.csv` — not read anywhere; name suggests it might supply the `area_cm2` column that `01_petal_xy_plots.qmd` is written to expect but currently does not find (see §16).
- `data/raw/Petals_AnnieDang_2024_03_08.csv`, `Petals_CamMiller_2024_03_15.csv`, `Petals_JR_2024_03_08.csv`, `Petals_KanchanGautam_2024_03_18.csv`, `Petals_KevinSimonin_2024_03_17.csv` — five 2024 student-collected datasets, not referenced by any script.
- `data/raw/flower_failure.xlsx` — not referenced by any script (note: unrelated to the documented "Pt. Conception sensor failure"; this appears to be a different, flower-level dataset).
- `Petal_scans/Percos2_binary.csv`, `Petal_scans/Percos_26mar25_imagej.csv` — ImageJ-derived measurement files with no consuming script found.
- `data/raw/rh_temp/downloads now combined/*` (raw per-download exports) — plausibly the direct predecessor of the per-site `*_rhtemp_2025.csv` files, but no script performs that combination; it appears to have been done by hand.
- `docs/DroughtBox_guide.docx`, `docs/Microgeographic Adaptation in California Poppy.docx`, `docs/nyctinastic species.docx`, `docs/plans for experiments.docx`, `docs/Paper Outline_...pdf`, `docs/Petal_area ImageJ.docx` — Word/PDF planning and methods documents; informative but outside the scope of code-based reconstruction (not orphan *code*, but orphan relative to the machine-readable pipeline).
- `outputs/figures/dunn_test_results.png`, `dunn_test_results_mg.png`, `outputs/plots/flower_ovary_temperatures.png` — their producing script (`archive/Differential_water_loss_paper.qmd`) writes to absolute paths (`~/GitHub/CApoppy/figures/...`, `.../plots/...`) that no longer match `outputs/figures`/`outputs/plots`; git history confirms these exact PNGs were `git mv`'d into the new `outputs/` layout in commit `ec49d82`, but the script itself was not updated to match, so **re-running the script today would recreate the old `figures/`/`plots/` folders rather than update the files now living in `outputs/`.**

---

## 13. Git-state findings

- **Working tree, at audit time:** one file staged (`scripts/project_initialization.R`, new), one file modified-not-staged (`.gitignore`, adding a `.positai` ignore rule). No other pending changes. This audit did not stage, commit, or modify either.
- **`docs/` has mixed git status:** `docs/Differential_water_loss_paper.html`, `docs/DroughtBox_guide.docx`, `docs/Screenshot 2023-11-17 at 1.50.16 PM.png`, `docs/nyctinastic species.docx`, `docs/plans for experiments.docx` are tracked (committed before the `docs/` ignore rule existed); everything else currently in `docs/` (the `.qmd` drafts, `.html` renders, one `.pdf`) is untracked/ignored. This means a `git clone` gets an inconsistent, partial `docs/` folder — some files, not others, with no obvious logic from a fresh user's perspective.
- **`scripts/.gitignore` excludes `scripts/01_PATH_FIXES.qmd`**, a file that is already tracked. Future edits to this specific file will not be picked up by `git status`/`git add .` unless force-added — worth confirming this is intentional (§17 Q7).
- **Large local-only data:** `Petal_scans/` (405 MB, entirely gitignored) and `data/raw/Apogee_PAR/` (size not separately measured, but all 4-site + midseason PAR CSVs, entirely gitignored) are the two largest gaps between local disk and GitHub.
- **Rendered outputs are not committed** (`*.html`, `*.pdf`, `*_files/`, `outputs/` are all gitignored) — this is a defensible, common choice, and is not itself a problem provided the generating code and inputs are complete (which, per §6, they currently are not in every case).
- **`outputs/figures` and `outputs/plots` currently hold 3 PNGs that were `git mv`'d there from old root-level `figures/`/`plots/` folders in commit `ec49d82` (2026-02-19)**, alongside the same commit's large trim of `petal_microclimate_analysis.qmd`. This is a real, confirmed reorganization step, not an accidental orphaning — but the producing script (`archive/Differential_water_loss_paper.qmd`) was not updated to match the new paths (see §12).
- **No branches other than `main`** exist locally or on the remote (`origin/HEAD -> origin/main`); no evidence of feature-branch work or anything hidden from view.
- **No secrets, credentials, or `.Renviron`/`.httr-oauth` files were found** tracked or untracked.

---

## 14. Documentation discrepancies

- **`README.md` is essentially empty** ("# CApoppy" / "CA-poppy") — it describes nothing about the study, the data, or how to run the analysis. All real documentation lives in `project_decisions_log.qmd` and `scripts/00_INDEX.qmd`, neither of which is linked from the README.
- **`scripts/00_INDEX.qmd`'s Theme A "Data used" section already lists the `petal_weight.csv` vs. `petal_weight_2025.csv` ambiguity as a known open issue** ("or `petal_weight_2025.csv` depending on file") — meaning the researcher (or a prior AI-assisted session) already knew about this exact problem at the time `00_INDEX.qmd` was written, but the underlying scripts were not subsequently fixed.
- **`scripts/01_PATH_FIXES.qmd` proposes specific fixes for `Petal_water_content.qmd`, `Gsw_comparison_bypop.qmd`, `Time_series.Rmd`, `Time_series_CR6_fltime.Rmd`, `Temp_time_series_CR6_ovary.Rmd`, and `CApoppy.wgt.Rmd`** — none of these fixes have been applied to the live scripts as of this audit (confirmed by direct comparison of the suggested fixes against current file contents).
- **`project_decisions_log.qmd`'s "File Structure & Paths" section documents a file named `-petal_weight.csv`** (leading hyphen appears to be a markdown-list rendering artifact, i.e., meant as "`petal_weight.csv`") as the petal data file — this document was **not updated** when the file was renamed to `petal_weight_2025.csv` on 2025-12-07, even though the decision log's own "Session Notes" section (Session 9, "Final Debugging... Fixed file paths for local analysis") claims path issues were resolved.
- **`project_decisions_log.qmd` states "Analysis Date: December 2025"** near the end but also contains a final dated note "*28 March 2026*" and a full decision-log entry about creating `01_petal_xy_plots.qmd` — i.e., the document has been extended well past its originally stated analysis date without updating that stated date, which could confuse a future reader about the document's currency.
- **`00_dummy_example.qmd` documents a `source(here::here("R","project_setup.R"))` pattern that does not currently work** (see §6), meaning the one file in the repo that's explicitly meant to demonstrate "how this project is supposed to be organized" cannot itself be rendered as-is.

---

## 15. Reproducibility assessment

### A. Reproducibility on this computer
**Rating: MOSTLY.**
Nearly all raw data referenced by the *current* (non-legacy) scripts exists somewhere on this Mac. The main local blockers are (1) the six scripts that reference the deleted `petal_weight.csv` rather than the present `petal_weight_2025.csv`, and (2) four scripts with wrong-subfolder or wrong-filename paths (`Shrinkage2.qmd`, `plant_flowering_analysis.qmd`, `flower_trait_analysis.qmd`, `petal_trait_analysis.qmd`/`research_plan.qmd`'s `plant_traits.csv` reference). These are all one-line fixes once the correct target is confirmed with the researcher (§17), not missing-data problems. The field-level gap (Pt. Conception sensor failure, Block 3) is a genuine data-collection limitation, already documented and already worked around in the code (an explicit filter), not a repository defect.

### B. Reproducibility from a clean GitHub clone
**Rating: PARTIALLY.**
A fresh `git clone` of `https://github.com/lebuhn/CApoppy.git` would obtain: all petal-weight, plant-trait, shrinkage, camera, RH/temp, and porometer raw data that is git-tracked; the `data/processed/porometer_4pops.csv` intermediate file; all analysis code; and the decision log/index documentation. It would **not** obtain: any PAR/light sensor data (`data/raw/Apogee_PAR/`, entirely gitignored — this alone prevents reproducing the full microclimate characterization and any model that includes `par_int_z`/PAR terms); the 405 MB of petal image scans; any rendered output; and the currently-untracked `docs/*.qmd` manuscript drafts. Combined with the broken file-path issues above (which affect the clean clone identically to this Mac, since they are code bugs, not missing-file-on-this-machine problems), a new researcher cloning this repository could successfully run `01_petal_xy_plots.qmd`, `plant_trait_analysis.qmd` (hard-coded data), and the sensor-comparison scripts, but **could not run any of the microclimate-integrated trait analyses (Workflow A) to completion** without first (a) fixing the `petal_weight.csv`/`petal_weight_2025.csv` reference and (b) obtaining the PAR data from the researcher directly (it is not recoverable from GitHub alone).

### Critical blockers
1. `data/raw/Apogee_PAR/` is git-ignored and absent from GitHub — no clean clone can run the PAR-dependent portions of Workflow A.
2. `petal_microclimate_analysis.qmd` and `petal_microclimate_analysis_2.qmd` reference a deleted file (`petal_weight.csv`) and will fail to load data for anyone, on any machine, including this one, without a manual fix.

### Important reproducibility gaps
3. Four scripts have wrong relative paths to files that do exist elsewhere in the repo (`Shrinkage2.qmd`, `plant_flowering_analysis.qmd`, `flower_trait_analysis.qmd`, and the `plant_traits.csv` reference in `petal_trait_analysis.qmd`/`research_plan.qmd`).
4. Several scripts use absolute, user-and-machine-specific paths (`~/GitHub/CApoppy/...`, `~/Dropbox/...`) that will not resolve for any other user or a differently-located checkout.
5. No `data/processed/porometer_4pops.csv`-producing script was found — a new researcher would need to either obtain this file directly or reverse-engineer how to build it from the raw porometer exports.
6. No package/version pinning (`renv`, `DESCRIPTION`, or documented R/package versions) — package drift over time is a real risk for exact numerical reproduction, independent of the data-path issues.

### Documentation gaps
7. `README.md` gives no orientation; a new user must discover `project_decisions_log.qmd` and `scripts/00_INDEX.qmd` on their own.
8. No single script is unambiguously marked "run this one" for the microclimate-trait workflow among the three overlapping candidates.
9. The relationship between `docs/Differential_water_loss_paper.qmd` and `docs/Differential_water_loss_paper_2.qmd` is not documented anywhere.

### Minor organizational issues
10. Empty placeholder directories (`scripts/analysis/`, `scripts/manuscripts/`, `R/`) exist without explanation.
11. `outputs/tables/` and `outputs/reports/` are empty — the recommended output structure (per `project_initialization.R`) is only partially adopted.
12. `scripts/.gitignore` excludes a file (`01_PATH_FIXES.qmd`) that is already tracked, which may or may not be intentional.

---

## 16. Potential scientific issues for later review

*(Flagged only where directly observed in the repository during this audit; not a general statistical review.)*

1. **Hard-coded/manually re-entered statistical result.** In `scripts/petal_physiology.qmd`, an `icc_table` object is first correctly computed from the data (chunk `trait-icc`, lines ~368–393). A later chunk (~line 417 onward) **redefines a variable with the same name, `icc_table`, using hand-typed numeric literals** (`0.427, 0.479, 0.107, 0.107, 0.107`) copied from what appears to be a previous run's printed output, and then builds a bar chart from that hard-coded version. If the underlying petal or microclimate data changes in any way, this bar chart will silently continue showing the old numbers rather than updating. This is a reproducibility/correctness risk specific to this one figure, not the underlying models.
2. **Different scripts use different outlier/window/exclusion logic that a reader must track by hand.** For example, `01_petal_xy_plots.qmd` deliberately **keeps** Pt. Conception Block 3 (no microclimate join, so the missing sensor data doesn't matter), while `petal_microclimate_analysis*.qmd`/`petal_physiology.qmd` **exclude** it. This is a documented, deliberate difference (per the decision log) rather than an inconsistency, but a reader encountering only the code (not the decision log) could easily miss why sample sizes differ between figures produced by different scripts.
3. **`Gsw_comparison_bypop.qmd` merges "Cojo" and "CojoHQ" into a single population label and manually offsets plant IDs for one date range** (`plant + 16` for dates in `2025-04-19` to `2025-04-21`) to avoid ID collisions. This is a defensible data-cleaning step, but it is a hand-written, date-specific rule with no comment explaining why those particular three dates were chosen or whether other date ranges might have the same collision risk.
4. **The Percos-outlier investigation in `01_petal_xy_plots.qmd` (Section D)** defines "extreme" as the top 5% of DMC values within Percos specifically, which is a sensible adaptive threshold, but the script's own commentary (Sections D1–D3) frames this explicitly as an open, unresolved question ("Are the most extreme records plausible, or do they look like data entry errors?") — i.e., this is correctly flagged as needing manual verification against field notebooks, and the audit found no evidence that this verification has yet occurred.
5. **No R version or package-version record exists anywhere in the repository** (no `renv.lock`, `DESCRIPTION`, or `sessionInfo()` output saved). Given the analyses use `lme4`/`lmerTest` mixed models, which can produce different convergence behavior or even different point estimates across package versions, this is worth addressing before manuscript submission (`project_decisions_log.qmd` itself independently flags "Model Convergence Problems" as Issue 4, and recommends convergence workarounds, which somewhat mitigates this risk but does not eliminate the version-pinning gap).

---

## 17. Questions for me

**Q1.** Among `petal_microclimate_analysis.qmd`, `petal_microclimate_analysis_2.qmd`, and `petal_physiology.qmd`, which one (if any) reflects the analysis you actually intend to carry into the manuscript? All three read slightly different data files and/or have different levels of completeness, and the repository does not record a decision among them.

**Q2.** For the nyctinasty/water-loss manuscript, `docs/Differential_water_loss_paper.qmd` and `docs/Differential_water_loss_paper_2.qmd` are two different, never-committed prose drafts with different author byline lists. Which is current, and should the other be removed or clearly marked as superseded?

**Q3.** Is `data/raw/plant/plant_traits_march25.csv` intended to be the same dataset that `petal_trait_analysis.qmd` and `research_plan.qmd` call `plant_traits.csv` (missing), or is it a different, narrower dataset (just the March sampling date)?

**Q4.** Is `data/processed/porometer_4pops.csv` built by hand (e.g., in Excel) from the raw porometer exports, or was there once a script that produced it that has since been lost? No producing script was found anywhere in the repository or its git history search.

**Q5.** Should `data/raw/Apogee_PAR/` be added to git (even if large), or is keeping it local-only intentional (e.g., for file-size or embargo reasons)? As it stands, no one else can reproduce the PAR-dependent parts of the analysis from GitHub alone.

**Q6.** Are the 2024 student-collected files (`Petals_AnnieDang_2024_03_08.csv`, `Petals_CamMiller_2024_03_15.csv`, `Petals_JR_2024_03_08.csv`, `Petals_KanchanGautam_2024_03_18.csv`, `Petals_KevinSimonin_2024_03_17.csv`) meant to feed into the current Dangermond study, a separate teaching exercise, or a predecessor pilot study? No script reads them, and their relationship to the current 4-population design is not documented.

**Q7.** Is excluding `scripts/01_PATH_FIXES.qmd` from future git tracking (via `scripts/.gitignore`) intentional — e.g., because it's meant to be a disposable working note rather than a permanent part of the repo?

**Q8.** Is the petal-area workflow (scans in `Petal_scans/` → ImageJ → an `area_cm2` column) something you still plan to integrate into `01_petal_xy_plots.qmd`'s Section B (which is currently written to auto-skip if no area column is found)? If so, is there an ImageJ macro or script that performs this measurement that simply isn't in this repository yet?

---

## 18. Recommended next steps

*(Not performed — for your prioritization. Grouped as requested; ordered within each group roughly by effort/impact.)*

### A. Fix before doing additional analysis
- Decide which of the three microclimate-trait scripts (Q1) is canonical, and repoint it (and any others you keep) at `petal_weight_2025.csv`.
- Fix the four wrong-subfolder path references: `Shrinkage2.qmd` → `data/raw/plant/fl_shrinkage2.csv`; `plant_flowering_analysis.qmd` → `data/raw/camera/opening_camera_2025.csv`; `flower_trait_analysis.qmd` → `data/raw/porometer/Flower_traits.xlsx`; and resolve the `plant_traits.csv`/`plant_traits_march25.csv` naming question (Q3) in `petal_trait_analysis.qmd`/`research_plan.qmd`.
- Decide on Q4/Q5 (porometer processing script, PAR data in git) before relying further on `porometer_4pops.csv` or running any GitHub-only clone of the microclimate analysis.

### B. Fix before manuscript submission or publication
- Replace the hard-coded ICC table in `petal_physiology.qmd` with a direct reference to the computed `icc_table` object (§16.1).
- Record R version and package versions used for the final analysis (at minimum, save `sessionInfo()` output; ideally adopt `renv`).
- Document the rationale for the Cojo/CojoHQ merge and plant-ID offset rule in `Gsw_comparison_bypop.qmd` (§16.3).
- Resolve the Percos-extreme-DMC verification against field notebooks (§16.4), and record the outcome in `project_decisions_log.qmd`.
- Replace absolute paths (`~/GitHub/CApoppy/...`) in `Gsw_comparison_bypop.qmd` with relative/`here()`-based paths, per the researcher's own `01_PATH_FIXES.qmd` recommendations.

### C. Fix before archiving on GitHub/Zenodo
- Decide whether `data/raw/Apogee_PAR/` should be committed (Q5) so the archived repository is self-contained; if not, document the exclusion and where the data can be obtained.
- Reconcile `docs/` — decide which files should be tracked vs. ignored, since the current mix (some old files tracked, current drafts ignored) will look accidental to an outside reader.
- Add a real `README.md` describing the study, data, and how to run the pipeline (even a short version pointing to `project_decisions_log.qmd` and `00_INDEX.qmd` would help).
- Add a package-management file (`renv.lock` or at minimum a `DESCRIPTION` listing required packages) so the archived version is runnable by others.

### D. Useful organizational cleanup
- Move `scripts/project_initialization.R` to `R/project_setup.R` (matching its own header comment and what `00_dummy_example.qmd` expects), or update `00_dummy_example.qmd` if you'd rather keep it in `scripts/`.
- Either populate or remove the empty `scripts/analysis/`, `scripts/manuscripts/`, and `R/` directories.
- Update `scripts/00_INDEX.qmd`'s Theme A data note now that the `petal_weight.csv`/`petal_weight_2025.csv` ambiguity has a clear answer (once Q1/Q3 are resolved).
- Update `project_decisions_log.qmd`'s stated "Analysis Date" and file-structure section to reflect the current file names and the more recent (March 2026) session notes.

### E. Optional improvements
- Consider whether the 2022 legacy scripts (`CApoppy.wgt.Rmd`, `Petal_water_content.qmd`, `Time_series*.Rmd`, `Temp_time_series_CR6_ovary.Rmd`) should move to an `archive/` folder alongside the other explicitly-archived scripts, for consistency.
- Consider documenting the relationship (if any) between the 2024 student petal CSVs and the current study (Q6), even just as a comment or a line in `00_INDEX.qmd`.
- Consider whether the ImageJ petal-area workflow (Q8) warrants a short script or documented macro in the repository, since `01_petal_xy_plots.qmd` is already written to use an `area_cm2` column that doesn't yet exist anywhere in the tracked data.

---

## Final verification notes

- All analysis-related file types present in the repository (`.R`, `.Rmd`, `.qmd`) were located via `find` and confirmed against `wc -l`; no `.py`, notebook, Makefile, or shell workflow files exist in this repository.
- Every `read_csv`/`read.csv`/`read_excel`/`source`/`here`/`file.path` call found by an exhaustive grep across all `.qmd`/`.Rmd`/`.R` files was individually checked against the actual filesystem contents (via `find`/`ls`) to determine existence, exact path match, and git-tracked status.
- Every `write_csv`/`ggsave`/`saveRDS`/`save_as_image` call found by the same exhaustive grep was checked against `outputs/`, `data/processed/`, and the (currently nonexistent) root-level `figures/`/`plots/` targets referenced by older scripts.
- `.gitignore` (root and all 5 nested copies) was read directly and cross-checked against `git status --ignored` and a full `git ls-files` listing (225 tracked files) to distinguish tracked / locally-ignored / genuinely-missing for every dataset discussed above.
- No repository changes of any kind were made during this audit.
