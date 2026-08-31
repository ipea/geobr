---
paths:
  - "python-package/geobr/**/*.py"
  - "python-package/tests/**/*.py"
  - "python-package/helpers/**/*.py"
  - "python-package/pyproject.toml"
  - "python-package/uv.lock"
  - "python-package/CHANGELOG.md"
---

# Python Package Standards (`python-package/`)

**Standard:** `uv sync --frozen` then `uv run pytest -n 2 -m "not network"` passes clean on
py3.10–3.13 across ubuntu / macOS / windows — exactly what
[`.github/workflows/Python-CMD-check.yaml`](../../.github/workflows/Python-CMD-check.yaml) runs.

> **This machine cannot run any of it.** No `python`, `uv`, or `.venv` is installed here. Python work
> is edited and reviewed statically; **CI is the enforcement point**. Never report a Python command as
> having passed locally — say `SKIPPED — no local Python toolchain` and name the CI job that covers it.

---

## 1. Package anatomy

```
python-package/
├── pyproject.toml     # metadata + deps (pdm-backend); hand-edited
├── uv.lock            # GENERATED — regenerate with uv, never hand-edit
├── geobr/
│   ├── __init__.py    # the public surface: re-exports read_*
│   ├── read_*.py      # one public reader per data set
│   ├── utils.py       # metadata sniffing, download, url_solver
│   ├── constants.py   # DataTypes and friends
│   ├── _cache.py      # private: cached_path / is_cached
│   ├── _filter.py     # private: row filtering
│   ├── _output.py     # private: convert_output (sf-equivalent return shaping)
│   └── _duckdb_backend.py  # private: duckdb relation plumbing
├── tests/             # pytest; `network` marker separates online tests
└── helpers/           # dev tooling (diff_packages.py, translate_from_R.py) — not shipped
```

**The cache is persistent, unlike R's.** `_cache.cache_dir()` resolves to `~/.cache/geobr` (or
`$XDG_CACHE_HOME/geobr`), falling back to the system temp dir only when `mkdir` fails. It never
expires and has no size cap, so a stale file under a superseded data release outlives the session.
Route every download through `cached_path()`; never build a path by hand.

**Leading-underscore modules are private.** `_cache`, `_filter`, `_output`, `_duckdb_backend` are
implementation detail: import them inside the package, never re-export them from `__init__.py`, and
do not let a test depend on their internals when a public path exists.

## 2. Dependencies

- Runtime deps go in `[project].dependencies` in `pyproject.toml`; dev-only tooling in
  `[dependency-groups].dev`. `helpers/` deps (`jinja2`, `fire`) are dev, never runtime.
- **CI installs with `uv sync --frozen`.** Editing `pyproject.toml` without regenerating `uv.lock`
  breaks every CI job. A dependency change is a two-file change.
- Respect the declared upper bounds (`geopandas>=1.0.0,<=1.1.2`, `shapely<=2.1.0`). They exist because
  the geo stack breaks on minor releases; widening one needs a deliberate test, not a guess.
- `requires-python = "<4.0,>=3.10"` — no syntax newer than 3.10 (no `match` exhaustiveness
  assumptions, no PEP 695 type params).

## 3. Testing (pytest)

- **The `network` marker is the contract.** Any test that reaches `geobr_prep_data` or `ipea.gov.br`
  is `@pytest.mark.network`. The default suite (`-m "not network"`) must pass with no internet.
- Tests run under `pytest-xdist` (`-n 2`) — no test may depend on execution order or on another
  test's temp files.
- Fixtures live in `tests/conftest.py`; sample payloads in `tests/samples/`. Prefer a sample over a
  live download when the assertion is about parsing, not about the server.
- Every public `read_*` has at least one offline test covering its argument contract (bad code, bad
  year, `simplified` toggle) plus a `network` test for the real fetch.

## 4. Return-type discipline

`read_*` returns a `GeoDataFrame` by default, but the duckdb/arrow path can return other shapes.
Whatever the path, one function returns **one documented type** — route shaping through
`_output.convert_output()` rather than branching on type at the call site. A function that sometimes
returns a `GeoDataFrame` and sometimes a duckdb relation, undocumented, is a bug.

## 5. Red flags

| Red flag | Why | Do instead |
|---|---|---|
| Writing outside `_cache.cache_dir()` | Bypasses the cache contract; may hit a read-only location | `_cache.cached_path()` |
| Inlining `v2.0.0` in a new URL | Fifth copy of a constant that already exists in four places | `GEOBR_DATA_RELEASE` |
| `print()` in library code | Uncontrollable output | `warnings.warn()`, or gate on `verbose` |
| Bare `except:` / `except Exception: pass` | Hides real failures as empty results | Catch the specific error, re-raise with context |
| Returning an empty frame on a failed download | Silent wrong answer | Raise `ConnectionError` / `ValueError` |
| Editing `uv.lock` by hand | CI installs `--frozen` | Regenerate with `uv` |
| New public name not in `__init__.py` | Invisible to users | Export it, or make it `_private` |

## 6. Checklist

```
[ ] pyproject.toml and uv.lock changed together
[ ] New/changed test carries @pytest.mark.network if it touches the network
[ ] Offline suite would pass: no network call outside a marked test
[ ] Public read_* exported from __init__.py; helpers stay _private
[ ] No hardcoded release tag; no writes outside the temp dir
[ ] Return type documented and routed through _output.convert_output()
[ ] R counterpart matched (see cross-language-parity.md)
[ ] CHANGELOG.md updated for a user-facing change
```

## Cross-references

- [`cross-language-parity.md`](cross-language-parity.md) — the R↔Python contract.
- [`data-release-conventions.md`](data-release-conventions.md) — download architecture invariants.
- [`../agents/python-package-reviewer.md`](../agents/python-package-reviewer.md) — the enforcing agent.
- [`../skills/py-package-check/SKILL.md`](../skills/py-package-check/SKILL.md) — the release gate.
