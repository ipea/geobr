── R CMD check results ────────────────────────────────────── geobr 2.0.1 ────
Duration: 13m 16.4s

0 errors ✔ | 0 warnings ✔ | 0 notes ✔

obs. all urls work fine on the browser.

# geobr v2.0.1

**Bug fixes**

- Moves the {arrow} package from "Suggests" to "Imports".
- Fix bug in `read_immediate_region()` which was hardcoded to read state 11 by mistake. Closes [#436](https://github.com/ipea/geobr/issues/436).
- The function `remove_islands()` now correctly drops the arquipelago de Trindade e Martim Vaz
- Fix documentation of arguments `year` and `date`.
- Make the internal function that downloads geobr metadata more robust and removes the dependency from piggyback
- More informative message when a municipality does not have neighborhood data. Closes [#424](https://github.com/ipea/geobr/issues/424).
