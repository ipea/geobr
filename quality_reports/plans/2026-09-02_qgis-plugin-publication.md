# Plan — Publish the geobr plugin to plugins.qgis.org

**Status:** v2 — reconciled with adversarial review. **Read §5 first: §1–§4 contain errors that §5 corrects.**
**Date:** 2026-09-02
**Subject:** `qgis-plugin/geobr_qgis/` → the official QGIS Plugin Repository

---

## 0. Sources

Requirements were read from the official documentation, not from memory:

- [Releasing a plugin](https://docs.qgis.org/latest/en/docs/pyqgis_developer_cookbook/plugins/releasing.html) — folder naming, mandatory files, generated-file exclusions, approval flow
- [Plugin metadata table](https://docs.qgis.org/latest/en/docs/pyqgis_developer_cookbook/plugins/plugins.html) — required vs optional fields
- [Publish a plugin](https://plugins.qgis.org/docs/publish) — approval criteria, rejection reasons, size limit, licence compatibility
- [Migrate your plugin to QGIS 4](https://plugins.qgis.org/docs/migrate-qgis4) — QGIS 4 listing mechanism

---

## 1. Compliance checklist

### 1.1 Already satisfied (verified, not assumed)

| # | Requirement | Evidence |
|---|---|---|
| 1 | Folder name: ASCII, digits, `_`/`-` only, no leading digit | `geobr_qgis` |
| 2 | Mandatory files `metadata.txt`, `__init__.py`, `LICENSE` all present | directory listing |
| 3 | `LICENSE` has **no extension** (an explicit rule — `LICENSE.txt` is non-compliant) | named `LICENSE` |
| 4 | Licence compatible with GPLv2-or-later | MIT — permissive, GPL-compatible |
| 5 | All **required** metadata fields present | `name`, `qgisMinimumVersion`, `description`, `about`, `version`, `author`, `email`, `repository` |
| 6 | Package ≤ 25 MB | ~400 KB total |
| 7 | No binaries shipped | pure Python; duckdb is a *user-installed* dependency, not bundled |
| 8 | No generated/hidden files (`ui_*.py`, `resources_rc.py`, `.gitignore`, `__pycache__`, `.git`) | `find` returned nothing |
| 9 | Name does not contain the word "plugin" | `name=geobr` |
| 10 | Category is one of Raster/Vector/Database/Mesh/Web | `category=Vector` |
| 11 | External dependency **declared in `about`** with an install command — this is the explicit rule for pip dependencies | `about=... Requires the geobr Python package: python -m pip install --user geobr` |
| 12 | QGIS 4 listing mechanism | `qgisMaximumVersion=4.99` — this, not `supportsQt6`, is what puts a plugin in the "QGIS 4 Ready" list |
| 13 | `supportsQt6` **absent** — the flag was removed from QGIS core and is no longer recognised | not present |
| 14 | Qt5/Qt6 portability via the `qgis.PyQt` shim rather than direct PyQt5 imports | verified running on QGIS 3.42.1 (Qt5) **and** 4.2.1 (Qt6) with no code change |
| 15 | Cross-platform code (no OS-specific calls) | `os.path`, `importlib`, `ast` only |
| 16 | English comments, PEP8-ish layout | source review |
| 17 | Public source repository, not a zip | GitHub |
| 18 | Works — the actual bar | 31 algorithms; `read_municipality CODE_MUNI=33` → 92; GUI confirmed by maintainer |

### 1.2 Not yet satisfied — blocking

| # | Gap | Why it matters | Fix |
|---|---|---|---|
| B1 | **`repository` URL is wrong** — `github.com/ipea/geobr`; the real remote is `github.com/ipea/geobr` | A dead repository link is an explicit rejection reason. (The same wrong URL is in `python-package/pyproject.toml` — worth fixing there too, separately.) | point at `https://github.com/ipea/geobr` |
| B2 | **`homepage` points at the R package's pkgdown site**, which documents the R package, not this plugin | ~~"any other links will result in the plugin being rejected"~~ — **that quote was fabricated; see §5.1.** The actual rule only asks for "a valid link to the homepage (the URL should either point to a page describing plugin usage or the README/wiki in your repository)". A pkgdown site for the R package is a weak choice, **not** a rejection trigger. **Demoted to SHOULD.** | point at `https://github.com/ipea/geobr/tree/master/qgis-plugin` (the plugin README) |
| B3 | **No `README` inside the plugin folder** — it lives at `qgis-plugin/README.md`, one level up, so it is not in the ZIP | "Include README and LICENSE files"; minimal documentation is an approval criterion | move/copy `README.md` into `geobr_qgis/` |
| B4 | **`icon=icon.svg`** but the metadata table specifies a **PNG/JPEG** for this field | The website renders this icon; SVG may not display in the repository listing | ship `icon.png` for `metadata.txt`; keep `icon.svg` for the in-app provider icon (Qt renders it correctly — verified) |
| B5 | **No `changelog` field** | Expected for a released plugin; users see it in the Plugin Manager | add a `changelog` block for 0.1.0 |
| B6 | **`read_health_region` returns wrong data** — ignores `geometry_level`, giving 92 features at every level | Shipping a publicly listed algorithm that silently returns the wrong geometry is worse than not shipping it | fix in geobr, or hide that one algorithm in v1 (see §3, D3) |

### 1.3 Not yet satisfied — non-blocking but review-visible

| # | Gap | Note |
|---|---|---|
| N1 | Guidance says use `QgsNetworkAccessManager` rather than `requests` | The plugin itself makes no HTTP calls — **geobr** does, and we cannot change that from here. The practical reason for the rule (QGIS proxy settings being ignored) is already mitigated by `apply_qgis_proxy()`. Worth stating in the submission notes rather than pretending it doesn't apply. |
| N2 | `qgis_process` exits with a crash code after a run (upstream duckdb) | Desktop app unaffected (confirmed). Document in the README; disclose in submission notes. |
| N3 | No tests for the plugin itself | Not an approval requirement. |
| N4 | `experimental=True` | Correct for a first release; means users must tick "show experimental plugins". |

---

## 2. Actions, in order

**Phase 1 — fix metadata and packaging (me)**

1. `repository` → `https://github.com/ipea/geobr` (B1)
2. `homepage` → the plugin folder URL (B2)
3. Move `README.md` into `geobr_qgis/` (B3)
4. Generate `icon.png` from `icon.svg` via Qt's renderer (already proven to rasterise correctly), set `icon=icon.png` (B4)
5. Add a `changelog` block (B5)
6. Resolve B6 — fix or hide `read_health_region`

**Phase 2 — build and validate the package (me)**

7. Build `geobr_qgis.zip` with `geobr_qgis/` at the ZIP root, excluding `__pycache__`, `.git`, `*.pyc`
8. Validate by installing the ZIP into a **clean QGIS profile** and confirming 31 algorithms load — this is the only test that exercises what a real user downloads
9. Re-run the headless smoke test from that clean profile

**Phase 3 — submit (maintainer)**

10. Obtain an **OSGeo ID** (osgeo.org) — required, and only you can do this
11. Upload at `plugins.qgis.org/plugins/add/`
12. Wait for staff approval; respond to reviewer comments

---

## 3. Decisions I need from you

| | Decision | Recommendation |
|---|---|---|
| D1 | `email` is currently your personal Gmail, and is visible to any logged-in user on plugins.qgis.org | Consider an institutional or shared address |
| D2 | `author` — "Rafael H. M. Pereira, Ipea" credits one person; geobr has six package authors | Decide whether to credit the geobr team |
| D3 | **`read_health_region`**: fix the geobr bug now, or ship v1 without that algorithm? | Fix in geobr — but that is a Python-package change with an R-parity question, so it is your call |
| D4 | Publish under your account, or an Ipea/ipea organisational account? | Organisational, for continuity |

---

## 4. Risks

| Risk | Mitigation |
|---|---|
| Reviewer objects to the pip dependency | The rule explicitly permits it when declared in `about` with install guidance — which we do. Cite that in submission notes. |
| Reviewer objects to `requests` usage (N1) | Disclose up front; explain it is in the upstream library and that QGIS proxy settings are bridged. |
| Name collision | No `geobr` plugin found in the repository search; the name looks free but this was not exhaustively confirmed. |
| `version` must be unique across submissions | First upload, so `0.1.0` is safe; never re-upload the same number. |

---

## 5. Reconciliation with the adversarial review — v2 (this is what gets executed)

### 5.1 The plan misquoted its own source

§1.2 B2 presented `"any other links will result in the plugin being rejected"` as a quoted rule.
**That sentence does not exist on the publish page.** It came from a search-engine summary and was
propagated into the plan as if it were verbatim documentation. The real text is:

> "The plugin metadata contains a valid link to the homepage (the URL should either point to a page
> describing plugin usage or the README/wiki in your repository), the repository (source code —
> should be publicly accessible and should not contain zipped files), the tracker (issue tracker)
> and a license."

A plan headed "verified, not assumed" that invents a quotation is worse than one that says
"unverified". B2 is demoted to SHOULD, the quote is struck, and every remaining claim below was
re-checked against primary sources before being accepted.

Same failure mode, smaller: B1 said the wrong `repository` URL was "dead". It is not —
`github.com/ipea/geobr` **redirects** to `ipea/geobr`, and the uploader's check is an HTTP HEAD
that a 301 passes. Still worth correcting to the canonical URL, but **cosmetic, not blocking**.

### 5.2 Verified against the QGIS-Django source (not the prose docs)

The website's uploader is the real gatekeeper, and it disagrees with the documentation table.
Confirmed by reading `qgis-app/plugins/validator.py` and `models.py`:

| Finding | Consequence |
|---|---|
| `PLUGIN_REQUIRED_METADATA = ("name", "description", "version", "qgisMinimumVersion", "author", "email", "about", "tracker", "repository")` | **`tracker` is REQUIRED**, though the docs table marks it optional — and ours carries the same stale `ipea` org. New blocker. |
| `PLUGIN_OPTIONAL_METADATA` includes **`external_deps`** | The site's own field for exactly our situation. Add `external_deps=geobr`. |
| `icon = models.ImageField(...)` | Pillow-backed — **SVG will not validate**. A raster icon is mandatory for `metadata.txt`, not merely "web friendly". |
| `package_name` is `unique=True, editable=False`; `name` is `unique=True` | `geobr_qgis` and `geobr` are **permanent and site-wide** after the first upload. Account ownership must be settled *before* uploading. |
| Rejects `.pyc`, `__MACOSX`, `.git`, `__pycache__`; requires one PEP8 top-level folder; validates URLs by HEAD | Packaging rules are enforced, not advisory. |

### 5.3 The real technical error: `qgisMinimumVersion=3.22` is a false promise

Never tested below 3.42.1 — and worse, **QGIS 3.22-era builds bundle Python 3.9**, while
`python-package/pyproject.toml` declares `requires-python = "<4.0,>=3.10"`. On our own declared
floor the sole mandatory dependency **cannot be installed at all**: the user would get a plugin that
registers zero algorithms plus a message-bar instruction to run a pip command that then refuses.

**Raise the floor to `3.40`** — the current LTR, Python 3.12, closest to what was actually tested.

### 5.4 Two defects the plan missed entirely

- **The `about` install command contradicts our own README.** `about` says
  `python -m pip install --user geobr`; `README.md` correctly says that this must run under *QGIS's*
  Python (`python-qgis.bat` on Windows), not a system Python. `about` is the one text a reviewer and
  every Plugin Manager user reads. Rewrite it, and name `duckdb`/`rapidfuzz` explicitly.
- **`LICENSE` is a verbatim copy of geobr's**, reading `Copyright (c) 2020 Institute for Applied
  Economic Research (Ipea)` on a work authored in 2026. Update the year span.

### 5.5 B6 resolved better than either option the plan offered

The plan framed `read_health_region` as "fix geobr, or hide the algorithm". Both are wrong.
**Suppress the broken *parameter*, not the algorithm** — `municipality` results are correct; only
`micro`/`macro` fail to aggregate. A per-reader skip entry in `algorithm.py` (~3 lines) stops QGIS
offering a knob that does nothing, while the working dataset still ships:

```python
_SKIP_PER_READER = {"read_health_region": {"geometry_level"}}
```

**Not a publication blocker either way** — staff approval is a packaging and code-hygiene review,
not a data audit, and the bug ships to every PyPI/CRAN geobr user already. Fixing it upstream stays
the right long-term move, but it must not gate the upload.

### 5.6 Cuts accepted

- **Action 3 (move README into the package) — CUT.** The validator requires `__init__.py`,
  `metadata.txt`, `LICENSE`; not README. Plugin Manager shows `about`, not a bundled README, and a
  second copy of a 7.6 KB document would drift. Pointing `homepage` at it satisfies the rule.
- **Action 9 (re-run headless data tests from the clean profile) — CUT.** Re-verifies data already
  verified on two QGIS versions. Zero new information.
- **Action 8 — KEPT but scoped down** to a structural check: unzip → fresh profile → confirm 31
  algorithms register. It is the only test of the artefact actually uploaded.
- **D1/D2/D3 dropped as decision gates.** Only **D4 (personal vs ipea account)** is a real
  decision, and it is now *first*, because `package_name` is permanent.

### 5.7 Overridden — `icon.svg` stays in the package

The reviewer wanted `icon.svg` deleted, arguing it is 380 KB of a ~400 KB package. **Rejected.** The
limit is **25 MB**; 380 KB is 1.5% of it, so "93% of the package" is a percentage of a number too
small to matter. `metadata.txt` must point at a raster (§5.2), but `provider.icon()` benefits from a
DPI-independent SVG in the toolbox, and Qt renders it correctly (verified at 64 px and 256 px).
**Ship both:** `icon.png` generated from `icon.svg`, with the SVG remaining the source of truth.

### 5.8 Final action list

**Blocking on the maintainer, start now**

1. **[maintainer]** Decide **D4** — publish under your account or an `ipea` org account.
   `package_name` is permanent and the uploading account owns the plugin.
2. **[maintainer]** Register an **OSGeo ID** — the only step with external latency.

**Metadata and code — one pass [me]**

3. `metadata.txt`: fix `repository` **and `tracker`** → `ipea`; `homepage` → the plugin folder;
   `qgisMinimumVersion=3.40`; add `changelog`; add `external_deps=geobr`;
   `hasProcessingProvider=True`; rewrite the `about` install sentence.
4. `LICENSE`: copyright year → `2020-2026`.
5. Icon: render `icon.png` (256 px) from `icon.svg`; `icon=icon.png`; keep the SVG for `provider.icon()`.
6. `algorithm.py`: `_SKIP_PER_READER` for `read_health_region.geometry_level`; one README line.
7. `README.md`: fix the stale `ipea/geobr` link — it is about to become the homepage.

**Package and submit**

8. **[me]** Build `geobr_qgis.zip`: one top-level `geobr_qgis/`, no `__pycache__`/`.pyc`/`.git`.
9. **[me]** Unzip into a fresh profile; confirm 31 algorithms register. Structure only.
10. **[maintainer]** Upload. Expect a `pyqgis4-checker` report flagging Qt5-era enum access
    (`QgsProcessingParameterNumber.Integer`) — **informational, does not block approval**.
11. **[maintainer]** Disclose in submission notes: the pip dependency with the corrected install
    command, `requests` living in the upstream library plus our proxy bridge, and the `qgis_process`
    teardown crash. B6 needs no caveat — step 6 handles it.

---

## 6. Execution record (2026-09-02)

All maintainer-independent steps are done. `LICENSE` was **not** changed: the maintainer directed
that the copyright holder match the sibling packages, and it already does — the plugin's line is
`Copyright (c) 2020 Institute for Applied Economic Research (Ipea)`, verbatim from
`python-package/LICENSE.txt`, with R using the same holder in its own template form
(`YEAR: 2019 / COPYRIGHT HOLDER: Ipea`). The reviewer's proposed year-bump to `2020-2026` was
**rejected**, because it would have broken exactly the consistency that was asked for.

| Step | Change | Verified |
|---|---|---|
| 3 | `metadata.txt`: `repository` **and `tracker`** → `ipea`; `homepage` → the plugin folder; `qgisMinimumVersion` `3.22` → **`3.40`**; `icon` → `icon.png`; `hasProcessingProvider` → `True`; added `external_deps=geobr` and a `changelog`; rewrote the `about` install sentence to name QGIS's own Python plus `duckdb`/`rapidfuzz` | plugin loads and parses |
| 4 | `LICENSE` — no change (see above) | matches python-package |
| 5 | `icon.png` rendered from `icon.svg` at 256 px, transparent background, 33 KB; SVG kept as the source of truth and for `provider.icon()` | rendered and visually checked |
| 6 | `_SKIP_PER_READER` in `algorithm.py` suppresses `geometry_level` on `read_health_region` only | `GEOMETRY_LEVEL` absent from that reader; `ZONE` still present on `read_census_tract`, proving the skip is scoped |
| 7 | `README.md`: stale `ipea/geobr` link → `ipea`; health-region limitation rewritten to describe the new behaviour | — |
| 8 | Built `geobr_qgis.zip` — **91 KB**, 7 files, single top-level `geobr_qgis/`, no `__pycache__`/`.pyc`/`.git` | listed archive contents |
| 9 | Installed the ZIP into an **isolated profile** (`QGIS_CUSTOM_CONFIG_PATH`) — the artefact a user actually downloads | **31 algorithms**; `read_health_region YEAR=2013 CODE_STATE=RJ` → 92 features, MultiPolygon |

The maintainer's live QGIS 4.2.1 profile was re-synced afterwards and also reports 31 algorithms.

**Package:** `<scratchpad>/geobr_qgis.zip` — a build artifact, deliberately not committed.

### Still open — maintainer only

1. **D4:** publish under a personal or `ipea` account. `package_name` is `editable=False` and
   unique site-wide, so this is permanent from the first upload.
2. Register an **OSGeo ID**.
3. Upload, and disclose in the submission notes: the pip dependency with the corrected install
   command, `requests` living in upstream geobr plus the plugin's proxy bridge, and the
   `qgis_process` teardown crash. Expect an informational `pyqgis4-checker` report about Qt5-era
   enum access; it does not block approval.

---

## 7. Correction: the org is `ipea`, not `ipea` (2026-09-02)

**§5.2 and §6 had this backwards, and so did B1.** Verified by resolving the redirect:

```
https://github.com/ipea/geobr  ->  301  ->  https://github.com/ipea/geobr   (final)
https://github.com/ipea/geobr     ->  200, direct, no redirect
```

Redirects point **old -> new**, so `ipea` is the current organisation and `ipea` is the legacy
name GitHub still forwards. B1 was not just mis-severitised, it was **inverted**: `metadata.txt`
was already correct before I "fixed" it, and `python-package/pyproject.toml` — which I flagged as a
loose end needing the same correction — was right all along.

**Root cause of the error:** I inferred the canonical org from `git remote get-url origin`, which
still reads `ipea/geobr`. A remote URL is not updated by an organisation rename; it keeps
working purely because of the redirect. It is evidence of what the clone was created from, never of
what the canonical URL is today. The redirect direction is the authority.

All three plugin URLs are now `ipea`, and the ZIP was rebuilt and redeployed (31 algorithms).

Note `MEMORY.md:91` and `quality_reports/plans/floating-launching-stream.md:178` both claim
`pyproject.toml` declares `ipea`. It declares `ipea`. Those entries are stale.

### 7.1 New blocker found while re-validating: `homepage` 404s

The uploader validates `repository`, `tracker` and `homepage` with an HTTP HEAD and rejects
anything returning >= 400. Checked as the uploader would:

| URL | Status |
|---|---|
| `https://github.com/ipea/geobr` | 200 |
| `https://github.com/ipea/geobr/issues` | 200 |
| `https://github.com/ipea/geobr/tree/master/qgis-plugin` | **404** |

The homepage points into a directory that **does not exist on GitHub yet**, because `qgis-plugin/`
is still untracked locally.

**Therefore: the plugin must be committed and pushed before the upload.** This is a hard ordering
dependency that neither the original plan nor the adversarial review caught — both treated the
upload as independent of the repository state. Add it to §5.8 as the step immediately preceding
"upload".

### 7.2 Also fixed

`README.md` still advertised "Requires QGIS 3.22+" after `metadata.txt` moved to `3.40`. Corrected,
with the reason stated (geobr needs Python >= 3.10; QGIS < 3.40 ships Python 3.9).

---

## 8. Decisions settled (2026-09-02)

| | Decision | Outcome |
|---|---|---|
| D1 `email` | personal vs institutional | **Keep** `rafa.pereira.br@gmail.com` — maintainer declined |
| D2 `author` | individual vs collective/institutional | **Keep** `Rafael H. M. Pereira, Ipea` — maintainer declined |
| D3 `read_health_region` | fix upstream vs hide | Neither — the broken **parameter** is suppressed (§5.5); geobr fix stays a separate task |
| Org name | `ipeaGIT` vs `ipea` | **`ipea`** — repo, docs domain, pkgdown `url:` and the git remote all normalised (§7) |

Recorded in `MEMORY.md` under "Settled decisions" so D1/D2 are not re-proposed.

### Still open

1. **D4 — publish under a personal or `ipea` organisation account.** `package_name` is
   `editable=False` and unique site-wide, so it is permanent from the first upload.
2. **Register an OSGeo ID.**
3. **Commit and push `qgis-plugin/`** — `homepage` currently 404s because the directory exists only
   locally, and the uploader rejects a homepage returning >= 400. This is a hard prerequisite for
   submission, not hygiene.
