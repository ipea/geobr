context("read_addresses")

# skip tests because they take too much time
testthat::skip_on_cran()
skip_if(Sys.getenv("TEST_ONE") != "")


test_that("read_addresses", {

  # a mid-sized municipality (Sete Lagoas, MG): 115,177 addresses
  temp <- read_addresses(year = 2022, code_muni = 3167202, output = "duckdb")
  testthat::expect_true(is(temp, "duckspatial_df"))

  temp <- read_addresses(year = 2022, code_muni = 3167202, output = "arrow")
  testthat::expect_true(is(temp, "ArrowObject"))
  testthat::expect_true(nrow(temp) > 0)

  temp <- read_addresses(year = 2022, code_muni = 3167202, output = "sf")
  testthat::expect_true("sf" %in% class(temp))

  # all addresses belong to the municipality that was requested
  testthat::expect_true(all(temp$code_muni == 3167202))

})


# ERRORS and messages -----------------------
test_that("read_addresses", {

  # `code_muni` is required, and must fail before any download
  testthat::expect_error(read_addresses(year = 2022))
  testthat::expect_error(read_addresses())

  # Wrong code
  testthat::expect_error(read_addresses(year = 2022, code_muni = 9999999))

  # Wrong year
  testthat::expect_error(read_addresses(year = 9999999, code_muni = 3167202))
  testthat::expect_error(read_addresses(year = "xxx", code_muni = 3167202))

  # Wrong output
  testthat::expect_error(
    read_addresses(year = 2022, code_muni = 3167202, output = "banana")
  )

})
