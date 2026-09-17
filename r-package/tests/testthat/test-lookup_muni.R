context("lookup_muni")

# skip tests because they take too much time
skip_if(Sys.getenv("TEST_ONE") != "")
testthat::skip_on_cran()


# Reading the data -----------------------


test_that("lookup_muni", {

  # read data
  test_sf <- lookup_muni(name_muni = "fortaleza", year = 2010)
  test_sf2 <- lookup_muni(code_muni=2304400, year = 2010)
  test_sf3 <- lookup_muni(name_muni="all", year = 2010)
  test_sf4 <- lookup_muni(code_muni="all", year = 2010)

  # check sf object
  expect_true(is(test_sf, "data.frame"))
  expect_true(is(test_sf2, "data.frame"))
  expect_true(is(test_sf3, "data.frame"))
  expect_true(is(test_sf4, "data.frame"))

  # check number of cols
  expect_true( ncol(test_sf) >= 8)

  # probabilistic
  test_sf5 <- lookup_muni(name_muni="rio de janeira", year = 2022)
  expect_true(is(test_sf5, "data.frame"))

  # probabilistic, name with apostrophe (regression: SQL quoting)
  test_sf6 <- lookup_muni(name_muni = "Santa Barbara d'Oest", year = 2022)
  expect_true(is(test_sf6, "data.frame"))
  expect_true(3545803 %in% test_sf6$code_muni)

})


# ERRORS and messagens  -----------------------
test_that("lookup_muni", {

   expect_error(lookup_muni())

  # Wrong name
   expect_error(lookup_muni(name_muni="arroz", year = 2022))

  # Wrong code
   expect_error(lookup_muni(code_muni=99999999))

   # When using two arguments
   expect_error(lookup_muni(name_muni="fortaleza", code_muni=2304400,year = 2010))
   expect_error( lookup_muni(name_muni="arroz", code_muni=2304400,year = 2010) )

})


