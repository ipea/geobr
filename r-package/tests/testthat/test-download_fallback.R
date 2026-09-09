# Each test gets its own cache and restores mocked bindings on exit.
local_fallback_cache <- function(.env = parent.frame()) {
  cache_dir <- tempfile("geobr-fallback-")
  dir.create(cache_dir)
  testthat::local_mocked_bindings(
    path_temp = function(...) fs::path(cache_dir, ...),
    .package = "fs", .env = .env
  )
  fs::path(cache_dir, "geobr")
}

for (failure in c("connection", "http", "partial", "missing")) {
  test_that(paste("data fallback recovers from", failure, "failure"), {
    cache_dir <- local_fallback_cache()
    calls <- character()
    expected <- dplyr::tibble(value = 1L)
    testthat::local_mocked_bindings(
      geobr_open_dataset = function(path) arrow::read_parquet(path, mmap = FALSE),
      .package = "geobr"
    )
    testthat::local_mocked_bindings(
      req_perform = function(req, path) {
        calls <<- c(calls, req$url)
        if (length(calls) == 1L) {
          if (failure == "missing") return(invisible(NULL))
          contents <- switch(failure, connection = "", http = "Not Found",
                             partial = "PAR1partial")
          writeBin(charToRaw(contents), path)
          stop("GitHub request failed")
        }
        expect_false(file.exists(path))
        arrow::write_parquet(expected, path)
        invisible(NULL)
      },
      .package = "httr2"
    )

    result <- download_parquet("fallback.parquet", showProgress = FALSE, cache = FALSE)
    expect_equal(result, expected)
    expect_equal(calls, c(
      paste0("https://github.com/ipea/geobr_prep_data/releases/download/",
             geobr_env$data_release, "/fallback.parquet"),
      paste0("https://www.ipea.gov.br/geobr/data_",
             geobr_env$data_release, "/fallback.parquet")
    ))
  })
}

test_that("successful GitHub downloads and valid caches avoid fallback", {
  local_fallback_cache()
  calls <- 0L
  expected <- dplyr::tibble(value = 1L)
  testthat::local_mocked_bindings(
    geobr_open_dataset = function(path) arrow::read_parquet(path, mmap = FALSE),
    .package = "geobr"
  )
  testthat::local_mocked_bindings(
    req_perform = function(req, path) {
      calls <<- calls + 1L
      expect_match(req$url, "https://github.com/", fixed = TRUE)
      arrow::write_parquet(expected, path)
      invisible(NULL)
    },
    .package = "httr2"
  )

  expect_equal(download_parquet("fallback.parquet", FALSE, FALSE), expected)
  expect_equal(download_parquet("fallback.parquet", FALSE, TRUE), expected)
  expect_equal(calls, 1L)
  expect_equal(download_parquet("fallback.parquet", TRUE, FALSE), expected)
  expect_equal(calls, 2L)
})

test_that("both failed downloads clean the cache and return without opening", {
  cache_dir <- local_fallback_cache()
  calls <- 0L
  testthat::local_mocked_bindings(
    geobr_open_dataset = function(...) stop("Must not open a failed download"),
    .package = "geobr"
  )
  testthat::local_mocked_bindings(
    req_perform = function(req, path) {
      calls <<- calls + 1L
      expect_false(file.exists(path))
      writeBin(charToRaw("partial"), path)
      stop("Request failed")
    },
    .package = "httr2"
  )

  expect_message(
    result <- withVisible(download_parquet("fallback.parquet", FALSE, FALSE)),
    "corrupted"
  )
  expect_null(result$value)
  expect_false(result$visible)
  expect_equal(calls, 2L)
  expect_false(file.exists(fs::path(cache_dir, "fallback.parquet")))
})

test_that("an unreadable cached data file is removed and downloaded again", {
  cache_dir <- local_fallback_cache()
  dir.create(cache_dir)
  writeBin(charToRaw("partial"), fs::path(cache_dir, "fallback.parquet"))
  expected <- dplyr::tibble(value = 1L)
  calls <- 0L
  testthat::local_mocked_bindings(
    geobr_open_dataset = function(path) {
      tryCatch(arrow::read_parquet(path, mmap = FALSE), error = function(e) NULL)
    },
    .package = "geobr"
  )
  testthat::local_mocked_bindings(
    req_perform = function(req, path) {
      calls <<- calls + 1L
      expect_false(file.exists(path))
      arrow::write_parquet(expected, path)
      invisible(NULL)
    },
    .package = "httr2"
  )

  expect_equal(download_parquet("fallback.parquet", FALSE, TRUE), expected)
  expect_equal(calls, 1L)
})

for (failure in c("none", "connection", "http", "no assets", "both")) {
  test_that(paste("metadata handles", failure), {
    cache_dir <- local_fallback_cache()
    calls <- character()
    testthat::local_mocked_bindings(
      curl_fetch_memory = function(url) {
        calls <<- c(calls, url)
        if (failure == "both" || (length(calls) == 1L && failure == "connection")) {
          stop("Connection failed")
        }
        if (length(calls) == 1L && failure == "http") {
          return(list(status_code = 503L, content = charToRaw("Unavailable")))
        }
        if (length(calls) == 1L && failure == "no assets") {
          return(list(status_code = 200L, content = charToRaw("<html></html>")))
        }
        href <- if (length(calls) == 1L) {
          "/ipea/geobr_prep_data/releases/download/v2.0.0/country_1872_simplified.parquet"
        } else {
          "country_1872_simplified.parquet"
        }
        list(status_code = 200L, content = charToRaw(paste0('<a href="', href, '">file</a>')))
      },
      .package = "curl"
    )

    if (failure == "both") {
      expect_message(result <- download_metadata2(), "Could not download")
      expect_null(result)
      expect_false(file.exists(fs::path(cache_dir, "metadata_geobr_gpkg.parquet")))
    } else {
      result <- download_metadata2()
      expect_equal(result, data.frame(
        file_name = "country_1872_simplified.parquet",
        geo = "country", year = "1872", simplified = TRUE
      ))
    }
    expect_length(calls, if (failure == "none") 1L else 2L)
    expect_match(calls[1], "https://github.com/", fixed = TRUE)
    if (length(calls) == 2L) {
      expect_equal(calls[2], paste0("https://www.ipea.gov.br/geobr/data_",
                                   geobr_env$data_release, "/"))
    }
  })
}
