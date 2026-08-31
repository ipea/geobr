---
paths:
  - "r-package/R/**/*.R"
  - "r-package/NAMESPACE"
  - "python-package/geobr/**/*.py"
---

# R ↔ Python Parity

**geobr is one package implemented twice.** Users move between the R and Python versions expecting
the same function names, the same arguments, and the same data. Parity is the product promise; drift
between the two is a defect even when both sides work.

---

## 1. The contract

For every data set geobr exposes:

1. **Same function name.** `read_municipality()` in R ↔ `read_municipality()` in Python.
   **There are no function-name exceptions** — every exported reader has an identically named
   Python counterpart. Two R *files* are named differently from the functions they define
   (`read_favelas.R` defines `read_favela`; `read_quilombos.R` defines `read_quilombola_land`),
   which makes any filename-based comparison report two false gaps. Compare **exported names**
   (`NAMESPACE` vs `geobr/__init__.py`), not filenames.
2. **Same argument names and defaults** — `year`, `code_*`, `simplified`, `output`, `showProgress`,
   `cache`, `verbose`. An argument added on one side is unfinished until it lands on the other.
3. **Same metadata key.** Both sides resolve the same `geo` value against the same metadata table, so
   both land on the same asset file.
4. **Same supported years.** Divergence here usually traces to the release-resolution divergence in
   [`data-release-conventions.md`](data-release-conventions.md) §3, not to a data bug.

## 2. When parity may lag — and how to record it

Parity does not have to land in the same commit, but an intentional gap must be **written down**, not
discovered later:

- Note it in the commit/PR body and in the lagging package's changelog (`r-package/NEWS.md` or
  `python-package/CHANGELOG.md`).
- Open the follow-up before closing the first side.

The failure mode is the silent gap: the R package gains an argument, the shared documentation implies
the same API, and a Python user discovers the difference as a `TypeError`.

## 3. Checking

```bash
# read_* modules present in r-package/R but missing from python-package/geobr
cd python-package && python helpers/diff_packages.py
```

That helper is a **filename set-difference only** — it catches a missing module, never an
argument-level mismatch. Argument drift needs both implementations read side by side, which is what
[`/parity-check`](../skills/parity-check/SKILL.md) does.

`helpers/translate_from_R.py` scaffolds a Python reader from its R counterpart, parsing the roxygen
block and the `select_metadata(geography=)` key. Useful for a first draft; its output is a starting
point, not a reviewed implementation.

## 4. What is *not* required to match

Idiom stays native to each language. Parity is about the **public API and the data**, not internals:

- R returns `sf`; Python returns a `GeoDataFrame`. Correct, not a divergence.
- R uses arrow plus `dplyr` verbs; Python uses duckdb relations and pandas. Fine.
- R `cli` messages and Python exceptions differ in form. Both must be actionable; neither has to
  match the other's wording.
- Test counts need not match. Coverage of the public contract must.

Do not refactor one language toward the other's idiom in the name of parity.

## 5. Checklist for a public API change

```
[ ] Function exists on both sides, or the gap is in the changelog with a follow-up
[ ] Argument names and defaults identical
[ ] Same metadata geo key, so the same asset resolves
[ ] Docs updated on both sides (roxygen + docstring)
[ ] r-package/NEWS.md and python-package/CHANGELOG.md reflect the user-facing change
[ ] helpers/diff_packages.py reports no new gap
```

## Cross-references

- [`../skills/parity-check/SKILL.md`](../skills/parity-check/SKILL.md) — the argument-level check.
- [`data-release-conventions.md`](data-release-conventions.md) — why supported years can diverge.
- [`python-package-conventions.md`](python-package-conventions.md) · [`r-package-conventions.md`](r-package-conventions.md)
