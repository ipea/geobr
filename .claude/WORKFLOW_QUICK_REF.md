# Workflow Quick Reference — geobr

**Model:** Contractor (you direct, Claude coordinates)

---

## The Loop

```
Your instruction
    ↓
[PLAN] (if multi-file or unclear) → Show plan → Your approval
    ↓
[EXECUTE] Implement, run the real gate, report the real output
    ↓
[REPORT] What passed, what was skipped and why
    ↓
Repeat
```

---

## I Ask You When

- **Design forks:** "Pin Python to the release tag, or unpin R? Which?"
- **Parity decisions:** "This argument lands on the R side now. Ship the Python side in this change, or record the gap?"
- **API ambiguity:** "This changes an exported signature. Deprecation cycle, or breaking bump?"
- **Scope:** "Also fix the duplicated release constant while here, or stay on task?"
- **Anything touching package source that users depend on.**

## I Just Execute When

- The fix is obvious (bug, typo, pattern application)
- Running verification (tests, `R CMD check`, doc regeneration)
- Documentation, session logs, plans
- Reporting results

---

## The Gate

There is no numeric quality score in this repo. The gate is the **touched package's test suite**:

| Changed | Gate |
|---|---|
| `r-package/**` | `devtools::document()` drift check + `devtools::test()` |
| `python-package/**` | `uv run pytest -m "not network"` — or an explicit `SKIPPED` |
| config / docs only | No test gate |

**A missing toolchain is a SKIP, never a PASS.**

---

## Non-Negotiables

- **Writes go to the cache and nowhere else.** R: session temp dir. Python: `~/.cache/geobr`
  (persistent). Never the working directory or the package library.
- **No hardcoded release tag in a new URL.** Use `geobr_env$data_release` / `GEOBR_DATA_RELEASE`.
- **Network tests carry `skip_on_cran()`** (R) and `@pytest.mark.network` (Python). The R suite
  needs a live connection locally; that is deliberate.
- **Failures are loud.** Never return an empty `sf` / `GeoDataFrame` to signal a problem.
- **`man/`, `NAMESPACE`, `uv.lock`, and `docs/` are generated.** Regenerate; never hand-edit.
- **Parity is the product promise.** A public API change on one side is unfinished until the other
  matches or the gap is recorded in a changelog.
- **No `library()` in `r-package/R/`.** Namespaced imports only.

---

## Environment Facts

- **R 4.6.1** available. **No `python`, `uv`, `gh`, or `conda`** on this machine.
- Python work is edit-and-CI: reviewed statically here, verified by `Python-CMD-check.yaml`.
- Default branch **`master`**; remote `ipea/geobr`. `/commit` pushes, never merges.

---

## Preferences

**Reporting:** Concise. Real command output over prose summary. Say what was skipped.
**Code changes:** Minimum necessary to address the request. No adjacent refactors.
**Session logs:** Always — post-plan, incremental, end-of-session.
**Parity gaps:** Flag every one; never let one pass silently.

---

## Next Step

You provide task → I plan (if needed) → Your approval → Execute → Report.
