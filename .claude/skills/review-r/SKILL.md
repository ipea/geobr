---
name: review-r
description: Read-only R code review protocol for `.R` scripts. Checks code quality, error handling, spatial-data correctness, and package conventions; produces a report without editing. Use when user says "review this R script", "check the R code", "audit the analysis code", "code review on the R", or when R code is touched as part of a release. NOT for running the code — pair with `/r-package-check` for the CRAN gate.
argument-hint: "[filename, directory, or 'all' for r-package/R/]"
allowed-tools: ["Read", "Grep", "Glob", "Write", "Task"]
---

# Review R Scripts

Run the comprehensive R code review protocol.

## Steps

1. **Identify scripts to review:**
   - If `$ARGUMENTS` is a specific `.R` filename: review that file only
   - If `$ARGUMENTS` is a directory: review the `.R` files under it
   - If `$ARGUMENTS` is `all`: review all files in `r-package/R/`

2. **For each script, launch the `r-reviewer` agent** with instructions to:
   - Follow the full protocol in the agent instructions
   - Read `.claude/rules/r-package-conventions.md`, `data-release-conventions.md`, and `cross-language-parity.md`
   - Save report to `quality_reports/audits/[file]_r_review.md`

3. **After all reviews complete**, present a summary:
   - Total issues found per script
   - Breakdown by severity (Critical / High / Medium / Low)
   - Top 3 most critical issues

4. **IMPORTANT: Do NOT edit any R source files.**
   Only produce reports. Fixes are applied after user review.
