context("read_capitals")

# skip tests because they take too much time
skip_if(Sys.getenv("TEST_ONE") != "")
testthat::skip_on_cran()

# Reading the data -----------------------

test_that("read_capitals", {

  # check sf output
  expect_true(is( read_capitals(), "sf"))

  # check df output
  expect_true(is( read_capitals(output = "arrow"), "ArrowObject"))

  # check df output
  expect_true(is( read_capitals(output = "duckdb"), "duckspatial_df"))

  # `verbose` must reach read_municipal_seat(): it used not to be forwarded,
  # so verbose = FALSE still printed "Using year/date 2010"
  expect_silent(read_capitals(verbose = FALSE, showProgress = FALSE))
  expect_message(read_capitals(verbose = TRUE, showProgress = FALSE))

  # `cache` must reach download_parquet() and still return the full result
  expect_equal(nrow(read_capitals(cache = FALSE, verbose = FALSE, showProgress = FALSE)), 27)

})



# ERRORS and messagens  -----------------------
test_that("read_capitals", {

  # Wrong year
  expect_error(read_capitals(as_sf = 9999999))
  expect_error(read_capitals(showProgress = 9999999))

})
