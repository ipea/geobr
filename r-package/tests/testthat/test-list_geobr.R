context("list_geobr")

# skip tests because they take too much time
skip_if(Sys.getenv("TEST_ONE") != "")
testthat::skip_on_cran()

# Reading the data -----------------------


test_that("list_geobr", {


  # read data
  df <- list_geobr()

  # check number of cols
  testthat::expect_equal(ncol(df), 4)
  testthat::expect_true(is.data.frame(df))


  df_long <- list_geobr(wide = FALSE)
  testthat::expect_true(nrow(df_long) > 190)

  # every function advertised in the catalogue must exist, and every
  # exported reader must be advertised (regression: read_favelas /
  # read_quilombola_lands were listed but never existed)
  exported_readers <- grep("^read_", getNamespaceExports("geobr"), value = TRUE)
  testthat::expect_equal(sort(df$Function), sort(exported_readers))

  # no data set is left without a year
  testthat::expect_false(any(is.na(df$year)))



})




# ERRORS and messagens  -----------------------
test_that("list_geobr", {

  expect_error(list_geobr(1))
  expect_error(list_geobr('a'))
  expect_error(list_geobr(NA))
  expect_error(list_geobr(c(TRUE, TRUE)))

})

