#' Download spatial data of Brazil's national borders
#'
#' @description
#' National borders
#'
#' @template year
#' @template simplified
#' @template output
#' @template showProgress
#' @template cache
#' @template verbose
#'
#' @return An `"sf" "data.frame"` OR an `ArrowObject`
#'
#' @export
#'
#' @examplesIf identical(tolower(Sys.getenv("NOT_CRAN")), "true")
#' # Read specific year
#' br_1872 <- read_country(year = 1872)
#'
#' br_2025 <- read_country(year = 2025)

read_country <- function(year,
                         simplified = TRUE,
                         output = "sf",
                         showProgress = TRUE,
                         cache = TRUE,
                         verbose = TRUE){

  # Get metadata with data url addresses
  temp_meta <- select_metadata(
    geography="country",
    year = year,
    simplified = simplified,
    verbose = verbose
  )

  # check if metadata download failed
  if (is.null(temp_meta)) { return(invisible(NULL)) } # nocov

  # download file and open arrow dataset
  temp_arrw <- download_parquet(
    filename_to_download = temp_meta$file_name,
    showProgress = showProgress,
    cache = cache
  )

  # check if download failed
  if (is.null(temp_arrw)) { return(invisible(NULL)) }

  # convert to sf
  temp <- convert_output(temp_arrw, output)

  return(temp)

}
