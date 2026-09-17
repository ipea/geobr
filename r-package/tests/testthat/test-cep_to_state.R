context("cep_to_state")

# skip tests because they take too much time
skip_if(Sys.getenv("TEST_ONE") != "")
testthat::skip_on_cran()


# Reading the data -----------------------


test_that("cep_to_state", {

  # check output
  expect_equal( cep_to_state(cep = '01001-000'), "SP")
  expect_equal( cep_to_state(cep = '69900000'), "AC")
  expect_equal( cep_to_state(cep = '69900-000'), "AC")
  expect_equal( cep_to_state(cep = '70233020'), "DF")
  expect_equal( cep_to_state(cep = '30130-000'), "MG")
  expect_equal( cep_to_state(cep = '39999999'), "MG")

})


# ERRORS and messagens  -----------------------
test_that("cep_to_state", {

  expect_error( cep_to_state(cep = 'aaaa') )
  expect_error( cep_to_state(cep = 'a999a') )
  expect_error( cep_to_state(cep = 70233020))
  expect_error( cep_to_state(cep = 123) )
  expect_error( cep_to_state() )


})


